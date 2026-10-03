from __future__ import annotations

import json
from pathlib import Path

import httpx
import pytest

from tabmill import cws


def _client(handler: httpx.MockTransport) -> cws.Client:
    return cws.Client("pub1", "tok", httpx.Client(transport=handler))


def test_upload_publish_status_requests(tmp_path: Path) -> None:
    seen: list[tuple[str, str, bytes]] = []

    def handle(req: httpx.Request) -> httpx.Response:
        seen.append((req.method, str(req.url), req.content))
        assert req.headers["Authorization"] == "Bearer tok"
        if req.url.path.endswith(":upload"):
            return httpx.Response(200, json={"uploadState": "SUCCEEDED"})
        if req.url.path.endswith(":publish"):
            return httpx.Response(200, json={})
        return httpx.Response(
            200, json={"submittedItemRevisionStatus": {"state": "PENDING_REVIEW"}}
        )

    z = tmp_path / "x.zip"
    z.write_bytes(b"PK")
    c = _client(httpx.MockTransport(handle))
    assert c.upload("item1", z)["uploadState"] == "SUCCEEDED"
    c.publish("item1", staged=True)
    status = cws.summarize(c.fetch_status("item1"))
    assert status["review_state"] == "PENDING_REVIEW"
    up, pub, st = seen
    assert up[1] == f"{cws.API}/upload/v2/publishers/pub1/items/item1:upload?uploadType=media"
    assert up[2] == b"PK"
    assert pub[1].endswith("/v2/publishers/pub1/items/item1:publish")
    assert json.loads(pub[2]) == {"publishType": "STAGED_PUBLISH"}
    assert st[0] == "GET" and st[1].endswith(":fetchStatus")


@pytest.mark.parametrize(
    ("code", "status", "needle", "transient"),
    [
        (401, "UNAUTHENTICATED", "credentials rejected", False),
        (403, "PERMISSION_DENIED", "Dashboard → Account", False),
        (404, "NOT_FOUND", "store_id", False),
        (429, "RESOURCE_EXHAUSTED", "rate limited", True),
        (503, "UNAVAILABLE", "retry later", True),
        (400, "INVALID_ARGUMENT", "rejected the request", False),
    ],
)
def test_errors_map_to_remedies(code: int, status: str, needle: str, transient: bool) -> None:
    body = {"error": {"code": code, "status": status, "message": "boom"}}
    c = _client(httpx.MockTransport(lambda req: httpx.Response(code, json=body)))
    with pytest.raises(cws.CwsError, match=needle) as err:
        c.fetch_status("item1")
    assert err.value.transient is transient


def test_oauth_refresh_token(monkeypatch: pytest.MonkeyPatch) -> None:
    def handle(req: httpx.Request) -> httpx.Response:
        assert b"grant_type=refresh_token" in req.content
        return httpx.Response(200, json={"access_token": "abc"})

    env = {"CWS_CLIENT_ID": "i", "CWS_CLIENT_SECRET": "s", "CWS_REFRESH_TOKEN": "r"}
    assert cws.access_token(env, httpx.Client(transport=httpx.MockTransport(handle))) == "abc"


def test_missing_credentials_names_fix() -> None:
    with pytest.raises(cws.CwsError, match="CWS_SA_KEY_FILE"):
        cws.access_token({}, httpx.Client())


def test_env_file_and_override(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    (tmp_path / ".env").write_text("# c\nCWS_PUBLISHER_ID='p1'\nCWS_CLIENT_ID=i\n")
    monkeypatch.setenv("CWS_CLIENT_ID", "from-env")
    env = cws.load_env(tmp_path)
    assert env["CWS_PUBLISHER_ID"] == "p1" and env["CWS_CLIENT_ID"] == "from-env"
