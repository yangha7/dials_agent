"""
Workspace skill: file access, shell commands, directory management,
calculations, and command timing.

These tools are CLI-agnostic — they touch the filesystem and subprocesses
directly, but none of them print to a console or block on a confirmation
prompt. Where user confirmation is required (destructive shell commands),
the handler returns a `status: "requires_confirmation"` result instead of
acting immediately; the host (the CLI today, an MCP client's own consent
mechanism in the future) decides how to ask and re-calls with
`_confirmed=True` once approved. See `run_shell_command` below.

Anything a handler wants the CLI to print (and only the CLI — it's display
metadata, not information for the LLM) goes in the `_cli_print` key of the
result, as a list of rich-markup strings. The CLI pops and prints these,
then strips them before forwarding the result to the LLM.
"""

import math as _math
import subprocess as sp
from pathlib import Path
from typing import Any

from .base import BaseSkill, SkillContext

TOOLS: list[dict] = [
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
    },
    {
        "name": "read_file",
        "description": "Read the contents of a file in the working directory. Use this to read log files (e.g., dials.find_spots.log, dials.index.log), output files, or any text file the user asks about. This allows you to directly analyze log output without asking the user to paste it.",
        "input_schema": {
            "type": "object",
            "properties": {
                "filename": {
                    "type": "string",
                    "description": "The filename to read (relative to working directory), e.g., 'dials.index.log', 'dials.scale.log'"
                },
                "tail_lines": {
                    "type": "integer",
                    "description": "If set, only return the last N lines of the file (useful for large log files). Default: return entire file up to max size."
                },
                "max_chars": {
                    "type": "integer",
                    "description": "Maximum number of characters to return (default: 50000). Large files will be truncated from the beginning."
                }
            },
            "required": ["filename"]
        }
    },
    {
        "name": "open_file",
        "description": "Open a file in the appropriate viewer. For HTML files (e.g., dials.scale.html, dials.report.html), opens in a web browser. For .expt/.refl files, suggests the appropriate DIALS viewer. Use this when the user wants to view HTML reports or other output files.",
        "input_schema": {
            "type": "object",
            "properties": {
                "filename": {
                    "type": "string",
                    "description": "The filename to open (relative to working directory)"
                }
            },
            "required": ["filename"]
        }
    },
    {
        "name": "change_working_directory",
        "description": "Change the current working directory. Use this when the user asks to 'switch to', 'go to', or 'move to' a directory. By default, this does NOT create new directories — it only switches to existing ones. Set create=true ONLY when the user explicitly asks to 'create', 'make', or 'new' a directory. If the directory is not found, the tool will search the current and parent directories for close matches (handles typos and case sensitivity).",
        "input_schema": {
            "type": "object",
            "properties": {
                "path": {
                    "type": "string",
                    "description": "The directory path to switch to. Can be absolute (/path/to/dir) or relative (subdir, ../sibling)."
                },
                "create": {
                    "type": "boolean",
                    "description": "If true, create the directory if it doesn't exist. Default: false. Only set to true when user explicitly says 'create', 'make', or 'new'."
                }
            },
            "required": ["path"]
        }
    },
    {
        "name": "calculate",
        "description": "Perform a mathematical calculation. Use this for ANY arithmetic: counting, subtraction, division, percentages, ranges, etc. Do NOT do mental math — always use this tool for numerical calculations to avoid errors.",
        "input_schema": {
            "type": "object",
            "properties": {
                "expression": {
                    "type": "string",
                    "description": "A Python math expression to evaluate (e.g., '1200 * 0.1', '67.85 - 67.82', '107640 / 1200', '100 * 12', '(3600 - 1200) / 100')"
                },
                "description": {
                    "type": "string",
                    "description": "Brief description of what this calculation represents"
                }
            },
            "required": ["expression"]
        }
    },
    {
        "name": "get_timing_report",
        "description": "Get the timing report showing how long each DIALS command took. The agent automatically records start time, end time, and duration for every command. Use this when the user asks about timing, performance, or how long steps took. The data is also saved to dials_agent_timing.log in the working directory.",
        "input_schema": {
            "type": "object",
            "properties": {},
            "required": []
        }
    },
    {
        "name": "get_token_usage",
        "description": "Get the LLM token usage for the current session (input/output/cached tokens, and remaining budget if one is configured). Use this when the user asks about token usage, API cost, or how much budget is left.",
        "input_schema": {
            "type": "object",
            "properties": {},
            "required": []
        }
    },
    {
        "name": "run_shell_command",
        "description": "Run a shell command in the working directory. Use this for non-DIALS commands like ls, rm, mv, cp, cat, head, tail, wc, grep, find, etc. For destructive commands (rm, mv), the user will be asked to confirm before execution. Use this instead of telling the user to run commands manually.",
        "input_schema": {
            "type": "object",
            "properties": {
                "command": {
                    "type": "string",
                    "description": "The shell command to execute (e.g., 'ls -la', 'rm *.expt *.refl', 'cat dials.index.log | tail -20')"
                },
                "explanation": {
                    "type": "string",
                    "description": "Brief explanation of what this command does"
                }
            },
            "required": ["command", "explanation"]
        }
    },
    {
        "name": "create_markdown_file",
        "description": "Write markdown content to a .md file in the working directory. Use this to save notes, summaries, processing reports, or any structured text the user wants to keep. The filename must end in .md. Content should be valid markdown.",
        "input_schema": {
            "type": "object",
            "properties": {
                "filename": {
                    "type": "string",
                    "description": "The filename to write (must end in .md, relative to working directory, e.g. 'processing_notes.md', 'session_report.md')"
                },
                "content": {
                    "type": "string",
                    "description": "The markdown content to write to the file"
                },
                "overwrite": {
                    "type": "boolean",
                    "description": "If true, overwrite existing file. If false and file exists, return an error. Default: true."
                }
            },
            "required": ["filename", "content"]
        }
    },
    {
        "name": "create_html_file",
        "description": "Write HTML content to a .html file in the working directory. Use this to save self-contained HTML reports, dashboards, or visualizations the user wants to keep. The filename must end in .html.",
        "input_schema": {
            "type": "object",
            "properties": {
                "filename": {
                    "type": "string",
                    "description": "The filename to write (must end in .html, relative to working directory, e.g. 'report.html', 'processing_summary.html')"
                },
                "content": {
                    "type": "string",
                    "description": "The HTML content to write to the file"
                },
                "overwrite": {
                    "type": "boolean",
                    "description": "If true, overwrite existing file. If false and file exists, return an error. Default: true."
                }
            },
            "required": ["filename", "content"]
        }
    },
]

DESTRUCTIVE_KEYWORDS = ["rm ", "rm\t", "rmdir", "mv ", "mv\t", "> ", ">> "]


def _is_destructive(command: str) -> bool:
    return any(kw in command for kw in DESTRUCTIVE_KEYWORDS) or command.startswith("rm ")


def format_timing_report(working_directory: str, command_timings: list[dict]) -> str:
    """Get the timing report from the log file (persists across restarts) or in-memory data."""
    timing_file = Path(working_directory) / "dials_agent_timing.log"
    if timing_file.exists():
        return timing_file.read_text()

    if not command_timings:
        return "No commands have been executed yet."

    lines = []
    for entry in command_timings:
        duration = entry["duration"]
        if duration >= 60:
            minutes = int(duration // 60)
            seconds = duration % 60
            duration_str = f"{minutes}m {seconds:.1f}s"
        else:
            duration_str = f"{duration:.1f}s"
        status = "OK" if entry["success"] else "FAILED"
        lines.append(
            f"{entry.get('start_time', 'N/A')}  →  {entry.get('end_time', 'N/A')}  "
            f"[{duration_str:>10}]  {status:6}  {entry['command']}"
        )
    return "\n".join(lines)


class WorkspaceSkill(BaseSkill):

    @property
    def name(self) -> str:
        return "workspace"

    @property
    def description(self) -> str:
        return "File access, shell commands, directory management, calculations, and command timing"

    def get_prompt_fragment(self) -> str:
        return """## Shell Commands

You can run arbitrary shell commands in the working directory using the `run_shell_command` tool. Use this for:
- Listing files: `ls -la`, `ls *.expt`
- Removing files: `rm *.expt *.refl *.log` (user will be asked to confirm)
- Checking disk usage: `du -sh *`
- Viewing file contents: `cat`, `head`, `tail`, `grep`
- Any other standard Unix commands

**IMPORTANT**: Use `run_shell_command` instead of telling the user to run commands manually. The tool will execute the command directly in the working directory. For destructive commands (rm, mv), the user will be prompted to confirm.

**TIP**: When the user says "start over", "clean up", or "remove old files", you can use `run_shell_command` with `rm` to remove DIALS output files. The user can also type `reset` or `clean` in the CLI to use the built-in cleanup feature.

## File Access

You have direct access to files in the working directory:

### Reading Log Files
Use the `read_file` tool to read log files directly - do NOT ask the user to run `cat` and paste the output. Common log files:
- `dials.import.log` - import output
- `dials.find_spots.log` - spot finding output
- `dials.index.log` - indexing output
- `dials.refine.log` - refinement output
- `dials.integrate.log` - integration output
- `dials.symmetry.log` - symmetry analysis output
- `dials.scale.log` - scaling output and merging statistics
- `dials.export.log` or `dials.merge.log` - export/merge output

When the user asks about results, errors, or wants to review output, use `read_file` to read the relevant log file and analyze it directly.

### Opening HTML Reports
Use the `open_file` tool to open HTML reports in a web browser - do NOT ask the user to open them manually. Common HTML files:
- `dials.scale.html` - scaling report with detailed statistics and plots
- `dials.report.html` - general processing report (from `dials.report`)

When an HTML report is generated (e.g., after scaling), proactively offer to open it for the user.

## Workspace Management

**You CAN change the working directory** — use the `change_working_directory` tool. Do NOT tell users they need to restart or type CLI commands to change directories.

**CRITICAL DISTINCTION — Switch vs Create:**
- **"switch to", "go to", "move to", "work in"** → use `change_working_directory(path="xxx", create=false)` — do NOT create new directories
- **"create", "make", "new directory"** → use `change_working_directory(path="xxx", create=true)` — creates the directory

When switching, the tool will search the current directory AND parent directory for matches, handling typos and case sensitivity. Sibling directories (in the parent) are commonly the target when users say "switch to xxx".

Examples:
- "Switch to the round2 folder" → `change_working_directory(path="../round2")` or `change_working_directory(path="round2")` — do NOT create
- "Go to the yang directory" → `change_working_directory(path="../yang")` — do NOT create
- "Create a directory called student1" → `change_working_directory(path="student1", create=true)` — creates it
- "Make a new folder for round 2" → `change_working_directory(path="round2", create=true)` — creates it
- "Go back to the main directory" → Tell user to type `cd` (returns to base directory)

This does NOT modify the .env file — the default starting directory is preserved for the next session.

The user can also use these CLI commands directly:
- `mkdir <name>` — Create a subdirectory and switch to it
- `cd <path>` — Change directory (relative or absolute)
- `cd` — Return to the base (starting) directory
- `pwd` / `workspace` — Show current and base directory

You can also use `change_data_directory` to switch the raw data directory when the user says their data is in a different location.

You can also use `run_shell_command` to rename directories (`mv old_name new_name`).

## Command Timing

The agent automatically records the execution time for every DIALS command, including start time, end time, and duration. This data is saved to `dials_agent_timing.log` in the working directory and persists across agent restarts.

When the user asks about timing, performance, or "how long did each step take?", use the `get_timing_report` tool to retrieve the timing data. Do NOT try to figure out timing from file timestamps or log files — use the tool.

## Token Usage

When the user asks about token usage, API cost, or how much of their budget remains, use the `get_token_usage` tool. It reports the cumulative session totals (input/output/cached tokens) and, if a budget is configured, how much remains. Do NOT guess at this from anything in the conversation — the per-turn usage line the CLI prints after each response is not visible to you, so this tool is the only way to answer these questions accurately.

## Calculations and Counting

**IMPORTANT**: Do NOT do mental arithmetic or visual counting. LLMs are unreliable at math and counting.

### For arithmetic (subtraction, division, percentages):
Use the `calculate` tool:
- Oscillation range: `calculate(expression="1200 * 0.1")`
- Percentage indexed: `calculate(expression="100 * 66997 / 107640")`
- Unit cell difference: `calculate(expression="67.85 - 67.82")`
- Spots per image: `calculate(expression="107640 / 1200")`

### For counting items (files, lines, datasets):
Use `run_shell_command` with shell counting tools — do NOT try to count visually:
- Count files: `run_shell_command(command="ls *.cbf.gz | wc -l")`
- Count datasets in output: `run_shell_command(command="grep -c 'template:' dials.import.log")`
- Count lines: `run_shell_command(command="wc -l < dials_agent_timing.log")`
- Count sweeps: `run_shell_command(command="grep -c 'sweep' dials.import.log")`

## Verify Before Reporting Outliers

**CRITICAL**: Before reporting any surprising or outlier results (e.g., "one dataset has a very different number of images", "the resolution is unusually high/low", "the scan range is different"), ALWAYS:
1. Double-check the numbers using the `calculate` tool or by re-reading the relevant log/output
2. Verify you are reading the data correctly (e.g., not confusing two columns, not misreading units)
3. If the outlier involves arithmetic (e.g., "dataset X has 50 fewer images"), use `calculate` to confirm
4. Only report the finding after verification

This prevents false alarms from LLM arithmetic errors or misread data."""

    def get_tools(self) -> list[dict]:
        return TOOLS

    def handle_tool_call(self, tool_name: str, tool_input: dict, context: SkillContext) -> dict:
        handler = getattr(self, f"_handle_{tool_name}", None)
        if handler is None:
            raise KeyError(f"workspace skill does not handle tool '{tool_name}'")
        return handler(tool_input, context)

    # ------------------------------------------------------------------
    # Handlers
    # ------------------------------------------------------------------

    def _handle_check_workflow_status(self, tool_input: dict, context: SkillContext) -> dict:
        context.workflow.refresh()
        return context.workflow.get_workflow_context()

    def _handle_list_available_commands(self, tool_input: dict, context: SkillContext) -> dict:
        from ..dials.commands import get_commands_by_category, CommandCategory

        category = tool_input.get("category", "all")
        if category == "all":
            commands = {}
            for cat in CommandCategory:
                commands.update(get_commands_by_category(cat))
        else:
            try:
                cat = CommandCategory(category)
                commands = get_commands_by_category(cat)
            except ValueError:
                commands = {}

        return {
            "commands": commands,
            "current_stage": context.workflow.get_stage_name(),
        }

    def _handle_read_file(self, tool_input: dict, context: SkillContext) -> dict:
        filename = tool_input.get("filename", "")
        tail_lines = tool_input.get("tail_lines")
        max_chars = tool_input.get("max_chars", 50000)

        working_directory = Path(context.working_directory)
        filepath = working_directory / filename
        if not filepath.exists():
            return {
                "error": f"File not found: {filename}",
                "available_files": [
                    f.name for f in working_directory.iterdir()
                    if f.is_file() and (f.suffix in {'.log', '.html', '.txt', '.json', '.expt'})
                ]
            }

        try:
            content = filepath.read_text(errors='replace')

            if tail_lines:
                lines = content.splitlines()
                content = "\n".join(lines[-tail_lines:])

            if len(content) > max_chars:
                content = f"[... truncated {len(content) - max_chars} chars from beginning ...]\n" + content[-max_chars:]

            return {
                "filename": filename,
                "content": content,
                "size_bytes": filepath.stat().st_size,
                "_cli_print": [f"[dim]📄 Reading {filename} ({len(content)} chars)[/dim]"],
            }
        except Exception as e:
            return {"error": f"Error reading {filename}: {str(e)}"}

    def _handle_open_file(self, tool_input: dict, context: SkillContext) -> dict:
        filename = tool_input.get("filename", "")
        filepath = Path(context.working_directory) / filename

        if not filepath.exists():
            return {"error": f"File not found: {filename}"}

        suffix = filepath.suffix.lower()

        if suffix == ".html":
            try:
                for browser_cmd in ["firefox", "xdg-open", "open"]:
                    try:
                        sp.Popen(
                            [browser_cmd, str(filepath)],
                            stdout=sp.DEVNULL,
                            stderr=sp.DEVNULL,
                            start_new_session=True
                        )
                        return {
                            "status": "opened",
                            "filename": filename,
                            "viewer": browser_cmd,
                            "_cli_print": [f"[green]🌐 Opened {filename} in browser[/green]"],
                        }
                    except FileNotFoundError:
                        continue

                return {"error": f"No web browser found to open {filename}. Try: firefox {filepath}"}
            except Exception as e:
                return {"error": f"Error opening {filename}: {str(e)}"}

        elif suffix in {".expt", ".refl"}:
            return {
                "status": "suggestion",
                "message": f"Use dials.image_viewer or dials.reciprocal_lattice_viewer to view {filename}",
                "suggested_commands": [
                    f"dials.image_viewer {filename}",
                    f"dials.reciprocal_lattice_viewer {filename}"
                ]
            }

        else:
            return {"error": f"Unsupported file type: {suffix}. Use read_file for text files."}

    def _handle_change_working_directory(self, tool_input: dict, context: SkillContext) -> dict:
        from ..dials.workflow import create_workflow_manager

        dir_path = tool_input.get("path", "")
        create = tool_input.get("create", False)  # Default: do NOT create

        if not dir_path:
            return {"error": "No path provided"}

        working_directory = Path(context.working_directory)

        if not Path(dir_path).is_absolute():
            new_path = (working_directory / dir_path).resolve()
        else:
            new_path = Path(dir_path).resolve()

        cli_print: list[str] = []

        if not new_path.exists():
            dir_name = new_path.name
            search_dirs = [working_directory, working_directory.parent]
            matches = []

            for search_dir in search_dirs:
                if not search_dir.exists():
                    continue
                for d in search_dir.iterdir():
                    if d.is_dir() and d.name.lower() == dir_name.lower():
                        matches.append(d)
                    elif d.is_dir() and (
                        dir_name.lower() in d.name.lower() or
                        d.name.lower() in dir_name.lower()
                    ):
                        matches.append(d)

            if len(matches) == 1:
                new_path = matches[0]
                cli_print.append(f"[yellow]📁 Found matching directory: {new_path.name}[/yellow]")
            elif len(matches) > 1:
                match_names = [str(m) for m in matches]
                return {
                    "error": f"Directory '{dir_name}' not found. Did you mean one of these?",
                    "suggestions": match_names
                }
            elif create:
                new_path.mkdir(parents=True, exist_ok=True)
                cli_print.append(f"[green]📁 Created directory: {new_path}[/green]")
            else:
                parent_path = (working_directory.parent / dir_name).resolve()
                if parent_path.exists() and parent_path.is_dir():
                    new_path = parent_path
                    cli_print.append(f"[yellow]📁 Found in parent directory: {new_path}[/yellow]")
                else:
                    return {
                        "error": f"Directory not found: {new_path}. "
                                 f"To create it, ask the user to say 'create' or 'make' a directory."
                    }

        # Purely to report back existing_files for the new directory — the
        # host (CLI) is responsible for adopting this as its live workflow.
        new_workflow = create_workflow_manager(str(new_path))
        cli_print.append(f"[green]📁 Working directory changed to: {new_path}[/green]")

        return {
            "status": "success",
            "working_directory": str(new_path),
            "message": f"Working directory changed to {new_path}. All DIALS output will now be saved here.",
            "existing_files": new_workflow.get_available_files(),
            "_cli_print": cli_print,
        }

    def _handle_calculate(self, tool_input: dict, context: SkillContext) -> dict:
        expression = tool_input.get("expression", "")
        description = tool_input.get("description", "")

        if not expression:
            return {"error": "No expression provided"}

        try:
            allowed_names = {
                k: v for k, v in _math.__dict__.items()
                if not k.startswith('_')
            }
            allowed_names.update({
                "abs": abs, "round": round, "min": min, "max": max,
                "sum": sum, "len": len, "int": int, "float": float,
            })
            result = eval(expression, {"__builtins__": {}}, allowed_names)
            return {
                "expression": expression,
                "result": result,
                "description": description,
            }
        except Exception as e:
            return {"error": f"Calculation error: {str(e)}", "expression": expression}

    def _handle_get_timing_report(self, tool_input: dict, context: SkillContext) -> dict:
        report = format_timing_report(context.working_directory, context.command_timings)
        total_duration = sum(e["duration"] for e in context.command_timings)
        if total_duration >= 60:
            total_str = f"{int(total_duration // 60)}m {total_duration % 60:.1f}s"
        else:
            total_str = f"{total_duration:.1f}s"

        return {
            "timing_report": report,
            "total_commands": len(context.command_timings),
            "total_duration": total_str,
            "timing_file": str(Path(context.working_directory) / "dials_agent_timing.log"),
        }

    def _handle_get_token_usage(self, tool_input: dict, context: SkillContext) -> dict:
        usage = context.session_usage
        input_tokens = getattr(usage, "input_tokens", 0) or 0
        output_tokens = getattr(usage, "output_tokens", 0) or 0
        cache_read_tokens = getattr(usage, "cache_read_tokens", 0) or 0
        cache_creation_tokens = getattr(usage, "cache_creation_tokens", 0) or 0
        total_tokens = getattr(usage, "total", input_tokens + output_tokens)

        result = {
            "session_input_tokens": input_tokens,
            "session_output_tokens": output_tokens,
            "session_cache_read_tokens": cache_read_tokens,
            "session_cache_creation_tokens": cache_creation_tokens,
            "session_total_tokens": total_tokens,
            "token_budget": context.token_budget,
            "budget_remaining": None,
            "budget_remaining_pct": None,
        }

        if context.token_budget > 0:
            remaining = max(0, context.token_budget - total_tokens)
            result["budget_remaining"] = remaining
            result["budget_remaining_pct"] = round(100 * remaining / context.token_budget, 1)

        return result

    def _handle_run_shell_command(self, tool_input: dict, context: SkillContext) -> dict:
        command = tool_input.get("command", "")
        explanation = tool_input.get("explanation", "")
        confirmed = tool_input.get("_confirmed", False)

        if not command:
            return {"error": "No command provided"}

        if _is_destructive(command) and not confirmed:
            return {
                "status": "requires_confirmation",
                "command": command,
                "explanation": explanation,
                "message": f"Shell command (destructive): {command}",
            }

        cli_print = [] if _is_destructive(command) else [f"[dim]$ {command}[/dim]"]

        try:
            result = sp.run(
                command,
                shell=True,
                cwd=context.working_directory,
                capture_output=True,
                text=True,
                timeout=60
            )

            output = result.stdout
            if result.stderr:
                output += f"\n[stderr]: {result.stderr}"

            if len(output) > 10000:
                output = output[:5000] + "\n\n[... output truncated ...]\n\n" + output[-5000:]

            return {
                "status": "success" if result.returncode == 0 else "error",
                "return_code": result.returncode,
                "output": output,
                "command": command,
                "_cli_print": cli_print,
                "_files_may_have_changed": True,
            }
        except sp.TimeoutExpired:
            return {"error": f"Command timed out after 60 seconds: {command}"}
        except Exception as e:
            return {"error": f"Failed to run command: {str(e)}"}

    def _handle_create_markdown_file(self, tool_input: dict, context: SkillContext) -> dict:
        return self._write_text_file(tool_input, context, extension=".md", emoji="📝")

    def _handle_create_html_file(self, tool_input: dict, context: SkillContext) -> dict:
        return self._write_text_file(tool_input, context, extension=".html", emoji="🌐")

    @staticmethod
    def _write_text_file(tool_input: dict, context: SkillContext, extension: str, emoji: str) -> dict:
        filename = tool_input.get("filename", "")
        content = tool_input.get("content", "")
        overwrite = tool_input.get("overwrite", True)

        if not filename:
            return {"error": "No filename provided"}
        if not filename.endswith(extension):
            filename = filename + extension
        if not content:
            return {"error": "No content provided"}

        filepath = Path(context.working_directory) / filename
        if filepath.exists() and not overwrite:
            return {"error": f"File already exists: {filename}. Set overwrite=true to replace it."}

        try:
            filepath.write_text(content, encoding="utf-8")
            size = len(content.encode("utf-8"))
            return {
                "status": "success",
                "filename": filename,
                "path": str(filepath),
                "bytes_written": size,
                "_cli_print": [f"[green]{emoji} Created {filename} ({size:,} bytes)[/green]"],
            }
        except Exception as e:
            return {"error": f"Failed to write {filename}: {e}"}
