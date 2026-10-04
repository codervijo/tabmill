"""`tabmill settings apikeys` — credentials in TOOL_DIR/tabmill.env (mirrors lamill's
`settings apikeys` / portfolio.env, D-025).

Edits are atomic (tmp file + rename, mode 600) and keep comments, blank lines, and the order
of unchanged keys. Probes answer "does this credential actually work?" with one cheap call.
"""

from __future__ import annotations

import json
import os
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

import httpx

ENV_FILE = "tabmill.env"
KNOWN_KEYS: tuple[str, ...] = (
    "CWS_PUBLISHER_ID",  # Developer Dashboard → Publisher → Settings
    "CWS_SA_KEY_FILE",  # service-account JSON key path (preferred auth)
    "CWS_CLIENT_ID",  # OAuth alternative: client + refresh token
    "CWS_CLIENT_SECRET",
    "CWS_REFRESH_TOKEN",
)
SECRET_KEYS = {"CWS_CLIENT_SECRET", "CWS_REFRESH_TOKEN"}

ProbeStatus = Literal["valid", "invalid", "not-testable", "missing"]


@dataclass(frozen=True)
class ProbeResult:
    status: ProbeStatus
    detail: str = ""


def env_path(tool_dir: Path) -> Path:
    return tool_dir / ENV_FILE


def _parse(line: str) -> tuple[str, str] | None:
    stripped = line.strip()
    if not stripped or stripped.startswith("#") or "=" not in stripped:
        return None
    key, _, value = stripped.partition("=")
    return key.strip(), value.strip().strip('"').strip("'")


def read(tool_dir: Path) -> dict[str, str]:
    path = env_path(tool_dir)
    if not path.exists():
        return {}
    pairs = (_parse(line) for line in path.read_text().splitlines())
    return {k: v for k, v in (p for p in pairs if p) if v}


def _atomic_write(path: Path, content: str) -> None:
    fd, tmp = tempfile.mkstemp(prefix=".tabmill_env.", dir=path.parent)
    try:
        with os.fdopen(fd, "w") as f:
            f.write(content)
        os.chmod(tmp, 0o600)
        os.replace(tmp, path)
    except BaseException:
        if os.path.exists(tmp):
            os.unlink(tmp)
        raise


def set_key(tool_dir: Path, key: str, value: str) -> bool:
    """Update in place or append. Returns True if the key already existed."""
    path = env_path(tool_dir)
    lines = path.read_text().splitlines() if path.exists() else []
    found = False
    for i, line in enumerate(lines):
        parsed = _parse(line)
        if parsed and parsed[0] == key:
            lines[i], found = f"{key}={value}", True
    if not found:
        lines.append(f"{key}={value}")
    _atomic_write(path, "\n".join(lines) + "\n")
    return found


def delete_key(tool_dir: Path, key: str) -> bool:
    path = env_path(tool_dir)
    if not path.exists():
        return False
    lines = path.read_text().splitlines()
    kept = [line for line in lines if (_parse(line) or ("",))[0] != key]
    if len(kept) == len(lines):
        return False
    _atomic_write(path, "\n".join(kept) + "\n")
    return True


def mask(key: str, value: str) -> str:
    if not value:
        return ""
    if key in SECRET_KEYS or len(value) > 24:
        return f"{value[:4]}…{value[-4:]}" if len(value) > 12 else "••••"
    return value


def probe_all(
    tool_dir: Path, store_id: str | None, http: httpx.Client | None = None
) -> dict[str, ProbeResult]:
    """One result per known key. Token exchange covers the auth keys; fetchStatus covers the
    publisher when a registered item exists."""
    from . import cws  # local: cws imports this module for credential loading

    env = cws.load_env(tool_dir)
    out: dict[str, ProbeResult] = {k: ProbeResult("missing") for k in KNOWN_KEYS if not env.get(k)}
    sa = env.get("CWS_SA_KEY_FILE")
    if sa:
        try:
            data = json.loads(Path(sa).expanduser().read_text())
            ok = data.get("type") == "service_account" and "client_email" in data
            out["CWS_SA_KEY_FILE"] = ProbeResult(
                "valid" if ok else "invalid",
                data.get("client_email", "") if ok else "not a service-account key",
            )
        except (OSError, ValueError) as e:
            out["CWS_SA_KEY_FILE"] = ProbeResult("invalid", type(e).__name__)
    auth_keys = (
        ("CWS_SA_KEY_FILE",) if sa else ("CWS_CLIENT_ID", "CWS_CLIENT_SECRET", "CWS_REFRESH_TOKEN")
    )
    http = http or httpx.Client(timeout=15)
    token: str | None = None
    sa_ok = not sa or out["CWS_SA_KEY_FILE"].status == "valid"
    if all(env.get(k) for k in auth_keys) and sa_ok:
        try:
            token = cws.access_token(env, http)
            for k in auth_keys:
                detail = out[k].detail if k in out else ""
                out[k] = ProbeResult("valid", detail or "token exchange OK")
        except cws.CwsError as e:
            for k in auth_keys:
                out[k] = ProbeResult("invalid", str(e)[:80])
    for k in ("CWS_CLIENT_ID", "CWS_CLIENT_SECRET", "CWS_REFRESH_TOKEN"):
        if sa and env.get(k):
            out[k] = ProbeResult("not-testable", "unused — CWS_SA_KEY_FILE takes precedence")
    for k in KNOWN_KEYS:
        if k not in out and k != "CWS_PUBLISHER_ID":
            out[k] = ProbeResult("not-testable", "set, but the rest of its auth group is missing")
    pub = env.get("CWS_PUBLISHER_ID")
    if pub:
        if token is None:
            out["CWS_PUBLISHER_ID"] = ProbeResult("not-testable", "needs working auth first")
        elif not store_id:
            out["CWS_PUBLISHER_ID"] = ProbeResult(
                "not-testable", "no store_id in registry.json yet"
            )
        else:
            try:
                cws.Client(pub, token, http).fetch_status(store_id)
                out["CWS_PUBLISHER_ID"] = ProbeResult("valid", f"fetchStatus {store_id} OK")
            except cws.CwsError as e:
                out["CWS_PUBLISHER_ID"] = ProbeResult("invalid", str(e)[:80])
    return out
