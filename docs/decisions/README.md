# Architecture Decision Records

Load-bearing architectural decisions for Tabmill, in Nygard format.

Relationship to `DECISIONS.md` (repo root): `DECISIONS.md` is the running log of every
decision (dependency justifications, convention choices, proposals awaiting the operator).
When a load-bearing entry there is **accepted by the operator**, it gets an ADR here and the
log entry links to it. Proposals never get an ADR until accepted.

## Format

`NNNN-kebab-case-title.md`, four-digit zero-padded, sequential. Never re-number.

```yaml
---
ID: ADR-NNNN
Title: <kebab-case title matching filename>
Status: Proposed | Accepted | Deprecated | Superseded by ADR-MMMM
Date: YYYY-MM-DD
Supersedes: <ADR-NNNN or "—">
---
```

Body: **Context**, **Decision**, **Consequences**, **Alternatives considered**.

## When to write an ADR

When someone six months from now would ask "why is it this way?" and need rationale beyond
the code. ✅ framework, linking mechanism, CLI language, schema shape, lockfile policy.
❌ small implementation details.

## Supersession

Never edit an accepted ADR. Write a new one (`Supersedes: ADR-NNNN`), set the old one's
status to `Superseded by ADR-MMMM`, update this index.

## Index

| ID | Title | Status | Date |
|---|---|---|---|
| ADR-0001 | Record architecture decisions | Accepted | 2026-10-03 |
| ADR-0002 | cli-python-uv | Accepted | 2026-10-03 |
| ADR-0003 | node-only-in-docker-builder | Accepted | 2026-10-03 |
| ADR-0004 | wxt-extension-framework | Accepted | 2026-10-03 |
| ADR-0005 | builder-overrides-via-makefile-local | Accepted | 2026-10-03 |
| ADR-0006 | cross-repo-pnpm-workspace | Accepted | 2026-10-03 |
