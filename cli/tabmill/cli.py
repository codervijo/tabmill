"""`tabmill` commands: init, skills sync, new, build, list, create, lint, dev, test, zip."""

from __future__ import annotations

import dataclasses
import json
import subprocess
from pathlib import Path

import typer
from rich.table import Table

from . import catalog, config, extension, generate, lint, output, registry, sync, workspace
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


def _config_and_workspace() -> tuple[config.Config, Path | None]:
    """list/create work from recipes alone; the workspace is optional for them."""
    try:
        cfg = config.load()
    except config.ConfigError:
        output.skip(f"no workspace configured (${ENV_WORKSPACE}) — recipes only")
        return config.load(require_workspace=False), None
    if not cfg.workspace.exists():
        output.skip(f"workspace {cfg.workspace} not found — recipes only")
        return cfg, None
    return cfg, cfg.workspace


STATUS_STYLE = {
    "built": "[green]✓ built[/green]",
    "generated": "[green]✓ generated[/green]",
    "recipe": "[yellow]↷ recipe only[/yellow]",
    "orphan": "[red]✗ orphan[/red]",
    "invalid": "[red]✗ invalid[/red]",
}


@app.command("list")
def list_(
    as_json: bool = typer.Option(False, "--json", help="Machine-readable output."),
) -> None:
    """All extensions: recipes in tabmill + what's generated/built in the workspace."""
    cfg, ws = _config_and_workspace()
    rows = catalog.rows(cfg.tool_dir, ws)
    if as_json:
        typer.echo(json.dumps([r.to_dict() for r in rows], indent=2))
        return
    if not rows:
        output.skip("no extensions yet — start one with `tabmill create <slug>`")
        return
    table = Table(show_edge=False, pad_edge=False, box=None, header_style="bold")
    for col in ("slug", "status", "version", "template", "store id"):
        table.add_column(col, no_wrap=True)
    table.add_column("needs filling", overflow="fold")
    for r in rows:
        todo = r.error or " ".join(r.placeholders)
        table.add_row(
            r.slug,
            STATUS_STYLE[r.status],
            r.version,
            r.template,
            r.store_id or "—",
            f"[yellow]{todo}[/yellow]" if todo else "—",
        )
    output.console.print(table)


@app.command()
def create(
    slug: str = typer.Argument(..., help="New extension slug, e.g. jwt-inspector."),
    template: str = typer.Option("popup", "--template", "-t", help="Surface template."),
) -> None:
    """Start a new extension: write a starter recipe in tabmill/recipes/<slug>/."""
    cfg, ws = _config_and_workspace()
    try:
        path = catalog.create(cfg.tool_dir, ws, slug, template)
    except catalog.CreateError as e:
        output.fail(str(e))
        raise typer.Exit(1) from e
    output.ok(f"created {path.relative_to(cfg.tool_dir)}")
    output.console.print(
        f"  next: fill every ‹FILL› in it (feature code goes in recipes/{slug}/src/feature/), "
        f"then `tabmill new {slug}`"
    )


def _registered(slug: str) -> config.Config:
    cfg = _load()
    if slug not in registry.slugs(cfg.workspace):
        output.fail(f"{slug} is not in registry.json — run `tabmill new {slug}` first")
        raise typer.Exit(1)
    return cfg


def _make(cfg: config.Config, target: str, slug: str) -> None:
    """Run a workspace make target in the builder container (ADR-0003)."""
    rc = subprocess.run(
        ["make", "--no-print-directory", f"in-docker-{target}", f"EXT={slug}"], cwd=cfg.workspace
    ).returncode
    if rc != 0:
        output.fail(f"{target} failed (exit {rc})")
        raise typer.Exit(rc)


def _lint(cfg: config.Config, slug: str, release: bool) -> bool:
    findings = lint.lint(cfg.tool_dir, cfg.workspace, slug, release=release)
    for f in findings:
        (output.fail if f.severity == "error" else output.skip)(f"{f.rule}: {f.message}")
    errors = sum(f.severity == "error" for f in findings)
    warns = len(findings) - errors
    mode = "release" if release else "dev"
    if errors:
        output.fail(f"lint {slug} ({mode}): {errors} error(s), {warns} warning(s)")
        return False
    output.ok(f"lint {slug} ({mode}): {warns} warning(s)")
    return True


@app.command("lint")
def lint_cmd(
    slug: str = typer.Argument(..., help="Extension slug."),
    release: bool = typer.Option(
        False, "--release", help="Release severities (placeholders block)."
    ),
) -> None:
    """Chrome Web Store policy checks on the recipe and the last build."""
    cfg, _ = _config_and_workspace()
    if not _lint(cfg, slug, release):
        raise typer.Exit(1)


@app.command()
def test(slug: str = typer.Argument(..., help="Extension slug.")) -> None:
    """Regenerate, then typecheck + unit tests + build + smoke test, in docker."""
    cfg = _registered(slug)
    _recipe(cfg, slug)
    _sync(cfg, force=False)
    for target in ("typecheck", "test", "smoke"):
        _make(cfg, target, slug)
    output.ok(f"{slug}: typecheck, unit, smoke passed")


@app.command()
def zip(
    slug: str = typer.Argument(..., help="Extension slug."),
    release: bool = typer.Option(False, "--release", help="Block on release-severity lint."),
) -> None:
    """Regenerate, build, lint, and zip (`--release`: placeholders block)."""
    cfg = _registered(slug)
    _recipe(cfg, slug)
    _sync(cfg, force=False)
    _make(cfg, "build", slug)
    if not _lint(cfg, slug, release):
        raise typer.Exit(1)
    _make(cfg, "zip", slug)
    zips = sorted((cfg.workspace / "extensions" / slug / ".output").glob("*.zip"))
    output.ok(f"zip: {zips[-1].relative_to(cfg.workspace) if zips else '(not found)'}")


@app.command()
def dev(slug: str = typer.Argument(..., help="Extension slug.")) -> None:
    """WXT dev server with hot reload in docker; load the dev build in your own Chrome."""
    cfg = _registered(slug)
    _recipe(cfg, slug)
    _sync(cfg, force=False)
    dev_dir = cfg.workspace / "extensions" / slug / ".output" / "chrome-mv3-dev"
    output.console.print(
        f"  Chrome → chrome://extensions → Developer mode → Load unpacked → {dev_dir}\n"
        "  (once the server prints 'Started'; changes then reload automatically; Ctrl-C stops)"
    )
    _make(cfg, "dev", slug)
