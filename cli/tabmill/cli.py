"""`tabmill` commands — see `tabmill --help` (README § Commands)."""

from __future__ import annotations

import dataclasses
import json
import os
import subprocess
import sys
from pathlib import Path

import typer
from rich.table import Table

from . import (
    apikeys,
    catalog,
    config,
    cws,
    extension,
    generate,
    hub,
    landing,
    lint,
    listing,
    output,
    preflight,
    privacy,
    registry,
    sync,
    workspace,
)
from .constants import ENV_WORKSPACE

app = typer.Typer(
    help="Create, release, and track Lamill's Chrome MV3 extensions.",
    no_args_is_help=True,
)
skills_app = typer.Typer(help="Workspace skills + other tabmill-managed files (read-only there).")
app.add_typer(skills_app, name="skills")
settings_app = typer.Typer(help="Setup: credentials.", no_args_is_help=True)
apikeys_app = typer.Typer(help="Credentials in tabmill/tabmill.env.", no_args_is_help=True)
settings_app.add_typer(apikeys_app, name="apikeys")
app.add_typer(settings_app, name="settings")


def _preflight(kind: str) -> None:
    """Fail fast, before any work, when a prerequisite of this command is missing."""
    failed = False
    for c in preflight.run(preflight.NEEDS[kind]):
        if c.status == "fail":
            output.fail(f"preflight {c.name}: {c.detail}")
            failed = True
        elif c.status == "warn":
            output.skip(f"preflight {c.name}: {c.detail}")
    if failed:
        raise typer.Exit(1)


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
    _preflight("docker")
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


def _make(cfg: config.Config, target: str, slug: str, *extra: str) -> None:
    """Run a workspace make target in the builder container (ADR-0003)."""
    _preflight("try" if target == "try" else "docker")
    rc = subprocess.run(
        ["make", "--no-print-directory", f"in-docker-{target}", f"EXT={slug}", *extra],
        cwd=cfg.workspace,
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


@app.command("try")
def try_(
    slug: str = typer.Argument(..., help="Extension slug."),
    url: str = typer.Option("", "--url", help="Page to open first (default: chrome://extensions)."),
    dev: bool = typer.Option(False, "--dev", help="Use the hot-reload dev build."),
) -> None:
    """Open Chromium in docker (window on your desktop) with the extension loaded."""
    cfg = _registered(slug)
    _recipe(cfg, slug)
    _sync(cfg, force=False)
    _make(cfg, "try", slug, f"URL={url}", f"DEV={'1' if dev else ''}")


@app.command()
def assets(slug: str = typer.Argument(..., help="Extension slug.")) -> None:
    """Render icons, promo tile, and 1280×800 screenshots into .output/store/ (docker)."""
    cfg = _registered(slug)
    _recipe(cfg, slug)
    _sync(cfg, force=False)
    _make(cfg, "assets", slug)
    problems = listing.image_problems(cfg.workspace, slug) or []
    for p in problems:
        output.fail(p)
    if problems:
        raise typer.Exit(1)
    output.ok(f"store images: extensions/{slug}/{listing.STORE_DIR}/")


@app.command("listing")
def listing_cmd(
    slug: str = typer.Argument(..., help="Extension slug."),
    force: bool = typer.Option(False, "--force", help="Regenerate, discarding edits to the draft."),
) -> None:
    """Write the store listing draft (paste into the Developer Dashboard)."""
    cfg = _registered(slug)
    ext = _recipe(cfg, slug)
    path, written = listing.write_listing(cfg.workspace, slug, ext, force=force)
    rel = path.relative_to(cfg.workspace)
    if written:
        output.ok(f"listing draft: {rel}")
    else:
        output.ok(f"listing draft: {rel} exists, kept (--force to regenerate)")
    for word, n in listing.keyword_repeats(path.read_text()).items():
        output.skip(f"keyword-repeat: `{word}` appears {n}× (store limit: 5)")
    output.console.print("  refine the description with the tabmill-store-listing skill")


FIRST_PUBLISH = """  First publish of a new item is manual (the API can't create items):
  1. https://chrome.google.com/webstore/devconsole → Add new item → upload {zip}
  2. Fill Store listing + Privacy practices from {listing}
  3. Set visibility; submit
  4. Put the item ID in registry.json → extensions.{slug}.store_id"""


def _store_call(fn: object) -> dict[str, object]:
    try:
        return fn()  # type: ignore[operator, no-any-return]  # thunk returning API JSON
    except cws.CwsError as e:
        (output.skip if e.transient else output.fail)(str(e))
        raise typer.Exit(1) from e


@app.command()
def publish(
    slug: str = typer.Argument(..., help="Extension slug."),
    staged: bool = typer.Option(
        False, "--staged", help="After approval, wait for a manual release."
    ),
    check: bool = typer.Option(
        False, "--check", help="Only fetch review status into registry.json."
    ),
) -> None:
    """Upload the release zip and submit for review. Attended only — never in CI."""
    cfg = _registered(slug)
    row = registry.read(cfg.workspace)["extensions"][slug]
    store_id = row.get("store_id")
    if not check and (os.environ.get("CI") or not sys.stdin.isatty()):
        output.fail("publish never runs unattended — run it yourself in a terminal")
        raise typer.Exit(1)
    if not store_id:
        zips = sorted((cfg.workspace / "extensions" / slug / ".output").glob("*.zip"))
        output.fail(f"{slug} has no store_id yet")
        output.console.print(
            FIRST_PUBLISH.format(
                zip=zips[-1] if zips else f"(run `tabmill zip {slug} --release`)",
                listing=listing.store_dir(cfg.workspace, slug) / listing.LISTING_FILE,
                slug=slug,
            )
        )
        raise typer.Exit(1)
    _preflight("publish")
    try:
        client = cws.connect(cfg.tool_dir)
    except cws.CwsError as e:
        output.fail(str(e))
        raise typer.Exit(1) from e
    if not check:
        if not _lint(cfg, slug, release=True):
            raise typer.Exit(1)
        ext = _recipe(cfg, slug)
        zips = sorted(
            (cfg.workspace / "extensions" / slug / ".output").glob(f"*-{ext['version']}-*.zip")
        )
        if not zips:
            output.fail(f"no zip for {ext['version']} — run `tabmill zip {slug} --release`")
            raise typer.Exit(1)
        kind = "staged" if staged else "default"
        if not typer.confirm(f"Upload {zips[-1].name} to item {store_id} and submit ({kind})?"):
            output.skip("publish cancelled")
            raise typer.Exit(0)
        up = _store_call(lambda: client.upload(store_id, zips[-1]))
        state = str(up.get("uploadState"))
        if state == "IN_PROGRESS":
            state = client.wait_for_upload(store_id)
        if state != "SUCCEEDED":
            output.fail(f"upload {state.lower() or 'failed'} — check the Developer Dashboard")
            raise typer.Exit(1)
        output.ok(f"uploaded {zips[-1].name}")
        _store_call(lambda: client.publish(store_id, staged=staged))
        output.ok("submitted for review")
        registry.upsert(cfg.workspace, slug, {"submitted_version": str(ext["version"])})
    status = cws.summarize(_store_call(lambda: client.fetch_status(store_id)))
    registry.upsert(cfg.workspace, slug, status)
    output.ok(
        f"review: {status['review_state'] or '—'} · published: {status['published_state'] or '—'}"
    )
    if status["taken_down"] or status["warned"]:
        output.fail("item is taken down or warned for policy — check the Developer Dashboard")


PROBE_STYLE = {
    "valid": "[green]✓ valid[/green]",
    "invalid": "[red]✗ invalid[/red]",
    "not-testable": "[yellow]↷ not testable[/yellow]",
    "missing": "—",
}


@apikeys_app.command("list")
def apikeys_list(
    no_probe: bool = typer.Option(False, "--no-probe", help="Skip the network probes."),
) -> None:
    """Known credentials: set / not set, masked value, and a live probe."""
    cfg, ws = _config_and_workspace()
    values = cws.load_env(cfg.tool_dir)
    store_id = None
    if ws is not None:
        store_id = next(
            (
                r.get("store_id")
                for r in registry.read(ws)["extensions"].values()
                if r.get("store_id")
            ),
            None,
        )
    probes = {} if no_probe else apikeys.probe_all(cfg.tool_dir, store_id)
    table = Table(show_edge=False, pad_edge=False, box=None, header_style="bold")
    for col in ("key", "value", "probe", "detail"):
        table.add_column(col, overflow="fold")
    for key in apikeys.KNOWN_KEYS:
        r = probes.get(key)
        table.add_row(
            key,
            apikeys.mask(key, values.get(key, "")) or "[dim]not set[/dim]",
            PROBE_STYLE[r.status] if r else "—",
            r.detail if r else "",
        )
    output.console.print(table)
    output.console.print(f"  file: {apikeys.env_path(cfg.tool_dir)} (gitignored, mode 600)")


@apikeys_app.command("set")
def apikeys_set(
    key: str = typer.Argument(..., help="Credential name, e.g. CWS_PUBLISHER_ID."),
    value: str = typer.Argument("", help="Value (omit to be prompted, hidden)."),
    force: bool = typer.Option(False, "--force", help="Allow a key name tabmill doesn't know."),
) -> None:
    """Set a credential in tabmill.env (prompted value stays out of shell history)."""
    if key not in apikeys.KNOWN_KEYS and not force:
        output.fail(
            f"unknown key {key} — known: {', '.join(apikeys.KNOWN_KEYS)} (--force to override)"
        )
        raise typer.Exit(1)
    if not value:
        value = typer.prompt(key, hide_input=key in apikeys.SECRET_KEYS)
    if key == "CWS_SA_KEY_FILE":
        path = Path(value).expanduser()
        if not path.exists():
            output.fail(f"{path} not found")
            raise typer.Exit(1)
        value = str(path.resolve())
    existed = apikeys.set_key(config.TOOL_DIR, key, value)
    output.ok(
        f"{key} {'updated' if existed else 'set'} — check with `tabmill settings apikeys list`"
    )


@apikeys_app.command("delete")
def apikeys_delete(
    key: str = typer.Argument(..., help="Credential name."),
    yes: bool = typer.Option(False, "--yes", help="Skip the confirmation."),
) -> None:
    """Remove a credential from tabmill.env."""
    if not yes and not typer.confirm(f"Delete {key} from tabmill.env?"):
        output.skip("not deleted")
        raise typer.Exit(0)
    if apikeys.delete_key(config.TOOL_DIR, key):
        output.ok(f"{key} deleted")
    else:
        output.skip(f"{key} was not set")


@app.command("preflight")
def preflight_cmd() -> None:
    """Check everything tabmill depends on: workspace, builder, docker, X11, credentials."""
    checks = preflight.run()
    for c in checks:
        {"ok": output.ok, "warn": output.skip, "fail": output.fail}[c.status](
            f"{c.name}: {c.detail}"
        )
    if any(c.status == "fail" for c in checks):
        raise typer.Exit(1)


@app.command()
def status(
    refresh: bool = typer.Option(False, "--refresh", help="Fetch review state from the store."),
) -> None:
    """Every extension's version, store state, and the publisher slot count."""
    cfg = _load()
    rows = registry.read(cfg.workspace)["extensions"]
    if refresh:
        _preflight("publish")
        try:
            client = cws.connect(cfg.tool_dir)
        except cws.CwsError as e:
            output.fail(str(e))
            raise typer.Exit(1) from e
        for slug, row in rows.items():
            if row.get("store_id"):
                state = cws.summarize(_store_call(lambda r=row: client.fetch_status(r["store_id"])))
                registry.upsert(cfg.workspace, slug, state)
        rows = registry.read(cfg.workspace)["extensions"]
    slots = registry.save_slots(cfg.workspace)
    table = Table(show_edge=False, pad_edge=False, box=None, header_style="bold")
    for col in ("slug", "version", "store id", "review", "published", "submitted"):
        table.add_column(col, no_wrap=True)
    for slug in sorted(rows):
        r = rows[slug]
        table.add_row(
            slug,
            str(r.get("version", "")),
            r.get("store_id") or "—",
            r.get("review_state") or "—",
            r.get("published_state") or "—",
            r.get("submitted_version") or "—",
        )
    output.console.print(table)
    line = f"slots: {slots['used']}/{slots['limit']} published"
    if slots["used"] >= slots["limit"]:
        output.skip(f"{line} — at the cap: request more in the Developer Dashboard")
    else:
        output.ok(line)


def _hub(cfg: config.Config) -> None:
    if not (cfg.hub_repo / ".git").exists():
        output.fail(f"hub repo {cfg.hub_repo} not found — set `hub_repo` in tabmill.config.json")
        raise typer.Exit(1)
    # The shared privacy policy goes first and always: its page must be live before any
    # extension's first store review, tool page or not (D-036).
    try:
        policy = privacy.load(cfg.tool_dir)
    except privacy.PolicyError as e:
        output.fail(str(e))
        raise typer.Exit(1) from e
    ppath, pchanged = privacy.write(cfg.hub_repo, policy)
    note = "" if pchanged else " (unchanged)"
    output.ok(
        f"hub: privacy policy v{policy.version} → {cfg.hub_repo.name}/"
        f"{ppath.relative_to(cfg.hub_repo)}{note}"
    )
    export = hub.build(cfg.tool_dir, cfg.workspace)
    for slug, why in export.skipped.items():
        output.skip(f"hub: {slug} skipped — {why}")
    if not export.entries:
        output.skip(f"hub: no entries — {cfg.hub_repo.name}/{hub.HUB_FILE} left untouched")
        changed = False
    else:
        changed = _hub_entries(cfg, export)
    if changed or pchanged:
        output.console.print(
            f"  HUMAN: review + commit {cfg.hub_repo.name}, push to main (Vercel deploys); "
            "tabmill never commits there"
        )


def _hub_entries(cfg: config.Config, export: hub.Export) -> bool:
    path, changed = hub.write(cfg.hub_repo, export)
    rel = path.relative_to(cfg.hub_repo)
    n = len(export.entries)
    note = "" if changed else " (unchanged)"
    output.ok(f"hub: {n} entr{'y' if n == 1 else 'ies'} → {cfg.hub_repo.name}/{rel}{note}")
    published = [e["slug"] for e in export.entries if e["status"] == "published"]
    if changed and published:
        output.console.print(
            f"  HUMAN: add /extensions/<slug> to public/sitemap.xml for: {', '.join(published)}"
        )
    return changed


@app.command("hub")
def hub_cmd() -> None:
    """Export extensions to the lamill.io hub (src/content/extensions.json, its zod contract)."""
    _hub(_load())


@app.command()
def release(slug: str = typer.Argument(..., help="Extension slug.")) -> None:
    """Prepare a release: test, assets, listing, release zip, slot check, hub. Never publishes."""
    cfg = _registered(slug)
    ext = _recipe(cfg, slug)
    _sync(cfg, force=False)
    for target in ("typecheck", "test", "smoke", "assets"):
        _make(cfg, target, slug)
    path, written = listing.write_listing(cfg.workspace, slug, ext)
    output.ok(
        f"listing draft {'written' if written else 'kept'}: {path.relative_to(cfg.workspace)}"
    )
    if not _lint(cfg, slug, release=True):
        output.fail("release blocked — fix the errors above, then re-run `tabmill release`")
        raise typer.Exit(1)
    _make(cfg, "zip", slug)
    slots = registry.save_slots(cfg.workspace)
    row = registry.read(cfg.workspace)["extensions"][slug]
    if row.get("published_state") != "PUBLISHED" and slots["used"] >= slots["limit"]:
        output.skip(
            f"slots {slots['used']}/{slots['limit']} — publishing {slug} needs another slot "
            "(Developer Dashboard → request an increase)"
        )
    todo = cfg.workspace / "TODO.md"
    line = f"- [ ] HUMAN: publish {slug} {ext['version']} — `uv run tabmill publish {slug}`"
    if line not in todo.read_text():
        with todo.open("a") as f:
            f.write(f"\n{line}\n")
    output.ok(f"TODO.md: {line.removeprefix('- [ ] ')}")
    _hub(cfg)


@app.command("landing")
def landing_cmd(
    slug: str = typer.Argument(..., help="Extension slug."),
    check: bool = typer.Option(
        False, "--check", help="Page is live: record it + resubmit sitemap."
    ),
) -> None:
    """Brief for the tool page on the portfolio site; `--check` records it once live."""
    cfg = _registered(slug)
    ext = _recipe(cfg, slug)
    problems = landing.precheck(ext)
    for p in problems:
        output.fail(p)
    if problems:
        raise typer.Exit(1)
    url = landing.landing_url(ext)
    if not check:
        store_id = registry.read(cfg.workspace)["extensions"][slug].get("store_id")
        draft = listing.store_dir(cfg.workspace, slug) / listing.LISTING_FILE
        text = landing.brief(ext, store_id, draft.read_text() if draft.exists() else None)
        path = landing.write_brief(cfg.workspace, slug, text)
        output.ok(f"brief: {path}")
        output.console.print(
            f'  next: cd {landing.site_dir(ext)} && claude → "Write the page in this brief" '
            f"(attach the file); page goes at {url}\n"
            f"  then: uv run tabmill landing {slug} --check"
        )
        return
    code = landing.is_live(url)
    if code != 200:
        output.fail(f"{url} not live (HTTP {code or 'unreachable'}) — deploy the site first")
        raise typer.Exit(1)
    output.ok(f"{url} is live")
    changed = landing.set_landing_url(cfg.tool_dir, slug, url)
    output.ok(f"recipe landing_page_url {'set' if changed else 'already set'}")
    site = str(ext["portfolio_site"])
    try:
        rc = subprocess.run(
            ["lamill", "settings", "gsc", "submit-sitemap", "--site", site, "--force"],
            capture_output=True,
            text=True,
            timeout=120,
        ).returncode
    except (OSError, subprocess.TimeoutExpired):
        rc = -1
    if rc == 0:
        output.ok(f"sitemap resubmitted to GSC for {site} (lamill)")
    else:
        output.skip(
            "sitemap resubmit failed — run "
            f"`lamill settings gsc submit-sitemap --site {site} --force`"
        )
    output.console.print("  next: uv run tabmill hub")
