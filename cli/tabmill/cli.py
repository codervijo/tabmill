"""`tabmill` command surface. v1.B: init, skills sync, new, build (minimal)."""

from __future__ import annotations

import dataclasses
import subprocess
from pathlib import Path

import typer

from . import config, extension, generate, output, registry, sync, workspace
from .constants import ENV_WORKSPACE

app = typer.Typer(
    help="Create, release, and track Lamill's Chrome MV3 extensions.",
    no_args_is_help=True,
)
skills_app = typer.Typer(help="Workspace skills + other tabmill-managed files (read-only there).")
app.add_typer(skills_app, name="skills")


def _load(workspace_override: Path | None = None) -> config.Config:
    try:
        cfg = config.load(require_workspace=workspace_override is None)
    except config.ConfigError as e:
        output.fail(str(e))
        raise typer.Exit(1) from e
    if workspace_override is not None:
        cfg = dataclasses.replace(cfg, workspace=workspace_override.expanduser().resolve())
    return cfg


def _sync(cfg: config.Config, force: bool) -> None:
    try:
        wanted = workspace.managed_files(cfg)
    except generate.RecipeError as e:
        output.fail(str(e))
        raise typer.Exit(1) from e
    result = sync.sync(cfg.workspace, wanted, force=force)
    sync.report(result, force=force)
    if result.refused and not force:
        raise typer.Exit(1)


@app.command()
def init(
    directory: Path | None = typer.Argument(  # noqa: B008 — typer's documented idiom
        None, help=f"Workspace dir (default: ${ENV_WORKSPACE} / tabmill.config.json)."
    ),
    force: bool = typer.Option(False, "--force", help="Overwrite edited installed skills."),
) -> None:
    """Create or complete a workspace: skeleton, skills, CI, tool pin. Never overwrites files."""
    cfg = _load(directory)
    try:
        configured: Path | None = config.load().workspace
    except config.ConfigError:
        configured = None
    if configured is not None and configured != cfg.workspace:
        output.skip(f"${ENV_WORKSPACE} points to {configured}, not {cfg.workspace}")
    output.ok(f"workspace: {cfg.workspace}")
    if not workspace.scaffold(cfg):
        raise typer.Exit(1)
    _sync(cfg, force)


@skills_app.command("sync")
def skills_sync(
    force: bool = typer.Option(False, "--force", help="Discard edits to installed copies."),
) -> None:
    """Update tabmill-managed workspace files: skills, CLAUDE.md, Makefiles, pnpm workspace, CI."""
    cfg = _load()
    if not cfg.workspace.exists():
        output.fail(f"workspace {cfg.workspace} does not exist — run `tabmill init` first")
        raise typer.Exit(1)
    _sync(cfg, force)


def _recipe(cfg: config.Config, slug: str) -> dict[str, object]:
    try:
        ext = generate.load_recipe(cfg.tool_dir, slug)
    except generate.RecipeError as e:
        output.fail(str(e))
        raise typer.Exit(1) from e
    output.ok(f"recipes/{slug}/extension.yaml: valid")
    for field in extension.placeholder_fields(ext):
        output.skip(f"{field}: placeholder URL — fine for dev, blocks release (D-015)")
    return ext


@app.command()
def new(
    slug: str = typer.Argument(..., help="Recipe slug (tabmill/recipes/<slug>/)."),
    force: bool = typer.Option(False, "--force", help="Discard edits to managed files."),
) -> None:
    """Generate extensions/<slug>/ in the workspace from its recipe + template (ADR-0008)."""
    cfg = _load()
    if not cfg.workspace.exists():
        output.fail(f"workspace {cfg.workspace} does not exist — run `tabmill init` first")
        raise typer.Exit(1)
    ext = _recipe(cfg, slug)
    changed = registry.upsert(
        cfg.workspace, slug, {"version": str(ext["version"]), "status": "generated"}
    )
    output.ok(f"registry.json: {slug} {'registered' if changed else 'already registered'}")
    _sync(cfg, force)


@app.command()
def build(
    slug: str = typer.Argument(..., help="Extension slug."),
) -> None:
    """Regenerate managed files, then build with WXT in the builder docker (never on the host)."""
    cfg = _load()
    if slug not in registry.slugs(cfg.workspace):
        output.fail(f"{slug} is not in registry.json — run `tabmill new {slug}` first")
        raise typer.Exit(1)
    _recipe(cfg, slug)
    _sync(cfg, force=False)
    rc = subprocess.run(
        ["make", "--no-print-directory", "in-docker-build", f"EXT={slug}"], cwd=cfg.workspace
    ).returncode
    if rc != 0:
        output.fail(f"WXT build failed (exit {rc})")
        raise typer.Exit(rc)
    output.ok(f"built: extensions/{slug}/.output/chrome-mv3/")
