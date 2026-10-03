---
ID: ADR-0008
Title: extensions-generated-from-recipes
Status: Accepted
Date: 2026-10-03
Supersedes: —
---

## Context

The kickoff had extension #1 hand-built in WORKSPACE_DIR and extension source living only
there ("never write extension code in TOOL_DIR"). The operator instead wants **tabmill to
generate extensions** — the tabmill session builds only tabmill — including each extension's
feature code (operator choice 2026-10-03: per-extension recipes in the tabmill repo, over a
separate Claude session writing feature code in the workspace).

## Decision

- Each extension's source of truth is a **recipe** in TOOL_DIR: `recipes/<slug>/extension.yaml`
  + feature files (`src/**`, tests). Recipes are tool input, reviewed and versioned with tabmill.
- Generic per-surface code lives in `templates/extension/<template>/` (popup, side-panel,
  devtools, context-menu, maps-overlay): branding, "Built by Lamill" footer, UTM CTA, privacy
  line, typed messaging, WXT config, smoke test.
- `tabmill new <slug>` / `tabmill skills sync` render template + recipe overlay (a recipe file
  replaces the template file at the same path) + YAML values into
  `WORKSPACE_DIR/extensions/<slug>/`, as **managed files** (sha manifest; hand edits refused).
- The workspace holds generated extensions, build output, `registry.json`, `TODO.md`; nothing in
  `extensions/` is edited there. Builds still run in the builder docker from the workspace.

## Consequences

**Good:** one place to change any extension; consistent branding/policy by construction;
regenerating after a template fix updates every extension.
**Bad:** extension-specific code now lives in the tool repo (the kickoff boundary is redrawn:
TOOL_DIR = generators **and** their inputs; WORKSPACE_DIR = output); the tabmill repo grows
with each extension; the workspace-installed `tabmill-new-extension` skill must re-target
recipes in TOOL_DIR.

## Alternatives considered

- **Feature code written by a Claude session in the workspace via installed skills** — keeps
  the original boundary; rejected by the operator.
- **extension.yaml in the workspace, feature code in recipes** — two sources of truth, and
  the workspace would need hand edits. Rejected.
