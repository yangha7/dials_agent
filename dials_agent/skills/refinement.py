"""Refinement skill: improving crystal and detector models (dials.refine)."""

from .base import BaseSkill


class RefinementSkill(BaseSkill):

    @property
    def name(self) -> str:
        return "refinement"

    @property
    def description(self) -> str:
        return "Improving crystal and detector models (dials.refine)"

    def get_prompt_fragment(self) -> str:
        return """### Refinement Quality Indicators
- RMSD should decrease during refinement
- Scan-varying refinement should show smooth parameter changes
- Large jumps in scan-varying parameters suggest problems"""
