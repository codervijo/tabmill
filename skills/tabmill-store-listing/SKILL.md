---
name: tabmill-store-listing
description: Write the Chrome Web Store listing for a Tabmill extension — title, 132-char summary, detailed description, screenshot captions, permission justifications, privacy-practices answers — from extension.yaml and its target_keywords. Use when the user asks for a listing, store copy, store description, screenshot captions, or when tabmill-release reaches its listing step.
---

# Tabmill store listing

> DRAFT (v1.A, 2026-10-03). Output path and `tabmill listing` *(planned v1.G)* may change.
> Limits verified 2026-10-03; see `chrome-store-policy` for sources.

## Inputs

The recipe `tabmill/recipes/<slug>/extension.yaml` (the generated copy in
`extensions/<slug>/README.md` summarizes it): `name`, `single_purpose`, `target_keywords`,
`permissions` + justifications, `analytics`, `cta_text`, `cta_url`, `portfolio_site`,
`landing_page_url`, `store_category`. Read the built extension's UI too — the listing must
describe what it actually does.

## Output

Write `extensions/<slug>/listing.md` with these sections, in order:

1. **Title** — the manifest `name`, ≤ 75 chars. Lead with the job ("Save Page as Markdown or
   PDF"), not "Lamill …". No "#1", "official", "best", no third-party trademarks.
2. **Summary** — the manifest `description`, ≤ 132 chars, plain text. One sentence naming the
   job and the main keyword once.
3. **Detailed description** — 3–6 short paragraphs:
   - what it does, in the user's words (the single purpose);
   - how to use it (2–4 steps);
   - privacy: what stays local, what (if anything) is sent where, analytics on/off;
   - permissions, plain-language reason for each;
   - "Built by Lamill" line with the portfolio site, and the CTA as an optional next step.
4. **Screenshot captions** — one per screenshot (1–5), each showing the purpose in action.
5. **Permission justifications** — one line per permission, copied from YAML, for the
   dashboard's Privacy practices tab.
6. **Privacy practices answers** — single-purpose statement, remote code: No, data
   categories (none, unless analytics), the three Limited Use certifications, privacy policy URL.

## Keyword rules

- Use each target keyword naturally, at most a few times; **no term more than 5 times**
  across the listing (policy limit). No keyword lists or lists of site/brand names.
- Search intent targets the tool ("markdown to pdf"), so write for that phrasing in the
  summary and first paragraph.
- The landing page (`tabmill-landing-page`) targets the web search; the listing targets
  in-store search. Don't copy text between them verbatim.

## Self-check before handing back

Run the listing items of the `chrome-store-policy` checklist. Count characters for title and
summary and state the counts. Flag any claim the extension doesn't actually deliver.
