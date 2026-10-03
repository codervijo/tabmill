"""Chrome Web Store API v2 client (v1 ends 2026-10-15). httpx-direct; google-auth only signs
the service-account JWT. The API can't create items or change visibility (dashboard only).

Credentials (TOOL_DIR/.env or environment, never committed):
  CWS_PUBLISHER_ID  + either CWS_SA_KEY_FILE (service account, preferred)
                    or CWS_CLIENT_ID / CWS_CLIENT_SECRET / CWS_REFRESH_TOKEN (OAuth)
"""

from __future__ import annotations

import os
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import httpx

API = "https://chromewebstore.googleapis.com"
SCOPE = "https://www.googleapis.com/auth/chromewebstore"
TOKEN_URI = "https://oauth2.googleapis.com/token"
ENV_KEYS = (
    "CWS_PUBLISHER_ID",
    "CWS_SA_KEY_FILE",
    "CWS_CLIENT_ID",
    "CWS_CLIENT_SECRET",
    "CWS_REFRESH_TOKEN",
)
SETUP_DOC = "skills/tabmill-release/reference.md § Auth"


class CwsError(Exception):
    """A store API failure with an operator-facing remedy. `transient` = safe to retry."""

    def __init__(self, message: str, *, transient: bool = False) -> None:
        super().__init__(message)
        self.transient = transient


def load_env(tool_dir: Path) -> dict[str, str]:
    """KEY=VALUE lines from TOOL_DIR/.env, overridden by the process environment."""
    values: dict[str, str] = {}
    env_file = tool_dir / ".env"
    if env_file.exists():
        for line in env_file.read_text().splitlines():
            key, sep, value = line.partition("=")
            if sep and not key.strip().startswith("#"):
                values[key.strip()] = value.strip().strip('"').strip("'")
    values.update({k: os.environ[k] for k in ENV_KEYS if os.environ.get(k)})
    return values


def _error(resp: httpx.Response, *, item: str = "", publisher: str = "") -> CwsError:
    try:
        err = resp.json().get("error", {})
    except ValueError:
        err = {}
    msg = str(err.get("message") or resp.text[:200])
    status = str(err.get("status", ""))
    code = resp.status_code
    if code == 429 or status == "RESOURCE_EXHAUSTED":
        return CwsError(f"rate limited ({msg}) — retry later", transient=True)
    if code >= 500:
        return CwsError(f"store API error {code} ({msg}) — retry later", transient=True)
    if code == 401 or status == "UNAUTHENTICATED":
        return CwsError(f"credentials rejected ({msg}) — refresh them, see {SETUP_DOC}")
    if code == 403 or status == "PERMISSION_DENIED":
        return CwsError(
            f"no access to publisher {publisher or '?'} ({msg}) — add the service account's email "
            "in the Developer Dashboard → Account, or use the publisher owner's OAuth credentials"
        )
    if code == 404 or status == "NOT_FOUND":
        return CwsError(
            f"item {item or '?'} not found under publisher {publisher or '?'} — check `store_id` "
            "in registry.json and CWS_PUBLISHER_ID (new items are created in the dashboard)"
        )
    return CwsError(f"store API rejected the request ({code} {status}: {msg})")


def access_token(env: dict[str, str], http: httpx.Client) -> str:
    if env.get("CWS_SA_KEY_FILE"):
        try:
            from google.auth import jwt
            from google.oauth2 import service_account
        except ImportError as e:
            raise CwsError(f"google-auth not installed ({e}) — run `uv sync`") from e
        # google-auth ships no type hints for these two calls.
        creds = service_account.Credentials.from_service_account_file(  # type: ignore[no-untyped-call]
            env["CWS_SA_KEY_FILE"]
        )
        now = int(time.time())
        claims = {
            "iss": creds.service_account_email,
            "scope": SCOPE,
            "aud": TOKEN_URI,
            "iat": now,
            "exp": now + 3600,
        }
        data = {
            "grant_type": "urn:ietf:params:oauth:grant-type:jwt-bearer",
            "assertion": jwt.encode(creds.signer, claims).decode(),  # type: ignore[no-untyped-call]
        }
    elif all(env.get(k) for k in ("CWS_CLIENT_ID", "CWS_CLIENT_SECRET", "CWS_REFRESH_TOKEN")):
        data = {
            "grant_type": "refresh_token",
            "client_id": env["CWS_CLIENT_ID"],
            "client_secret": env["CWS_CLIENT_SECRET"],
            "refresh_token": env["CWS_REFRESH_TOKEN"],
        }
    else:
        raise CwsError(
            "no store credentials — set CWS_SA_KEY_FILE (or CWS_CLIENT_ID / CWS_CLIENT_SECRET / "
            f"CWS_REFRESH_TOKEN) in tabmill/.env; see {SETUP_DOC}"
        )
    resp = http.post(TOKEN_URI, data=data)
    if resp.status_code != 200:
        raise CwsError(
            f"token exchange failed ({resp.status_code}: {resp.text[:200]}) — see {SETUP_DOC}"
        )
    return str(resp.json()["access_token"])


@dataclass
class Client:
    publisher: str
    token: str
    http: httpx.Client

    def _name(self, item: str) -> str:
        return f"publishers/{self.publisher}/items/{item}"

    def _call(self, method: str, url: str, item: str, **kw: Any) -> dict[str, Any]:
        headers = {"Authorization": f"Bearer {self.token}", **kw.pop("headers", {})}
        resp = self.http.request(method, url, headers=headers, **kw)
        if resp.status_code >= 400:
            raise _error(resp, item=item, publisher=self.publisher)
        data: dict[str, Any] = resp.json() if resp.content else {}
        return data

    def upload(self, item: str, zip_path: Path) -> dict[str, Any]:
        return self._call(
            "POST",
            f"{API}/upload/v2/{self._name(item)}:upload",
            item,
            params={"uploadType": "media"},
            headers={"Content-Type": "application/zip"},
            content=zip_path.read_bytes(),
        )

    def fetch_status(self, item: str) -> dict[str, Any]:
        return self._call("GET", f"{API}/v2/{self._name(item)}:fetchStatus", item)

    def publish(self, item: str, *, staged: bool = False) -> dict[str, Any]:
        body = {"publishType": "STAGED_PUBLISH" if staged else "DEFAULT_PUBLISH"}
        return self._call("POST", f"{API}/v2/{self._name(item)}:publish", item, json=body)

    def wait_for_upload(self, item: str, *, timeout: float = 60, every: float = 3) -> str:
        """Poll lastAsyncUploadState after an IN_PROGRESS upload."""
        deadline = time.monotonic() + timeout
        while True:
            state = str(self.fetch_status(item).get("lastAsyncUploadState", ""))
            if state != "IN_PROGRESS" or time.monotonic() > deadline:
                return state
            time.sleep(every)


def connect(tool_dir: Path, http: httpx.Client | None = None) -> Client:
    env = load_env(tool_dir)
    if not env.get("CWS_PUBLISHER_ID"):
        raise CwsError(
            "CWS_PUBLISHER_ID missing — Developer Dashboard → Publisher → Settings; put it in "
            "tabmill/.env"
        )
    http = http or httpx.Client(timeout=120)
    return Client(env["CWS_PUBLISHER_ID"], access_token(env, http), http)


def summarize(status: dict[str, Any]) -> dict[str, Any]:
    """Registry fields from a fetchStatus response."""
    sub = status.get("submittedItemRevisionStatus") or {}
    pub = status.get("publishedItemRevisionStatus") or {}
    return {
        "review_state": sub.get("state") or None,
        "published_state": pub.get("state") or None,
        "taken_down": bool(status.get("takenDown")),
        "warned": bool(status.get("warned")),
    }
