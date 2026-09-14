---
name: indexing
description: Assigning Miller indices and determining the unit cell (dials.index)
---

### Indexing Quality Indicators
- Good: >80% spots indexed
- RMS deviation: <0.3 pixels is excellent, <0.5 is acceptable
- If < 50% indexed: check for multiple lattices, ice rings, or wrong beam centre
- If indexing *succeeds* but reports more than one lattice (or a single crystal that
  looks split), don't assume it's genuinely multi-lattice yet — an incorrect initial
  beam centre commonly produces this exact pattern. Try
  `dials.search_beam_position imported.expt strong.refl` and re-index first; see the
  `troubleshooting` skill for the full reasoning (this is the failure mode covered in
  DIALS's "Correcting Poor Initial Geometry" tutorial).

### After Indexing (Geometry Check + Visualization)
Run the reciprocal-lattice linearity check (see the numeric check described in your base
instructions) automatically right after `dials.index` succeeds — don't wait to be asked.
- **Clean result**: briefly note geometry checks out. Still offer visualization as a normal
  option (not a warning): "Would you like to visualize the indexed reflections in reciprocal
  space?" → `dials.reciprocal_lattice_viewer indexed.expt indexed.refl` (colored by lattice;
  switch to "crystal frame" to see the reciprocal lattice directly). Then proceed to
  refinement.
- **Flagged (bent/spiral)**: explain the finding, actively suggest (not just offer) the user
  visually confirm with `dials.reciprocal_lattice_viewer indexed.expt indexed.refl` since you
  can't view it yourself, and propose the specific troubleshooting command(s) (e.g.
  `dials.search_beam_position`) — see `Indexing Quality Indicators` above and the
  `troubleshooting` skill.
