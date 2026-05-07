"""
Tutorial definitions for the DIALS AI Agent.

Each tutorial is a dictionary containing:
- name: Display name
- description: Brief description
- trigger_phrases: Keywords that activate this tutorial
- data_format: Expected data file format
- data_patterns: Glob patterns to look for in the data directory
- rounds: List of processing rounds (each round is a complete workflow)
- notes: Important notes for the agent
"""

TUTORIALS = {
    "simple_insulin": {
        "name": "Simple Insulin (Single Crystal)",
        "description": "Basic single-crystal workflow using cubic insulin data. "
                       "Ideal for learning the DIALS processing pipeline.",
        "trigger_phrases": [
            "insulin", "simple tutorial", "basic workflow", "WORKFLOW tutorial",
            "single crystal tutorial", "beginner tutorial",
        ],
        "data_format": "HDF5/NeXus (.nxs, .h5)",
        "data_patterns": ["ins*.nxs", "ins*_master.h5", "*.nxs"],
        "rounds": [
            {
                "name": "Process insulin data",
                "description": "Standard single-crystal workflow",
                "steps": [
                    {
                        "command": "dials.import {data_path}",
                        "options": {
                            "quick": "image_range=1,1200",
                            "full": "",
                        },
                        "description": "Import the insulin diffraction data",
                        "ask_user": "Would you like to process the full dataset or a quick subset (first 1200 images)?",
                    },
                    {
                        "command": "dials.find_spots imported.expt",
                        "description": "Find strong diffraction spots on all images",
                        "parallel": "spotfinder.mp.nproc={nproc}",
                    },
                    {
                        "command": "dials.index imported.expt strong.refl",
                        "description": "Assign Miller indices and determine unit cell",
                    },
                    {
                        "command": "dials.refine indexed.expt indexed.refl",
                        "description": "Refine crystal and detector models (static + scan-varying)",
                    },
                    {
                        "command": "dials.integrate refined.expt refined.refl",
                        "description": "Measure spot intensities by profile fitting",
                        "parallel": "integration.mp.nproc={nproc}",
                    },
                    {
                        "command": "dials.symmetry integrated.expt integrated.refl",
                        "description": "Determine the space group from integrated intensities",
                    },
                    {
                        "command": "dials.scale symmetrized.expt symmetrized.refl",
                        "description": "Scale and correct the data for experimental effects",
                    },
                    {
                        "command": "dials.export scaled.expt scaled.refl",
                        "description": "Export to MTZ format for structure determination",
                    },
                ],
            },
        ],
        "notes": [
            "This is a single-crystal dataset — use standard dials.symmetry (not cosym)",
            "Expected symmetry: I213 with unit cell ~67 Å",
            "Good for learning: each step should work without issues",
        ],
    },

    "cows_pigs_people": {
        "name": "Cows, Pigs, and People (Multi-Crystal Insulin)",
        "description": "Multi-crystal insulin from three species (cow, pig, human). "
                       "Demonstrates multi-crystal processing, indexing ambiguity resolution, "
                       "and dataset clustering by species.",
        "trigger_phrases": [
            "cows pigs people", "cow data", "pig data", "human data",
            "multi-crystal", "multiple crystals", "COWS_PIGS_PEOPLE",
            "CIX", "PIX", "species", "cows pigs human",
            "cows pigs and people", "cows pigs and human",
        ],
        "data_format": "Compressed CBF (.cbf.gz)",
        "data_patterns": ["CIX*.cbf.gz", "PIX*.cbf.gz", "X*.cbf.gz"],
        "rounds": [
            # ── Round 1: Cows only ──
            {
                "name": "Round 1: Process cow insulin (CIX*)",
                "description": "Process 12 crystals of bovine insulin. Each crystal covers "
                               "a small rotation range (~10°). Merging gives a complete dataset.",
                "import_pattern": "CIX*gz",
                "steps": [
                    {
                        "command": "dials.import {data_dir}/CIX*gz",
                        "description": "Import all 12 cow insulin crystals (CIX1 through CIX15). "
                                       "Each has ~100 images of 0.1° oscillation.",
                    },
                    {
                        "command": "dials.find_spots imported.expt",
                        "description": "Find spots across all 12 sweeps. Spots are found in 3D "
                                       "(connected across adjacent images).",
                        "parallel": "spotfinder.mp.nproc={nproc}",
                    },
                    {
                        "command": "dials.index imported.expt strong.refl joint=false",
                        "description": "Index each crystal independently (joint=false). "
                                       "Each crystal has a different orientation so they cannot "
                                       "share an orientation matrix.",
                        "important": "MUST use joint=false for multi-crystal data",
                    },
                    {
                        "command": "dials.refine indexed.expt indexed.refl",
                        "description": "Refine all 12 crystal models simultaneously.",
                    },
                    {
                        "command": "dials.integrate refined.expt refined.refl",
                        "description": "Integrate all 12 sweeps. This measures intensities "
                                       "for each crystal independently.",
                        "parallel": "integration.mp.nproc={nproc}",
                    },
                    {
                        "command": "dials.cosym integrated.expt integrated.refl",
                        "description": "Resolve indexing ambiguity across the 12 crystals. "
                                       "In I213, each crystal can be indexed in 2 equivalent ways. "
                                       "Cosym determines which choice is consistent across all crystals.",
                        "important": "Use dials.cosym NOT dials.symmetry for multi-crystal data",
                    },
                    {
                        "command": "dials.correlation_matrix symmetrized.expt symmetrized.refl",
                        "description": "Compute the correlation matrix between the 12 cow datasets. "
                                       "Since all are from the same species, they should all cluster "
                                       "together with high correlation. This serves as a baseline "
                                       "comparison for Round 2.",
                        "options": {
                            "default": "symmetrized.expt symmetrized.refl (before scaling)",
                            "alternative": "scaled.expt scaled.refl (after scaling, may show cleaner correlations)",
                        },
                    },
                    {
                        "command": "dials.scale symmetrized.expt symmetrized.refl",
                        "description": "Scale and merge the 12 partial datasets into one complete "
                                       "bovine insulin dataset. Check merging statistics.",
                    },
                    {
                        "command": "dials.export scaled.expt scaled.refl",
                        "description": "Export the merged cow insulin data to MTZ format.",
                    },
                ],
            },
            # ── Round 2: All species ──
            {
                "name": "Round 2: Process all species together (*gz)",
                "description": "Process all 36 crystals (12 cow + 12 pig + 12 human) together. "
                               "All have I213 symmetry and similar unit cells. Cosym will compute "
                               "inter-dataset correlations that reveal natural species groupings.",
                "import_pattern": "*gz",
                "prerequisite": "Complete Round 1 first. Create a new working directory for Round 2.",
                "steps": [
                    {
                        "command": "dials.import {data_dir}/*gz",
                        "description": "Import all 36 crystals from all three species. "
                                       "DIALS will find ~36 sweeps, ~3600 images total.",
                    },
                    {
                        "command": "dials.find_spots imported.expt",
                        "description": "Find spots across all 36 sweeps.",
                        "parallel": "spotfinder.mp.nproc={nproc}",
                    },
                    {
                        "command": "dials.index imported.expt strong.refl joint=false",
                        "description": "Index all 36 crystals independently.",
                        "important": "MUST use joint=false",
                    },
                    {
                        "command": "dials.refine indexed.expt indexed.refl",
                        "description": "Refine all 36 crystal models.",
                    },
                    {
                        "command": "dials.integrate refined.expt refined.refl",
                        "description": "Integrate all 36 sweeps.",
                        "parallel": "integration.mp.nproc={nproc}",
                    },
                    {
                        "command": "dials.cosym integrated.expt integrated.refl",
                        "description": "This is the key step! Cosym resolves indexing ambiguity AND "
                                       "computes a correlation matrix between all 36 datasets. "
                                       "The correlation matrix will reveal 3 natural clusters "
                                       "corresponding to the three species — datasets from the same "
                                       "species correlate strongly, while cross-species correlations "
                                       "are weaker.",
                        "important": "Examine the cosym output carefully — it shows which datasets cluster together",
                    },
                    {
                        "command": "dials.scale symmetrized.expt symmetrized.refl",
                        "description": "Scale all 36 datasets together. The merging statistics "
                                       "(Rmerge) will be higher than Round 1 because you're averaging "
                                       "different structures. This demonstrates why species separation matters.",
                    },
                    {
                        "command": "dials.correlation_matrix symmetrized.expt symmetrized.refl",
                        "description": "Compute and visualize the correlation matrix between all 36 datasets. "
                                       "This generates an HTML report with a heatmap and dendrogram showing "
                                       "how datasets cluster. You should see 3 distinct clusters corresponding "
                                       "to the three species (cow, pig, human). Datasets from the same species "
                                       "will have high correlation (red), while cross-species correlations "
                                       "will be lower (blue).",
                        "important": "This is the key analysis step — it reveals species groupings without prior knowledge",
                        "options": {
                            "default": "symmetrized.expt symmetrized.refl (before scaling)",
                            "alternative": "scaled.expt scaled.refl (after scaling, may show cleaner correlations)",
                        },
                    },
                    {
                        "command": "dials.export scaled.expt scaled.refl",
                        "description": "Export the combined data. For proper analysis, you would "
                                       "separate the species groups identified by the correlation matrix "
                                       "and scale each group independently.",
                    },
                ],
            },
        ],
        "notes": [
            "IMPORTANT: This tutorial has TWO rounds. Always start with Round 1 (cows only) first, then Round 2 (all species).",
            "All three species have I213 symmetry and very similar unit cells (~67 Å)",
            "They CAN be merged together but SHOULD NOT — different amino acid sequences",
            "Round 1 (cows only) demonstrates basic multi-crystal processing",
            "Round 2 (all species) demonstrates dataset classification without prior knowledge",
            "The correlation analysis from cosym reveals natural species groupings",
            "Always use joint=false for indexing (different crystal orientations)",
            "Always use dials.cosym (not dials.symmetry) for multi-crystal data",
            "Between rounds, create a new working directory (use change_working_directory tool to create 'round2')",
            "After Round 1 completes, tell the user about Round 2 and offer to continue",
        ],
    },

    "multi_lattice": {
        "name": "Multi-Lattice Proteinase K",
        "description": "A single crystal that turns out to contain two lattices. "
                       "Demonstrates how to detect and handle multiple lattices in one dataset.",
        "trigger_phrases": [
            "multi-lattice", "multi lattice", "proteinase K", "protK",
            "two lattices", "multiple lattices", "MULTI_LATTICE",
        ],
        "data_format": "HDF5 (.h5)",
        "data_patterns": ["ProtK*.h5", "ProtK*.nxs"],
        "rounds": [
            {
                "name": "Process Proteinase K with multiple lattices",
                "description": "Start with standard processing, discover two lattices, "
                               "then re-index with max_lattices=2.",
                "steps": [
                    {
                        "command": "dials.import {data_path} image_range=1,600",
                        "description": "Import first 600 images (subset for speed).",
                    },
                    {
                        "command": "dials.find_spots imported.expt",
                        "description": "Find spots — expect ~100,000+ spots (more than usual due to two lattices).",
                        "parallel": "spotfinder.mp.nproc={nproc}",
                    },
                    {
                        "command": "dials.index imported.expt strong.refl",
                        "description": "First indexing attempt — expect only ~62% indexed. "
                                       "This is a clue that there's a second lattice.",
                        "expect": "~62% indexed, suggesting a second lattice",
                    },
                    {
                        "command": "dials.index imported.expt strong.refl max_lattices=2",
                        "description": "Re-index with max_lattices=2. Now expect ~97% indexed "
                                       "with two crystal models.",
                        "important": "This replaces the previous indexing result",
                        "expect": "~97% indexed with 2 lattice models",
                    },
                    {
                        "command": "dials.refine indexed.expt indexed.refl",
                        "description": "Refine both lattice models.",
                    },
                    {
                        "command": "dials.integrate refined.expt refined.refl",
                        "description": "Integrate reflections from both lattices. "
                                       "Takes longer than single-lattice processing.",
                        "parallel": "integration.mp.nproc={nproc}",
                    },
                    {
                        "command": "dials.symmetry integrated.expt integrated.refl",
                        "description": "Determine symmetry. Both lattices should have "
                                       "similar unit cells (~68×68×103 Å, P43212).",
                    },
                    {
                        "command": "dials.scale symmetrized.expt symmetrized.refl",
                        "description": "Scale the data from both lattices together.",
                    },
                    {
                        "command": "dials.export scaled.expt scaled.refl",
                        "description": "Export the processed data.",
                    },
                ],
            },
        ],
        "notes": [
            "The crystal appears single but contains two lattices",
            "First indexing attempt will only index ~62% of spots — this is the diagnostic clue",
            "Re-indexing with max_lattices=2 should index ~97%",
            "Use dials.reciprocal_lattice_viewer to visualize the two lattices",
            "Both lattices have similar unit cells (P43212, ~68×68×103 Å)",
            "Overlapping reflections from the two lattices may affect data quality",
        ],
    },
}


def get_tutorial(name: str) -> dict | None:
    """Get a tutorial by name."""
    return TUTORIALS.get(name)


def find_tutorial_by_phrase(phrase: str) -> tuple[str, dict] | None:
    """Find a tutorial matching a trigger phrase.
    
    Args:
        phrase: User input to match against trigger phrases
        
    Returns:
        Tuple of (tutorial_key, tutorial_dict) or None
    """
    phrase_lower = phrase.lower()
    for key, tutorial in TUTORIALS.items():
        for trigger in tutorial["trigger_phrases"]:
            if trigger.lower() in phrase_lower:
                return key, tutorial
    return None


def get_tutorial_names() -> list[str]:
    """Get list of available tutorial names."""
    return [t["name"] for t in TUTORIALS.values()]


def get_tutorials_summary() -> str:
    """Get a formatted summary of all available tutorials."""
    lines = []
    for i, (key, tutorial) in enumerate(TUTORIALS.items(), 1):
        lines.append(f"{i}. **{tutorial['name']}**: {tutorial['description']}")
    return "\n".join(lines)


def get_tutorial_prompt_section() -> str:
    """Generate the tutorial section for the system prompt."""
    sections = [
        "**For tutorials with multiple rounds**: Present the available rounds to the user "
        "and let them choose which round to run. Explain what each round covers. "
        "If they want to run both, start with Round 1, then after it completes, "
        "create a new working directory for Round 2 (use `change_working_directory`) "
        "so output files don't overwrite each other.\n"
    ]
    
    for key, tutorial in TUTORIALS.items():
        section = f"### {tutorial['name']}\n"
        section += f"- **Description**: {tutorial['description']}\n"
        section += f"- **Data format**: {tutorial['data_format']}\n"
        section += f"- **Data patterns**: {', '.join(tutorial['data_patterns'])}\n"
        section += f"- **Trigger phrases**: {', '.join(tutorial['trigger_phrases'][:5])}...\n"
        
        for round_info in tutorial["rounds"]:
            section += f"\n#### {round_info['name']}\n"
            section += f"{round_info['description']}\n"
            
            if "prerequisite" in round_info:
                section += f"**Prerequisite**: {round_info['prerequisite']}\n"
            
            section += "\n**Steps:**\n"
            for i, step in enumerate(round_info["steps"], 1):
                cmd = step["command"]
                desc = step["description"]
                section += f"  {i}. `{cmd}` — {desc}\n"
                if "important" in step:
                    section += f"     ⚠️ {step['important']}\n"
                if "expect" in step:
                    section += f"     📊 Expected: {step['expect']}\n"
                if "options" in step:
                    opts = step["options"]
                    if "default" in opts:
                        section += f"     📋 Default: {opts['default']}\n"
                    if "alternative" in opts:
                        section += f"     📋 Alternative: {opts['alternative']}\n"
                    # Handle other option formats (e.g., quick/full)
                    for k, v in opts.items():
                        if k not in ("default", "alternative"):
                            section += f"     📋 {k}: {v}\n"
        
        if tutorial.get("notes"):
            section += "\n**Important notes:**\n"
            for note in tutorial["notes"]:
                section += f"  - {note}\n"
        
        sections.append(section)
    
    return "\n".join(sections)
