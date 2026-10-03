---
ID: ADR-0006
Title: cross-repo-pnpm-workspace
Status: Superseded by ADR-0007
Date: 2026-10-03
Supersedes: —
---

## Context

Extensions in WORKSPACE_DIR must use `@tabmill/*` packages from TOOL_DIR without copying tool
code, locally and in CI. Node runs only in the builder docker (ADR-0003), adapted via the
workspace `Makefile.local` (ADR-0005). TOOL_DIR is a **private** GitHub repo.

## Decision

`WORKSPACE_DIR/pnpm-workspace.yaml` lists `'extensions/*'` and `'../tabmill/packages/*'`;
extensions depend on `@tabmill/<pkg>: workspace:*` (symlinks, TS source built by Vite).
The two repos always sit side by side: locally, `Makefile.local` mounts their common parent
into the container; in CI, the workspace workflow checks out tabmill beside itself at the
commit pinned in `WORKSPACE_DIR/.tabmill-ref`, authenticating with a read-only token stored as
the `TABMILL_PAT` secret. Operator decision, 2026-10-03.

## Consequences

**Good:** shared-package edits are visible to extensions immediately; no publish/version step;
tool packages' own deps install normally.
**Bad:** relies on pnpm behaviour that works (tested in v1.A) but isn't explicitly documented
for a workspace outside the root; identical sibling layout required everywhere; installs write
`node_modules` into TOOL_DIR packages (gitignored); CI needs a token that must be rotated.

## Alternatives considered

- **Publish `@tabmill/*` to npm / GitHub Packages** — version bump per change. Rejected for iteration speed.
- **`link:` protocol** — doesn't install the linked package's deps. Rejected.
- **TS paths / Vite alias** — duplicated config, deps not installed. Rejected.
