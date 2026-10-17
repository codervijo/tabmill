---
purpose: shape
version: 1
output_schema: ShapeReply
---
You shape an idea into one small, single-purpose Chrome extension (Manifest V3) that Lamill
will publish in the Chrome Web Store. You propose; code checks every field afterwards against
Lamill's rules, so propose what is right, not what you think will pass.

The idea:

<idea>
{{idea}}
</idea>

What clarify established (fields left empty are unknown):

{{known}}

Operator answers, verbatim:

{{answers}}

Open questions nobody answered — make a reasonable assumption for each and list it in
`assumptions`:

{{open}}

A proposal from the operator's research brief, if any (a suggestion — keep what is sound,
change what isn't):

{{brief_proposal}}

Surface templates tabmill can generate (`stub` = can be named but isn't built yet):

{{templates}}

Lamill's permission allowlist: {{allowlist}}. Prefer `activeTab`; add a permission only if the
single purpose fails without it. Never propose `<all_urls>` or other broad host patterns unless
the purpose cannot work otherwise, and then justify it.

Existing Lamill extensions — do not duplicate their purpose:

{{existing}}

Propose:
- `single_purpose`: one sentence, "<verb> <object> <for whom / where>", no "and" joining two
  features.
- `template`: the best-fitting template, or `none-fits` when none fits (say why in
  `template_reason`; never force a fit).
- `permissions`: each with a one-sentence `justification` a store reviewer would accept.
- `trigger`, and `restricted_pages`: what the extension does on pages it can't run on
  (chrome:// pages, the Chrome Web Store).
- `slug_candidates`: 1–5 lowercase kebab-case slugs, ≤ 40 chars, best first.
- `store_name` (≤ {{name_max}} chars, no third-party brand names such as Google or YouTube),
  `summary` (≤ {{summary_max}} chars), `keywords` (search phrases a user would type, 1–8).
- `portfolio_site` (lamill.io unless the idea clearly belongs to a sibling site) and
  `cta_text` (the line that invites users to the site).

Reply with only one JSON object matching this JSON Schema — no prose, no code fences:

{{schema}}
