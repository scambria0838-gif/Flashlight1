"""Skill loading: inject real workflow instructions into agent context.

Skills are Markdown workflow modules (SKILL.md files with YAML
frontmatter) vendored in the repository's skills/ directory from
https://github.com/addyosmani/agent-skills (MIT). Loading a skill
prepends its full, real content to the agent's conversation as a
system message — nothing is summarized, paraphrased or stubbed.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

DEFAULT_SKILLS_DIR = Path(__file__).resolve().parents[2] / "skills"

# qwen2.5:1.5b agents run with num_ctx 8192 (~32 KB of text). Warn when
# injected skills leave little room for the task and the answer.
SKILL_BUDGET_BYTES = 24_000


class SkillError(RuntimeError):
    pass


@dataclass
class Skill:
    key: str
    name: str
    description: str
    content: str
    path: Path


def _skills_dir() -> Path:
    return Path(os.environ.get("FLASHLIGHT_SKILLS_DIR", DEFAULT_SKILLS_DIR))


def _parse_frontmatter(text: str) -> tuple[dict[str, str], str]:
    """Parse the simple `key: value` YAML frontmatter used by SKILL.md."""
    if not text.startswith("---"):
        return {}, text
    lines = text.splitlines()
    meta: dict[str, str] = {}
    for idx, line in enumerate(lines[1:], start=1):
        if line.strip() == "---":
            body = "\n".join(lines[idx + 1:]).lstrip("\n")
            return meta, body
        if ":" in line:
            key, _, value = line.partition(":")
            meta[key.strip()] = value.strip()
    return {}, text


def list_skills() -> list[Skill]:
    root = _skills_dir()
    if not root.is_dir():
        return []
    skills = []
    for skill_md in sorted(root.glob("*/SKILL.md")):
        text = skill_md.read_text(encoding="utf-8")
        meta, _ = _parse_frontmatter(text)
        key = skill_md.parent.name
        skills.append(
            Skill(
                key=key,
                name=meta.get("name", key),
                description=meta.get("description", ""),
                content=text,
                path=skill_md,
            )
        )
    return skills


def load_skill(key: str) -> Skill:
    root = _skills_dir()
    skill_md = root / key / "SKILL.md"
    if not skill_md.is_file():
        available = ", ".join(s.key for s in list_skills()) or "(none installed)"
        raise SkillError(
            f"Skill not found: {key!r}. Available skills: {available}"
        )
    text = skill_md.read_text(encoding="utf-8")
    meta, _ = _parse_frontmatter(text)
    return Skill(
        key=key,
        name=meta.get("name", key),
        description=meta.get("description", ""),
        content=text,
        path=skill_md,
    )


def skills_system_message(keys: list[str]) -> tuple[dict, int]:
    """Build one system message carrying the full content of each skill.

    Returns the message and the total content size in bytes so callers
    can warn when the context budget is tight.
    """
    parts = [
        "Follow these skill workflows while completing the task. They are "
        "authoritative process instructions, not reference material:"
    ]
    total = 0
    for key in keys:
        skill = load_skill(key)
        total += len(skill.content.encode("utf-8"))
        parts.append(f"\n===== SKILL: {skill.name} =====\n{skill.content}")
    return {"role": "system", "content": "\n".join(parts)}, total
