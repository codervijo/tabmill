---
ID: ADR-0003
Title: node-only-in-docker-builder
Status: Accepted
Date: 2026-10-03
Supersedes: —
---

## Context

Extensions need Node ≥ 22 (WXT, Vite, pnpm, ESLint, Playwright). The host has Node 12 and
no pnpm by design; every Lamill site builds inside the central docker builder
(`~/work/projects/builder/`).

## Decision

**Node is never installed on the host.** All Node commands run through the builder Makefile
(docker). The CLI invokes `make <target>` in WORKSPACE_DIR; it never runs `node`, `pnpm`, or
host tools that bundle Node (e.g. Python Playwright). Operator rule, 2026-10-03.

## Consequences

**Good:** one pinned Node environment shared with the sites fleet; host stays clean.
**Bad:** `tabmill dev` hot reload must bridge container ↔ host Chrome (WXT dev server in the
container on the forwarded port, host Chrome loads the bind-mounted dev build) — to be
verified in v1.B. The container mounts only `${PWD}` by default, so the cross-repo pnpm
workspace (D-006) needs a parent-dir `VOLUME_MOUNT`. The builder's React stack assumes a
`webapp/` dir and its Playwright image is pinned to an old version — builder-repo changes
or `Makefile.local` overrides are needed (builder is a separate repo: operator approves).

## Alternatives considered

- **Host Node via nvm/corepack** — forbidden by the operator.
