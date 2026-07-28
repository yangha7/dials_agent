"""Data import skill: bringing raw diffraction images into DIALS format."""

from pathlib import Path

from ..base import BaseSkill, SkillContext, load_skill_md

_DESCRIPTION, _PROMPT_FRAGMENT = load_skill_md(Path(__file__).parent / "SKILL.md")

TOOLS: list[dict] = [
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
]


class DataImportSkill(BaseSkill):

    @property
    def name(self) -> str:
        return "data_import"

    @property
    def description(self) -> str:
        return _DESCRIPTION

    def get_prompt_fragment(self) -> str:
        return _PROMPT_FRAGMENT

    def get_tools(self) -> list[dict]:
        return TOOLS

    def handle_tool_call(self, tool_name: str, tool_input: dict, context: SkillContext) -> dict:
        if tool_name != "change_data_directory":
            raise KeyError(f"data_import skill does not handle tool '{tool_name}'")
        return self._handle_change_data_directory(tool_input, context)

    def _handle_change_data_directory(self, tool_input: dict, context: SkillContext) -> dict:
        from ...core.tools import discover_data_files

        dir_path = tool_input.get("path", "")
        if not dir_path:
            return {"error": "No path provided"}

        data_path = Path(dir_path).resolve()

        if not data_path.exists():
            return {"error": f"Data directory does not exist: {data_path}"}

        if not data_path.is_dir():
            return {"error": f"Not a directory: {data_path}"}

        data_files = discover_data_files(context.working_directory, data_directory=str(data_path))

        file_summary = list(data_files[:10])
        if len(data_files) > 10:
            file_summary.append(f"... and {len(data_files) - 10} more")

        return {
            "status": "success",
            "data_directory": str(data_path),
            "data_files_found": len(data_files),
            "sample_files": file_summary,
            "message": f"Data directory changed to {data_path}. Found {len(data_files)} data file(s).",
            "_cli_print": [f"[green]📂 Data directory changed to: {data_path}[/green]"],
        }
