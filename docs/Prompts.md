# Prompt History — tabmill

<!-- Append new prompts at the bottom, newest last. Format:

## YYYY-MM-DD [optional title]
> <prompt text or summary of the conversation>

The dated H2 is what `lamill project status` parses. Append-only.
-->

## 2026-10-03 — v1.A kickoff (initialization + spikes + skill drafts)

> Operator pasted the Tabmill kickoff brief (archived verbatim in `docs/kickoff.md`):
> CLI + templates + Claude Code skills to create/publish/manage a portfolio of
> narrowly scoped Chrome MV3 extensions for Lamill, each paired with an SEO landing
> page. Asked to initialize from existing skills + Lamill conventions, then run
> Phase 0 (now v1.A): 8 spikes verified against official docs, create README / PLAN /
> CLAUDE / TODO / NOTES / DECISIONS, the tabmill-dev skill, and drafts of the five
> workspace skills — then STOP with a summary.

## 2026-10-03 — v1.A decisions: Python CLI, Node only in docker

> "use python+uv no typescript. dont use node for the tool, if you are using node for
> extensions, always use builder Makefile (docker for nodejs) NEVER INSTALL Nodejs on host."
> → ADR-0002 (CLI Python + uv), ADR-0003 (Node only via builder docker); docs + skills updated.

## 2026-10-03 — v1.A decisions: WXT, local PDF, Makefile.local

> "accept WXT, generate PDF locally, use Makefile.local overrides"
> → ADR-0004 (WXT), D-013 (save-page-pdf-md renders PDF locally), ADR-0005 (builder adapted via
> workspace `Makefile.local`, no builder-repo changes).

## 2026-10-03 — v1.A decisions: linking, IndexNow, repo visibility, placeholder CTA

> Accept D-006; skip IndexNow; tabmill repo is private. Rankmill CTA: placeholder
> `https://rankmill.example/local-seo-audit` in extension.yaml, lint warning for placeholder CTA
> URLs, `HUMAN: set real Rankmill CTA URL` in TODO.md; lint must block release (not dev) while
> the placeholder remains.
> → ADR-0006, D-015, D-016; policy reference, skills, PLAN, TODO updated.
