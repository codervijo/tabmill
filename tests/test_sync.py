from __future__ import annotations

from tabmill import skills, sync, workspace
from tabmill.config import TOOL_DIR, Config
from tabmill.constants import GENERATED_MARKER

SKILL = ".claude/skills/chrome-store-policy/SKILL.md"


def _sync(cfg: Config, force: bool = False) -> sync.SyncResult:
    return sync.sync(cfg.workspace, workspace.managed_files(cfg), force=force)


def test_first_sync_installs_managed_files(cfg: Config) -> None:
    r = _sync(cfg)
    assert not r.refused
    for rel in (
        SKILL,
        "CLAUDE.md",
        "Makefile",
        "Makefile.local",
        "pnpm-workspace.yaml",
        ".github/workflows/extensions.yml",
    ):
        assert rel in r.installed, rel
    claude = (cfg.workspace / "CLAUDE.md").read_text()
    assert claude.startswith(GENERATED_MARKER)
    assert "**tabmill-release**" in claude


def test_resync_is_idempotent(cfg: Config) -> None:
    _sync(cfg)
    r = _sync(cfg)
    assert r.installed == r.updated == r.removed == []
    assert SKILL in r.unchanged


def test_template_change_reaches_workspace(cfg: Config) -> None:
    _sync(cfg)
    tmpl = cfg.tool_dir / "templates/workspace/managed/Makefile.local.tmpl"
    tmpl.write_text(tmpl.read_text() + "\n# new rule\n")
    r = _sync(cfg)
    assert r.updated == ["Makefile.local"]


def test_source_change_updates_installed_skill(cfg: Config) -> None:
    _sync(cfg)
    src = cfg.tool_dir / "skills/chrome-store-policy/SKILL.md"
    src.write_text(src.read_text() + "\nnew line\n")
    assert _sync(cfg).updated == [SKILL]


def test_hand_edit_is_refused_then_forced(cfg: Config) -> None:
    _sync(cfg)
    installed = cfg.workspace / SKILL
    installed.write_text("hand edit")
    r = _sync(cfg)
    assert r.refused and r.drift == [SKILL]
    assert installed.read_text() == "hand edit"  # nothing written on refusal
    r = _sync(cfg, force=True)
    assert SKILL in r.updated
    assert installed.read_text() != "hand edit"


def test_untracked_collision_counts_as_drift(cfg: Config) -> None:
    cfg.workspace.mkdir(parents=True)
    (cfg.workspace / "Makefile").write_text("someone else's Makefile")
    assert _sync(cfg).drift == ["Makefile"]


def test_file_dropped_from_source_is_removed(cfg: Config) -> None:
    _sync(cfg)
    (cfg.tool_dir / "skills/tabmill-release/reference.md").unlink()
    rel = ".claude/skills/tabmill-release/reference.md"
    assert _sync(cfg).removed == [rel]
    assert not (cfg.workspace / rel).exists()


def test_frontmatter_parse() -> None:
    meta = skills.parse_frontmatter("---\nname: x\ndescription: Use when: y\n---\nbody")
    assert meta == {"name": "x", "description": "Use when: y"}


def test_real_skill_sources_have_frontmatter_and_fit_size() -> None:
    for s in skills.load_skills(TOOL_DIR):
        assert s.name and s.description, s.name
        assert len(s.description) <= 1536, s.name
        assert s.files["SKILL.md"].decode().count("\n") <= 150, s.name
    assert (TOOL_DIR / ".claude/skills/tabmill-dev/SKILL.md").exists()
