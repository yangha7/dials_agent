---
name: export
description: Exporting scaled data to MTZ and other downstream formats (dials.export / dials.merge)
---

### Export Step Options
1. **Unmerged MTZ**: `dials.export scaled.expt scaled.refl` - for programs that merge themselves
2. **Merged MTZ**: `dials.merge scaled.expt scaled.refl` - for most downstream software

### After Export
No `dials.image_viewer`/`dials.reciprocal_lattice_viewer` needed — the output is now a
crystallographic file format (MTZ) for downstream software, not something these DIALS
viewers open.
