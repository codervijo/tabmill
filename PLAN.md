# PLAN — tabmill

Per-phase scope and done criteria. Status lives in `docs/prd.md` § 5. Every phase's "done"
includes updated docs (prd row, PLAN, architecture, NOTES, DECISIONS, skills). When a phase
ships, its section moves to `docs/shipping-history.md`.

Core principle: **extract, don't design upfront.** #1 is built in the workspace with minimal
tooling; packages and CLI commands move into TOOL_DIR only when #2 needs them.

## v2 — Idea stage (D-039, D-040)

Full plan, phases v2.A–v2.H, open decisions: `docs/prd.md` § v2 (accepted 2026-10-15).
Build one phase at a time; stop for review after each. v2.A–v2.E ✅ 2026-10-16; v2.F in progress.

Carried from v1: first real CWS API upload + publish (#1's first update); v1.L real-use
validation. Idea candidates: local-schema-generator, jwt-inspector.

## v4.A — WordPress plugins: planning / decisions lock (D-037; renumbered by D-039, D-040)

Not started. Target: the wordpress.org plugin directory. Spikes: plugin directory rules +
submission flow, PHP build/test in docker, how recipes carry a platform. Open: which plugin is
first (v4.C). Build phases v4.B–v4.E: `docs/prd.md` § 5.
