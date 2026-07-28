"""
Skill registry for the DIALS AI Agent.

Each skill is a self-contained unit of domain knowledge (a system-prompt
fragment), tool definitions, and handler logic. The registry loads all
skills and dispatches tool calls to whichever skill owns that tool.

Progressive disclosure: the system prompt does NOT contain every skill's
full guidance by default. get_composed_prompt() returns a compact index
(name + one-line description per skill) plus a `load_skill` tool the LLM
calls on demand — the same pattern Claude Code itself uses for its own
skills. A skill's full prompt fragment only enters the conversation (as a
load_skill tool result) on the turns that actually need it, which keeps
the cached static system prompt small regardless of how many skills are
registered. Use get_full_prompt() if you need the old always-everything
concatenation (e.g. for content-equivalence tests).
"""

from .base import BaseSkill, SkillContext

__all__ = ["BaseSkill", "SkillContext", "SkillRegistry", "create_default_registry"]

LOAD_SKILL_TOOL_NAME = "load_skill"


class SkillRegistry:
    """Registry that loads, composes, and dispatches to skills."""

    def __init__(self) -> None:
        self._skills: dict[str, BaseSkill] = {}
        self._tool_to_skill: dict[str, BaseSkill] = {}

    def register(self, skill: BaseSkill) -> None:
        """Register a skill. Raises if it claims a tool another skill already owns."""
        self._skills[skill.name] = skill
        for tool_name in skill.get_tool_names():
            if tool_name in self._tool_to_skill:
                raise ValueError(
                    f"Tool '{tool_name}' already registered by "
                    f"skill '{self._tool_to_skill[tool_name].name}'"
                )
            self._tool_to_skill[tool_name] = skill

    def get_composed_prompt(self) -> str:
        """
        Build the always-loaded skills section of the system prompt: a
        compact index of every registered skill's name and one-line
        description, plus instructions to call `load_skill` for detailed
        guidance. This is what keeps the cached static prompt small.
        """
        lines = [
            "## Available Skills",
            "",
            "Each skill below covers one area of DIALS processing in depth "
            "(detailed parameters, conventions, troubleshooting steps, etc). "
            "Only the name and one-line description are loaded here — call "
            "the `load_skill` tool with a skill's name before you need its "
            "full guidance for that turn. Loading is cheap and only needs to "
            "happen once per skill per session; its guidance then stays "
            "available for the rest of the conversation.",
            "",
        ]
        for skill in self._skills.values():
            lines.append(f"- **{skill.name}**: {skill.description}")
        return "\n".join(lines)

    def get_full_prompt(self) -> str:
        """Compose every skill's full prompt fragment into one block (no disclosure gating)."""
        fragments = [skill.get_prompt_fragment() for skill in self._skills.values()]
        return "\n\n".join(fragment for fragment in fragments if fragment)

    def get_all_tools(self) -> list[dict]:
        """Get all tool definitions from all registered skills, plus `load_skill`."""
        tools = []
        for skill in self._skills.values():
            tools.extend(skill.get_tools())
        tools.append(self._load_skill_tool_schema())
        return tools

    def _load_skill_tool_schema(self) -> dict:
        return {
            "name": LOAD_SKILL_TOOL_NAME,
            "description": (
                "Load the full guidance for one of the skills listed in the "
                "'Available Skills' index of your system prompt (detailed "
                "parameters, conventions, troubleshooting steps, etc). Call "
                "this before you need in-depth instructions for that area — "
                "only the skill's name and one-line description are in your "
                "context until you load it."
            ),
            "input_schema": {
                "type": "object",
                "properties": {
                    "skill_name": {
                        "type": "string",
                        "description": "Name of the skill to load, e.g. 'troubleshooting' or 'workspace'.",
                        "enum": sorted(self._skills.keys()),
                    }
                },
                "required": ["skill_name"],
            },
        }

    def _handle_load_skill(self, tool_input: dict) -> dict:
        skill_name = tool_input.get("skill_name", "")
        skill = self._skills.get(skill_name)
        if skill is None:
            return {
                "error": f"Unknown skill '{skill_name}'.",
                "available_skills": sorted(self._skills.keys()),
            }
        return {"skill": skill.name, "guidance": skill.get_prompt_fragment()}

    def handle_tool_call(self, tool_name: str, tool_input: dict, context: SkillContext) -> dict:
        """Dispatch a tool call to whichever skill owns it."""
        if tool_name == LOAD_SKILL_TOOL_NAME:
            return self._handle_load_skill(tool_input)
        skill = self._tool_to_skill.get(tool_name)
        if skill is None:
            return {"error": f"Unknown tool: {tool_name}"}
        return skill.handle_tool_call(tool_name, tool_input, context)

    def owns_tool(self, tool_name: str) -> bool:
        """Whether some registered skill (or the registry itself) handles this tool."""
        return tool_name == LOAD_SKILL_TOOL_NAME or tool_name in self._tool_to_skill

    def get_skill(self, name: str) -> BaseSkill | None:
        """Get a skill by name."""
        return self._skills.get(name)

    @property
    def skill_names(self) -> list[str]:
        return list(self._skills.keys())


def create_default_registry() -> SkillRegistry:
    """Create a registry with all default skills loaded, in prompt order."""
    from .data_import import DataImportSkill
    from .spot_finding import SpotFindingSkill
    from .indexing import IndexingSkill
    from .refinement import RefinementSkill
    from .integration import IntegrationSkill
    from .symmetry import SymmetrySkill
    from .scaling import ScalingSkill
    from .export import ExportSkill
    from .troubleshooting import TroubleshootingSkill
    from .workspace import WorkspaceSkill
    from .phil_params import PhilParamsSkill
    from .tutorials import TutorialsSkill

    registry = SkillRegistry()
    for skill_class in [
        DataImportSkill,
        SpotFindingSkill,
        IndexingSkill,
        RefinementSkill,
        IntegrationSkill,
        SymmetrySkill,
        ScalingSkill,
        ExportSkill,
        TroubleshootingSkill,
        WorkspaceSkill,
        PhilParamsSkill,
        TutorialsSkill,
    ]:
        registry.register(skill_class())
    return registry
