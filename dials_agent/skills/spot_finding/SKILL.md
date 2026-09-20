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
Report the spot count/distribution, then offer numbered options and wait (see "Step
Transitions" in your base instructions):
1. Proceed to `dials.index` (default)
2. Check reciprocal-lattice geometry first (`dials.reciprocal_lattice_viewer imported.expt
   strong.refl`) — this works even before indexing (reflection positions come from pixel
   coordinates + geometry, not Miller indices), and is exactly the check DIALS's own
   SLAC-2026 workflow tutorial uses here: rotate the view and look for straight lines; if
   they're crooked, the beam centre/detector distance may be off.
3. Run `dials.search_beam_position imported.expt strong.refl` (optional, not required —
   "for a well-calibrated beamline... it does no harm" per that tutorial). If run, use its
   `optimised.expt` output for indexing instead of `imported.expt`.
4. View the raw images (`dials.image_viewer imported.expt strong.refl`)
5. Something else.
