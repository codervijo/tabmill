from __future__ import annotations

import json
import shutil

import pytest

from tabmill import hub, registry
from tabmill.config import TOOL_DIR, Config

SLUG = "save-page-pdf-md"


@pytest.fixture
def setup(cfg: Config) -> Config:
    shutil.copytree(TOOL_DIR / "recipes" / SLUG, cfg.tool_dir / "recipes" / SLUG)
    cfg.workspace.mkdir(parents=True)
    return cfg


def _set_landing(cfg: Config, url: str) -> None:
    path = cfg.tool_dir / "recipes" / SLUG / "extension.yaml"
    path.write_text(path.read_text().replace('landing_page_url: ""', f"landing_page_url: {url}"))


def test_skips_without_store_or_tool_page(setup: Config) -> None:
    export = hub.build(setup.tool_dir, setup.workspace)
    assert export.entries == []
    assert "store_url / tool_page_url" in export.skipped[SLUG]


def test_entry_matches_contract_and_status(setup: Config) -> None:
    _set_landing(setup, "https://markpdf.dev/webpage-to-pdf")
    registry.upsert(setup.workspace, SLUG, {"store_id": "abc123", "published_state": "PUBLISHED"})
    export = hub.build(setup.tool_dir, setup.workspace)
    (entry,) = export.entries
    hub.HubEntry.model_validate(entry)
    assert entry["store_url"] == "https://chromewebstore.google.com/detail/abc123"
    assert entry["pitch"].startswith("Save the current page")
    assert entry["status"] == "published"
    assert {p["name"] for p in entry["permissions"]} == {"activeTab", "scripting", "storage"}
    assert entry["data_collected"] == [] and entry["analytics"] is False
    path, changed = hub.write(setup.hub_repo, export)
    assert changed and json.loads(path.read_text()) == [entry]
    assert hub.write(setup.hub_repo, export)[1] is False


def test_placeholder_tool_page_is_skipped(setup: Config) -> None:
    _set_landing(setup, "https://markpdf.example/x")
    registry.upsert(setup.workspace, SLUG, {"store_id": "abc123"})
    assert "tool_page_url" in hub.build(setup.tool_dir, setup.workspace).skipped[SLUG]


def test_contract_rejects_reserved_slug_and_bad_dates() -> None:
    base = {"name": "n", "pitch": "p", "store_url": "https://a.b", "tool_page_url": "https://a.b"}
    with pytest.raises(ValueError):
        hub.HubEntry.model_validate({**base, "slug": "support"})
    with pytest.raises(ValueError):
        hub.HubEntry.model_validate(
            {**base, "slug": "x", "changelog": [{"version": "1", "date": "Oct 3", "notes": ""}]}
        )


def test_slots(cfg: Config) -> None:
    cfg.workspace.mkdir(parents=True)
    registry.upsert(cfg.workspace, "a", {"published_state": "PUBLISHED"})
    registry.upsert(cfg.workspace, "b", {"published_state": "PENDING_REVIEW"})
    assert registry.slots(cfg.workspace) == {"used": 1, "limit": 2}
    assert registry.save_slots(cfg.workspace) == {"used": 1, "limit": 2}
    assert registry.read(cfg.workspace)["slots"] == {"used": 1, "limit": 2}
