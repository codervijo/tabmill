"""Manifest-tracked sync of tabmill-managed files into the workspace.

Managed files (installed skills, generated CLAUDE.md, Makefile, Makefile.local,
pnpm-workspace.yaml, CI workflow) are tool code: never hand-edited in the workspace.
`.tabmill-sync.json` records the sha256 of everything tabmill wrote; sync refuses (unless
forced) when a tracked file changed, or an untracked file sits where tabmill wants to write.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from pathlib import Path

from . import output
from .constants import SYNC_MANIFEST


@dataclass
class SyncResult:
    installed: list[str] = field(default_factory=list)
    updated: list[str] = field(default_factory=list)
    unchanged: list[str] = field(default_factory=list)
    removed: list[str] = field(default_factory=list)
    drift: list[str] = field(default_factory=list)

    @property
    def refused(self) -> bool:
        return bool(self.drift)


def _sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def read_manifest(workspace: Path) -> dict[str, str]:
    path = workspace / SYNC_MANIFEST
    if not path.exists():
        return {}
    files = json.loads(path.read_text()).get("files", {})
    return {str(k): str(v) for k, v in files.items()}


def sync(workspace: Path, wanted: dict[str, bytes], *, force: bool = False) -> SyncResult:
    """Make managed files match `wanted` (paths relative to the workspace). Idempotent."""
    result = SyncResult()
    manifest = read_manifest(workspace)

    for rel, recorded in manifest.items():
        path = workspace / rel
        if path.exists() and _sha(path.read_bytes()) != recorded:
            result.drift.append(rel)
    for rel, data in wanted.items():
        path = workspace / rel
        if rel not in manifest and path.exists() and path.read_bytes() != data:
            result.drift.append(rel)
    if result.drift and not force:
        return result

    new_manifest: dict[str, str] = {}
    for rel, data in wanted.items():
        path = workspace / rel
        if path.exists() and path.read_bytes() == data:
            result.unchanged.append(rel)
        else:
            (result.updated if path.exists() else result.installed).append(rel)
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(data)
        new_manifest[rel] = _sha(data)

    for rel in manifest:
        if rel not in wanted and (workspace / rel).exists():
            (workspace / rel).unlink()
            result.removed.append(rel)

    (workspace / SYNC_MANIFEST).write_text(
        json.dumps({"files": new_manifest}, indent=2, sort_keys=True) + "\n"
    )
    return result


def report(result: SyncResult, *, force: bool) -> None:
    if result.drift and not force:
        for rel in result.drift:
            output.fail(f"{rel}: edited in the workspace (tabmill-managed, read-only)")
        output.fail(
            "sync refused — move the edit into the tabmill repo (skills/, templates/, ci/) and "
            "re-run, or `tabmill skills sync --force` to discard workspace edits"
        )
        return
    for rel in result.drift:
        output.skip(f"{rel}: workspace edit overwritten (--force)")
    for rel in result.installed:
        output.ok(f"{rel}: installed")
    for rel in result.updated:
        output.ok(f"{rel}: updated")
    for rel in result.removed:
        output.ok(f"{rel}: removed (dropped from source)")
    total = len(result.installed) + len(result.updated) + len(result.unchanged)
    output.ok(f"managed files in sync ({total} files, {len(result.unchanged)} unchanged)")
