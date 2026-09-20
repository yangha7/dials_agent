#!/bin/bash
# Fetch detailed PHIL parameter documentation for all DIALS commands
# Usage: source dials && bash dials_agent/docs/fetch_phil_params.sh
#
# Output must stay inside dials_agent/docs/ (not the outer repo docs/) so it
# ships via both `git clone` and sync_to_remote.sh, which only syncs dials_agent/.

source /Users/yha/DIALS_2026/conda_base/etc/profile.d/conda.sh
conda activate /Users/yha/DIALS_2026/conda_base

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
OUTDIR="$SCRIPT_DIR/phil_params"
mkdir -p "$OUTDIR"

# List of all DIALS commands
COMMANDS=(
    dials.align_crystal
    dials.anvil_correction
    dials.apply_mask
    dials.assign_experiment_identifiers
    dials.augment_spots
    dials.background
    dials.check_indexing_symmetry
    dials.cluster_unit_cell
    dials.combine_experiments
    dials.compare_orientation_matrices
    dials.complete_full_sphere
    dials.compute_delta_cchalf
    dials.convert_to_cbf
    dials.correlation_matrix
    dials.cosym
    dials.create_profile_model
    dials.damage_analysis
    dials.detect_blanks
    dials.estimate_gain
    dials.estimate_resolution
    dials.export
    dials.export_best
    dials.export_bitmaps
    dials.filter_reflections
    dials.find_bad_pixels
    dials.find_hot_pixels
    dials.find_rotation_axis
    dials.find_spots
    dials.find_spots_client
    dials.find_spots_server
    dials.frame_orientations
    dials.generate_distortion_maps
    dials.generate_mask
    dials.geometry_viewer
    dials.goniometer_calibration
    dials.image_viewer
    dials.import
    dials.import_xds
    dials.index
    dials.indexed_as_integrated
    dials.integrate
    dials.merge
    dials.merge_cbf
    dials.merge_reflection_lists
    dials.missing_reflections
    dials.model_background
    dials.modify_experiments
    dials.modify_geometry
    dials.plot_Fo_vs_Fc
    dials.plot_reflections
    dials.plot_scan_varying_model
    dials.powder_calibrate
    dials.predict
    dials.reciprocal_lattice_viewer
    dials.reference_profile_viewer
    dials.refine
    dials.refine_bravais_settings
    dials.refine_error_model
    dials.reflection_viewer
    dials.reindex
    dials.report
    dials.rl_png
    dials.rs_mapper
    dials.scale
    dials.search_beam_position
    dials.sequence_to_stills
    dials.shadow_plot
    dials.show
    dials.slice_sequence
    dials.sort_reflections
    dials.split_experiments
    dials.split_still_data
    dials.spot_counts_per_image
    dials.spot_resolution_shells
    dials.ssx_index
    dials.ssx_integrate
    dials.stereographic_projection
    dials.stills_process
    dials.symmetry
    dials.tof_integrate
    dials.two_theta_offset
    dials.two_theta_refine
    dials.unit_cell_histogram
)

SUCCESS=0
FAIL=0

for cmd in "${COMMANDS[@]}"; do
    filename=$(echo "$cmd" | tr '.' '_')
    outfile="$OUTDIR/${filename}.txt"
    echo "Fetching: $cmd -> $outfile"
    
    # Try -c -e2 -a2 first, fall back to -c -e2, then -c, then --help
    if $cmd -c -e2 -a2 > "$outfile" 2>&1; then
        echo "  OK (full params)"
        SUCCESS=$((SUCCESS + 1))
    elif $cmd -c -e2 > "$outfile" 2>&1; then
        echo "  OK (expert level 2)"
        SUCCESS=$((SUCCESS + 1))
    elif $cmd -c > "$outfile" 2>&1; then
        echo "  OK (basic params)"
        SUCCESS=$((SUCCESS + 1))
    elif $cmd --help > "$outfile" 2>&1; then
        echo "  OK (help only)"
        SUCCESS=$((SUCCESS + 1))
    else
        echo "  FAILED"
        echo "# No parameter documentation available for $cmd" > "$outfile"
        FAIL=$((FAIL + 1))
    fi
done

echo ""
echo "Done! Success: $SUCCESS, Failed: $FAIL"
echo "Output directory: $OUTDIR"
