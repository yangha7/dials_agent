# DIALS Algorithmic Optimization Opportunities

Beyond GPU acceleration, there are several algorithmic-level optimizations that could significantly improve performance for both `dials.find_spots` and `dials.integrate`.

---

## 1. `dials.find_spots` — Algorithmic Optimizations

### 1.1 The DispersionExtendedThreshold Does 4 Full Passes — Can Be Reduced

The default `dispersion_extended` algorithm in [`local.h`](../modules/dials/src/dials/algorithms/image/threshold/local.h) performs **4 sequential full-image passes** per panel per image:

```
Pass 1: compute_sat()                    — Build summed area table (SAT)
Pass 2: compute_dispersion_threshold()   — Dispersion test using SAT
Pass 3: erode_dispersion_mask()          — Chebyshev distance + erosion
         compute_sat() again             — Rebuild SAT excluding strong pixels
Pass 4: compute_final_threshold()        — Final threshold using cleaned SAT
```

**Optimization: Fuse passes 1+2 and 3+4**

The SAT construction and threshold computation could be fused into a single pass. Currently, `compute_sat()` writes the entire SAT to memory, then `compute_dispersion_threshold()` reads it back. These could be combined using a sliding-window approach that computes the SAT row-by-row and immediately applies the threshold, reducing memory bandwidth by ~50%.

**Estimated speedup: 1.3-1.5x for the threshold step**

### 1.2 Use the Simpler `dispersion` Algorithm Instead of `dispersion_extended`

The `dispersion` algorithm does only **2 passes** (SAT + threshold) vs. 4 for `dispersion_extended`. The extended version adds:
- Morphological erosion to remove strong pixels from the background estimate
- A second SAT pass with a wider kernel using the cleaned background

For many datasets, the simpler `dispersion` algorithm produces nearly identical results. This is a parameter change, not a code change:

```
dials.find_spots imported.expt spotfinder.threshold.algorithm=dispersion
```

**Estimated speedup: ~2x for the threshold step (half the passes)**

### 1.3 Avoid Redundant sqrt() Computations

In the threshold inner loop (line 496-498 of `local.h`):
```cpp
double c = x * nsig_b_ * std::sqrt(2 * (m - 1));
double d = nsig_s_ * std::sqrt(x * m);
dst[k] = a > c && b > d;
```

The `sqrt()` calls are expensive. Since we're only comparing `a > c` and `b > d`, we can square both sides:
```cpp
// Instead of: a > c  where c = x * nsig_b * sqrt(2*(m-1))
// Use:        a*a > c*c  where c*c = x*x * nsig_b*nsig_b * 2*(m-1)
// But only when a >= 0 and c >= 0
```

This eliminates 2 `sqrt()` calls per pixel. For a 16M pixel detector, that's 32M fewer sqrt operations per image.

**Estimated speedup: 1.1-1.2x for the threshold step**

### 1.4 SIMD Vectorization of the Threshold Loop

The inner threshold loop processes pixels sequentially. Modern CPUs support AVX2/AVX-512 SIMD instructions that can process 4-8 doubles simultaneously. The current code has data-dependent branches (`if (mask[k] && m >= min_count_ ...)`) that prevent auto-vectorization.

**Optimization**: Restructure the inner loop to be branchless:
```cpp
// Instead of:
if (mask[k] && m >= min_count_ && x >= 0 && src[k] > threshold_) {
    // compute and set
}

// Use:
double a = m * y - x * x - x * (m - 1);
double c = x * nsig_b_ * std::sqrt(2 * (m - 1));
double d = nsig_s_ * std::sqrt(x * m);
double b = m * src[k] - x;
dst[k] = mask[k] & (m >= min_count_) & (x >= 0) & (src[k] > threshold_) & (a > c) & (b > d);
```

With compiler hints (`#pragma omp simd` or explicit intrinsics), this could vectorize.

**Estimated speedup: 2-4x for the threshold step on AVX2 hardware**

### 1.5 Skip Masked Regions Early

The current code processes every pixel including masked regions. For detectors with significant masked areas (gaps between panels, beam stop shadow), a pre-pass to identify contiguous unmasked regions and only process those could save time.

**Estimated speedup: 1.1-1.3x depending on mask coverage**

### 1.6 Reduce Image I/O with Asynchronous Prefetching

Currently, image reading and threshold computation are sequential:
```
read image[i] → threshold image[i] → read image[i+1] → threshold image[i+1] → ...
```

With async I/O, the next image can be read while the current one is being thresholded:
```
read image[i] → threshold image[i] + read image[i+1] → threshold image[i+1] + read image[i+2] → ...
```

This overlaps I/O with computation. For HDF5 data with bitshuffle compression, decompression is CPU-bound, so this would need a separate thread for I/O.

**Estimated speedup: 1.2-1.5x (depends on I/O vs compute ratio)**

### 1.7 Use `radial_profile` Algorithm for Certain Data Types

The `radial_profile` threshold algorithm computes background in 2θ shells rather than local windows. It's:
- Faster for data with strong radial background variation
- Less sensitive to detector noise properties
- Already implemented in DIALS

```
dials.find_spots imported.expt spotfinder.threshold.algorithm=radial_profile
```

**Estimated speedup: varies, but can be 2-3x for electron diffraction data**

---

## 2. `dials.integrate` — Algorithmic Optimizations

### 2.1 Skip Profile Fitting for Initial Screening

Profile fitting is the most expensive step. For initial data assessment, summation integration is sufficient:

```
dials.integrate refined.expt refined.refl profile.fitting=False
```

**Estimated speedup: ~2x for the integration step**

### 2.2 Reduce Block Overlap

The integration processor splits data into rotation-angle blocks. Each block reads images for its range. If blocks overlap (to handle reflections spanning block boundaries), the same images are read multiple times.

**Optimization**: Cache recently-read images in a shared memory pool so overlapping blocks don't re-read from disk.

**Estimated speedup: 1.1-1.3x for I/O-bound scenarios**

### 2.3 Batch Shoebox Processing

Currently, the `ShoeboxProcessor` processes reflections one image at a time:
```python
for i in range(len(imageset)):
    image = imageset.get_corrected_data(i)
    mask = imageset.get_mask(i)
    processor.next(make_image(image, mask), self.executor)
```

The C++ `ShoeboxProcessor.next()` extracts pixels for all reflections that overlap with the current image. This is efficient, but the subsequent background estimation and profile fitting happen per-reflection.

**Optimization**: Batch the background estimation across all reflections in a block simultaneously, using vectorized operations on the shoebox arrays rather than iterating per-reflection.

**Estimated speedup: 1.3-1.5x for background + fitting steps**

### 2.4 Adaptive Resolution Cutoff During Integration

Many reflections at high resolution have very weak signal and contribute little to the final statistics. An adaptive approach could:
1. Integrate a subset of high-resolution reflections first
2. Estimate the effective resolution limit
3. Skip remaining high-resolution reflections below the limit

This is similar to what `dials.estimate_resolution` does post-hoc, but applied during integration.

**Estimated speedup: 1.2-2x depending on data quality**

### 2.5 Use the `3d_threaded` Integrator

DIALS has an experimental threaded integrator that uses C++ threads instead of Python multiprocessing:

```
dials.integrate refined.expt refined.refl integration.integrator=3d_threaded
```

This avoids pickle serialization overhead and can share memory between threads. It's marked as expert-level but is functional.

**Estimated speedup: 1.2-1.5x (avoids serialization overhead)**

### 2.6 Reduce Profile Model Complexity

The Gaussian RS profile model computes reference profiles on a grid. The default `grid_size=5` creates a 5×5×5 = 125-point grid per reflection. Reducing to `grid_size=3` (27 points) would be ~4.6x faster for profile fitting:

```
dials.integrate refined.expt refined.refl profile.gaussian_rs.fitting.grid_size=3
```

**Estimated speedup: 1.5-2x for profile fitting (with some quality trade-off)**

### 2.7 Parallelize Background and Profile Fitting Independently

Currently, background estimation and profile fitting are done sequentially within each task. Since they operate on different data (background on shoebox edges, fitting on shoebox center), they could be pipelined:

```
Block N:   [read images] → [extract shoeboxes] → [background] → [profile fit]
Block N+1:                  [read images] → [extract shoeboxes] → [background] → [profile fit]
```

With pipelining:
```
Block N:   [read] → [extract] → [background] → [profile fit]
Block N+1:          [read] → [extract] → [background] → [profile fit]
```

**Estimated speedup: 1.2-1.4x**

---

## 3. Cross-Cutting Optimizations (Both Steps)

### 3.1 Replace Python multiprocessing with C++ Threading

Both `find_spots` and `integrate` use Python's `multiprocessing` module, which:
- Pickles data between processes (expensive for large pixel lists and reflection tables)
- Has process startup overhead
- Cannot share memory efficiently

**Optimization**: Move the parallelism into C++ using `std::thread` or OpenMP, releasing the GIL. The C++ code already does the heavy computation — it just needs to be called from a thread pool instead of separate processes.

**Estimated speedup: 1.3-1.5x (eliminates pickle overhead)**

### 3.2 Memory Layout Optimization (Structure of Arrays)

The current `Data<T>` struct in the SAT uses Array of Structures (AoS):
```cpp
struct Data { int m; T x; T y; };  // AoS
```

For SIMD processing, Structure of Arrays (SoA) is better:
```cpp
int* m;    // separate arrays
T* x;
T* y;
```

SoA enables better cache utilization and SIMD vectorization.

**Estimated speedup: 1.2-1.5x for SAT computation**

### 3.3 Use Memory-Mapped I/O for HDF5

Instead of reading images through the HDF5 API (which involves decompression + copy), use direct memory mapping for uncompressed datasets or pre-decompress the entire file into a memory-mapped region.

**Estimated speedup: 1.1-1.3x for I/O**

### 3.4 Compile with Profile-Guided Optimization (PGO)

Recompile the C++ extensions with PGO:
1. Build with instrumentation
2. Run a representative workload
3. Rebuild using the profile data

This helps the compiler optimize branch prediction and code layout.

**Estimated speedup: 1.1-1.2x across all C++ code**

---

## Summary: Estimated Impact

### find_spots (currently 6m 14s)

| Optimization | Speedup | New Time | Effort |
|-------------|---------|----------|--------|
| Use `dispersion` instead of `dispersion_extended` | 1.5-2x | 3-4 min | Parameter change |
| Fuse SAT + threshold passes | 1.3-1.5x | 4-5 min | C++ refactor |
| Eliminate sqrt() in inner loop | 1.1-1.2x | 5-6 min | C++ change |
| SIMD vectorization | 2-4x | 1.5-3 min | C++ rewrite |
| Async I/O prefetching | 1.2-1.5x | 4-5 min | Python + threading |
| Combined (realistic) | **2-4x** | **1.5-3 min** | Medium |

### integrate (currently 5m 58s)

| Optimization | Speedup | New Time | Effort |
|-------------|---------|----------|--------|
| Summation-only | 2x | 3 min | Parameter change |
| `3d_threaded` integrator | 1.2-1.5x | 4-5 min | Parameter change |
| Reduce grid_size | 1.5-2x | 3-4 min | Parameter change |
| Batch shoebox processing | 1.3-1.5x | 4-5 min | C++ refactor |
| Adaptive resolution cutoff | 1.2-2x | 3-5 min | Python + C++ |
| Combined (realistic) | **2-3x** | **2-3 min** | Medium-High |

### Overall Pipeline (currently 15m 55s)

With algorithmic optimizations alone (no GPU), a realistic target is **6-8 minutes** — roughly a **2-2.5x speedup**.

With GPU acceleration on top, the target would be **2-4 minutes**.
