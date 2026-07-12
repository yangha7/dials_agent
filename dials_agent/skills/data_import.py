"""Data import skill: bringing raw diffraction images into DIALS format."""

from pathlib import Path

from .base import BaseSkill, SkillContext

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
        return "Importing raw diffraction images into DIALS format (dials.import)"

    def get_prompt_fragment(self) -> str:
        return """### dials.import
- Formats: CBF, HDF5/NeXus (.nxs, .h5), SMV, TIFF
- Tip: for large datasets, offer `image_range=1,1200` to process a subset first
- Use `lookup_phil_params` for full parameter list

### Import Step Options
When the user wants to import data (e.g., "analyze the insulin data", "work up my data"):

**CRITICAL**: Always use the actual data file paths from the "Available diffraction data files" section in the Current Context below. NEVER use hardcoded example paths like `../ins10_1.nxs` - these are just examples and will not work for the user's actual data.

Present these options in your response (using the ACTUAL file path from the context):
1. **Full dataset**: `dials.import <actual_file_path>` - processes all images (recommended for final processing)
2. **Quick test with subset**: `dials.import <actual_file_path> image_range=1,1200` - processes first 1200 images (faster, good for learning/testing)

Example response format (replace `<data_file>` with the actual path from context):
```
I can help you process your data! I found the following data file: <data_file>

Would you like to:

**Option 1 - Full dataset:**
`dials.import <data_file>`
This processes all images. Best for final data processing.

**Option 2 - Quick test (recommended for learning):**
`dials.import <data_file> image_range=1,1200`
This processes only the first 1200 images, which is much faster and good for testing the workflow.

Which option would you prefer?
```

**If no data files are found in the context**, do NOT abort or give up. Instead:
1. Ask the user where their data is located
2. When the user provides a path, **immediately use the `change_data_directory` tool** to switch to it
3. After switching, confirm the data was found and proceed with the import

**CRITICAL**: When the user tells you a data path (e.g., "my data is in /path/to/data"), you MUST:
1. Use `change_data_directory` with that path — do NOT just run `ls` on it
2. After switching, the data files will appear in your context automatically
3. Then proceed to suggest the import command

Example: "I don't see any diffraction data files in the current data directory. Where is your data located? I can switch to the correct directory for you."

Wait for the user to choose before using the suggest_dials_command tool.

### After Import (Visualization)
Ask: "Would you like to inspect the diffraction images before proceeding to spot finding?"
- **Yes**: Suggest `dials.image_viewer imported.expt` - allows checking beam center, detector distance, image quality
- **No**: Proceed to spot finding"""

    def get_tools(self) -> list[dict]:
        return TOOLS

    def handle_tool_call(self, tool_name: str, tool_input: dict, context: SkillContext) -> dict:
        if tool_name != "change_data_directory":
            raise KeyError(f"data_import skill does not handle tool '{tool_name}'")
        return self._handle_change_data_directory(tool_input, context)

    def _handle_change_data_directory(self, tool_input: dict, context: SkillContext) -> dict:
        from ..core.tools import discover_data_files

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
