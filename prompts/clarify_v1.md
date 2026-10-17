---
purpose: clarify
version: 1
output_schema: ClarifyReply
---
You help shape an idea for a small, single-purpose Chrome extension (Manifest V3) that Lamill
will publish in the Chrome Web Store. This is round {{round}} of at most {{max_rounds}} rounds of
questions to the operator who had the idea.

The idea, verbatim:

<idea>
{{idea}}
</idea>

Answers the operator has given so far:

{{answers}}

Your job:

1. Fill `known` with what the idea and the answers already state, in a few words each. Leave a
   field as "" when it isn't stated — do not guess or infer beyond the text.
   - `target_user`: who uses it.
   - `core_action`: the one thing it does.
   - `trigger`: how the user starts it (toolbar button, keyboard shortcut, right-click menu,
     side panel).
   - `pages`: which pages it works on or reads (any page, one site, the current tab only).
   - `done_looks_like`: what the user has when it worked.
2. Ask questions only about fields that are still "". At most {{max_questions}} questions. Ask
   nothing about a field that is already filled. Ask nothing if every field is filled.
   - Prefer multiple choice: give 2–5 short `choices` when the answer space is small. Leave
     `choices` empty only when a free-text answer is genuinely needed.
   - Set `about` to the field the question fills; use `other` only for a question that blocks
     the idea and fits no field.
   - One question per field. Plain words; no jargon.
3. Do not propose features, names, permissions or a verdict. That comes later.

Reply with only one JSON object matching this JSON Schema — no prose, no code fences:

{{schema}}
