from __future__ import annotations

from pathlib import Path

from tabmill import listing

SLUG = "save-page-pdf-md"


def test_collect_release_gathers_upload_files(tmp_path: Path) -> None:
    ws = tmp_path
    built = ws / "extensions" / SLUG / ".output"
    store = listing.store_dir(ws, SLUG)
    store.mkdir(parents=True)
    (built / f"{SLUG}-0.1.0-chrome.zip").write_bytes(b"zip")
    (built / f"{SLUG}-0.0.9-chrome.zip").write_bytes(b"old")
    (store / "icon-128.png").write_bytes(b"png")
    (store / listing.LISTING_FILE).write_text("listing")
    (store / "landing-brief.md").write_text("not for the dashboard")
    (ws / ".gitignore").write_text("/node_modules/\n")

    out = listing.collect_release(ws, SLUG, "0.1.0")
    assert out == ws / "releases" / f"{SLUG}-0.1.0"
    assert sorted(f.name for f in out.iterdir()) == [
        "icon-128.png",
        "listing.md",
        f"{SLUG}-0.1.0-chrome.zip",
    ]
    listing.collect_release(ws, SLUG, "0.1.0")
    assert (ws / ".gitignore").read_text().count("/releases/") == 1
