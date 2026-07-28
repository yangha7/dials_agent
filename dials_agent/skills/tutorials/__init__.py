"""Tutorials skill: guided, step-by-step walkthroughs of built-in example datasets."""

from pathlib import Path

from ..base import BaseSkill, load_skill_md

_DESCRIPTION, _PROMPT_TEMPLATE = load_skill_md(Path(__file__).parent / "SKILL.md")


class TutorialsSkill(BaseSkill):

    @property
    def name(self) -> str:
        return "tutorials"

    @property
    def description(self) -> str:
        return _DESCRIPTION

    def get_prompt_fragment(self) -> str:
        from ...core.tutorials import get_tutorial_prompt_section

        tutorials_section = get_tutorial_prompt_section()
        return _PROMPT_TEMPLATE.replace("{{tutorials_section}}", tutorials_section)
