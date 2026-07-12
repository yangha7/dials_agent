"""Troubleshooting skill: diagnosing common DIALS processing problems."""

from .base import BaseSkill, SkillContext

TOOLS: list[dict] = [
    {
        "name": "suggest_troubleshooting",
        "description": "Suggest troubleshooting steps for a problem the user is experiencing. Use this when something has gone wrong or the user is confused.",
        "input_schema": {
            "type": "object",
            "properties": {
                "problem": {
                    "type": "string",
                    "description": "Description of the problem or error"
                },
                "context": {
                    "type": "string",
                    "description": "Additional context like the command that failed, error messages, etc."
                }
            },
            "required": ["problem"]
        }
    },
    {
        "name": "diagnose_problem",
        "description": "Diagnose a DIALS processing problem and suggest parameter-level fixes. Use this when the user reports an issue like 'indexing failed', 'too few spots', 'high Rmerge', 'low completeness', etc. Returns specific parameter suggestions based on common crystallography problems.",
        "input_schema": {
            "type": "object",
            "properties": {
                "problem": {
                    "type": "string",
                    "description": "Description of the problem (e.g., 'indexing failed', 'too few spots found', 'high Rmerge after scaling', 'low resolution', 'multiple lattices')"
                },
                "current_stage": {
                    "type": "string",
                    "description": "Current workflow stage (e.g., 'find_spots', 'index', 'refine', 'integrate', 'scale')"
                },
                "context": {
                    "type": "string",
                    "description": "Additional context like error messages, metrics, or data characteristics"
                }
            },
            "required": ["problem"]
        }
    },
]

# Comprehensive problem → solution mapping based on PHIL parameters
PROBLEM_SOLUTIONS = {
    # === Spot Finding Problems ===
    "too_few_spots": {
        "description": "Too few spots found (< 1000)",
        "stage": "find_spots",
        "solutions": [
            {
                "action": "Lower the sigma threshold to detect weaker spots",
                "params": ["spotfinder.threshold.dispersion.sigma_strong=2.0"],
                "explanation": "Default is 3.0. Lowering to 2.0 finds more spots but may include noise."
            },
            {
                "action": "Lower the global threshold",
                "params": ["spotfinder.threshold.dispersion.global_threshold=0"],
                "explanation": "Set to 0 to not apply a global intensity cutoff."
            },
            {
                "action": "Reduce minimum spot size",
                "params": ["spotfinder.filter.min_spot_size=1"],
                "explanation": "Default is Auto (3 for pixel detectors). Reducing allows smaller spots."
            },
            {
                "action": "Extend resolution range",
                "params": ["spotfinder.filter.d_min=1.0", "spotfinder.filter.d_max=100"],
                "explanation": "Widen the resolution range to include more spots."
            },
            {
                "action": "Try a different threshold algorithm",
                "params": ["spotfinder.threshold.algorithm=radial_profile"],
                "explanation": "radial_profile may work better for certain detector types."
            },
            {
                "action": "Check for ice rings and filter them",
                "params": ["spotfinder.filter.ice_rings.filter=True"],
                "explanation": "Ice rings can confuse spot finding. Filtering them may help."
            },
        ]
    },
    "too_many_spots": {
        "description": "Too many spots found (> 100,000) — may include noise",
        "stage": "find_spots",
        "solutions": [
            {
                "action": "Raise the sigma threshold",
                "params": ["spotfinder.threshold.dispersion.sigma_strong=6.0"],
                "explanation": "Default is 3.0. Raising to 6.0 keeps only the strongest spots."
            },
            {
                "action": "Set a global intensity threshold",
                "params": ["spotfinder.threshold.dispersion.global_threshold=100"],
                "explanation": "Only pixels above this absolute intensity are considered."
            },
            {
                "action": "Increase minimum spot size",
                "params": ["spotfinder.filter.min_spot_size=6"],
                "explanation": "Filters out very small spots that may be noise."
            },
            {
                "action": "Limit resolution range",
                "params": ["spotfinder.filter.d_min=2.0"],
                "explanation": "Exclude high-resolution spots that are often weak/noisy."
            },
        ]
    },

    # === Indexing Problems ===
    "indexing_failed": {
        "description": "Indexing failed — no solution found",
        "stage": "index",
        "solutions": [
            {
                "action": "Try a different indexing method",
                "params": ["indexing.method=fft1d"],
                "explanation": "fft1d is more robust for difficult cases. Also try real_space_grid_search if you know the unit cell."
            },
            {
                "action": "Provide known unit cell",
                "params": ["indexing.known_symmetry.unit_cell=a,b,c,alpha,beta,gamma"],
                "explanation": "If you know the unit cell, providing it constrains the search."
            },
            {
                "action": "Provide known space group",
                "params": ["indexing.known_symmetry.space_group=P212121"],
                "explanation": "Constrains indexing to consistent solutions only."
            },
            {
                "action": "Search for correct beam centre first",
                "params": [],
                "explanation": "Run dials.search_beam_position imported.expt strong.refl before indexing."
            },
            {
                "action": "Increase max cell length",
                "params": ["indexing.max_cell=300"],
                "explanation": "Default auto-detection may underestimate for large unit cells."
            },
            {
                "action": "Reduce minimum cell volume",
                "params": ["indexing.min_cell_volume=10"],
                "explanation": "Default is 25 Å³. Small molecules may need lower."
            },
            {
                "action": "Increase search scope for beam centre",
                "params": ["indexing.mm_search_scope=8.0"],
                "explanation": "Default is 4.0mm. Increase if beam centre is far off."
            },
            {
                "action": "Use a subset of images",
                "params": ["indexing.image_range=1,100"],
                "explanation": "Try indexing on a subset first, especially if crystal decays."
            },
        ]
    },
    "low_indexed_percentage": {
        "description": "Low percentage of spots indexed (< 70%)",
        "stage": "index",
        "solutions": [
            {
                "action": "Look for multiple lattices",
                "params": ["indexing.max_lattices=2"],
                "explanation": "Multiple crystals in the beam will cause low indexed %."
            },
            {
                "action": "Increase HKL tolerance",
                "params": ["indexing.index_assignment.simple.hkl_tolerance=0.4"],
                "explanation": "Default is 0.3. Increasing allows more spots to be assigned."
            },
            {
                "action": "Filter ice rings during spot finding",
                "params": ["spotfinder.filter.ice_rings.filter=True"],
                "explanation": "Ice ring spots won't index and lower the percentage."
            },
            {
                "action": "Use more refinement cycles",
                "params": ["indexing.refinement_protocol.n_macro_cycles=10"],
                "explanation": "More cycles may improve the model and index more spots."
            },
        ]
    },
    "multiple_lattices": {
        "description": "Multiple lattices / crystals in the beam",
        "stage": "index",
        "solutions": [
            {
                "action": "Enable multi-lattice indexing",
                "params": ["indexing.max_lattices=5"],
                "explanation": "Find up to 5 lattices. Check reciprocal lattice viewer to see them."
            },
            {
                "action": "Use joint=false for independent indexing",
                "params": ["joint=false"],
                "explanation": "Index each sweep independently when crystals differ."
            },
        ]
    },

    # === Refinement Problems ===
    "refinement_failed": {
        "description": "Refinement failed or diverged",
        "stage": "refine",
        "solutions": [
            {
                "action": "Fix detector parameters",
                "params": ["refinement.parameterisation.detector.fix=all"],
                "explanation": "Fixing the detector reduces the number of free parameters."
            },
            {
                "action": "Fix beam parameters",
                "params": ["refinement.parameterisation.beam.fix=all"],
                "explanation": "Fix beam if wavelength and direction are well-known."
            },
            {
                "action": "Disable scan-varying refinement",
                "params": ["refinement.parameterisation.scan_varying=False"],
                "explanation": "Scan-varying has more parameters and can be unstable."
            },
            {
                "action": "Use more static macro-cycles first",
                "params": ["n_static_macrocycles=3"],
                "explanation": "More static cycles before scan-varying can stabilize refinement."
            },
            {
                "action": "Change outlier rejection algorithm",
                "params": ["refinement.reflections.outlier.algorithm=tukey"],
                "explanation": "Try tukey or mcd instead of auto for better outlier handling."
            },
        ]
    },

    # === Integration Problems ===
    "integration_slow": {
        "description": "Integration is very slow",
        "stage": "integrate",
        "solutions": [
            {
                "action": "Use more processors",
                "params": ["integration.mp.nproc=8"],
                "explanation": "Parallelize across CPU cores."
            },
            {
                "action": "Reduce memory usage",
                "params": ["integration.block.max_memory_usage=0.75"],
                "explanation": "Prevents swapping by limiting memory per block."
            },
            {
                "action": "Limit resolution",
                "params": ["prediction.d_min=2.0"],
                "explanation": "Fewer reflections to integrate at lower resolution."
            },
            {
                "action": "Use summation integration only",
                "params": ["integration.profile.fitting=False"],
                "explanation": "Skip profile fitting for faster (but less accurate) integration."
            },
        ]
    },
    "integration_memory": {
        "description": "Integration runs out of memory",
        "stage": "integrate",
        "solutions": [
            {
                "action": "Reduce memory usage fraction",
                "params": ["integration.block.max_memory_usage=0.50"],
                "explanation": "Use smaller blocks to reduce peak memory."
            },
            {
                "action": "Reduce number of processors",
                "params": ["integration.mp.nproc=2"],
                "explanation": "Each process uses memory independently."
            },
            {
                "action": "Use smaller block size",
                "params": ["integration.block.size=5", "integration.block.units=degrees"],
                "explanation": "Process fewer images at a time."
            },
        ]
    },

    # === Scaling Problems ===
    "high_rmerge": {
        "description": "High Rmerge (> 10%) during scaling",
        "stage": "scale",
        "solutions": [
            {
                "action": "Apply absorption correction",
                "params": ["physical.absorption_correction=True", "physical.absorption_level=medium"],
                "explanation": "Absorption causes systematic intensity differences."
            },
            {
                "action": "Enable delta CC½ filtering",
                "params": ["filtering.method=deltacchalf", "filtering.deltacchalf.stdcutoff=4.0"],
                "explanation": "Remove outlier images/datasets that degrade statistics."
            },
            {
                "action": "Try a different scaling model",
                "params": ["model=array"],
                "explanation": "Array model has more parameters and may fit better."
            },
            {
                "action": "Apply resolution cutoff",
                "params": ["d_min=2.5"],
                "explanation": "Exclude weak high-resolution data that inflates Rmerge."
            },
            {
                "action": "Check for consistent indexing",
                "params": ["scaling_options.check_consistent_indexing=True"],
                "explanation": "Inconsistent indexing between datasets causes high Rmerge."
            },
            {
                "action": "Exclude damaged images",
                "params": ["exclude_images=0:start:end"],
                "explanation": "Exclude radiation-damaged images at the end of the scan."
            },
        ]
    },
    "low_completeness": {
        "description": "Low completeness (< 90%)",
        "stage": "scale",
        "solutions": [
            {
                "action": "Check for missing wedge",
                "params": [],
                "explanation": "Run dials.missing_reflections to identify gaps. May need more data."
            },
            {
                "action": "Lower partiality threshold",
                "params": ["partiality_threshold=0.2"],
                "explanation": "Include more partial reflections (default 0.4)."
            },
            {
                "action": "Extend resolution range",
                "params": ["d_max=100"],
                "explanation": "Include low-resolution reflections that may be missing."
            },
        ]
    },
    "radiation_damage": {
        "description": "Radiation damage detected",
        "stage": "scale",
        "solutions": [
            {
                "action": "Use dose_decay scaling model",
                "params": ["model=dose_decay"],
                "explanation": "Explicitly models radiation damage as a function of dose."
            },
            {
                "action": "Exclude damaged images",
                "params": ["exclude_images=0:start:end"],
                "explanation": "Remove the most damaged images from the end of the scan."
            },
            {
                "action": "Run damage analysis",
                "params": [],
                "explanation": "Run dials.damage_analysis scaled.expt scaled.refl to quantify damage."
            },
            {
                "action": "Enable decay correction in physical model",
                "params": ["physical.decay_correction=True"],
                "explanation": "Apply B-factor decay correction (enabled by default)."
            },
        ]
    },

    # === Beam Centre Problems ===
    "wrong_beam_centre": {
        "description": "Beam centre appears incorrect",
        "stage": "import",
        "solutions": [
            {
                "action": "Search for beam position",
                "params": [],
                "explanation": "Run dials.search_beam_position imported.expt strong.refl"
            },
            {
                "action": "Override beam centre during import",
                "params": ["geometry.detector.slow_fast_beam_centre=y_mm,x_mm"],
                "explanation": "Manually set beam centre in mm (slow, fast order)."
            },
            {
                "action": "Increase search scope",
                "params": ["indexing.mm_search_scope=8.0"],
                "explanation": "Allow indexing to search further from the header beam centre."
            },
        ]
    },

    # === Ice Ring Problems ===
    "ice_rings": {
        "description": "Ice rings visible in diffraction images",
        "stage": "find_spots",
        "solutions": [
            {
                "action": "Filter ice rings during spot finding",
                "params": ["spotfinder.filter.ice_rings.filter=True"],
                "explanation": "Automatically exclude spots in ice ring resolution ranges."
            },
            {
                "action": "Generate mask for ice rings",
                "params": [],
                "explanation": "Run dials.generate_mask imported.expt ice_rings.filter=True"
            },
            {
                "action": "Filter ice rings during integration",
                "params": ["integration.filter.ice_rings=True"],
                "explanation": "Flag reflections in ice ring regions during integration."
            },
            {
                "action": "Filter ice rings during export",
                "params": ["mtz.filter_ice_rings=True"],
                "explanation": "Remove ice ring reflections from the exported MTZ file."
            },
        ]
    },

    # === Electron Diffraction ===
    "electron_diffraction": {
        "description": "Processing electron diffraction data",
        "stage": "import",
        "solutions": [
            {
                "action": "Set probe type to electron",
                "params": ["geometry.beam.probe=electron"],
                "explanation": "Tell DIALS this is electron diffraction data."
            },
            {
                "action": "Use appropriate spot finding parameters",
                "params": ["spotfinder.threshold.dispersion.sigma_strong=4.0", "spotfinder.filter.min_spot_size=2"],
                "explanation": "Electron diffraction spots are often smaller and sharper."
            },
            {
                "action": "Exclude images for cRED data",
                "params": ["exclude_images_multiple=20"],
                "explanation": "For cRED, exclude crystal positioning images (every Nth frame)."
            },
        ]
    },

    # === High-Pressure (DAC) ===
    "high_pressure_dac": {
        "description": "Processing high-pressure diamond anvil cell data",
        "stage": "integrate",
        "solutions": [
            {
                "action": "Apply anvil correction after integration",
                "params": [],
                "explanation": "Run dials.anvil_correction integrated.expt integrated.refl anvil.thickness=1.5925"
            },
            {
                "action": "Generate mask for shadowed regions",
                "params": [],
                "explanation": "Run dials.generate_mask imported.expt to mask DAC shadows."
            },
        ]
    },
}


_KEYWORD_MAP = {
    "too few spots": "too_few_spots",
    "few spots": "too_few_spots",
    "not enough spots": "too_few_spots",
    "low spot count": "too_few_spots",
    "too many spots": "too_many_spots",
    "high spot count": "too_many_spots",
    "indexing fail": "indexing_failed",
    "no solution": "indexing_failed",
    "cannot index": "indexing_failed",
    "index fail": "indexing_failed",
    "low indexed": "low_indexed_percentage",
    "poor indexing": "low_indexed_percentage",
    "multiple lattice": "multiple_lattices",
    "multi-lattice": "multiple_lattices",
    "multiple crystal": "multiple_lattices",
    "twin": "multiple_lattices",
    "refinement fail": "refinement_failed",
    "refine fail": "refinement_failed",
    "refinement diverge": "refinement_failed",
    "integration slow": "integration_slow",
    "integrate slow": "integration_slow",
    "taking too long": "integration_slow",
    "memory": "integration_memory",
    "out of memory": "integration_memory",
    "oom": "integration_memory",
    "high rmerge": "high_rmerge",
    "high r-merge": "high_rmerge",
    "poor merging": "high_rmerge",
    "bad statistics": "high_rmerge",
    "low completeness": "low_completeness",
    "incomplete": "low_completeness",
    "missing data": "low_completeness",
    "radiation damage": "radiation_damage",
    "decay": "radiation_damage",
    "beam cent": "wrong_beam_centre",
    "beam center": "wrong_beam_centre",
    "beam position": "wrong_beam_centre",
    "ice ring": "ice_rings",
    "ice": "ice_rings",
    "electron": "electron_diffraction",
    "micro-ed": "electron_diffraction",
    "microed": "electron_diffraction",
    "cred": "electron_diffraction",
    "anvil": "high_pressure_dac",
    "dac": "high_pressure_dac",
    "high pressure": "high_pressure_dac",
    "diamond anvil": "high_pressure_dac",
}


def diagnose_problem(problem: str, current_stage: str = "", context: str = "") -> str:
    """
    Diagnose a DIALS processing problem and suggest solutions.

    Args:
        problem: Description of the problem
        current_stage: Current workflow stage
        context: Additional context

    Returns:
        Formatted string with diagnosis and solutions
    """
    problem_lower = problem.lower()

    matched_keys = []
    for keyword, key in _KEYWORD_MAP.items():
        if keyword in problem_lower:
            if key not in matched_keys:
                matched_keys.append(key)

    if not matched_keys:
        return (
            f"I don't have a specific diagnosis for '{problem}'. "
            f"Here are some general suggestions:\n\n"
            f"1. Check the log file for the failing step (e.g., dials.index.log)\n"
            f"2. Use dials.show to inspect your experiment/reflection files\n"
            f"3. Use dials.report to generate a diagnostic HTML report\n"
            f"4. Use lookup_phil_params to see all available parameters for the relevant command\n"
            f"5. Try running with default parameters first, then adjust\n\n"
            f"You can also look up detailed parameters with: dials.<command> -c -e2 -a2"
        )

    result_parts = []
    for key in matched_keys:
        if key not in PROBLEM_SOLUTIONS:
            continue
        prob = PROBLEM_SOLUTIONS[key]
        result_parts.append(f"## {prob['description']}\n")
        result_parts.append(f"Stage: {prob['stage']}\n")

        for i, sol in enumerate(prob["solutions"], 1):
            params_str = " ".join(sol["params"]) if sol["params"] else "(see explanation)"
            result_parts.append(f"\n### Solution {i}: {sol['action']}")
            result_parts.append(f"Parameters: `{params_str}`")
            result_parts.append(f"Explanation: {sol['explanation']}")

        result_parts.append("")

    return "\n".join(result_parts)


class TroubleshootingSkill(BaseSkill):

    @property
    def name(self) -> str:
        return "troubleshooting"

    @property
    def description(self) -> str:
        return "Diagnosing common DIALS processing problems with parameter-level fixes"

    def get_prompt_fragment(self) -> str:
        return """## Problem Diagnosis

You have access to a `diagnose_problem` tool that maps common crystallography problems to specific parameter-level solutions. Use this when:
- A command fails or produces poor results
- The user reports issues like "too few spots", "indexing failed", "high Rmerge"
- You need to suggest specific parameter adjustments

The tool covers problems in all workflow stages: spot finding, indexing, refinement, integration, scaling, and special cases (ice rings, electron diffraction, high-pressure DAC).

## Troubleshooting

### "No experiments found" during import
- Check file paths and patterns
- Verify image format is supported (CBF, HDF5/NXS, SMV, TIFF)
- Try using `input.template=image_####.cbf` parameter
- For HDF5/NXS: check the file is not corrupted with `h5dump -H file.nxs`

### "No solution found" during indexing
- Try different method: `indexing.method=fft1d` or `indexing.method=real_space_grid_search`
- Provide known unit cell: `indexing.known_symmetry.unit_cell=a,b,c,alpha,beta,gamma`
- Check for multiple lattices: `indexing.max_lattices=2`
- Verify beam center: run `dials.search_beam_position` first
- Increase search scope: `indexing.mm_search_scope=8.0`
- Try with fewer spots: use `spotfinder.scan_range=1,100` to find spots on a subset

### Low indexed percentage (< 70%)
- Crystal may have multiple domains → `indexing.max_lattices=2`
- Ice rings present → `spotfinder.filter.ice_rings.filter=True`
- Increase HKL tolerance → `indexing.index_assignment.simple.hkl_tolerance=0.4`
- Wrong beam centre → run `dials.search_beam_position`

### Refinement fails or diverges
- Fix detector: `refinement.parameterisation.detector.fix=all`
- Fix beam: `refinement.parameterisation.beam.fix=all`
- Disable scan-varying: `refinement.parameterisation.scan_varying=False`
- More static cycles: `n_static_macrocycles=3`
- Change outlier rejection: `refinement.reflections.outlier.algorithm=tukey`

### Integration out of memory
- Reduce memory: `integration.block.max_memory_usage=0.50`
- Fewer processors: `integration.mp.nproc=2`
- Smaller blocks: `integration.block.size=5 integration.block.units=degrees`

### High Rmerge during scaling
- Apply absorption correction: `physical.absorption_correction=True physical.absorption_level=medium`
- Enable ΔCC½ filtering: `filtering.method=deltacchalf filtering.deltacchalf.stdcutoff=4.0`
- Try array model: `model=array`
- Apply resolution cutoff: `d_min=2.5`
- Check indexing consistency: `scaling_options.check_consistent_indexing=True`
- Exclude damaged images: `exclude_images=0:start:end`

### Ice rings in data
- Filter during spot finding: `spotfinder.filter.ice_rings.filter=True`
- Generate mask: `dials.generate_mask imported.expt ice_rings.filter=True`
- Filter during integration: `integration.filter.ice_rings=True`
- Filter during export: `mtz.filter_ice_rings=True`

### Electron diffraction (MicroED/cRED)
- Set probe type: `geometry.beam.probe=electron` during import
- Adjust spot finding: `spotfinder.threshold.dispersion.sigma_strong=4.0`
- For cRED: `exclude_images_multiple=20` to skip positioning images

### High-pressure DAC data
- Apply anvil correction: `dials.anvil_correction integrated.expt integrated.refl anvil.thickness=1.5925`
- Generate shadow mask: `dials.generate_mask imported.expt`

### Multiple crystals / multi-lattice
- Index multiple lattices: `indexing.max_lattices=5`
- Use cosym for symmetry: `dials.cosym` instead of `dials.symmetry`
- Check consistent indexing during scaling: `scaling_options.check_consistent_indexing=True`

### Weak diffraction / low resolution
- Lower sigma threshold: `spotfinder.threshold.dispersion.sigma_strong=2.0`
- Use summation integration: `integration.profile.fitting=False`
- Apply resolution cutoff: `d_min=3.0` during scaling
- Use dose_decay model: `model=dose_decay` for radiation-sensitive crystals"""

    def get_tools(self) -> list[dict]:
        return TOOLS

    def handle_tool_call(self, tool_name: str, tool_input: dict, context: SkillContext) -> dict:
        if tool_name == "suggest_troubleshooting":
            return {
                "status": "troubleshooting_requested",
                "problem": tool_input.get("problem"),
            }
        elif tool_name == "diagnose_problem":
            problem = tool_input.get("problem", "")
            current_stage = tool_input.get("current_stage", "")
            prob_context = tool_input.get("context", "")
            return {"diagnosis": diagnose_problem(problem, current_stage, prob_context)}
        raise KeyError(f"troubleshooting skill does not handle tool '{tool_name}'")
