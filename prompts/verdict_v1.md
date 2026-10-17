---
purpose: verdict
version: 1
output_schema: VerdictReply
---
You score one proposed Chrome extension for Lamill. Lamill is a pre-revenue studio of small,
single-purpose, privacy-respecting browser and web tools, published under the Lamill name with
a hub at lamill.io. It is building an audience first; each store listing links back to a Lamill
site. Lamill has a small number of Chrome Web Store slots, so every extension must earn one.

You score; code computes the weighted total and the verdict, and caps it when the evidence is
weak. Score what the evidence supports. Do not invent numbers: when evidence is missing or only
AI synthesis, say so in the reason and score conservatively.

The idea:

<idea>
{{idea}}
</idea>

The shaped extension:

{{concept}}

Assumptions made for open questions:

{{assumptions}}

Evidence — every row has a kind: real (fetched by tabmill), external (a sourced row), user,
external_suggestion, synthesis (an AI guess or an unsourced row), missing (looked for, not
found):

{{evidence}}

Rule check results:

{{findings}}

Existing Lamill extensions:

{{existing}}

Score each dimension 0–10 (10 = best for Lamill) with a one- or two-sentence reason that cites
the evidence rows it rests on:
- `reach`: how many Chrome Web Store users plausibly look for this.
- `outrate`: how likely Lamill's version beats the incumbents (ratings, freshness, privacy,
  simplicity) — judge from store competition evidence; without it, say so.
- `audience`: fit with the people Lamill's sites serve, and the link back to lamill.io.
- `risk`: 10 = low policy, privacy and support risk; low = sensitive permissions, brittle
  pages, high support load.
- `effort`: 10 = small build on an existing template; low = new template or heavy logic.

Also list the main `risks` (short phrases) and `needs_evidence`: the evidence that would most
change the scores.

Reply with only one JSON object matching this JSON Schema — no prose, no code fences:

{{schema}}
