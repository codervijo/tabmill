# chrome-store-policy — reference

Fetched 2026-10-03. `pp/` = `https://developer.chrome.com/docs/webstore/program-policies/`.
Re-verify on each tier kickoff; policies change.

## Lint rules (proposed for `packages/policy`, v1.C)

| id | sev | mechanical check | source |
|---|---|---|---|
| mv3-no-remote-script | error | No `<script src>` to a non-package origin in HTML or injected DOM | pp/mv3-requirements |
| mv3-no-eval | error | Bundle has no `eval(`, `new Function(`, string `setTimeout`/`setInterval`, `import()` of http(s) | pp/mv3-requirements |
| remote-code-declared | error | YAML declares `remote_code: false`; any `fetch` targets are listed (data/config/images only) | pp/mv3-requirements, /docs/webstore/cws-dashboard-privacy |
| no-obfuscation | warn | Heuristics: `_0x` identifiers, hex string tables, very high per-line entropy | pp/code-readability |
| perm-justification | error | Every `permissions` / `host_permissions` / `optional_permissions` entry has a non-empty YAML justification | /docs/webstore/cws-dashboard-privacy |
| perm-broad-host | error unless acked | Host perms or content-script `matches` include `<all_urls>`, `*://*/*`, `https://*/*` | /docs/webstore/review-process, pp/permissions |
| perm-unused | warn | Declared permission whose `chrome.<api>` is never referenced in the bundle | pp/permissions |
| single-purpose-field | error | `single_purpose` non-empty, one sentence (warn on " and " joining features) | pp/quality-guidelines |
| manifest-name-len | error | `name` ≤ 75 chars | /docs/extensions/reference/manifest/name |
| manifest-desc-len | error | `description` ≤ 132 chars, plain text | /docs/extensions/reference/manifest/description |
| listing-required | error | Detailed description, icon, ≥1 screenshot, small tile present | pp/listing-requirements, /docs/webstore/images |
| icon-128 | error | 128×128 PNG (warn if 16px border not transparent) | /docs/webstore/images |
| screenshot-size | error | Exactly 1280×800 or 640×400; 1–5 of them | /docs/webstore/images |
| promo-small | error | 440×280; marquee if present 1400×560 | /docs/webstore/images |
| keyword-repeat | error | Any non-stopword term > 5 occurrences in listing text | pp/listing-requirements |
| keyword-lists | warn | Comma lists of many brands/sites/regions (threshold = Tabmill heuristic) | pp/listing-requirements |
| no-false-badges | error | "#1", "Editor's Choice", "Number One", "official" in listing | pp/impersonation-and-intellectual-property |
| brand-in-name | warn | Third-party trademark (denylist) in name | pp/impersonation-and-intellectual-property |
| privacy-policy-url | error | If analytics or any data category: `privacy_policy_url` set, https, 200 | pp/privacy |
| data-categories-declared | error | If analytics on: YAML data categories non-empty and match bundle | /docs/webstore/cws-dashboard-privacy |
| limited-use-certs | error | All three Limited Use certifications true in YAML | pp/limited-use |
| analytics-consent-ui | error | Analytics gated by stored consent flag defaulting false; consent screen contains disclosure text | pp/user-data-faq, pp/disclosure-requirements |
| analytics-no-ad-endpoints | error | Telemetry endpoint not on ad-network/data-broker denylist | pp/limited-use |
| cta-attributed | warn | CTA names Lamill/target domain; not in notifications; can be hidden | pp/ads, pp/spam-and-abuse |
| cta-placeholder | warn (dev/build) · **error (`--release`)** | `cta_url` / `landing_page_url` host is a reserved example/test name (`.example`, `.test`, `.invalid`, `.localhost`, `example.com/net/org`) or contains `‹FILL›` | Tabmill rule (D-015) — listing must match behaviour (pp/listing-requirements) |
| cta-not-core | error | Extension has a non-CTA primary entry point | pp/minimum-functionality |
| no-affiliate-silent | error | No URL rewriting adding ref params; no third-party cookie writes | pp/affiliate-ads |
| portfolio-similarity | warn (error > 0.9) | Similarity of `single_purpose` + description + permission set + bundle across registry (thresholds are Tabmill heuristics, not policy) | pp/spam-and-abuse, pp/minimum-functionality |
| privacy-consistency | error | YAML data categories ↔ privacy policy text ↔ network calls agree | pp/listing-requirements |

## Key quotes

- Spam: "We don't allow any developer, related developer accounts, or their affiliates to
  submit multiple extensions that provide duplicate experiences or functionality."
- Minimum functionality: bans "Click-baity template extensions that only vary slightly in
  functionality with negligible utility" (examples: "Word of the Day", "Daily Inspirational
  Quotes"); bans extensions whose purpose is launching another app/webpage.
- Quality: "single purpose that is narrow and easy to understand".
- User data FAQ: prominent disclosure "must not be located only in a privacy policy";
  disclosure applies even to local-only processing; analytics allowed when "reasonably
  necessary to maintain, secure, or measure the performance and reliability" of the
  disclosed functionality.
- Ads: must be clearly disclosed, attributed, easily removable, never required to use the
  extension. Affiliate: disclosed on listing + UI + before install, user action each time.
- Publish: a new publisher is limited to **two published extensions** at first; more can
  be requested from the dashboard (`/docs/webstore/publish`).

## UNVERIFIED (do not state as fact)

Dashboard data-category definitions (e.g. whether opt-in click counts = "User activity" —
treat as declare-it); detailed-description and `short_name` limits; explicit HTTPS rule for
telemetry; any guidance on `optional_permissions`; in-depth review duration.

## Sources fetched

pp/spam-and-abuse · pp/quality-guidelines · pp/limited-use · pp/privacy · pp/user-data-faq ·
pp/disclosure-requirements · pp/listing-requirements · pp/minimum-functionality ·
pp/mv3-requirements · pp/code-readability · pp/ads · pp/affiliate-ads ·
pp/impersonation-and-intellectual-property · pp/permissions · pp/policies ·
/docs/webstore/cws-dashboard-privacy · /docs/webstore/cws-dashboard-listing ·
/docs/webstore/images · /docs/webstore/review-process · /docs/webstore/publish ·
/docs/extensions/reference/manifest/name · /docs/extensions/reference/manifest/description ·
/docs/extensions/develop/concepts/activeTab
