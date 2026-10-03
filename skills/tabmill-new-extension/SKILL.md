---
name: tabmill-new-extension
description: Turn a Chrome extension idea into a Tabmill extension.yaml — one narrow single purpose, a template (popup, side-panel, devtools, context-menu, maps-overlay), minimal permissions with justifications, funnel fields (portfolio site, CTA, UTM, keywords), analytics opt-in (default off) — then scaffold it with `tabmill new`. Use when the user proposes a new extension, says "new extension", "extension idea", "let's build a tool that…", or asks to scaffold one. Refuses ideas that duplicate an entry in registry.json.
---

# Tabmill: new extension

> DRAFT (v1.A, 2026-10-03). `tabmill new` and the typed schema land in v1.C; before then,
> write extension.yaml by hand and copy the closest existing extension's layout.

## 1. Duplicate check (refuse first, build later)

Read `registry.json` and every `extensions/*/extension.yaml`. Compare the idea's job — not
its keywords — against each `single_purpose`. If it does the same job as an existing
extension (or a reskin of it), **refuse** and say which one it duplicates. The store's spam
policy forbids duplicate functionality from one publisher (see `chrome-store-policy`).
Shared code with an existing extension is fine; shared purpose is not.

## 2. Single purpose

Write one sentence: "<verb> <object> <for whom/where>". No "and" joining features. If the
idea needs two sentences, it's two extensions — or one is out of scope. Confirm with the user.

## 3. Template

| template | when |
|---|---|
| `popup` | one action on the current page (save, convert, inspect) |
| `side-panel` | persistent results while browsing (audits, checkers) |
| `devtools` | developer inspection (requests, storage, tokens) |
| `context-menu` | act on a selection or link |
| `maps-overlay` | content script UI on google.com/maps |

## 4. Permissions (minimal)

Start from `activeTab` only. Add each further permission only if the purpose fails without it,
prefer `optional_permissions` requested at the moment of need, and write a justification for
every one. Host permissions need a justification naming the host and why `activeTab` isn't
enough; broad hosts (`<all_urls>`) need explicit user sign-off.

## 5. Funnel fields

Ask the user — never invent: `portfolio_site`, `cta_text`, `cta_url`, `utm_campaign`,
`target_keywords` (tool queries, e.g. "webpage to pdf"), `store_category`. `landing_page_url`
may be empty until the landing page exists. If a CTA destination doesn't exist yet, use a
reserved placeholder host (`https://<name>.example/<path>`) and add `HUMAN: set real <name> CTA
URL` to the workspace TODO.md — dev builds warn, release lint blocks (D-015).

## 6. Analytics

`analytics: false` unless the user explicitly opts in. If on, note the obligations: consent
screen, privacy policy URL, data categories, Limited Use certifications.

## 7. Write and scaffold

```yaml
name: Save Page as Markdown or PDF   # ≤ 75 chars
slug: save-page-pdf-md
version: 0.1.0
single_purpose: Save the current web page as clean Markdown or a branded PDF.
template: popup
permissions:
  - name: activeTab
    justification: Read the current page only when the user clicks the toolbar button.
optional_permissions: []
portfolio_site: markpdf.dev
landing_page_url: ""
target_keywords: [markdown to pdf, save webpage as pdf]
cta_text: ‹FILL›
cta_url: ‹FILL›
utm_campaign: ‹FILL›
store_category: ‹FILL›
analytics: false
theme: {}      # optional token overrides
```

(Field names are the kickoff list; the typed schema in v1.C is authoritative once it exists.)

Then `tabmill new <slug>` *(planned v1.C)*, add a row to `registry.json`
(`status: "scaffolded"`), and record start time in TOOL_DIR `NOTES.md` for
time-to-first-build. Run `chrome-store-policy` before writing feature code.
