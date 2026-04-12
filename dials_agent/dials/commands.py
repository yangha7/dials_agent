"""
DIALS command definitions and metadata.

This module defines the available DIALS commands, their parameters,
and expected inputs/outputs for the AI agent.
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Optional


class CommandCategory(Enum):
    """Categories of DIALS commands."""
    WORKFLOW = "workflow"
    UTILITY = "utility"
    VISUALIZATION = "visualization"


@dataclass
class CommandParameter:
    """Definition of a command parameter."""
    name: str
    description: str
    param_type: str = "string"  # string, int, float, bool, path
    required: bool = False
    default: Optional[str] = None
    example: Optional[str] = None


@dataclass
class CommandDefinition:
    """Definition of a DIALS command."""
    name: str
    description: str
    category: CommandCategory
    input_files: list[str] = field(default_factory=list)
    output_files: list[str] = field(default_factory=list)
    parameters: list[CommandParameter] = field(default_factory=list)
    requires_gui: bool = False
    typical_runtime: str = "seconds"  # seconds, minutes, hours
    
    def get_basic_usage(self) -> str:
        """Get basic usage string for the command."""
        inputs = " ".join(self.input_files) if self.input_files else ""
        return f"{self.name} {inputs}".strip()


# Define all DIALS commands
DIALS_COMMANDS = {
    # Workflow commands
    "dials.import": CommandDefinition(
        name="dials.import",
        description="Import diffraction images and create an experiment file containing beam, detector, goniometer, and scan models.",
        category=CommandCategory.WORKFLOW,
        input_files=["/path/to/images/*.cbf"],
        output_files=["imported.expt"],
        parameters=[
            CommandParameter(
                name="output.experiments",
                description="Output experiment file name",
                default="imported.expt",
                example="output.experiments=my_data.expt"
            ),
            CommandParameter(
                name="template",
                description="Image filename template with # for frame numbers",
                example="template=/data/image_####.cbf"
            ),
            CommandParameter(
                name="geometry.beam.wavelength",
                description="Override beam wavelength in Angstroms",
                param_type="float",
                example="geometry.beam.wavelength=0.9795"
            ),
            CommandParameter(
                name="geometry.detector.distance",
                description="Override detector distance in mm",
                param_type="float",
                example="geometry.detector.distance=200"
            ),
            CommandParameter(
                name="geometry.goniometer.axis",
                description="Override rotation axis direction",
                example="geometry.goniometer.axis=1,0,0"
            ),
        ],
        typical_runtime="seconds"
    ),
    
    "dials.find_spots": CommandDefinition(
        name="dials.find_spots",
        description="Find strong diffraction spots on images using a dispersion threshold algorithm.",
        category=CommandCategory.WORKFLOW,
        input_files=["imported.expt"],
        output_files=["strong.refl"],
        parameters=[
            CommandParameter(
                name="output.reflections",
                description="Output reflection file name",
                default="strong.refl",
                example="output.reflections=spots.refl"
            ),
            CommandParameter(
                name="spotfinder.threshold.dispersion.sigma_strong",
                description="Sigma threshold for strong spots (higher = fewer spots)",
                param_type="float",
                default="3.0",
                example="spotfinder.threshold.dispersion.sigma_strong=6"
            ),
            CommandParameter(
                name="spotfinder.threshold.dispersion.sigma_background",
                description="Sigma threshold for background",
                param_type="float",
                default="6.0"
            ),
            CommandParameter(
                name="spotfinder.filter.d_min",
                description="Minimum resolution for spots in Angstroms",
                param_type="float",
                example="spotfinder.filter.d_min=2.0"
            ),
            CommandParameter(
                name="spotfinder.filter.d_max",
                description="Maximum resolution for spots in Angstroms",
                param_type="float",
                example="spotfinder.filter.d_max=50"
            ),
            CommandParameter(
                name="spotfinder.filter.min_spot_size",
                description="Minimum spot size in pixels",
                param_type="int",
                default="3"
            ),
            CommandParameter(
                name="spotfinder.filter.max_spot_size",
                description="Maximum spot size in pixels",
                param_type="int",
                default="1000"
            ),
            CommandParameter(
                name="spotfinder.scan_range",
                description="Image range to search (start, end)",
                example="spotfinder.scan_range=1,100"
            ),
        ],
        typical_runtime="minutes"
    ),
    
    "dials.index": CommandDefinition(
        name="dials.index",
        description="Index the diffraction spots to determine the crystal unit cell and orientation, assigning Miller indices to each spot.",
        category=CommandCategory.WORKFLOW,
        input_files=["imported.expt", "strong.refl"],
        output_files=["indexed.expt", "indexed.refl"],
        parameters=[
            CommandParameter(
                name="output.experiments",
                description="Output experiment file name",
                default="indexed.expt"
            ),
            CommandParameter(
                name="output.reflections",
                description="Output reflection file name",
                default="indexed.refl"
            ),
            CommandParameter(
                name="unit_cell",
                description="Known unit cell parameters (a,b,c,alpha,beta,gamma)",
                example="unit_cell=37,79,79,90,90,90"
            ),
            CommandParameter(
                name="space_group",
                description="Known space group",
                example="space_group=P212121"
            ),
            CommandParameter(
                name="indexing.method",
                description="Indexing method to use",
                default="fft3d",
                example="indexing.method=fft1d"
            ),
            CommandParameter(
                name="joint",
                description="Index multiple crystals jointly (true) or separately (false)",
                param_type="bool",
                default="true",
                example="joint=false"
            ),
            CommandParameter(
                name="max_lattices",
                description="Maximum number of lattices to find",
                param_type="int",
                default="1",
                example="max_lattices=2"
            ),
        ],
        typical_runtime="minutes"
    ),
    
    "dials.refine": CommandDefinition(
        name="dials.refine",
        description="Refine the crystal and detector models to improve the agreement between predicted and observed spot positions.",
        category=CommandCategory.WORKFLOW,
        input_files=["indexed.expt", "indexed.refl"],
        output_files=["refined.expt", "refined.refl"],
        parameters=[
            CommandParameter(
                name="output.experiments",
                description="Output experiment file name",
                default="refined.expt"
            ),
            CommandParameter(
                name="output.reflections",
                description="Output reflection file name",
                default="refined.refl"
            ),
            CommandParameter(
                name="scan_varying",
                description="Allow crystal model to vary during scan",
                param_type="bool",
                default="false",
                example="scan_varying=true"
            ),
            CommandParameter(
                name="detector.fix",
                description="Fix detector parameters",
                example="detector.fix=all"
            ),
            CommandParameter(
                name="beam.fix",
                description="Fix beam parameters",
                example="beam.fix=all"
            ),
        ],
        typical_runtime="minutes"
    ),
    
    "dials.integrate": CommandDefinition(
        name="dials.integrate",
        description="Integrate the diffraction spots to measure their intensities using profile fitting.",
        category=CommandCategory.WORKFLOW,
        input_files=["refined.expt", "refined.refl"],
        output_files=["integrated.expt", "integrated.refl"],
        parameters=[
            CommandParameter(
                name="output.experiments",
                description="Output experiment file name",
                default="integrated.expt"
            ),
            CommandParameter(
                name="output.reflections",
                description="Output reflection file name",
                default="integrated.refl"
            ),
            CommandParameter(
                name="prediction.d_min",
                description="Minimum resolution for integration",
                param_type="float",
                example="prediction.d_min=1.5"
            ),
            CommandParameter(
                name="prediction.d_max",
                description="Maximum resolution for integration",
                param_type="float",
                example="prediction.d_max=50"
            ),
            CommandParameter(
                name="profile.fitting",
                description="Use profile fitting",
                param_type="bool",
                default="true"
            ),
            CommandParameter(
                name="nproc",
                description="Number of processors to use",
                param_type="int",
                example="nproc=4"
            ),
        ],
        typical_runtime="minutes"
    ),
    
    "dials.symmetry": CommandDefinition(
        name="dials.symmetry",
        description="Determine the Patterson symmetry of the crystal from the integrated data (for single crystals).",
        category=CommandCategory.WORKFLOW,
        input_files=["integrated.expt", "integrated.refl"],
        output_files=["symmetrized.expt", "symmetrized.refl"],
        parameters=[
            CommandParameter(
                name="output.experiments",
                description="Output experiment file name",
                default="symmetrized.expt"
            ),
            CommandParameter(
                name="output.reflections",
                description="Output reflection file name",
                default="symmetrized.refl"
            ),
        ],
        typical_runtime="minutes"
    ),
    
    "dials.cosym": CommandDefinition(
        name="dials.cosym",
        description="Determine symmetry and resolve indexing ambiguity for multiple crystals using correlation analysis.",
        category=CommandCategory.WORKFLOW,
        input_files=["integrated.expt", "integrated.refl"],
        output_files=["symmetrized.expt", "symmetrized.refl"],
        parameters=[
            CommandParameter(
                name="output.experiments",
                description="Output experiment file name",
                default="symmetrized.expt"
            ),
            CommandParameter(
                name="output.reflections",
                description="Output reflection file name",
                default="symmetrized.refl"
            ),
            CommandParameter(
                name="space_group",
                description="Target space group",
                example="space_group=I213"
            ),
        ],
        typical_runtime="minutes"
    ),
    
    "dials.scale": CommandDefinition(
        name="dials.scale",
        description="Scale the integrated data, applying corrections for absorption, decay, and other systematic effects.",
        category=CommandCategory.WORKFLOW,
        input_files=["symmetrized.expt", "symmetrized.refl"],
        output_files=["scaled.expt", "scaled.refl", "dials.scale.html"],
        parameters=[
            CommandParameter(
                name="output.experiments",
                description="Output experiment file name",
                default="scaled.expt"
            ),
            CommandParameter(
                name="output.reflections",
                description="Output reflection file name",
                default="scaled.refl"
            ),
            CommandParameter(
                name="d_min",
                description="High resolution cutoff",
                param_type="float",
                example="d_min=1.8"
            ),
            CommandParameter(
                name="d_max",
                description="Low resolution cutoff",
                param_type="float",
                example="d_max=50"
            ),
            CommandParameter(
                name="physical.absorption_correction",
                description="Apply absorption correction",
                param_type="bool",
                default="true"
            ),
            CommandParameter(
                name="outlier_rejection",
                description="Outlier rejection method",
                default="standard",
                example="outlier_rejection=simple"
            ),
        ],
        typical_runtime="minutes"
    ),
    
    "dials.export": CommandDefinition(
        name="dials.export",
        description="Export the processed data to other formats for downstream analysis (e.g., MTZ for CCP4/Phenix).",
        category=CommandCategory.WORKFLOW,
        input_files=["scaled.expt", "scaled.refl"],
        output_files=["scaled.mtz"],
        parameters=[
            CommandParameter(
                name="format",
                description="Output format",
                default="mtz",
                example="format=nxs"
            ),
            CommandParameter(
                name="mtz.hklout",
                description="Output MTZ filename",
                default="scaled.mtz",
                example="mtz.hklout=output.mtz"
            ),
            CommandParameter(
                name="intensity",
                description="Intensity type to export",
                default="scale",
                example="intensity=profile"
            ),
        ],
        typical_runtime="seconds"
    ),
    
    # Utility commands
    "dials.show": CommandDefinition(
        name="dials.show",
        description="Display information about experiment and reflection files.",
        category=CommandCategory.UTILITY,
        input_files=["*.expt", "*.refl"],
        output_files=[],
        parameters=[
            CommandParameter(
                name="show_all_reflection_data",
                description="Show all reflection data columns",
                param_type="bool",
                default="false"
            ),
        ],
        typical_runtime="seconds"
    ),
    
    "dials.report": CommandDefinition(
        name="dials.report",
        description="Generate an HTML report with analysis plots and statistics.",
        category=CommandCategory.UTILITY,
        input_files=["*.expt", "*.refl"],
        output_files=["dials.report.html"],
        parameters=[
            CommandParameter(
                name="output.html",
                description="Output HTML filename",
                default="dials.report.html"
            ),
        ],
        typical_runtime="seconds"
    ),
    
    "dials.refine_bravais_settings": CommandDefinition(
        name="dials.refine_bravais_settings",
        description="Determine possible Bravais lattices consistent with the indexed data.",
        category=CommandCategory.UTILITY,
        input_files=["indexed.expt", "indexed.refl"],
        output_files=["bravais_summary.json", "bravais_setting_*.expt"],
        parameters=[],
        typical_runtime="minutes"
    ),
    
    "dials.reindex": CommandDefinition(
        name="dials.reindex",
        description="Change the indexing or space group of the data.",
        category=CommandCategory.UTILITY,
        input_files=["*.expt", "*.refl"],
        output_files=["reindexed.expt", "reindexed.refl"],
        parameters=[
            CommandParameter(
                name="change_of_basis_op",
                description="Change of basis operator",
                example="change_of_basis_op=a,b,c"
            ),
            CommandParameter(
                name="space_group",
                description="New space group",
                example="space_group=P212121"
            ),
        ],
        typical_runtime="seconds"
    ),
    
    "dials.detect_blanks": CommandDefinition(
        name="dials.detect_blanks",
        description="Identify blank or damaged images in the dataset.",
        category=CommandCategory.UTILITY,
        input_files=["imported.expt", "strong.refl"],
        output_files=[],
        parameters=[
            CommandParameter(
                name="phi_step",
                description="Phi step for analysis",
                param_type="float",
                default="2.0"
            ),
        ],
        typical_runtime="seconds"
    ),
    
    "dials.estimate_resolution": CommandDefinition(
        name="dials.estimate_resolution",
        description="Estimate resolution limits based on various criteria.",
        category=CommandCategory.UTILITY,
        input_files=["scaled.expt", "scaled.refl"],
        output_files=[],
        parameters=[
            CommandParameter(
                name="cc_half",
                description="CC1/2 cutoff for resolution",
                param_type="float",
                default="0.3"
            ),
            CommandParameter(
                name="isigma",
                description="I/sigma cutoff for resolution",
                param_type="float",
                default="0.25"
            ),
        ],
        typical_runtime="seconds"
    ),
    
    "dials.merge": CommandDefinition(
        name="dials.merge",
        description="Merge scaled data and output MTZ file.",
        category=CommandCategory.UTILITY,
        input_files=["scaled.expt", "scaled.refl"],
        output_files=["merged.mtz"],
        parameters=[
            CommandParameter(
                name="output.mtz",
                description="Output MTZ filename",
                default="merged.mtz"
            ),
        ],
        typical_runtime="seconds"
    ),
    
    "dials.split_experiments": CommandDefinition(
        name="dials.split_experiments",
        description="Split an experiment list into separate files.",
        category=CommandCategory.UTILITY,
        input_files=["*.expt", "*.refl"],
        output_files=["split_*.expt", "split_*.refl"],
        parameters=[],
        typical_runtime="seconds"
    ),
    
    "dials.combine_experiments": CommandDefinition(
        name="dials.combine_experiments",
        description="Combine multiple experiment lists into one.",
        category=CommandCategory.UTILITY,
        input_files=["*.expt", "*.refl"],
        output_files=["combined.expt", "combined.refl"],
        parameters=[],
        typical_runtime="seconds"
    ),
    
    # Visualization commands
    "dials.image_viewer": CommandDefinition(
        name="dials.image_viewer",
        description="Interactive viewer for diffraction images with spot overlay.",
        category=CommandCategory.VISUALIZATION,
        input_files=["*.expt"],
        output_files=[],
        parameters=[],
        requires_gui=True,
        typical_runtime="seconds"
    ),
    
    "dials.reciprocal_lattice_viewer": CommandDefinition(
        name="dials.reciprocal_lattice_viewer",
        description="3D viewer for reciprocal space showing indexed reflections.",
        category=CommandCategory.VISUALIZATION,
        input_files=["indexed.expt", "indexed.refl"],
        output_files=[],
        parameters=[],
        requires_gui=True,
        typical_runtime="seconds"
    ),
}


def get_command(name: str) -> Optional[CommandDefinition]:
    """
    Get a command definition by name.
    
    Args:
        name: Command name (e.g., 'dials.import')
        
    Returns:
        CommandDefinition or None if not found
    """
    return DIALS_COMMANDS.get(name)


def get_commands_by_category(category: CommandCategory) -> dict[str, CommandDefinition]:
    """
    Get all commands in a category.
    
    Args:
        category: The command category
        
    Returns:
        Dictionary of command name to definition
    """
    return {
        name: cmd for name, cmd in DIALS_COMMANDS.items()
        if cmd.category == category
    }


def get_workflow_commands() -> list[str]:
    """Get the ordered list of workflow commands."""
    return [
        "dials.import",
        "dials.find_spots",
        "dials.index",
        "dials.refine",
        "dials.integrate",
        "dials.symmetry",
        "dials.scale",
        "dials.export"
    ]


def validate_command(command_str: str) -> tuple[bool, str]:
    """
    Validate a DIALS command string.
    
    Args:
        command_str: The command string to validate
        
    Returns:
        Tuple of (is_valid, error_message)
    """
    parts = command_str.strip().split()
    if not parts:
        return False, "Empty command"
    
    cmd_name = parts[0]
    
    # Check if it's a known DIALS command
    if not cmd_name.startswith("dials."):
        return False, f"Not a DIALS command: {cmd_name}"
    
    if cmd_name not in DIALS_COMMANDS:
        # Allow unknown dials.* commands but warn
        return True, f"Warning: Unknown DIALS command '{cmd_name}'"
    
    return True, ""


def get_next_workflow_command(current_files: list[str]) -> Optional[str]:
    """
    Suggest the next workflow command based on existing files.
    
    Args:
        current_files: List of files in the working directory
        
    Returns:
        Suggested next command or None if workflow is complete
    """
    file_set = set(current_files)
    
    # Check workflow progression
    if "scaled.mtz" in file_set:
        return None  # Workflow complete
    
    if "scaled.expt" in file_set and "scaled.refl" in file_set:
        return "dials.export"
    
    if "symmetrized.expt" in file_set and "symmetrized.refl" in file_set:
        return "dials.scale"
    
    if "integrated.expt" in file_set and "integrated.refl" in file_set:
        return "dials.symmetry"
    
    if "refined.expt" in file_set and "refined.refl" in file_set:
        return "dials.integrate"
    
    if "indexed.expt" in file_set and "indexed.refl" in file_set:
        return "dials.refine"
    
    if "imported.expt" in file_set and "strong.refl" in file_set:
        return "dials.index"
    
    if "imported.expt" in file_set:
        return "dials.image_viewer"
    
    return "dials.import"
