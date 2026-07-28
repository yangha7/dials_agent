"""Spot finding skill: locating diffraction spots on images (dials.find_spots)."""

from pathlib import Path

from ..base import BaseSkill, load_skill_md

_DESCRIPTION, _PROMPT_FRAGMENT = load_skill_md(Path(__file__).parent / "SKILL.md")


class SpotFindingSkill(BaseSkill):

    @property
    def name(self) -> str:
        return "spot_finding"

    @property
    def description(self) -> str:
        return _DESCRIPTION

    def get_prompt_fragment(self) -> str:
        return _PROMPT_FRAGMENT
