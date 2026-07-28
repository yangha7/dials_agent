"""Export skill: exporting scaled data to MTZ/other formats (dials.export / dials.merge)."""

from pathlib import Path

from ..base import BaseSkill, load_skill_md

_DESCRIPTION, _PROMPT_FRAGMENT = load_skill_md(Path(__file__).parent / "SKILL.md")


class ExportSkill(BaseSkill):

    @property
    def name(self) -> str:
        return "export"

    @property
    def description(self) -> str:
        return _DESCRIPTION

    def get_prompt_fragment(self) -> str:
        return _PROMPT_FRAGMENT
