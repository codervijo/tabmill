# TODO — tabmill

Work queue for the tool repo. Plans before patches: any change over ~20 lines gets a planned
item here first. When an item is done, check it off and take the next; if blocked, write the
blocker to `NOTES.md`, mark it BLOCKED, move on.

## v1.A — Kickoff / decisions lock

- [x] Initialize doc structure (project-init) + reconcile with kickoff files
- [x] Spikes 1–8 (NOTES.md)
- [x] DECISIONS.md, PLAN.md, README.md, CLAUDE.md, AI_AGENTS.md
- [x] tabmill-dev skill; drafts of five workspace skills
- [x] CLI language → Python + uv (ADR-0002); Node only in docker builder (ADR-0003)
- [x] WXT (ADR-0004), local PDF (D-013), Makefile.local overrides (ADR-0005)
- [x] Linking (ADR-0006), skip IndexNow (D-016), tabmill private, placeholder-CTA lint (D-015)
- [ ] HUMAN: set real Rankmill CTA URL (placeholder `https://rankmill.example/local-seo-audit`; release lint blocks until replaced)
- [ ] HUMAN: `git init` TOOL_DIR (+ GitHub repo if wanted)

## v1.B — queued (don't start until v1.A is locked)

- [ ] Plan `tabmill init` + `skills sync` (Python/uv package in `cli/`, config resolution `tabmill.config.json` → `TABMILL_WORKSPACE`)
- [ ] `templates/workspace/Makefile.local` (ADR-0005): WXT targets, parent-dir `VOLUME_MOUNT`, WXT dev-server port; verify `tabmill dev` HMR container → host Chrome
- [ ] Workspace CI template (`ci/`) — typecheck, lint, test, build
- [ ] save-page-pdf-md: extension.yaml (fill CTA / UTM / category with operator)
- [ ] save-page-pdf-md: runtime deps → DECISIONS.md rows before adding
- [ ] 10 real test URLs list (operator supplies or approves)
- [ ] Workspace CI template: second checkout of private tabmill at `.tabmill-ref` with `TABMILL_PAT`
- [ ] HUMAN (when the workspace repo exists): create a fine-grained PAT, repo access = tabmill only,
      permission Contents: read-only — https://github.com/settings/personal-access-tokens/new — and save
      it as secret `TABMILL_PAT` in the tabmill-extensions repo (Settings → Secrets and variables → Actions)

## v1.C — queued

- [ ] local-seo-checker extension.yaml: `cta_url: https://rankmill.example/local-seo-audit` (placeholder, D-015);
      copy the `HUMAN: set real Rankmill CTA URL` line into the workspace TODO.md at scaffold
- [ ] `packages/policy` rule `cta-placeholder` (warn; error under `--release`) + per-rule release severity
