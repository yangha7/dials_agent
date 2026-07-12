"""Export skill: exporting scaled data to MTZ/other formats (dials.export / dials.merge)."""

from .base import BaseSkill


class ExportSkill(BaseSkill):

    @property
    def name(self) -> str:
        return "export"

    @property
    def description(self) -> str:
        return "Exporting scaled data to MTZ and other downstream formats (dials.export / dials.merge)"

    def get_prompt_fragment(self) -> str:
        return """### Export Step Options
1. **Unmerged MTZ**: `dials.export scaled.expt scaled.refl` - for programs that merge themselves
2. **Merged MTZ**: `dials.merge scaled.expt scaled.refl` - for most downstream software"""
