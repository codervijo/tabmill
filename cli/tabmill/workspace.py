"""Workspace files: *seed* files (workspace-owned, created once by `init`, never overwritten)
and *managed* files (tool code rendered from templates, kept current by `skills sync`)."""

from __future__ import annotations

import os
import subprocess
from pathlib import Path

from . import generate, output, registry, skills
from .config import Config
from .constants import (
    CI_DST_DIR,
    CI_TEMPLATE_DIR,
    GENERATED_MARKER,
    TABMILL_REF_FILE,
    WORKSPACE_TEMPLATE_DIR,
)
from .templates import render

TEMPLATE_SUFFIX = ".tmpl"
SEED_DIR = "seed"
MANAGED_DIR = "managed"


def tool_ref(tool_dir: Path) -> str | None:
    """TOOL_DIR HEAD commit, pinned in the workspace so CI checks out the same tool code."""
    try:
        out = subprocess.run(
            ["git", "-C", str(tool_dir), "rev-parse", "HEAD"],
            check=True,
            capture_output=True,
            text=True,
        )
    except (OSError, subprocess.CalledProcessError):
        return None
    return out.stdout.strip() or None


def template_values(cfg: Config) -> dict[str, str]:
    ws, tool = cfg.workspace, cfg.tool_dir
    mount_root = Path(os.path.commonpath([ws, tool, cfg.builder]))
    return {
        # pnpm-workspace.yaml + CI layout (ADR-0007): tool path relative to the workspace.
        "tool_rel": os.path.relpath(tool, ws),
        "builder_rel": os.path.relpath(cfg.builder, ws),
        # Makefile.local: mount the common parent so the container sees tool + workspace.
        "mount_root": str(mount_root),
        "workspace_in_mount": os.path.relpath(ws, mount_root),
        "tool_in_mount": os.path.relpath(tool, mount_root),
        # CI second checkout (private repo, TABMILL_PAT).
        "tool_repo": cfg.tool_repo or "OWNER/tabmill",
        "marker": GENERATED_MARKER,
    }


def _dest_name(name: str) -> str:
    name = name.removesuffix(TEMPLATE_SUFFIX)
    # Dotfiles are stored as dot-<name> so they stay visible in the tool repo.
    return "." + name.removeprefix("dot-") if name.startswith("dot-") else name


def _render_tree(root: Path, values: dict[str, str]) -> dict[str, str]:
    files: dict[str, str] = {}
    for src in sorted(p for p in root.rglob("*") if p.is_file()):
        rel = src.relative_to(root)
        text = src.read_text()
        if src.name.endswith(TEMPLATE_SUFFIX):
            text = render(text, values)
        files[str(rel.with_name(_dest_name(rel.name)))] = text
    return files


def managed_files(cfg: Config) -> dict[str, bytes]:
    """Every file `skills sync` owns, keyed by path relative to the workspace."""
    values = template_values(cfg)
    loaded = skills.load_skills(cfg.tool_dir)
    values["skills"] = skills.index_markdown(loaded)
    tdir = cfg.tool_dir / WORKSPACE_TEMPLATE_DIR
    wanted = {rel: t.encode() for rel, t in _render_tree(tdir / MANAGED_DIR, values).items()}
    for rel, text in _render_tree(cfg.tool_dir / CI_TEMPLATE_DIR, values).items():
        wanted[f"{CI_DST_DIR}/{rel}"] = text.encode()
    wanted.update(skills.installed_files(loaded))
    # Every extension registered by `tabmill bootstrap` is regenerated from its recipe (ADR-0008).
    for slug in registry.slugs(cfg.workspace):
        for rel, data in generate.extension_files(cfg.tool_dir, slug).items():
            wanted[f"extensions/{slug}/{rel}"] = data
    return wanted


def scaffold(cfg: Config) -> bool:
    """Create missing seed files + pin the tool ref. False if operator action is needed."""
    ws = cfg.workspace
    if not cfg.builder.joinpath("Makefile").exists():
        output.fail(f"builder Makefile not found at {cfg.builder} — set TABMILL_BUILDER")
        return False
    ws.mkdir(parents=True, exist_ok=True)
    seed = cfg.tool_dir / WORKSPACE_TEMPLATE_DIR / SEED_DIR
    for rel, text in _render_tree(seed, template_values(cfg)).items():
        path = ws / rel
        if path.exists():
            output.ok(f"{rel}: exists, skipping")
            continue
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text)
        output.ok(f"{rel}: created")
    (ws / "extensions").mkdir(exist_ok=True)
    output.ok("extensions/: ready")

    ref = tool_ref(cfg.tool_dir)
    ref_path = ws / TABMILL_REF_FILE
    if ref is None:
        output.skip(f"{TABMILL_REF_FILE}: TOOL_DIR has no commit yet — not pinned")
    elif ref_path.exists() and ref_path.read_text().strip() == ref:
        output.ok(f"{TABMILL_REF_FILE}: already {ref[:7]}")
    else:
        ref_path.write_text(ref + "\n")
        output.ok(f"{TABMILL_REF_FILE}: pinned {ref[:7]}")
    return True
