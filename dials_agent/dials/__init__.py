"""
DIALS integration module for the AI Agent.

This module provides components for executing DIALS commands,
parsing output, and managing workflow state.
"""

from .commands import (
    CommandCategory,
    CommandDefinition,
    CommandParameter,
    DIALS_COMMANDS,
    get_command,
    get_commands_by_category,
    get_next_workflow_command,
    get_workflow_commands,
    validate_command,
)
from .executor import (
    CommandExecutor,
    CommandResult,
    create_executor,
    is_gui_command,
    GUI_COMMANDS,
)
from .parser import (
    OutputParser,
    ParsedMetrics,
    create_parser,
)
from .workflow import (
    WorkflowManager,
    WorkflowStage,
    WorkflowState,
    create_workflow_manager,
)

__all__ = [
    # Commands
    "CommandCategory",
    "CommandDefinition",
    "CommandParameter",
    "DIALS_COMMANDS",
    "get_command",
    "get_commands_by_category",
    "get_next_workflow_command",
    "get_workflow_commands",
    "validate_command",
    # Executor
    "CommandExecutor",
    "CommandResult",
    "create_executor",
    "is_gui_command",
    "GUI_COMMANDS",
    # Parser
    "OutputParser",
    "ParsedMetrics",
    "create_parser",
    # Workflow
    "WorkflowManager",
    "WorkflowStage",
    "WorkflowState",
    "create_workflow_manager",
]
