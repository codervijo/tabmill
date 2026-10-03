---
name: tabmill-new-extension
description: Turn a Chrome extension idea into a tabmill recipe — recipes/<slug>/extension.yaml with one narrow single purpose, a template (popup, side-panel, devtools, context-menu, maps-overlay), minimal permissions with justifications, funnel fields, analytics opt-in (default off), plus feature code under recipes/<slug>/src/ — then generate it with `tabmill new <slug>`. Use in the tabmill repo when the user proposes a new extension, says "new extension", "extension idea", "let's build a tool that…", or asks to scaffold one. Refuses ideas that duplicate an entry in the workspace registry.json or an existing recipe.
---

# tabmill: new extension (recipe)

Tool-repo skill (ADR-0008): extensions are **generated**. Everything you write goes in
`recipes/<slug>/` in this repo; never write in `$TABMILL_WORKSPACE/extensions/`.

## 1. Duplicate check (refuse first, build later)

Read every `recipes/*/extension.yaml`, `$TABMILL_WORKSPACE/registry.json`, and the
pre-tabmill projects at the workspace top level (e.g. `chrome-dejargon`, `chrome-synonymizer`).
Compare the idea's **job**, not its keywords. Same job (or a reskin) → **refuse** and name the
duplicate. The store's spam policy forbids duplicate functionality from one publisher (see the
`chrome-store-policy` skill in `skills/`). Shared code is fine; shared purpose is not.

## 2. Single purpose

One sentence: "<verb> <object> <for whom/where>". No "and" joining features. Needs two
sentences → two extensions, or one is out of scope. Confirm with the user.

## 3. Template

| template | when | status |
|---|---|---|
| `popup` | one action on the current page | ✅ `templates/extension/popup/` |
| `side-panel` | persistent results while browsing | planned |
| `devtools` | developer inspection | planned |
| `context-menu` | act on a selection or link | planned |
| `maps-overlay` | content-script UI on google.com/maps | planned |

A planned template must be added to `templates/extension/` first (it's a tabmill change —
plan it in TODO.md).

## 4. Permissions (minimal)

Start from `activeTab`. Add a permission only if the purpose fails without it; prefer
`optional_permissions` requested at the moment of need; every entry needs a `justification`.
Broad hosts (`<all_urls>`) need explicit user sign-off.

## 5. Funnel fields — ask, never invent

`portfolio_site`, `cta_text`, `cta_url`, `utm_campaign`, `target_keywords` (tool queries,
e.g. "webpage to pdf"), `store_category` (‹FILL› — picked in the dashboard; no official list).
No real CTA destination yet → reserved placeholder host (`https://<name>.example/<path>`) and a
`HUMAN: set real <name> CTA URL` line in this repo's TODO.md; dev builds warn, release blocks (D-015).

## 6. Analytics

`analytics: false` unless the user explicitly opts in (supported from v1.H).

## 7. Write the recipe

Start from the starter: `uv run tabmill create <slug> [--template popup]` (refuses bad or
existing slugs), then fill every `‹FILL›`. Resulting shape:

```yaml
name: Save Page as Markdown or PDF          # ≤ 75 chars
slug: save-page-pdf-md                     # = directory name
version: 0.1.0
summary: Save the current page as …        # manifest description, ≤ 132 chars
single_purpose: Save the current web page as clean Markdown or a branded PDF.
template: popup
permissions:
  - name: activeTab
    justification: Read the current page only after the user clicks the toolbar button.
optional_permissions: []
dependencies: {}        # runtime npm deps — each needs a DECISIONS.md row first
dev_dependencies: {}
portfolio_site: markpdf.dev
landing_page_url: ""
target_keywords: [markdown to pdf, save webpage as pdf]
cta_text: …
cta_url: …
utm_campaign: …
store_category: ‹FILL›
analytics: false
```

Feature code: `recipes/<slug>/src/feature/index.ts` exporting `mount(root: HTMLElement)`
(replaces the template stub); extra entrypoints under `recipes/<slug>/src/entrypoints/`;
tests under `recipes/<slug>/tests/`. A recipe file replaces the template file at the same path.

## 8. Generate and verify

`uv run tabmill new <slug>` (refuses while name / summary / single_purpose are `‹FILL›`) →
`uv run tabmill build <slug>` → in the workspace
`make in-docker-test EXT=<slug>` and `make in-docker-smoke EXT=<slug>`. Record start/first-build
times in NOTES.md (time-to-first-build). `uv run tabmill list` shows status and remaining
placeholders. Run the `chrome-store-policy` checklist before feature work.
