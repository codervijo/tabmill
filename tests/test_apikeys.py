from __future__ import annotations

import json
import stat
from pathlib import Path

import httpx
import pytest

from tabmill import apikeys, preflight


@pytest.fixture(autouse=True)
def _clean_env(monkeypatch: pytest.MonkeyPatch) -> None:
    for k in apikeys.KNOWN_KEYS:
        monkeypatch.delenv(k, raising=False)


def test_set_update_delete_preserve_comments(tmp_path: Path) -> None:
    (tmp_path / "tabmill.env").write_text("# creds\nCWS_PUBLISHER_ID=old\n\nOTHER=x\n")
    assert apikeys.set_key(tmp_path, "CWS_PUBLISHER_ID", "new") is True
    assert apikeys.set_key(tmp_path, "CWS_CLIENT_ID", "cid") is False
    text = (tmp_path / "tabmill.env").read_text()
    assert text == "# creds\nCWS_PUBLISHER_ID=new\n\nOTHER=x\nCWS_CLIENT_ID=cid\n"
    assert stat.S_IMODE((tmp_path / "tabmill.env").stat().st_mode) == 0o600
    assert apikeys.delete_key(tmp_path, "OTHER") is True
    assert apikeys.delete_key(tmp_path, "OTHER") is False
    assert apikeys.read(tmp_path) == {"CWS_PUBLISHER_ID": "new", "CWS_CLIENT_ID": "cid"}


def test_mask() -> None:
    assert apikeys.mask("CWS_PUBLISHER_ID", "abc") == "abc"
    assert apikeys.mask("CWS_REFRESH_TOKEN", "1//0abcdefghijklmnop") == "1//0…mnop"
    assert apikeys.mask("CWS_CLIENT_SECRET", "short") == "••••"


def _http(handler: object) -> httpx.Client:
    return httpx.Client(transport=httpx.MockTransport(handler))  # type: ignore[arg-type]


def test_probe_missing_everything(tmp_path: Path) -> None:
    results = apikeys.probe_all(tmp_path, None, _http(lambda r: httpx.Response(500)))
    assert {r.status for r in results.values()} == {"missing"}


def test_probe_oauth_valid_and_publisher(tmp_path: Path) -> None:
    for k, v in {
        "CWS_PUBLISHER_ID": "pub",
        "CWS_CLIENT_ID": "i",
        "CWS_CLIENT_SECRET": "s",
        "CWS_REFRESH_TOKEN": "r",
    }.items():
        apikeys.set_key(tmp_path, k, v)

    def handle(req: httpx.Request) -> httpx.Response:
        if req.url.host == "oauth2.googleapis.com":
            return httpx.Response(200, json={"access_token": "t"})
        return httpx.Response(200, json={"itemId": "item1"})

    results = apikeys.probe_all(tmp_path, "item1", _http(handle))
    assert results["CWS_REFRESH_TOKEN"].status == "valid"
    assert results["CWS_PUBLISHER_ID"].status == "valid"
    no_item = apikeys.probe_all(tmp_path, None, _http(handle))
    assert no_item["CWS_PUBLISHER_ID"].status == "not-testable"


def test_probe_bad_token_and_bad_key_file(tmp_path: Path) -> None:
    apikeys.set_key(tmp_path, "CWS_SA_KEY_FILE", str(tmp_path / "key.json"))
    (tmp_path / "key.json").write_text(json.dumps({"type": "authorized_user"}))
    results = apikeys.probe_all(tmp_path, None, _http(lambda r: httpx.Response(400)))
    assert results["CWS_SA_KEY_FILE"].status == "invalid"
    assert "not a service-account key" in results["CWS_SA_KEY_FILE"].detail


def test_preflight_x11_and_workspace(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("DISPLAY", raising=False)
    assert preflight.x11().status == "fail"
    assert preflight.workspace(None).status == "fail"
    assert "source ~/.profile" in preflight.workspace(None).detail
