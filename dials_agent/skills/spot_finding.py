"""Spot finding skill: locating diffraction spots on images (dials.find_spots)."""

from .base import BaseSkill


class SpotFindingSkill(BaseSkill):

    @property
    def name(self) -> str:
        return "spot_finding"

    @property
    def description(self) -> str:
        return "Finding diffraction spots on images using threshold algorithms (dials.find_spots)"

    def get_prompt_fragment(self) -> str:
        return """### Spot Finding Quality Indicators
- Good: 5,000-50,000 spots total
- Spots should be evenly distributed across images
- Very few spots (< 1000): lower sigma_strong, check data quality
- Too many spots (> 100,000): raise sigma_strong, check for powder rings

### dials.find_spots parallelism
- Parameter: `spotfinder.mp.nproc=N`
- Default: Auto (uses all available cores)
- **Advantages of more cores**: Faster spot finding — each core processes a chunk of images independently. Near-linear speedup up to ~8-16 cores.
- **Disadvantages of more cores**: Higher memory usage (each process loads images independently). On shared systems, using all cores may impact other users.
- **Recommendation**: For a dedicated workstation, use all cores. For a shared cluster, use half the available cores (e.g., `nproc=8` on a 16-core node).

### After Spot Finding (Visualization)
Ask: "Would you like to visualize the found spots on the diffraction images?"
- **View on images**: Suggest `dials.image_viewer imported.expt strong.refl` - shows spots overlaid on diffraction images with bounding boxes
- **Skip**: Proceed to indexing
- **NOTE**: Do NOT suggest `dials.reciprocal_lattice_viewer` at this stage — it requires indexed data to show meaningful results. The reciprocal lattice viewer should only be used AFTER indexing."""
