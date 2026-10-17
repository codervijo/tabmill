# CLAUDE.md — tabmill (docs conventions)

Lamill-standard orientation. The operative **Rules** for this repo are in the root `CLAUDE.md`;
this file holds doc workflow, ADR workflow, and code-shape conventions.

## Project

CLI + templates + skills for Lamill's Chrome extension portfolio. `docs/prd.md` is the
canonical spec (phases, plans and the work queue), `docs/Prompts.md` the prompt log.

## Canonical doc surfaces

- `docs/prd.md` — WHY / WHAT / WHEN (purpose, non-goals, goals, phases, conformance, open questions)
- `docs/architecture.md` — HOW (layout, mechanisms, schemas, integrations, risks, tracked refactors)
- `docs/shipping-history.md` — archived rationale for shipped phases (append-only, newest first)
- `docs/decisions/` — ADRs for accepted load-bearing decisions; `DECISIONS.md` is the running log
- `CLAUDE.md` (root) — Rules; this file — doc/code conventions
- `NOTES.md` — findings, blockers, time-to-first-build

## When to update which doc

| If you're changing… | …update | same commit |
|---|---|---|
| A mechanism, schema, or module | `docs/architecture.md` | yes |
| Phase status | `docs/prd.md` § 5 row | yes |
| A phase shipped | move its PRD plan notes + work-queue list → `docs/shipping-history.md` | yes |
| A dependency | `DECISIONS.md` § Dependency register | yes |
| A load-bearing decision (accepted / reversed) | new ADR in `docs/decisions/` + `DECISIONS.md` link | yes |
| A skill | `skills/<name>/` then sync | yes |

Stale docs are a conformance failure, not a backlog item.

## ADR workflow

See `docs/decisions/README.md`. Naming `NNNN-kebab-case-title.md`; never renumber; supersede,
don't edit. Status: `Proposed` | `Accepted` | `Deprecated` | `Superseded by ADR-NNNN`.

## Heading hygiene

Before adding a heading to a long-lived Markdown file, print its outline
(`grep -nE '^#+ ' file.md`) and confirm depth and that the label doesn't collide or look like
a `vN.X` phase id.

## Code-shape conventions

### CLI / module split threshold
When a file aggregating command surface passes ~1,500 lines, propose a split by scope.

### Canonical constants
A string used by two modules (permission names, template ids, rule ids) goes in a shared
constants module immediately.

### Lazy-import error wrap
Any function-local `from optional_dep import X` is wrapped in `try / except ImportError` and
re-raised as a typed error naming the fix command (`uv sync`).

### Direct HTTP over SDKs
For the CWS API, a hand-written `httpx` client tested with `httpx.MockTransport` over
`googleapiclient`; add `google-auth` only if the service-account JWT flow genuinely needs it
(record in DECISIONS.md).

### Pipeline idempotency markers
Each pipeline step probes state first and prints `✓ exists, skipping` / `✓ created` /
`↷ warn-skipped: <reason>` / `✗ <error>`. Safe to re-run.

### Soft-fail non-load-bearing steps
Auxiliary steps (sitemap resubmit, metrics import) don't abort the main flow; surface status
below the main result.

### Error causes from response bodies
Parse CWS API error bodies and map each distinct cause to a specific remediation — never
surface a bare HTTP status.

### Root cause before symptom
Symptom patches get a tracked-refactor entry in `docs/architecture.md` § 10.

## Locked target shapes

(none yet)

## Deferred decisions

(none yet)

## Project-specific conventions

- CLI: Python + uv only (ADR-0002) — `uv run pytest | ruff | mypy`.
- Extensions: Node only inside the builder docker (ADR-0003); pnpm only; Prettier config from
  lamill.io; ESLint 9 flat + typescript-eslint.
