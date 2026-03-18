"""Parse optional plugin-local skill.md metadata."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


@dataclass(slots=True)
class SkillDocument:
    """Structured representation of one plugin skill document."""

    path: str
    title: str = ""
    summary: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)
    content: str = ""


def parse_skill_file(path: str | Path) -> SkillDocument | None:
    """Parse a single `skill.md` file if it exists."""

    skill_path = Path(path)
    if not skill_path.exists() or not skill_path.is_file():
        return None

    raw_text = skill_path.read_text(encoding="utf-8").strip()
    metadata, body = _split_front_matter(raw_text)
    title, summary = _extract_title_and_summary(body)

    return SkillDocument(
        path=str(skill_path),
        title=title,
        summary=summary,
        metadata=metadata,
        content=body,
    )


def parse_plugin_skill(plugin_dir: str | Path) -> SkillDocument | None:
    """Parse `skill.md` from one plugin directory."""

    return parse_skill_file(Path(plugin_dir) / "skill.md")


def _split_front_matter(text: str) -> tuple[dict[str, Any], str]:
    if not text.startswith("---\n"):
        return {}, text

    end_marker = text.find("\n---\n", 4)
    if end_marker == -1:
        return {}, text

    front_matter = text[4:end_marker]
    body = text[end_marker + 5 :].strip()
    metadata = _parse_simple_front_matter(front_matter)
    return metadata, body


def _parse_simple_front_matter(front_matter: str) -> dict[str, Any]:
    metadata: dict[str, Any] = {}

    for line in front_matter.splitlines():
        if ":" not in line:
            continue
        key, value = line.split(":", 1)
        metadata[key.strip()] = value.strip().strip("'\"")

    return metadata


def _extract_title_and_summary(body: str) -> tuple[str, str]:
    title = ""
    summary = ""

    for line in body.splitlines():
        stripped = line.strip()
        if not stripped:
            continue
        if not title and stripped.startswith("#"):
            title = stripped.lstrip("#").strip()
            continue
        if not summary:
            summary = stripped
            break

    return title, summary


__all__ = ["SkillDocument", "parse_plugin_skill", "parse_skill_file"]
