---
name: integration
description: Measuring spot intensities by profile fitting (dials.integrate)
---

### Integration Quality Indicators
- Profile fitting should succeed for >90% of reflections
- Check for systematic patterns in integration failures

### dials.integrate parallelism
- Parameter: `integration.mp.nproc=N`
- Default: Auto (uses all available cores)
- **Advantages of more cores**: Faster integration — each core processes a block of rotation angles independently.
- **Disadvantages of more cores**: Integration is memory-intensive. Each process needs memory for shoeboxes. With too many cores, you may run out of memory and the program will crash or slow down due to swapping.
- **Recommendation**: Start with `nproc=4` or `nproc=8`. If memory is not an issue, increase. Use `integration.block.max_memory_usage=0.80` to control memory.

### After Integration (Visualization)
Report the integration statistics, then offer numbered options and wait (see "Step
Transitions" in your base instructions): 1. Proceed to the next step below (default) 2. View
predicted reflection positions on the images first (`dials.image_viewer integrated.expt
integrated.refl` — useful for spotting systematic prediction offsets) 3. Something else.
`dials.reciprocal_lattice_viewer` isn't useful here — the lattice itself doesn't change during
integration; it was already checked after indexing and refinement.

### After Integration (Centring vs. Pseudo-centring Check)
Now that real intensities exist, run the numeric centring/pseudo-centring check described in
your base instructions — this is the first point in the workflow where it's possible (it
needs intensity data, not just geometry). Do this proactively, before/alongside the `symmetry`
skill's choice between `dials.symmetry` and `dials.cosym`. A flagged result changes what to
watch for during symmetry determination, so surface it before that step rather than after.
