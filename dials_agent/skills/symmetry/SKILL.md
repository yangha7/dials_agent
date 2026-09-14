---
name: symmetry
description: Determining space group and resolving indexing ambiguity (dials.symmetry / dials.cosym)
---

### Choosing dials.symmetry vs. dials.cosym
- Single crystal: use `dials.symmetry`
- Multiple crystals / multi-lattice: use `dials.cosym` instead — it also resolves indexing ambiguity across datasets

### After Symmetry (Visualization)
- **After `dials.cosym`** (multi-crystal case): since cosym can reindex individual datasets
  to a consistent setting, offer to confirm this visually: "Would you like to check that all
  datasets are now consistently indexed?" → `dials.reciprocal_lattice_viewer` with the
  reindexed experiment/reflection files together — datasets that are still inconsistent will
  show as misaligned reciprocal lattices rather than overlapping cleanly.
- **After `dials.symmetry`** (single crystal): no image/reciprocal-lattice viewer needed here
  — the lattice geometry was already checked after indexing/refinement, and symmetry
  determination doesn't change it. Look at the symmetry log / HTML report if generated
  instead.
