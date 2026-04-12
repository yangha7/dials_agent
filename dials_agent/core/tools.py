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
        "dials.export": "Export data to other formats (MTZ, etc.)",
    },
    "utility": {
        "dials.show": "Display experiment and reflection information",
        "dials.report": "Generate HTML analysis report",
        "dials.refine_bravais_settings": "Determine possible Bravais lattices",
        "dials.reindex": "Change indexing or space group",
        "dials.detect_blanks": "Identify blank or damaged images",
        "dials.estimate_resolution": "Estimate resolution limits",
        "dials.merge": "Merge scaled data to MTZ",
        "dials.split_experiments": "Split experiment list into separate files",
        "dials.combine_experiments": "Combine multiple experiment lists",
    },
    "visualization": {
        "dials.image_viewer": "Interactive image viewer (GUI)",
        "dials.reciprocal_lattice_viewer": "3D reciprocal space viewer (GUI)",
        "dials.report": "Generate HTML report with plots",
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
    max_depth: int = 2
) -> list[dict[str, str]]:
    """
    Discover diffraction data files that can be imported by DIALS.
    
    Searches the working directory and optionally parent/sibling directories
    for common diffraction data file formats.
    
    Args:
        working_directory: The directory to start searching from
        search_parent: Whether to also search parent directory and siblings
        max_depth: Maximum depth to search within directories
        
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
