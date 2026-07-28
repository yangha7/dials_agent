"""Scaling skill: applying corrections and scaling data (dials.scale)."""

from pathlib import Path

from ..base import BaseSkill, load_skill_md

_DESCRIPTION, _PROMPT_FRAGMENT = load_skill_md(Path(__file__).parent / "SKILL.md")


class ScalingSkill(BaseSkill):

    @property
    def name(self) -> str:
        return "scaling"

    @property
    def description(self) -> str:
        return _DESCRIPTION

    def get_prompt_fragment(self) -> str:
        return _PROMPT_FRAGMENT
