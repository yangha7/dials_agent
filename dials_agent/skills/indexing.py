"""Indexing skill: assigning Miller indices and determining the unit cell (dials.index)."""

from .base import BaseSkill


class IndexingSkill(BaseSkill):

    @property
    def name(self) -> str:
        return "indexing"

    @property
    def description(self) -> str:
        return "Assigning Miller indices and determining the unit cell (dials.index)"

    def get_prompt_fragment(self) -> str:
        return """### Indexing Quality Indicators
- Good: >80% spots indexed
- RMS deviation: <0.3 pixels is excellent, <0.5 is acceptable
- If < 50% indexed: check for multiple lattices, ice rings, or wrong beam centre

### After Indexing (Visualization)
Ask: "Would you like to visualize the indexed reflections in reciprocal space?"
- **Yes**: Suggest `dials.reciprocal_lattice_viewer indexed.expt indexed.refl` - shows indexed spots colored by lattice; you can switch to "crystal frame" to see the reciprocal lattice. This is the first point where the reciprocal lattice viewer is useful.
- **No**: Proceed to refinement"""
