"""Workspace skill sources (TOOL_DIR/skills/<name>/SKILL.md + supporting files)."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from .constants import SKILLS_DST_DIR, SKILLS_SRC_DIR


@dataclass(frozen=True)
class Skill:
    name: str
    description: str
    files: dict[str, bytes]  # path relative to the skill dir → content


def parse_frontmatter(text: str) -> dict[str, str]:
    """Minimal `key: value` frontmatter reader (SKILL.md frontmatter is flat)."""
    lines = text.splitlines()
    if not lines or lines[0].strip() != "---":
        return {}
    meta: dict[str, str] = {}
    for line in lines[1:]:
        if line.strip() == "---":
            break
        key, sep, value = line.partition(":")
        if sep:
            meta[key.strip()] = value.strip()
    return meta


def load_skills(tool_dir: Path) -> list[Skill]:
    skills: list[Skill] = []
    for skill_dir in sorted(p for p in (tool_dir / SKILLS_SRC_DIR).iterdir() if p.is_dir()):
        skill_md = skill_dir / "SKILL.md"
        if not skill_md.exists():
            continue
        meta = parse_frontmatter(skill_md.read_text())
        files = {
            str(f.relative_to(skill_dir)): f.read_bytes()
            for f in sorted(skill_dir.rglob("*"))
            if f.is_file()
        }
        skills.append(
            Skill(
                name=meta.get("name", skill_dir.name),
                description=meta.get("description", ""),
                files=files,
            )
        )
    return skills


def installed_files(skills: list[Skill]) -> dict[str, bytes]:
    """Skill files keyed by their path relative to the workspace."""
    return {
        f"{SKILLS_DST_DIR}/{s.name}/{rel}": data for s in skills for rel, data in s.files.items()
    }


def index_markdown(skills: list[Skill]) -> str:
    return "\n".join(f"- **{s.name}** — {s.description}" for s in skills)
