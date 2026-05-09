"""
Tool definitions for Claude function calling.

This module defines the tools that Claude can use to interact with DIALS
and help users process their crystallography data.
"""

import os
from pathlib import Path
from typing import Any

# Tool definitions for Claude API
TOOLS = [
    {
        "name": "suggest_dials_command",
        "description": "Suggest a DIALS command to execute based on the user's request. Use this when the user wants to perform a data processing step.",
        "input_schema": {
            "type": "object",
            "properties": {
                "command": {
                    "type": "string",
                    "description": "The complete DIALS command to execute, including all arguments and parameters"
                },
                "explanation": {
                    "type": "string",
                    "description": "A clear, user-friendly explanation of what this command does and why it's appropriate"
                },
                "expected_output": {
                    "type": "string",
                    "description": "Description of the expected output files and what they contain"
                },
                "warnings": {
                    "type": "string",
                    "description": "Any warnings or considerations the user should be aware of (optional)"
                }
            },
            "required": ["command", "explanation", "expected_output"]
        }
    },
    {
        "name": "check_workflow_status",
        "description": "Check what DIALS files exist in the working directory and determine the current workflow stage. Use this to understand where the user is in their data processing.",
        "input_schema": {
            "type": "object",
            "properties": {
                "working_directory": {
                    "type": "string",
                    "description": "The directory to check for DIALS files (default: current directory)"
                }
            },
            "required": []
        }
    },
    {
        "name": "explain_dials_concept",
        "description": "Explain a DIALS concept, parameter, or crystallography term to the user. Use this when the user asks questions about terminology or needs clarification.",
        "input_schema": {
            "type": "object",
            "properties": {
                "concept": {
                    "type": "string",
                    "description": "The concept, term, or parameter to explain"
                },
                "context": {
                    "type": "string",
                    "description": "Additional context about why this concept is relevant (optional)"
                }
            },
            "required": ["concept"]
        }
    },
    {
        "name": "analyze_dials_output",
        "description": "Analyze the output from a DIALS command and provide a summary. Use this after a command has been executed to help the user understand the results.",
        "input_schema": {
            "type": "object",
            "properties": {
                "command": {
                    "type": "string",
                    "description": "The DIALS command that was executed"
                },
                "output": {
                    "type": "string",
                    "description": "The output text from the command"
                },
                "return_code": {
                    "type": "integer",
                    "description": "The return code from the command (0 = success)"
                }
            },
            "required": ["command", "output"]
        }
    },
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
        "name": "list_available_commands",
        "description": "List available DIALS commands relevant to the user's current situation. Use this when the user asks what they can do or needs guidance on available options.",
        "input_schema": {
            "type": "object",
            "properties": {
                "category": {
                    "type": "string",
                    "enum": ["all", "workflow", "utility", "visualization"],
                    "description": "Category of commands to list"
                },
                "current_stage": {
                    "type": "string",
                    "description": "The current workflow stage (e.g., 'after_indexing')"
                }
            },
            "required": []
        }
    },
    {
        "name": "read_file",
        "description": "Read the contents of a file in the working directory. Use this to read log files (e.g., dials.find_spots.log, dials.index.log), output files, or any text file the user asks about. This allows you to directly analyze log output without asking the user to paste it.",
        "input_schema": {
            "type": "object",
            "properties": {
                "filename": {
                    "type": "string",
                    "description": "The filename to read (relative to working directory), e.g., 'dials.index.log', 'dials.scale.log'"
                },
                "tail_lines": {
                    "type": "integer",
                    "description": "If set, only return the last N lines of the file (useful for large log files). Default: return entire file up to max size."
                },
                "max_chars": {
                    "type": "integer",
                    "description": "Maximum number of characters to return (default: 50000). Large files will be truncated from the beginning."
                }
            },
            "required": ["filename"]
        }
    },
    {
        "name": "open_file",
        "description": "Open a file in the appropriate viewer. For HTML files (e.g., dials.scale.html, dials.report.html), opens in a web browser. For .expt/.refl files, suggests the appropriate DIALS viewer. Use this when the user wants to view HTML reports or other output files.",
        "input_schema": {
            "type": "object",
            "properties": {
                "filename": {
                    "type": "string",
                    "description": "The filename to open (relative to working directory)"
                }
            },
            "required": ["filename"]
        }
    },
    {
        "name": "change_working_directory",
        "description": "Change the current working directory. Use this when the user asks to 'switch to', 'go to', or 'move to' a directory. By default, this does NOT create new directories — it only switches to existing ones. Set create=true ONLY when the user explicitly asks to 'create', 'make', or 'new' a directory. If the directory is not found, the tool will search the current and parent directories for close matches (handles typos and case sensitivity).",
        "input_schema": {
            "type": "object",
            "properties": {
                "path": {
                    "type": "string",
                    "description": "The directory path to switch to. Can be absolute (/path/to/dir) or relative (subdir, ../sibling)."
                },
                "create": {
                    "type": "boolean",
                    "description": "If true, create the directory if it doesn't exist. Default: false. Only set to true when user explicitly says 'create', 'make', or 'new'."
                }
            },
            "required": ["path"]
        }
    },
    {
        "name": "change_data_directory",
        "description": "Change the raw data directory where input files (images, HDF5, CBF, NXS) are located. Use this when the user says their data is in a different location, or wants to process a different dataset. The agent will re-scan the new directory for data files.",
        "input_schema": {
            "type": "object",
            "properties": {
                "path": {
                    "type": "string",
                    "description": "The directory path containing raw diffraction data files."
                }
            },
            "required": ["path"]
        }
    },
    {
        "name": "calculate",
        "description": "Perform a mathematical calculation. Use this for ANY arithmetic: counting, subtraction, division, percentages, ranges, etc. Do NOT do mental math — always use this tool for numerical calculations to avoid errors.",
        "input_schema": {
            "type": "object",
            "properties": {
                "expression": {
                    "type": "string",
                    "description": "A Python math expression to evaluate (e.g., '1200 * 0.1', '67.85 - 67.82', '107640 / 1200', '100 * 12', '(3600 - 1200) / 100')"
                },
                "description": {
                    "type": "string",
                    "description": "Brief description of what this calculation represents"
                }
            },
            "required": ["expression"]
        }
    },
    {
        "name": "get_timing_report",
        "description": "Get the timing report showing how long each DIALS command took. The agent automatically records start time, end time, and duration for every command. Use this when the user asks about timing, performance, or how long steps took. The data is also saved to dials_agent_timing.log in the working directory.",
        "input_schema": {
            "type": "object",
            "properties": {},
            "required": []
        }
    },
    {
        "name": "run_shell_command",
        "description": "Run a shell command in the working directory. Use this for non-DIALS commands like ls, rm, mv, cp, cat, head, tail, wc, grep, find, etc. For destructive commands (rm, mv), the user will be asked to confirm before execution. Use this instead of telling the user to run commands manually.",
        "input_schema": {
            "type": "object",
            "properties": {
                "command": {
                    "type": "string",
                    "description": "The shell command to execute (e.g., 'ls -la', 'rm *.expt *.refl', 'cat dials.index.log | tail -20')"
                },
                "explanation": {
                    "type": "string",
                    "description": "Brief explanation of what this command does"
                }
            },
            "required": ["command", "explanation"]
        }
    },
    {
        "name": "lookup_phil_params",
        "description": "Look up the full PHIL parameter documentation for any DIALS command. Returns the complete parameter listing with help text, types, defaults, and expert levels. Use this when the user asks about available parameters for a specific command, wants to know what options exist, or when you need to suggest advanced parameters for troubleshooting. This reads from pre-fetched documentation generated by running 'dials.program -c -e2 -a2'.",
        "input_schema": {
            "type": "object",
            "properties": {
                "command": {
                    "type": "string",
                    "description": "The DIALS command name (e.g., 'dials.index', 'dials.scale', 'dials.find_spots')"
                },
                "search_term": {
                    "type": "string",
                    "description": "Optional: search for a specific parameter or keyword within the output (case-insensitive). If provided, only matching lines and their context will be returned."
                }
            },
            "required": ["command"]
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
    }
]


def get_tools() -> list[dict[str, Any]]:
    """Get the list of tool definitions for Claude."""
    return TOOLS


def get_tool_names() -> list[str]:
    """Get the list of tool names."""
    return [tool["name"] for tool in TOOLS]


# Mapping of workflow stages to expected files
WORKFLOW_FILES = {
    "import": ["imported.expt"],
    "find_spots": ["strong.refl"],
    "index": ["indexed.expt", "indexed.refl"],
    "refine": ["refined.expt", "refined.refl"],
    "integrate": ["integrated.expt", "integrated.refl"],
    "symmetry": ["symmetrized.expt", "symmetrized.refl"],
    "scale": ["scaled.expt", "scaled.refl"],
    "export": ["scaled.mtz", "*.mtz"]
}


# Mapping of file patterns to workflow stages
FILE_TO_STAGE = {
    "imported.expt": "import",
    "strong.refl": "find_spots",
    "indexed.expt": "index",
    "indexed.refl": "index",
    "refined.expt": "refine",
    "refined.refl": "refine",
    "integrated.expt": "integrate",
    "integrated.refl": "integrate",
    "symmetrized.expt": "symmetry",
    "symmetrized.refl": "symmetry",
    "scaled.expt": "scale",
    "scaled.refl": "scale",
}


def determine_workflow_stage(files: list[str]) -> tuple[str, str]:
    """
    Determine the current workflow stage based on existing files.
    
    Args:
        files: List of filenames in the working directory
        
    Returns:
        Tuple of (current_stage, suggested_next_step)
    """
    stages_completed = set()
    
    for filename in files:
        if filename in FILE_TO_STAGE:
            stages_completed.add(FILE_TO_STAGE[filename])
    
    # Determine current stage and next step
    workflow_order = ["import", "image_viewer", "find_spots", "index", "refine", "integrate", "symmetry", "scale", "export"]
    
    current_stage = "none"
    for stage in reversed(workflow_order):
        if stage in stages_completed:
            current_stage = stage
            break
    
    # Suggest next step
    if current_stage == "none":
        next_step = "import"
    else:
        try:
            current_idx = workflow_order.index(current_stage)
            if current_idx < len(workflow_order) - 1:
                next_step = workflow_order[current_idx + 1]
            else:
                next_step = "complete"
        except ValueError:
            next_step = "import"
    
    return current_stage, next_step


# Command information for listing
COMMAND_INFO = {
    "workflow": {
        "dials.import": "Import diffraction images and create experiment file",
        "dials.find_spots": "Find strong diffraction spots on images",
        "dials.index": "Assign Miller indices and determine unit cell",
        "dials.refine": "Refine crystal and detector models",
        "dials.integrate": "Measure spot intensities",
        "dials.symmetry": "Determine Patterson symmetry (single crystal)",
        "dials.cosym": "Determine symmetry with indexing ambiguity resolution (multiple crystals)",
        "dials.scale": "Apply corrections and scale data",
        "dials.merge": "Merge scaled data into MTZ with R-free flags and French-Wilson",
        "dials.export": "Export data to other formats (MTZ, mmCIF, SHELX, etc.)",
    },
    "utility": {
        "dials.show": "Display experiment and reflection information",
        "dials.report": "Generate HTML analysis report with diagnostic plots",
        "dials.refine_bravais_settings": "Determine possible Bravais lattices",
        "dials.reindex": "Change indexing or space group",
        "dials.detect_blanks": "Identify blank or damaged images in a scan",
        "dials.estimate_resolution": "Estimate resolution limits using CC½, I/σ, etc.",
        "dials.estimate_gain": "Estimate detector gain from images",
        "dials.split_experiments": "Split multi-experiment file into separate files",
        "dials.combine_experiments": "Combine multiple experiment/reflection files",
        "dials.filter_reflections": "Filter reflections by flags, resolution, partiality",
        "dials.sort_reflections": "Sort reflections by column values",
        "dials.slice_sequence": "Extract a subset of images from a scan",
        "dials.search_beam_position": "Search for optimal beam centre position",
        "dials.check_indexing_symmetry": "Check indexing symmetry of indexed reflections",
        "dials.two_theta_refine": "Refine unit cell using 2θ angles (more accurate)",
        "dials.generate_mask": "Generate pixel mask for excluding bad detector regions",
        "dials.apply_mask": "Apply a pixel mask to an experiment file",
        "dials.predict": "Predict reflection positions from experiment model",
        "dials.create_profile_model": "Create profile model from strong spots",
        "dials.modify_experiments": "Modify experiment models (beam, detector, goniometer)",
        "dials.assign_experiment_identifiers": "Assign unique identifiers to experiments",
        "dials.compute_delta_cchalf": "Compute ΔCC½ for outlier dataset detection",
        "dials.damage_analysis": "Analyze radiation damage using dose-dependent statistics",
        "dials.correlation_matrix": "Compute correlation matrix between datasets",
        "dials.refine_error_model": "Refine the error model for scaled data",
        "dials.missing_reflections": "Identify missing reflections for completeness analysis",
        "dials.background": "Analyze background levels across images",
        "dials.spot_counts_per_image": "Print spot counts per image for quality assessment",
        "dials.find_hot_pixels": "Find hot pixels in detector images",
        "dials.anvil_correction": "Apply diamond anvil cell absorption correction",
        "dials.import_xds": "Import XDS processing results into DIALS format",
        "dials.align_crystal": "Calculate goniometer settings to align crystal axes",
        "dials.cluster_unit_cell": "Cluster unit cells from multiple experiments",
        "dials.unit_cell_histogram": "Plot histogram of unit cell parameters",
        "dials.sequence_to_stills": "Convert rotation data to still shots",
        "dials.complete_full_sphere": "Calculate goniometer settings for full sphere",
    },
    "serial_crystallography": {
        "dials.stills_process": "Full SSX/stills processing pipeline (import→integrate)",
        "dials.ssx_index": "Index serial crystallography still shots",
        "dials.ssx_integrate": "Integrate serial crystallography still shots",
        "dials.split_still_data": "Split still data into subsets",
    },
    "visualization": {
        "dials.image_viewer": "Interactive image viewer with spot overlay (GUI)",
        "dials.reciprocal_lattice_viewer": "3D reciprocal space viewer (GUI)",
        "dials.report": "Generate HTML report with plots",
        "dials.plot_scan_varying_model": "Plot scan-varying crystal model parameters",
        "dials.stereographic_projection": "Generate stereographic projections",
        "dials.shadow_plot": "Plot goniometer shadow regions",
        "dials.rl_png": "Generate reciprocal lattice PNG images",
        "dials.rs_mapper": "Map data into reciprocal space",
        "dials.export_bitmaps": "Export diffraction images as bitmap files",
    },
    "format_conversion": {
        "dials.convert_to_cbf": "Convert images to CBF format",
        "dials.merge_cbf": "Merge multiple CBF files into one",
        "dials.export_best": "Export data for BEST strategy program",
    }
}


def get_commands_for_category(category: str = "all") -> dict[str, str]:
    """
    Get commands for a specific category.
    
    Args:
        category: One of 'all', 'workflow', 'utility', 'visualization'
        
    Returns:
        Dictionary mapping command names to descriptions
    """
    if category == "all":
        result = {}
        for cat_commands in COMMAND_INFO.values():
            result.update(cat_commands)
        return result
    elif category in COMMAND_INFO:
        return COMMAND_INFO[category]
    else:
        return {}


# Supported data file extensions for DIALS import
DATA_FILE_EXTENSIONS = {
    ".nxs",      # NeXus files (HDF5-based)
    ".h5",       # HDF5 files
    ".hdf5",     # HDF5 files
    ".cbf",      # Crystallographic Binary Format
    ".img",      # ADSC image files
    ".mccd",     # MAR CCD files
    ".sfrm",     # Bruker frames
    ".osc",      # Oscillation images
}


def discover_data_files(
    working_directory: str = ".",
    search_parent: bool = True,
    max_depth: int = 2,
    data_directory: str = ""
) -> list[dict[str, str]]:
    """
    Discover diffraction data files that can be imported by DIALS.
    
    Searches the working directory, optionally parent/sibling directories,
    and a configured data directory for common diffraction data file formats.
    
    Args:
        working_directory: The directory to start searching from
        search_parent: Whether to also search parent directory and siblings
        max_depth: Maximum depth to search within directories
        data_directory: Additional directory to search for input data files
        
    Returns:
        List of dicts with 'path' (relative path to file) and 'type' (file type)
    """
    data_files = []
    working_path = Path(working_directory).resolve()
    
    def scan_directory(directory: Path, relative_base: Path, current_depth: int = 0):
        """Recursively scan a directory for data files."""
        if current_depth > max_depth:
            return
        
        try:
            for item in directory.iterdir():
                if item.is_file():
                    suffix = item.suffix.lower()
                    if suffix in DATA_FILE_EXTENSIONS:
                        # Calculate relative path from working directory
                        try:
                            rel_path = item.relative_to(working_path)
                        except ValueError:
                            # File is not under working_path, use relative path with ..
                            rel_path = os.path.relpath(item, working_path)
                        
                        data_files.append({
                            "path": str(rel_path),
                            "type": suffix[1:].upper(),  # Remove dot, uppercase
                            "name": item.name,
                            "size_mb": round(item.stat().st_size / (1024 * 1024), 1)
                        })
                elif item.is_dir() and not item.name.startswith('.'):
                    # Recurse into subdirectories
                    scan_directory(item, relative_base, current_depth + 1)
        except PermissionError:
            pass  # Skip directories we can't access
    
    # Scan the working directory
    scan_directory(working_path, working_path)
    
    # Optionally scan parent directory and siblings
    if search_parent and working_path.parent.exists():
        parent = working_path.parent
        
        # Scan parent directory itself (not recursively)
        try:
            for item in parent.iterdir():
                if item.is_file():
                    suffix = item.suffix.lower()
                    if suffix in DATA_FILE_EXTENSIONS:
                        rel_path = os.path.relpath(item, working_path)
                        data_files.append({
                            "path": str(rel_path),
                            "type": suffix[1:].upper(),
                            "name": item.name,
                            "size_mb": round(item.stat().st_size / (1024 * 1024), 1)
                        })
        except PermissionError:
            pass
        
        # Scan sibling directories
        try:
            for sibling in parent.iterdir():
                if sibling.is_dir() and sibling != working_path and not sibling.name.startswith('.'):
                    scan_directory(sibling, working_path, current_depth=1)
        except PermissionError:
            pass
    
    # Scan the configured data directory if provided
    if data_directory:
        data_path = Path(data_directory).resolve()
        if data_path.exists() and data_path != working_path:
            # Track already-found files by resolved absolute path to avoid duplicates
            existing_resolved = set()
            for f in data_files:
                try:
                    # Resolve relative paths against working_path
                    p = Path(f["path"])
                    if not p.is_absolute():
                        p = (working_path / p).resolve()
                    else:
                        p = p.resolve()
                    existing_resolved.add(str(p))
                except (OSError, ValueError):
                    pass
            
            def scan_data_directory(directory: Path, current_depth: int = 0):
                """Scan data directory for data files, using absolute paths."""
                if current_depth > max_depth:
                    return
                try:
                    for item in directory.iterdir():
                        if item.is_file():
                            suffix = item.suffix.lower()
                            if suffix in DATA_FILE_EXTENSIONS:
                                resolved = str(item.resolve())
                                if resolved not in existing_resolved:
                                    # Use absolute path for data directory files
                                    data_files.append({
                                        "path": str(item),
                                        "type": suffix[1:].upper(),
                                        "name": item.name,
                                        "size_mb": round(item.stat().st_size / (1024 * 1024), 1)
                                    })
                                    existing_resolved.add(resolved)
                        elif item.is_dir() and not item.name.startswith('.'):
                            scan_data_directory(item, current_depth + 1)
                except PermissionError:
                    pass
            
            scan_data_directory(data_path)
    
    # Sort by path for consistent ordering
    data_files.sort(key=lambda x: x["path"])
    
    return data_files


def format_data_files_for_prompt(data_files: list[dict[str, str]]) -> str:
    """
    Format discovered data files into a string for inclusion in the system prompt.
    
    Args:
        data_files: List of data file info dicts from discover_data_files()
        
    Returns:
        Formatted string describing available data files
    """
    if not data_files:
        return "No diffraction data files found in the working directory or nearby."
    
    lines = ["Available diffraction data files:"]
    for f in data_files:
        lines.append(f"- {f['path']} ({f['type']}, {f['size_mb']} MB)")
    
    return "\n".join(lines)


# ============================================================================
# PHIL Parameter Lookup
# ============================================================================

# Base directory for PHIL parameter files (relative to project root)
_PHIL_PARAMS_DIR = Path(__file__).parent.parent.parent / "docs" / "phil_params"


def lookup_phil_params(command: str, search_term: str = "") -> str:
    """
    Look up PHIL parameter documentation for a DIALS command.
    
    Args:
        command: DIALS command name (e.g., 'dials.index')
        search_term: Optional search term to filter results
        
    Returns:
        String containing the PHIL parameter documentation
    """
    # Normalize command name to filename
    filename = command.replace(".", "_") + ".txt"
    filepath = _PHIL_PARAMS_DIR / filename
    
    if not filepath.exists():
        # Try alternative paths
        alt_path = Path(os.environ.get("DIALS_AGENT_ROOT", "")) / "docs" / "phil_params" / filename
        if alt_path.exists():
            filepath = alt_path
        else:
            return (
                f"No PHIL parameter documentation found for '{command}'.\n"
                f"Looked in: {_PHIL_PARAMS_DIR}\n"
                f"Available commands can be listed with: ls docs/phil_params/\n"
                f"You can generate it by running: {command} -c -e2 -a2"
            )
    
    try:
        content = filepath.read_text(encoding="utf-8")
    except Exception as e:
        return f"Error reading PHIL params for {command}: {e}"
    
    if not search_term:
        # Return full content, but truncate if very large
        if len(content) > 15000:
            return (
                content[:15000] +
                f"\n\n... [TRUNCATED - {len(content)} chars total. "
                f"Use search_term to find specific parameters]"
            )
        return content
    
    # Search for specific term
    search_lower = search_term.lower()
    lines = content.split("\n")
    matching_sections = []
    
    for i, line in enumerate(lines):
        if search_lower in line.lower():
            # Include context: 2 lines before and 5 lines after
            start = max(0, i - 2)
            end = min(len(lines), i + 6)
            section = "\n".join(lines[start:end])
            matching_sections.append(f"--- Line {i+1} ---\n{section}")
    
    if not matching_sections:
        return f"No parameters matching '{search_term}' found in {command}."
    
    return (
        f"Parameters matching '{search_term}' in {command}:\n\n" +
        "\n\n".join(matching_sections)
    )


# ============================================================================
# Problem Diagnosis
# ============================================================================

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
    
    # Match problem to known solutions
    matched_keys = []
    
    # Keyword matching
    keyword_map = {
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
    
    for keyword, key in keyword_map.items():
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
