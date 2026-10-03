"""`{{name}}` placeholder rendering. Not `string.Template`: Makefiles are full of `$(...)`."""

from __future__ import annotations

import re

_PLACEHOLDER = re.compile(r"\{\{\s*([a-z_]+)\s*\}\}")


class TemplateError(Exception):
    """A template references a value the caller didn't provide."""


def render(text: str, values: dict[str, str]) -> str:
    def repl(m: re.Match[str]) -> str:
        key = m.group(1)
        if key not in values:
            raise TemplateError(f"template placeholder {{{{{key}}}}} has no value")
        return values[key]

    return _PLACEHOLDER.sub(repl, text)
