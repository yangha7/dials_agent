---
name: scaling
description: Applying absorption/decay corrections and scaling data (dials.scale)
---

### Scaling Quality Indicators
- Rmerge: <10% overall is good, <5% is excellent
- CC1/2: >0.5 in outer shell is common cutoff, >0.3 is acceptable
- Completeness: >95% is good, >99% is excellent
- Multiplicity: >3 is good, >5 is excellent
- I/σ(I): >2 in outer shell is common cutoff
- Anomalous signal: if CC_anom > 0.3 in inner shells, anomalous signal is present

### Scaling Step Options
1. **Standard scaling**: `dials.scale symmetrized.expt symmetrized.refl`
2. **Anomalous data**: `dials.scale symmetrized.expt symmetrized.refl anomalous=True`
3. **High absorption**: Add `absorption_level=medium` or `absorption_level=high`

### After Scaling
Proactively open the HTML report: Use the `open_file` tool to open `dials.scale.html` which contains detailed statistics and diagnostic plots.
