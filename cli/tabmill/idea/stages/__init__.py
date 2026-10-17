"""Registered stages, in engine order."""

from __future__ import annotations

from ..engine import Stage
from .check import Check
from .clarify import Clarify
from .shape import Shape

REGISTERED: tuple[Stage, ...] = (Clarify(), Shape(), Check())
PROMPTS: tuple[tuple[str, int], ...] = (("clarify", 1), ("shape", 1))  # `doctor` loads these
