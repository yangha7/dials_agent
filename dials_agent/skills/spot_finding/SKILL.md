---
name: spot_finding
description: Finding diffraction spots on images using threshold algorithms (dials.find_spots)
---

### Spot Finding Quality Indicators
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
Default to suggesting `dials.index` directly, mentioning in the same message that
`dials.image_viewer imported.expt strong.refl` is available if they want to see the found
spots overlaid on the images first — don't ask and wait. Do NOT mention
`dials.reciprocal_lattice_viewer` at this stage — it requires indexed data to show anything
meaningful; that's the next step's viewer, not this one's.
