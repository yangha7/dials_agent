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
    {
        "name": "select_dataset",
        "description": (
            "Find a dataset by name/keyword among the subdirectories of the configured data "
            "directory, and switch to it automatically if there's exactly one match. Use this "
            "FIRST whenever the user refers to a dataset by name (e.g. 'process the insulin "
            "data', 'switch to lysozyme') rather than by an exact path -- do NOT reach for "
            "run_shell_command/find to search for it yourself; this tool does a direct, "
            "reliable filesystem check (not a shell search that can be affected by directory "
            "caching) and is the tested way to do this. Omit name_hint to just list every "
            "dataset subdirectory found, e.g. when the user asks what data is available."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "name_hint": {
                    "type": "string",
                    "description": "A dataset name or keyword the user mentioned (e.g. 'insulin'), matched case-insensitively as a substring against subdirectory names. Omit to just list all datasets found."
                }
            },
            "required": []
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
        if tool_name == "change_data_directory":
            return self._handle_change_data_directory(tool_input, context)
        if tool_name == "select_dataset":
            return self._handle_select_dataset(tool_input, context)
        raise KeyError(f"data_import skill does not handle tool '{tool_name}'")

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

    def _handle_select_dataset(self, tool_input: dict, context: SkillContext) -> dict:
        from ...core.tools import discover_data_files, discover_dataset_subdirectories

        name_hint = tool_input.get("name_hint", "").strip()
        data_dir = context.data_directory
        if not data_dir:
            return {"error": "No data directory is currently configured."}

        candidates = discover_dataset_subdirectories(data_dir)
        if not candidates:
            return {
                "status": "none_found",
                "data_directory": data_dir,
                "message": (
                    f"No dataset subdirectories with recognized diffraction data files were "
                    f"found under {data_dir}. If you're sure the data is there, it may be "
                    f"nested deeper than 2 levels, or use an unrecognized file extension."
                ),
            }

        names = [d.name for d in candidates]
        if not name_hint:
            return {
                "status": "listed",
                "data_directory": data_dir,
                "datasets": names,
                "message": f"Found {len(names)} dataset(s) under {data_dir}: {', '.join(names)}.",
            }

        matches = [d for d in candidates if name_hint.lower() in d.name.lower()]
        if len(matches) == 1:
            chosen = matches[0]
            data_files = discover_data_files(context.working_directory, data_directory=str(chosen))
            return {
                "status": "selected",
                "data_directory": str(chosen),
                "data_files_found": len(data_files),
                "message": (
                    f"Found and switched to dataset '{chosen.name}' at {chosen} "
                    f"({len(data_files)} data file(s))."
                ),
                "_cli_print": [f"[green]📂 Data directory changed to: {chosen}[/green]"],
            }
        if len(matches) > 1:
            return {
                "status": "ambiguous",
                "data_directory": data_dir,
                "datasets": [d.name for d in matches],
                "message": f"Multiple datasets match '{name_hint}': {', '.join(d.name for d in matches)}. Which one did you mean?",
            }
        return {
            "status": "no_match",
            "data_directory": data_dir,
            "datasets": names,
            "message": f"No dataset matching '{name_hint}' found under {data_dir}. Available datasets: {', '.join(names)}.",
        }
