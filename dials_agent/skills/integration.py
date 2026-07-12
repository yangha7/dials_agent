"""Integration skill: measuring spot intensities (dials.integrate)."""

from .base import BaseSkill


class IntegrationSkill(BaseSkill):

    @property
    def name(self) -> str:
        return "integration"

    @property
    def description(self) -> str:
        return "Measuring spot intensities by profile fitting (dials.integrate)"

    def get_prompt_fragment(self) -> str:
        return """### Integration Quality Indicators
- Profile fitting should succeed for >90% of reflections
- Check for systematic patterns in integration failures

### dials.integrate parallelism
- Parameter: `integration.mp.nproc=N`
- Default: Auto (uses all available cores)
- **Advantages of more cores**: Faster integration — each core processes a block of rotation angles independently.
- **Disadvantages of more cores**: Integration is memory-intensive. Each process needs memory for shoeboxes. With too many cores, you may run out of memory and the program will crash or slow down due to swapping.
- **Recommendation**: Start with `nproc=4` or `nproc=8`. If memory is not an issue, increase. Use `integration.block.max_memory_usage=0.80` to control memory.

### After Integration (Visualization)
Optionally offer: `dials.image_viewer integrated.expt integrated.refl` - shows predicted reflection positions as red boxes on images"""
