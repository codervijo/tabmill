"""Registered stages, in engine order. v2.B: clarify only."""

from __future__ import annotations

from ..engine import Stage
from .clarify import Clarify

REGISTERED: tuple[Stage, ...] = (Clarify(),)
PROMPTS: tuple[tuple[str, int], ...] = (("clarify", 1),)  # what `doctor` checks loads
