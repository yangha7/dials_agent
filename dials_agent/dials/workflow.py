"""
DIALS workflow state management.

This module tracks the state of a DIALS data processing workflow,
including completed steps, available files, and suggested next actions.
"""

import json
import logging
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Optional

from .commands import get_next_workflow_command, get_workflow_commands
from .executor import CommandResult

logger = logging.getLogger(__name__)


# Tutorial-based workflow suggestions with context
# Based on DIALS tutorial: https://dials.github.io/documentation/tutorials/processing_in_detail_betalactamase.html
WORKFLOW_SUGGESTIONS = {
    "import": {
        "next_command": "dials.image_viewer imported.expt",
        "explanation": "Now that the images are imported, the next step is to visualize the data using the image viewer. This allows you to inspect the diffraction images, check for any issues, and get familiar with your data before proceeding.",
        "tip": "Use the image viewer to check image quality, look for ice rings, and verify the beam center. Adjust the brightness slider until spots are clearly visible.",
        "optional_commands": ["dials.show imported.expt", "dials.find_spots imported.expt"]
    },
    "find_spots": {
        "next_command": "dials.index imported.expt strong.refl",
        "next_command_multi": "dials.index imported.expt strong.refl joint=false",
        "explanation": "Spots have been found. Next, we need to index them to determine the unit cell and assign Miller indices.",
        "explanation_multi": "For multiple crystals, use joint=false to index each sweep independently.",
        "tip": "If indexing fails, try: indexing.method=fft1d or provide a known unit cell. You can also try dials.search_beam_position first if the beam center seems wrong.",
        "optional_commands": [
            "dials.search_beam_position imported.expt strong.refl",
            "dials.reciprocal_lattice_viewer imported.expt strong.refl"
        ]
    },
    "index": {
        "next_command": "dials.refine indexed.expt indexed.refl",
        "explanation": (
            "Indexing is complete. Now we refine the crystal and detector models to improve accuracy. "
            "You can optionally run dials.refine_bravais_settings first to determine the correct "
            "Bravais lattice — this is recommended if you don't already know the space group."
        ),
        "tip": (
            "If you run refine_bravais_settings, choose the highest symmetry solution with good metric fit "
            "and low RMSD. Then use dials.reindex if the change_of_basis_op is not a,b,c. "
            "Example: dials.reindex indexed.refl change_of_basis_op=a+b,-a+b,c"
        ),
        "optional_commands": [
            "dials.refine_bravais_settings indexed.expt indexed.refl",
            "dials.reciprocal_lattice_viewer indexed.expt indexed.refl"
        ]
    },
    "refine_bravais_settings": {
        "next_command": "dials.reindex indexed.refl change_of_basis_op=<op_from_table>",
        "next_command_identity": "dials.refine bravais_setting_<N>.expt indexed.refl",
        "explanation": (
            "Bravais settings have been determined. Choose the best solution from the table "
            "(usually the highest symmetry with good metric fit and low RMSD, marked with *). "
            "If the change_of_basis_op is not a,b,c (identity), you need to reindex the reflections first."
        ),
        "tip": (
            "Use dials.reindex indexed.refl change_of_basis_op=<op> with the operator from the table. "
            "Then refine with: dials.refine bravais_setting_<N>.expt reindexed.refl"
        ),
    },
    "reindex": {
        "next_command": "dials.refine bravais_setting_<N>.expt reindexed.refl",
        "explanation": "Reflections have been reindexed. Now refine using the chosen Bravais setting experiment file and the reindexed reflections.",
        "tip": "Use the bravais_setting_N.expt file corresponding to your chosen solution from the Bravais settings table.",
    },
    "refine": {
        "next_command": "dials.integrate refined.expt refined.refl",
        "explanation": (
            "Models are refined. The refinement includes both static and scan-varying passes by default. "
            "Now we integrate to measure the spot intensities."
        ),
        "tip": "Integration may take several minutes depending on data size. You can set a resolution limit with prediction.d_min=1.8",
        "optional_commands": ["dials.report refined.expt refined.refl"]
    },
    "integrate": {
        "next_command": "dials.symmetry integrated.expt integrated.refl",
        "next_command_multi": "dials.cosym integrated.expt integrated.refl",
        "explanation": (
            "Integration complete. Now we determine the full crystal symmetry from the integrated intensities. "
            "This assesses both the Laue group symmetry and systematic absences to determine the space group."
        ),
        "explanation_multi": "For multiple crystals, use dials.cosym to resolve indexing ambiguity.",
        "tip": "This step determines the space group from the integrated intensities. It may change the space group from what was used during indexing.",
        "optional_commands": ["dials.image_viewer integrated.expt integrated.refl"]
    },
    "symmetry": {
        "next_command": "dials.scale symmetrized.expt symmetrized.refl",
        "explanation": (
            "Symmetry determined. Now we scale the data to correct for experimental effects "
            "(sample illumination/absorption, radiation damage) that cause symmetry-equivalent "
            "reflections to have unequal measured intensities."
        ),
        "tip": "For anomalous data, add anomalous=True. For high absorption, try physical.absorption_level=medium or high"
    },
    "scale": {
        "next_command": "dials.export scaled.expt scaled.refl",
        "next_command_merge": "dials.merge scaled.expt scaled.refl",
        "explanation": (
            "Scaling complete! The HTML report (dials.scale.html) contains detailed merging statistics. "
            "Export the data for downstream analysis, or merge for a scaled+merged MTZ."
        ),
        "tip": "Use dials.export for unmerged data, dials.merge for merged data. Most downstream software needs merged data.",
        "optional_commands": [
            "dials.report scaled.expt scaled.refl",
            "dials.estimate_resolution scaled.expt scaled.refl"
        ]
    },
    "export": {
        "next_command": None,
        "explanation": "🎉 Workflow complete! Your processed data is ready for structure determination.",
        "tip": "You can generate a detailed report with: dials.report scaled.expt scaled.refl"
    }
}


class WorkflowStage(Enum):
    """Stages in the DIALS workflow."""
    NOT_STARTED = "not_started"
    IMPORTED = "imported"
    SPOTS_FOUND = "spots_found"
    INDEXED = "indexed"
    REFINED = "refined"
    INTEGRATED = "integrated"
    SYMMETRY_DETERMINED = "symmetry_determined"
    SCALED = "scaled"
    EXPORTED = "exported"


# Mapping of files to workflow stages
FILE_TO_STAGE = {
    "imported.expt": WorkflowStage.IMPORTED,
    "strong.refl": WorkflowStage.SPOTS_FOUND,
    "indexed.expt": WorkflowStage.INDEXED,
    "indexed.refl": WorkflowStage.INDEXED,
    "refined.expt": WorkflowStage.REFINED,
    "refined.refl": WorkflowStage.REFINED,
    "integrated.expt": WorkflowStage.INTEGRATED,
    "integrated.refl": WorkflowStage.INTEGRATED,
    "symmetrized.expt": WorkflowStage.SYMMETRY_DETERMINED,
    "symmetrized.refl": WorkflowStage.SYMMETRY_DETERMINED,
    "scaled.expt": WorkflowStage.SCALED,
    "scaled.refl": WorkflowStage.SCALED,
}

# Stage progression order
STAGE_ORDER = [
    WorkflowStage.NOT_STARTED,
    WorkflowStage.IMPORTED,
    WorkflowStage.SPOTS_FOUND,
    WorkflowStage.INDEXED,
    WorkflowStage.REFINED,
    WorkflowStage.INTEGRATED,
    WorkflowStage.SYMMETRY_DETERMINED,
    WorkflowStage.SCALED,
    WorkflowStage.EXPORTED,
]

# Suggested commands for each stage
STAGE_COMMANDS = {
    WorkflowStage.NOT_STARTED: "dials.import",
    WorkflowStage.IMPORTED: "dials.image_viewer",
    WorkflowStage.SPOTS_FOUND: "dials.index",
    WorkflowStage.INDEXED: "dials.refine",
    WorkflowStage.REFINED: "dials.integrate",
    WorkflowStage.INTEGRATED: "dials.symmetry",
    WorkflowStage.SYMMETRY_DETERMINED: "dials.scale",
    WorkflowStage.SCALED: "dials.export",
    WorkflowStage.EXPORTED: None,
}


@dataclass
class CommandHistory:
    """Record of a command execution."""
    command: str
    timestamp: str
    success: bool
    duration: float
    output_files: list[str] = field(default_factory=list)
    metrics: dict[str, Any] = field(default_factory=dict)


@dataclass
class WorkflowState:
    """Current state of the workflow."""
    working_directory: str
    current_stage: WorkflowStage
    files: dict[str, list[str]]  # Category -> list of files
    command_history: list[CommandHistory] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    updated_at: str = field(default_factory=lambda: datetime.now().isoformat())


class WorkflowManager:
    """
    Manages the state of a DIALS data processing workflow.
    
    Tracks completed steps, available files, and provides suggestions
    for next actions.
    """
    
    def __init__(self, working_directory: str = "."):
        """
        Initialize the workflow manager.
        
        Args:
            working_directory: Directory containing DIALS files
        """
        self.working_directory = Path(working_directory).absolute()
        self.state = self._initialize_state()
    
    def _initialize_state(self) -> WorkflowState:
        """Initialize workflow state from existing files."""
        files = self._scan_files()
        stage = self._determine_stage(files)
        
        return WorkflowState(
            working_directory=str(self.working_directory),
            current_stage=stage,
            files=files
        )
    
    def _scan_files(self) -> dict[str, list[str]]:
        """Scan working directory for DIALS-related files."""
        files = {
            "experiments": [],
            "reflections": [],
            "mtz": [],
            "html": [],
            "json": [],
            "log": [],
            "images": [],
            "other": []
        }
        
        if not self.working_directory.exists():
            return files
        
        for f in self.working_directory.iterdir():
            if not f.is_file():
                continue
            
            name = f.name
            suffix = f.suffix.lower()
            
            if suffix == ".expt":
                files["experiments"].append(name)
            elif suffix == ".refl":
                files["reflections"].append(name)
            elif suffix == ".mtz":
                files["mtz"].append(name)
            elif suffix == ".html":
                files["html"].append(name)
            elif suffix == ".json":
                files["json"].append(name)
            elif suffix == ".log":
                files["log"].append(name)
            elif suffix in [".cbf", ".h5", ".nxs", ".img"]:
                files["images"].append(name)
        
        return files
    
    def _determine_stage(self, files: dict[str, list[str]]) -> WorkflowStage:
        """Determine current workflow stage from files."""
        all_files = set()
        for file_list in files.values():
            all_files.update(file_list)
        
        # Check for MTZ files (exported)
        if any(f.endswith(".mtz") for f in all_files):
            return WorkflowStage.EXPORTED
        
        # Check stages in reverse order
        stage_checks = [
            (WorkflowStage.SCALED, ["scaled.expt", "scaled.refl"]),
            (WorkflowStage.SYMMETRY_DETERMINED, ["symmetrized.expt", "symmetrized.refl"]),
            (WorkflowStage.INTEGRATED, ["integrated.expt", "integrated.refl"]),
            (WorkflowStage.REFINED, ["refined.expt", "refined.refl"]),
            (WorkflowStage.INDEXED, ["indexed.expt", "indexed.refl"]),
            (WorkflowStage.SPOTS_FOUND, ["strong.refl"]),
            (WorkflowStage.IMPORTED, ["imported.expt"]),
        ]
        
        for stage, required_files in stage_checks:
            if all(f in all_files for f in required_files):
                return stage
        
        return WorkflowStage.NOT_STARTED
    
    def refresh(self):
        """Refresh the workflow state from disk."""
        self.state.files = self._scan_files()
        self.state.current_stage = self._determine_stage(self.state.files)
        self.state.updated_at = datetime.now().isoformat()
    
    def record_command(
        self,
        result: CommandResult,
        metrics: Optional[dict[str, Any]] = None
    ):
        """
        Record a command execution in the history.
        
        Args:
            result: CommandResult from executor
            metrics: Optional parsed metrics
        """
        history = CommandHistory(
            command=result.command,
            timestamp=datetime.now().isoformat(),
            success=result.success,
            duration=result.duration,
            output_files=result.output_files,
            metrics=metrics or {}
        )
        
        self.state.command_history.append(history)
        self.refresh()
    
    def get_current_stage(self) -> WorkflowStage:
        """Get the current workflow stage."""
        return self.state.current_stage
    
    def get_stage_name(self) -> str:
        """Get human-readable name of current stage."""
        stage_names = {
            WorkflowStage.NOT_STARTED: "Not started",
            WorkflowStage.IMPORTED: "Images imported",
            WorkflowStage.SPOTS_FOUND: "Spots found",
            WorkflowStage.INDEXED: "Data indexed",
            WorkflowStage.REFINED: "Models refined",
            WorkflowStage.INTEGRATED: "Data integrated",
            WorkflowStage.SYMMETRY_DETERMINED: "Symmetry determined",
            WorkflowStage.SCALED: "Data scaled",
            WorkflowStage.EXPORTED: "Data exported",
        }
        return stage_names.get(self.state.current_stage, "Unknown")
    
    def get_next_command(self) -> Optional[str]:
        """Get the suggested next command."""
        return STAGE_COMMANDS.get(self.state.current_stage)
    
    def get_available_files(self) -> list[str]:
        """Get list of all DIALS-related files."""
        all_files = []
        for file_list in self.state.files.values():
            all_files.extend(file_list)
        return sorted(all_files)
    
    def get_experiment_files(self) -> list[str]:
        """Get list of experiment files."""
        return self.state.files.get("experiments", [])
    
    def get_reflection_files(self) -> list[str]:
        """Get list of reflection files."""
        return self.state.files.get("reflections", [])
    
    def get_input_files_for_stage(self, stage: Optional[WorkflowStage] = None) -> tuple[str, str]:
        """
        Get the appropriate input files for a workflow stage.
        
        Args:
            stage: Target stage (uses current stage if not provided)
            
        Returns:
            Tuple of (experiment_file, reflection_file)
        """
        stage = stage or self.state.current_stage
        
        # Map stages to expected input files
        stage_inputs = {
            WorkflowStage.NOT_STARTED: ("", ""),
            WorkflowStage.IMPORTED: ("imported.expt", ""),
            WorkflowStage.SPOTS_FOUND: ("imported.expt", "strong.refl"),
            WorkflowStage.INDEXED: ("indexed.expt", "indexed.refl"),
            WorkflowStage.REFINED: ("refined.expt", "refined.refl"),
            WorkflowStage.INTEGRATED: ("integrated.expt", "integrated.refl"),
            WorkflowStage.SYMMETRY_DETERMINED: ("symmetrized.expt", "symmetrized.refl"),
            WorkflowStage.SCALED: ("scaled.expt", "scaled.refl"),
        }
        
        return stage_inputs.get(stage, ("", ""))
    
    def is_complete(self) -> bool:
        """Check if the workflow is complete."""
        return self.state.current_stage == WorkflowStage.EXPORTED
    
    def get_progress_percentage(self) -> float:
        """Get workflow progress as a percentage."""
        try:
            current_idx = STAGE_ORDER.index(self.state.current_stage)
            return (current_idx / (len(STAGE_ORDER) - 1)) * 100
        except ValueError:
            return 0.0
    
    def is_multi_crystal(self) -> bool:
        """
        Determine if this is a multi-crystal dataset.
        
        Returns:
            True if multiple crystals/sweeps detected
        """
        # Check metadata if set
        if self.state.metadata.get("multi_crystal") is not None:
            return self.state.metadata["multi_crystal"]
        
        # Check command history for joint=false
        for cmd in self.state.command_history:
            if "joint=false" in cmd.command.lower():
                return True
        
        # Check metrics for multiple lattices
        for cmd in self.state.command_history:
            if cmd.metrics.get("num_lattices", 1) > 1:
                return True
            if cmd.metrics.get("num_sequences", 1) > 1:
                return True
        
        return False
    
    def set_multi_crystal(self, is_multi: bool):
        """Set whether this is a multi-crystal dataset."""
        self.state.metadata["multi_crystal"] = is_multi
    
    def get_next_step_suggestion(self) -> dict[str, Any]:
        """
        Get detailed suggestion for the next workflow step.
        
        Based on the tutorial workflow, provides context-aware suggestions
        including the command, explanation, tips, and optional commands.
        
        Returns:
            Dictionary with next_command, explanation, tip, and optional_commands
        """
        # Map workflow stages to suggestion keys
        stage_to_key = {
            WorkflowStage.NOT_STARTED: None,
            WorkflowStage.IMPORTED: "import",
            WorkflowStage.SPOTS_FOUND: "find_spots",
            WorkflowStage.INDEXED: "index",
            WorkflowStage.REFINED: "refine",
            WorkflowStage.INTEGRATED: "integrate",
            WorkflowStage.SYMMETRY_DETERMINED: "symmetry",
            WorkflowStage.SCALED: "scale",
            WorkflowStage.EXPORTED: "export",
        }
        
        key = stage_to_key.get(self.state.current_stage)
        
        if key is None:
            # Not started - need to import first
            return {
                "next_command": "dials.import /path/to/images/*.cbf",
                "explanation": "First, we need to import your diffraction images. This reads the image headers and creates an experiment file.",
                "tip": "Replace /path/to/images/*.cbf with the actual path to your data files. For NeXus files use *.nxs",
                "optional_commands": []
            }
        
        suggestion = WORKFLOW_SUGGESTIONS.get(key, {})
        is_multi = self.is_multi_crystal()
        
        # Get the appropriate command based on multi-crystal status
        if is_multi and "next_command_multi" in suggestion:
            next_cmd = suggestion["next_command_multi"]
            explanation = suggestion.get("explanation_multi", suggestion.get("explanation", ""))
        else:
            next_cmd = suggestion.get("next_command")
            explanation = suggestion.get("explanation", "")
        
        # For scale step, also mention merge option
        if key == "scale":
            merge_cmd = suggestion.get("next_command_merge")
            if merge_cmd:
                explanation += f"\n\nAlternatively, use `{merge_cmd}` for a merged MTZ file."
        
        return {
            "next_command": next_cmd,
            "explanation": explanation,
            "tip": suggestion.get("tip", ""),
            "optional_commands": suggestion.get("optional_commands", []),
            "is_multi_crystal": is_multi,
            "current_stage": self.get_stage_name(),
            "progress": f"{self.get_progress_percentage():.0f}%"
        }
    
    def get_next_step_message(self) -> str:
        """
        Get a formatted message suggesting the next step.
        
        Returns:
            Human-readable message with next step suggestion
        """
        suggestion = self.get_next_step_suggestion()
        
        if suggestion["next_command"] is None:
            return (
                "🎉 **Workflow Complete!**\n\n"
                f"{suggestion['explanation']}\n\n"
                f"💡 Tip: {suggestion['tip']}"
            )
        
        lines = [
            f"**Next Step: {suggestion['current_stage']} → Next**",
            f"Progress: {suggestion['progress']}",
            "",
            f"**Suggested command:**",
            f"```",
            f"{suggestion['next_command']}",
            f"```",
            "",
            f"{suggestion['explanation']}",
        ]
        
        if suggestion.get("tip"):
            lines.extend(["", f"💡 **Tip:** {suggestion['tip']}"])
        
        # Add optional commands if available
        optional_cmds = suggestion.get("optional_commands", [])
        if optional_cmds:
            lines.extend(["", "**Optional commands:**"])
            for cmd in optional_cmds:
                lines.append(f"  • `{cmd}`")
        
        if suggestion.get("is_multi_crystal"):
            lines.extend(["", "📊 *Multi-crystal mode detected*"])
        
        return "\n".join(lines)
    
    def get_status_summary(self) -> str:
        """Get a summary of the current workflow status."""
        lines = [
            f"Working directory: {self.working_directory}",
            f"Current stage: {self.get_stage_name()}",
            f"Progress: {self.get_progress_percentage():.0f}%",
        ]
        
        # Add file counts
        exp_count = len(self.state.files.get("experiments", []))
        refl_count = len(self.state.files.get("reflections", []))
        if exp_count or refl_count:
            lines.append(f"Files: {exp_count} experiment(s), {refl_count} reflection file(s)")
        
        # Add multi-crystal indicator
        if self.is_multi_crystal():
            lines.append("Mode: Multi-crystal")
        
        # Add next step suggestion
        suggestion = self.get_next_step_suggestion()
        if suggestion["next_command"]:
            lines.append(f"Suggested next step: {suggestion['next_command']}")
        else:
            lines.append("Workflow complete!")
        
        return "\n".join(lines)
    
    def get_workflow_context(self) -> dict[str, Any]:
        """
        Get context information for the AI agent.
        
        Returns:
            Dictionary with workflow context
        """
        return {
            "working_directory": str(self.working_directory),
            "current_stage": self.state.current_stage.value,
            "stage_name": self.get_stage_name(),
            "progress_percentage": self.get_progress_percentage(),
            "is_complete": self.is_complete(),
            "experiment_files": self.get_experiment_files(),
            "reflection_files": self.get_reflection_files(),
            "mtz_files": self.state.files.get("mtz", []),
            "suggested_next_command": self.get_next_command(),
            "command_history_count": len(self.state.command_history),
            "last_command": self.state.command_history[-1].command if self.state.command_history else None,
        }
    
    def save_state(self, filepath: Optional[str] = None):
        """
        Save workflow state to a JSON file.
        
        Args:
            filepath: Path to save file (default: .dials_workflow.json)
        """
        filepath = filepath or str(self.working_directory / ".dials_workflow.json")
        
        state_dict = {
            "working_directory": self.state.working_directory,
            "current_stage": self.state.current_stage.value,
            "files": self.state.files,
            "command_history": [
                {
                    "command": h.command,
                    "timestamp": h.timestamp,
                    "success": h.success,
                    "duration": h.duration,
                    "output_files": h.output_files,
                    "metrics": h.metrics
                }
                for h in self.state.command_history
            ],
            "metadata": self.state.metadata,
            "created_at": self.state.created_at,
            "updated_at": self.state.updated_at
        }
        
        with open(filepath, 'w') as f:
            json.dump(state_dict, f, indent=2)
        
        logger.info(f"Saved workflow state to {filepath}")
    
    def load_state(self, filepath: Optional[str] = None) -> bool:
        """
        Load workflow state from a JSON file.
        
        Args:
            filepath: Path to state file (default: .dials_workflow.json)
            
        Returns:
            True if state was loaded successfully
        """
        filepath = filepath or str(self.working_directory / ".dials_workflow.json")
        
        try:
            with open(filepath, 'r') as f:
                state_dict = json.load(f)
            
            self.state = WorkflowState(
                working_directory=state_dict["working_directory"],
                current_stage=WorkflowStage(state_dict["current_stage"]),
                files=state_dict["files"],
                command_history=[
                    CommandHistory(**h) for h in state_dict.get("command_history", [])
                ],
                metadata=state_dict.get("metadata", {}),
                created_at=state_dict.get("created_at", datetime.now().isoformat()),
                updated_at=state_dict.get("updated_at", datetime.now().isoformat())
            )
            
            # Refresh to pick up any new files
            self.refresh()
            
            logger.info(f"Loaded workflow state from {filepath}")
            return True
            
        except FileNotFoundError:
            logger.debug(f"No state file found at {filepath}")
            return False
        except Exception as e:
            logger.error(f"Error loading state: {e}")
            return False


def create_workflow_manager(working_directory: str = ".") -> WorkflowManager:
    """
    Create a new workflow manager instance.
    
    Args:
        working_directory: Directory containing DIALS files
        
    Returns:
        Configured WorkflowManager instance
    """
    return WorkflowManager(working_directory=working_directory)
