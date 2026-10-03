---
ID: ADR-0002
Title: cli-python-uv
Status: Accepted
Date: 2026-10-03
Supersedes: —
---

## Context

Tabmill needs a CLI (`init`, `new`, `build`, `lint`, `publish`, `status`, …) and a typed
extension.yaml schema validated at build. Lamill's CLIs (lamill, rankmill) are Python + uv.
The extensions themselves are TypeScript built with Node tooling, and the operator forbids
Node on the host (ADR-0003). v1.A had proposed a TypeScript CLI so the build could share one
schema with the CLI.

## Decision

The `tabmill` CLI is **Python ≥ 3.11 managed by uv** (typer, rich, httpx; pydantic for the
schema). The schema exists once, in Python. The CLI validates extension.yaml and generates the
manifest JSON that the extension build reads. All Node work is delegated to the builder
Makefile in docker. Operator decision, 2026-10-03.

## Consequences

**Good:** matches fleet convention and tooling (`uv run pytest/ruff/mypy`); no Node on the
host; single schema with no cross-language drift; policy lint (manifest/bundle/listing checks)
is plain file analysis, natural in Python.
**Bad:** two languages in the tool repo (Python CLI, TS browser packages/templates); the
extension build depends on a CLI-generated file, so `tabmill build` (not a bare WXT build) is
the supported entry point.

## Alternatives considered

- **TypeScript CLI on Node** — one language with the extensions, but requires host Node. Rejected.
- **Python CLI + duplicated TS schema** — drift between two schemas. Rejected.
