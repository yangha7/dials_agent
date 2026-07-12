"""
Skill registry for the DIALS AI Agent.

Each skill is a self-contained unit of domain knowledge (a system-prompt
fragment), tool definitions, and handler logic. The registry loads all
skills, composes their prompt fragments into one system prompt, and
dispatches tool calls to whichever skill owns that tool.

Loading every skill (the default, via create_default_registry()) produces
identical behavior to the old monolithic agent — skills are a way of
organizing that same knowledge, not a change in what the agent knows.
"""

from .base import BaseSkill, SkillContext

__all__ = ["BaseSkill", "SkillContext", "SkillRegistry", "create_default_registry"]


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
        """Compose all skill prompt fragments into one system-prompt block."""
        fragments = [skill.get_prompt_fragment() for skill in self._skills.values()]
        return "\n\n".join(fragment for fragment in fragments if fragment)

    def get_all_tools(self) -> list[dict]:
        """Get all tool definitions from all registered skills."""
        tools = []
        for skill in self._skills.values():
            tools.extend(skill.get_tools())
        return tools

    def handle_tool_call(self, tool_name: str, tool_input: dict, context: SkillContext) -> dict:
        """Dispatch a tool call to whichever skill owns it."""
        skill = self._tool_to_skill.get(tool_name)
        if skill is None:
            return {"error": f"Unknown tool: {tool_name}"}
        return skill.handle_tool_call(tool_name, tool_input, context)

    def owns_tool(self, tool_name: str) -> bool:
        """Whether some registered skill handles this tool (vs. a host/base tool)."""
        return tool_name in self._tool_to_skill

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
