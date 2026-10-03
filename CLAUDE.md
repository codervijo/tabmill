# CLAUDE.md — tabmill (tool repo)

Tabmill = CLI + templates + shared packages + Claude Code skills that create, release, and
track Lamill's portfolio of single-purpose Chrome MV3 extensions.

Read first: `AI_AGENTS.md` (orientation, versioning), `docs/prd.md` (scope, phase status,
open questions), `PLAN.md` (current phase), `TODO.md` (queue), `DECISIONS.md`.
Lamill doc conventions (ADRs, heading hygiene, code shape): `docs/CLAUDE.md`.
Working on Tabmill itself → the `tabmill-dev` skill (`.claude/skills/tabmill-dev/`).

## Directories

- **TOOL_DIR** = this repo. CLI, packages, templates, CI templates, skill sources.
- **WORKSPACE_DIR** = from `tabmill.config.json` or `TABMILL_WORKSPACE` — never hardcoded.
  Currently `../tabmill-extensions`. Extension source, extension.yaml, registry.json, build output.

## Rules

- Never write extension code in TOOL_DIR; never write tool code in WORKSPACE_DIR. Templates,
  CI templates, and skill sources are tool code.
- extension.yaml is the source of truth; never hand-edit generated manifest.json.
- Manifest V3 only. Extension code is TypeScript strict; no `any` without a comment explaining why.
- The `tabmill` CLI is Python + uv (ADR-0002): `uv run …` only — never pip/venv/bare python.
- Every new runtime dependency needs a justification in `DECISIONS.md`.
- Permissions: activeTab + optional permissions by default. Any host permission needs a
  written justification in the YAML; lint fails without it.
- No remote code. Processing stays local unless the single purpose requires otherwise.
- Analytics are opt-in per extension, never include URLs or page content, and must be
  disclosed in the listing and privacy statement.
- Every extension ships with: single-purpose statement, UTM-tagged CTA, "Built by Lamill"
  mark + footer, privacy statement, generated README.
- `publish` NEVER runs unattended. In unattended sessions, stop at "zip built + checks
  passing + listing drafted" and add `HUMAN: publish <slug>` to WORKSPACE_DIR/TODO.md.
- Don't extract a shared package until two extensions need it.
- Plans before patches: for any change over ~20 lines, plan in TODO.md first.
- Git: TOOL_DIR and WORKSPACE_DIR are separate repos. Small commits per TODO item — **only
  when the operator asks** (global never-auto-commit rule wins). Never force-push, never
  commit `.env` or credentials.
- Continuation: when a TODO item is done, check it off, take the next. If blocked, write the
  blocker to NOTES.md, mark it BLOCKED, move on.
- Skills: edit sources in `skills/`, then `tabmill skills sync`. Never edit installed copies.
  Write skills from verified findings; SKILL.md ≤ ~150 lines.
- Versioning: `vN.X` only (`docs/prd.md` § 5). Never "Phase N", never `vN.X.Y`.
- **Never install Node on the host** (ADR-0003). Node (≥ 22, pnpm only) runs only inside the
  builder docker via `make <target>`; the CLI shells out to make, never to node/pnpm.
