"""
Shared helper: group reflections into "systematic rows" by Miller index.

A systematic row fixes two of the three Miller indices and lets the third
vary -- e.g. all reflections with (h,k) = (2,-1), for whatever l values were
observed. Both the reciprocal-lattice geometry check
(`reciprocal_lattice_linearity.py`) and the centring/pseudo-centring
intensity check (`centring_vs_pseudocentring_check.py`) need this same
grouping; only what they *compute* per row differs (line-fit residual vs.
intensity alternation), so the grouping itself lives here once.
"""
import numpy as np

MIN_POINTS_PER_ROW = 5
MAX_ROWS_PER_FAMILY = 400  # cap for speed on very dense datasets

# (family label, columns held fixed, column that varies)
ROW_FAMILIES = [
    ("h,k fixed (rows along c*)", (0, 1), 2),
    ("h,l fixed (rows along b*)", (0, 2), 1),
    ("k,l fixed (rows along a*)", (1, 2), 0),
]


def iter_systematic_rows(miller_indices: np.ndarray, min_points: int = MIN_POINTS_PER_ROW,
                          max_rows_per_family: int = MAX_ROWS_PER_FAMILY):
    """
    Yield (family_name, fixed_indices, varying_index_values, row_mask) for
    every systematic row with enough points to be worth analyzing.

    `row_mask` is a boolean array selecting this row's reflections out of
    the original `miller_indices` (and therefore out of any same-length
    array of per-reflection data the caller wants to pull alongside it,
    e.g. rlp coordinates or intensities).
    """
    for family_name, fixed_cols, varying_col in ROW_FAMILIES:
        keys = miller_indices[:, fixed_cols]
        uniq, inverse = np.unique(keys, axis=0, return_inverse=True)
        n_rows_used = 0
        for row_id in range(len(uniq)):
            if n_rows_used >= max_rows_per_family:
                break
            mask = inverse == row_id
            n = int(mask.sum())
            if n < min_points:
                continue
            varying_values = miller_indices[mask, varying_col]
            if len(np.unique(varying_values)) < min_points:
                continue
            n_rows_used += 1
            yield family_name, tuple(int(v) for v in uniq[row_id]), varying_values, mask
