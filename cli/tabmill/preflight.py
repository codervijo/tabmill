"""`tabmill settings preflight` + per-command preflights (D-025). Each check is cheap,
read-only, and returns a status plus the fix — commands run only the checks they depend on,
before acting."""

from __future__ import annotations

import os
import shutil
import subprocess
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

from . import config
from .constants import ENV_WORKSPACE

Status = Literal["ok", "warn", "fail"]
CONTAINER = "tabmill-ext"  # templates/workspace/managed/Makefile.local.tmpl


@dataclass(frozen=True)
class Check:
    name: str
    status: Status
    detail: str


def _run(*cmd: str) -> subprocess.CompletedProcess[str] | None:
    try:
        return subprocess.run(cmd, capture_output=True, text=True, timeout=15)
    except (OSError, subprocess.TimeoutExpired):
        return None


def workspace(cfg: config.Config | None) -> Check:
    if cfg is None:
        return Check(
            "workspace",
            "fail",
            f"${ENV_WORKSPACE} not set — exported in ~/.profile; `source ~/.profile` "
            "or log in again",
        )
    if not cfg.workspace.exists():
        return Check("workspace", "fail", f"{cfg.workspace} missing — run `tabmill settings init`")
    if not (cfg.workspace / "registry.json").exists():
        return Check(
            "workspace", "fail", f"{cfg.workspace} not initialized — run `tabmill settings init`"
        )
    return Check("workspace", "ok", str(cfg.workspace))


def builder(cfg: config.Config | None) -> Check:
    b = cfg.builder if cfg else Path(os.path.expanduser("~/work/projects/builder"))
    if not (b / "Makefile").exists():
        return Check("builder", "fail", f"no builder Makefile at {b} — set TABMILL_BUILDER")
    return Check("builder", "ok", str(b))


def docker() -> Check:
    if not shutil.which("docker"):
        return Check("docker", "fail", "docker CLI not installed")
    r = _run("docker", "info", "--format", "{{.ServerVersion}}")
    if r is None or r.returncode != 0:
        msg = (r.stderr.strip().splitlines() or ["no response"])[-1] if r else "timed out"
        hint = (
            "add yourself to the docker group"
            if "permission denied" in msg.lower()
            else "start the docker daemon"
        )
        return Check("docker", "fail", f"daemon unreachable ({msg[:80]}) — {hint}")
    return Check("docker", "ok", f"server {r.stdout.strip()}")


def container() -> Check:
    r = _run("docker", "ps", "-a", "--filter", f"name=^{CONTAINER}$", "--format", "{{.Status}}")
    status = r.stdout.strip() if r and r.returncode == 0 else ""
    if not status:
        return Check(
            "container",
            "warn",
            f"{CONTAINER} not created yet — first docker command builds it (minutes)",
        )
    return Check("container", "ok", f"{CONTAINER}: {status}")


def x11() -> Check:
    display = os.environ.get("DISPLAY", "")
    sock = Path(f"/tmp/.X11-unix/X{display.lstrip(':').split('.')[0]}") if display else None
    if not display or sock is None or not sock.exists():
        return Check(
            "x11",
            "fail",
            "no X11 display — `tabmill try` needs a desktop session (DISPLAY + /tmp/.X11-unix)",
        )
    return Check("x11", "ok", f"DISPLAY={display}")


def credentials(cfg: config.Config | None) -> Check:
    from . import apikeys, registry

    tool_dir = cfg.tool_dir if cfg else config.TOOL_DIR
    store_id = None
    if cfg and cfg.workspace.exists():
        ids = [r.get("store_id") for r in registry.read(cfg.workspace)["extensions"].values()]
        store_id = next((i for i in ids if i), None)
    results = apikeys.probe_all(tool_dir, store_id)
    bad = [k for k, r in results.items() if r.status == "invalid"]
    missing = [k for k, r in results.items() if r.status == "missing"]
    if bad:
        return Check(
            "credentials", "fail", f"invalid: {', '.join(bad)} — `tabmill settings apikeys list`"
        )
    if "CWS_PUBLISHER_ID" in missing or len(missing) == len(apikeys.KNOWN_KEYS):
        return Check(
            "credentials",
            "warn",
            "not configured — only `publish` and `status --refresh` need them "
            "(`tabmill settings apikeys set`)",
        )
    return Check(
        "credentials",
        "ok",
        "store API reachable" if results["CWS_PUBLISHER_ID"].status == "valid" else "auth OK",
    )


def _config() -> config.Config | None:
    try:
        return config.load()
    except config.ConfigError:
        return None


ALL: dict[str, Callable[[config.Config | None], Check]] = {
    "workspace": workspace,
    "builder": builder,
    "docker": lambda _c: docker(),
    "container": lambda _c: container(),
    "x11": lambda _c: x11(),
    "credentials": credentials,
}
# What each command needs before it starts.
NEEDS: dict[str, tuple[str, ...]] = {
    "docker": ("workspace", "builder", "docker"),
    "try": ("workspace", "builder", "docker", "x11"),
    "publish": ("workspace", "credentials"),
}


def run(names: tuple[str, ...] | None = None) -> list[Check]:
    cfg = _config()
    return [ALL[n](cfg) for n in (names or tuple(ALL))]
