"""Registered stages, in engine order."""

from __future__ import annotations

from ..engine import Stage
from .check import Check
from .clarify import Clarify
from .evidence import Evidence
from .shape import Shape
from .verdict import Verdict
from .write import Write

REGISTERED: tuple[Stage, ...] = (Clarify(), Shape(), Evidence(), Check(), Verdict(), Write())
PROMPTS: tuple[tuple[str, int], ...] = (
    ("clarify", 1),
    ("shape", 1),
    ("verdict", 1),
)  # `doctor` loads these
