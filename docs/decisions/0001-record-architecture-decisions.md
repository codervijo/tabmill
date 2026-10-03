---
ID: ADR-0001
Title: Record architecture decisions
Status: Accepted
Date: 2026-10-03
Supersedes: —
---

## Context

Tabmill will accumulate load-bearing decisions (framework, cross-repo linking, CLI language,
schema shape, store-API auth). Once embodied in code, the rationale becomes invisible.

## Decision

Record load-bearing decisions as ADRs in `docs/decisions/` (lightly adapted Nygard format),
numbered sequentially, with explicit supersession. `DECISIONS.md` at the repo root is the
running log that the kickoff asked for; accepted load-bearing entries graduate to ADRs.

## Consequences

**Good:** rationale is retraceable without git archaeology; IDs are citable in commits.
**Bad:** two surfaces (log + ADRs) — mitigated by the rule that an ADR exists only for
accepted load-bearing decisions and the log entry links to it.

## Alternatives considered

- **Only DECISIONS.md.** Supersession is awkward; long files hide decisions.
- **Only ADRs.** Too heavy for dependency justifications and small convention choices.
