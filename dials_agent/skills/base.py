"""
Base class and shared context for DIALS agent skills.

A "skill" bundles everything the agent needs to know and do for one
area of DIALS processing: the system-prompt fragment that teaches the
LLM about it, the tool schemas it exposes (if any), and the handler
logic that executes those tools.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


def load_skill_md(path: "str | Path") -> tuple[str, str]:
    """
    Parse a SKILL.md file into (description, body).

    Frontmatter here is intentionally a minimal flat `key: value` format
    (not full YAML) between `---` markers, since a skill only needs a
    name and one-line description — this avoids adding a yaml dependency
    for two fields. `name` in the frontmatter is documentation only; the
    skill class remains the source of truth for its own `name` property.
    """
    text = Path(path).read_text()
    _, frontmatter_text, body = text.split("---", 2)
    frontmatter = {}
    for line in frontmatter_text.strip().splitlines():
        key, _, value = line.partition(":")
        frontmatter[key.strip()] = value.strip()
    return frontmatter["description"], body.strip()


@dataclass
class SkillContext:
    """
    Read-mostly context passed to every skill handler call.

    Handlers should treat this as input, not as a place to stash new
    state — callers that need to react to a handler's effects (e.g. the
    CLI switching directories) read that back out of the handler's
    *return value*, not by mutating this object. That keeps handlers
    callable the same way from the CLI or from an MCP server.
    """
    working_directory: str = "."
    data_directory: str = ""
    existing_files: list[str] = field(default_factory=list)
    executor: Any = None       # CommandExecutor instance
    parser: Any = None         # OutputParser instance
    workflow: Any = None       # WorkflowManager instance
    command_timings: list[dict] = field(default_factory=list)
    session_usage: Any = None  # TokenUsage instance (cumulative session totals)
    token_budget: int = 0      # 0 = no limit


class BaseSkill(ABC):
    """Base class for all DIALS agent skills."""

    @property
    @abstractmethod
    def name(self) -> str:
        """Unique skill identifier (e.g. 'spot_finding')."""
        ...

    @property
    @abstractmethod
    def description(self) -> str:
        """Human-readable description of what this skill provides."""
        ...

    @abstractmethod
    def get_prompt_fragment(self) -> str:
        """
        Return the system-prompt fragment for this skill.

        This is the portion of the system prompt that teaches the LLM
        about this skill's domain. It is composed with other skills'
        fragments (and the shared base prompt) to form the complete
        system prompt.
        """
        ...

    def get_tools(self) -> list[dict]:
        """
        Return the tool definitions (JSON schemas) for this skill.

        Most workflow skills contribute a prompt fragment only and use
        tools owned by another skill (or the CLI's shared/base tools),
        so the default is "no tools".
        """
        return []

    def handle_tool_call(
        self,
        tool_name: str,
        tool_input: dict,
        context: SkillContext,
    ) -> dict:
        """
        Handle a tool call for this skill.

        Args:
            tool_name: Name of the tool being called
            tool_input: Input parameters from the LLM
            context: Shared, read-only context (working directory, executor, ...)

        Returns:
            A plain, JSON-serializable result dict to send back to the LLM.
            Keys starting with an underscore (e.g. "_new_working_directory")
            are host-only metadata: the CLI (or other host) may read them to
            update its own state, but must strip them before the result is
            forwarded to the LLM.

        Raises:
            KeyError: If tool_name is not handled by this skill.
        """
        raise KeyError(f"{self.name} skill does not handle tool '{tool_name}'")

    def get_tool_names(self) -> list[str]:
        """Return the list of tool names this skill handles."""
        return [t["name"] for t in self.get_tools()]
