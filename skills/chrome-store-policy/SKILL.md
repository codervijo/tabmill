---
name: chrome-store-policy
description: Chrome Web Store policy checklist for Tabmill extensions — single purpose, spam/repetitive content, remote code, permission justification, privacy/analytics disclosure, CTA/ads rules, listing metadata limits — and how to read the lint output of `tabmill check` / `tabmill ship`. Use before writing or changing any extension.yaml, manifest permission, CTA, analytics setting, or listing text; when `tabmill check` or `tabmill ship` reports a rule id; when deciding whether a new extension idea is distinct enough to publish; or when the user asks "will this pass review?"
---

# Chrome Web Store policy (Tabmill)

> DRAFT (v1.A, 2026-10-03). Verified against developer.chrome.com policy pages on
> 2026-10-03 — sources and the full rule table are in [reference.md](reference.md).
> `uv run tabmill check <slug>` runs the mechanical rules (dev severities); `tabmill ship` runs
> them at release severity. The rest of this checklist is still by hand.

Policy is priority #1 for Tabmill — above speed. When in doubt, choose the reading that
asks for less permission and discloses more.

## The portfolio risk (read first)

Tabmill ships many extensions from one publisher. The spam policy forbids
"multiple extensions that provide duplicate experiences or functionality", and minimum
functionality bans "click-baity template extensions that only vary slightly in
functionality". There is **no numeric threshold**. So for every new extension:

1. It must do a genuinely different job than every entry in `registry.json` (not a reskin,
   not the same engine with a different keyword).
2. Shared code is fine; shared *purpose* is not.
3. The extension itself must do the work — an extension whose purpose is opening a
   Lamill site is banned. The CTA is secondary.

If you can't write a one-sentence purpose that clearly differs from every registry entry,
stop and tell the user.

## Checklist (every extension, every release)

**Single purpose**
- [ ] `single_purpose` in extension.yaml: one sentence, narrow, no bundled unrelated features.
- [ ] Every UI surface serves that purpose; the CTA is clearly secondary.

**Permissions**
- [ ] Default to `activeTab` (no install warning). Request others via `optional_permissions` at
      the moment of need (Tabmill policy; narrowest-permission rule).
- [ ] Every permission has a non-empty justification in the YAML — the dashboard asks for one
      per permission.
- [ ] No `<all_urls>`, `*://*/*`, `https://*/*` unless the purpose truly requires it — broad
      host permissions trigger longer in-depth review.
- [ ] No permission "for the future"; every one is used by the bundle.

**Code**
- [ ] No remote code: no external `<script src>`, no `eval`/`new Function`/string timers,
      no `import()` of http(s) URLs. Fetching data/config/images is allowed — declare it.
- [ ] No obfuscation (minification is fine).

**User data and analytics**
- [ ] Analytics `false` unless the YAML opts in. If on: consent screen in the extension UI
      with the disclosure text itself (not only a link), explicit user action, stored flag
      defaulting to false.
- [ ] Events never include URLs, page content, or identifiers of the page.
- [ ] Privacy policy URL set (required if any user data is handled), names every recipient.
- [ ] Privacy-practices tab: data categories declared, all three Limited Use certifications.
- [ ] Local-only processing still gets disclosed if user data is handled.

**CTA / promotion**
- [ ] CTA attributed to Lamill/the target site, never required to use the feature, never in
      a notification, dismissible or quiet.
- [ ] No affiliate/ref params added silently; no URL rewriting.
- [ ] CTA and landing URLs are real — no `.example` / `‹FILL›` placeholders at release.

**Listing**
- [ ] `name` ≤ 75 chars; `description` (store summary) ≤ 132 chars, plain text.
- [ ] No keyword stuffing: no term repeated more than 5 times; no long lists of brands/sites.
- [ ] No "#1", "Editor's Choice", "official", no third-party trademarks in name/icon.
- [ ] Icon 128×128 PNG (96×96 art + 16px transparent padding); 1–5 screenshots at exactly
      1280×800 or 640×400; small promo tile 440×280 (mandatory).
- [ ] Listing text matches what the extension actually does.

## Reading lint output

Each finding is one line: `✗ <rule-id> <file>: <message>` (error — blocks zip/release) or
`↷ <rule-id> <file>: <message>` (warning — review it, may be acknowledged in YAML).
`tabmill ship` escalates rules that have a release severity — e.g. `cta-placeholder`
(`https://rankmill.example/…`) is a warning while developing and an error at release.
`✓ lint` means all rules passed. Look up any rule id in [reference.md](reference.md) for the
source policy and the fix. Never silence an error by editing generated `manifest.json` —
fix extension.yaml or the source.

## Human-only review (lint cannot decide these)

Is it a genuinely distinct, useful tool? Is the CTA honest and secondary? Does the listing
match behavior? Does the privacy policy name every recipient? Any trademark conflicts?
Is every broad permission truly needed? Record the answers in the release notes.

## Known unknowns

Not documented on official pages (2026-10-03): exact dashboard data-category definitions,
detailed-description length limit, per-account item caps beyond the new-publisher limit of
two published extensions, in-depth review duration. Don't state numbers for these.
