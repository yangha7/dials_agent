"""Symmetry skill: determining the space group (dials.symmetry / dials.cosym)."""

from .base import BaseSkill


class SymmetrySkill(BaseSkill):

    @property
    def name(self) -> str:
        return "symmetry"

    @property
    def description(self) -> str:
        return "Determining space group and resolving indexing ambiguity (dials.symmetry / dials.cosym)"

    def get_prompt_fragment(self) -> str:
        return """### Choosing dials.symmetry vs. dials.cosym
- Single crystal: use `dials.symmetry`
- Multiple crystals / multi-lattice: use `dials.cosym` instead — it also resolves indexing ambiguity across datasets"""
