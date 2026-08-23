"""
MCP server exposing the DIALS agent's tools to other MCP-compatible agents
(e.g. a future Phenix agent, or any orchestrator) over the Model Context
Protocol, instead of only through the interactive CLI.

This is a narrower host than the interactive CLI (`dials_agent/cli.py`):

- No LLM client of its own. The calling agent, on the other end of the MCP
  connection, is the "brain" that decides which tools to call; this process
  only executes them and returns results. There is deliberately no
  `get_token_usage` tool here — this host makes no LLM calls, so there is no
  session token usage to report.
- A curated subset of the CLI's tool surface, not full parity:
    - `run_shell_command` (arbitrary shell execution) is excluded. It's
      fine when a human is present to confirm destructive commands; handing
      it to an external agent process is a materially bigger blast radius.
    - `suggest_dials_command` / `explain_dials_concept` are excluded. Both
      are designed around the CLI's own approve-then-execute loop and the
      CLI's own LLM answering in the same turn — neither maps onto a
      stateless external tool call. `execute_dials_command` below replaces
      `suggest_dials_command`'s role: it runs immediately, since the
      calling agent's decision to invoke the tool over MCP already *is*
      the approval.
    - `suggest_troubleshooting` is excluded for the same reason: it just
      echoes `{"status": "troubleshooting_requested", "problem": ...}`
      back, expecting the CLI's own LLM to answer — `diagnose_problem`
      (which does real lookup work) is exposed instead.

Run with: python -m dials_agent.mcp_server
"""

import logging
from datetime import datetime
from pathlib import Path
from typing import Any, Literal, Optional

from mcp.server.mcpserver import MCPServer

from . import __version__
from .config import Settings, get_settings
from .dials.executor import CommandExecutor, CommandResult, create_executor
from .dials.parser import OutputParser, create_parser
from .dials.workflow import WorkflowManager, create_workflow_manager
from .skills import SkillContext, SkillRegistry, create_default_registry

logger = logging.getLogger(__name__)

SkillName = Literal[
    "data_import", "spot_finding", "indexing", "refinement", "integration",
    "symmetry", "scaling", "export", "troubleshooting", "workspace",
    "phil_params", "tutorials",
]
CommandCategory = Literal["all", "workflow", "utility", "visualization"]

# Excluded from the MCP surface: run_shell_command (arbitrary shell — see
# module docstring), suggest_dials_command, explain_dials_concept,
# suggest_troubleshooting, get_token_usage (no LLM usage to report here).
_EXCLUDED_TOOLS = {
    "run_shell_command", "suggest_dials_command", "explain_dials_concept",
    "suggest_troubleshooting", "get_token_usage",
}

# Output kept from a DIALS command's stdout/stderr before truncating —
# mirrors the head+tail truncation `run_auto` already applies in cli.py so
# a verbose command (e.g. dials.integrate) doesn't blow up the caller's
# context.
_MAX_OUTPUT_CHARS = 8000


def _truncate(text: str, max_chars: int = _MAX_OUTPUT_CHARS) -> str:
    if not text or len(text) <= max_chars:
        return text
    head = text[: max_chars // 3]
    tail = text[-(max_chars * 2 // 3):]
    return f"{head}\n\n[... output truncated ...]\n\n{tail}"


class DIALSMCPHost:
    """
    Holds the DIALS-processing state for one MCP server connection:
    working directory, executor, parser, workflow manager, skill registry,
    and command timings. Analogous to `DIALSAgent` in cli.py, minus the
    LLM client and interactive-approval machinery.
    """

    def __init__(self, working_directory: str = ".", settings: Optional[Settings] = None):
        self.working_directory = Path(working_directory).absolute()
        self.settings = settings or get_settings()
        self.workflow: WorkflowManager = create_workflow_manager(str(self.working_directory))
        self.executor: CommandExecutor = create_executor(str(self.working_directory))
        self.parser: OutputParser = create_parser()
        self.registry: SkillRegistry = create_default_registry()
        self.command_timings: list[dict] = []

    def _build_skill_context(self) -> SkillContext:
        return SkillContext(
            working_directory=str(self.working_directory),
            data_directory=self.settings.data_directory,
            existing_files=self.workflow.get_available_files(),
            executor=self.executor,
            parser=self.parser,
            workflow=self.workflow,
            command_timings=self.command_timings,
            session_usage=None,
            token_budget=self.settings.token_budget,
        )

    @staticmethod
    def _strip_host_keys(result: dict) -> dict:
        """Drop host-only metadata (leading underscore) — see base.py's handle_tool_call docstring."""
        return {k: v for k, v in result.items() if not k.startswith("_")}

    def dispatch(self, tool_name: str, tool_input: dict) -> dict:
        """
        Dispatch a tool call to the skill registry, applying the same
        host-side state updates the interactive CLI applies for the two
        tools that change agent state (working directory / data directory).
        """
        context = self._build_skill_context()
        result = self.registry.handle_tool_call(tool_name, tool_input, context)

        if tool_name == "change_working_directory" and result.get("status") == "success":
            new_path = Path(result["working_directory"])
            self.working_directory = new_path
            self.workflow = create_workflow_manager(str(new_path))
            self.executor = create_executor(str(new_path))
        elif tool_name == "change_data_directory" and result.get("status") == "success":
            self.settings.data_directory = result["data_directory"]

        return self._strip_host_keys(result)

    def execute_dials_command(self, command: str) -> dict:
        """Run a validated DIALS command immediately and return its result, timing, and parsed metrics."""
        result = self.executor.execute(command)

        cmd_name = command.split()[0] if command else command
        end = datetime.now()
        start = datetime.fromtimestamp(end.timestamp() - result.duration)
        timing_entry = {
            "command": command,
            "command_name": cmd_name,
            "duration": result.duration,
            "success": result.success,
            "start_time": start.strftime("%Y-%m-%d %H:%M:%S"),
            "end_time": end.strftime("%Y-%m-%d %H:%M:%S"),
        }
        self.command_timings.append(timing_entry)
        self._append_timing_log(timing_entry)

        parsed = self.parser.parse(result)
        self.workflow.record_command(result, parsed.metrics)

        return {
            "success": result.success,
            "return_code": result.return_code,
            "duration": result.duration,
            "stdout": _truncate(result.stdout),
            "stderr": _truncate(result.stderr),
            "output_files": result.output_files,
            "summary": parsed.summary,
            "metrics": parsed.metrics,
            "warnings": parsed.warnings,
            "suggestions": parsed.suggestions,
        }

    def _append_timing_log(self, entry: dict) -> None:
        """Append to dials_agent_timing.log, matching the CLI's format — see cli.py's _save_timing_to_file."""
        timing_file = self.working_directory / "dials_agent_timing.log"
        duration = entry["duration"]
        if duration >= 60:
            duration_str = f"{int(duration // 60)}m {duration % 60:.1f}s"
        else:
            duration_str = f"{duration:.1f}s"
        status = "OK" if entry["success"] else "FAILED"
        line = (
            f"{entry['start_time']}  →  {entry['end_time']}  "
            f"[{duration_str:>10}]  {status:6}  {entry['command']}\n"
        )
        with open(timing_file, "a") as f:
            f.write(line)

    def analyze_dials_output(self, command: str, output: str, return_code: int = 0) -> dict:
        """Parse raw DIALS command output text into a summary — for output the caller already has in hand."""
        result = CommandResult(
            command=command,
            return_code=return_code,
            stdout=output,
            stderr="",
            duration=0,
            success=return_code == 0,
            working_directory=str(self.working_directory),
        )
        parsed = self.parser.parse(result)
        return {
            "summary": parsed.summary,
            "metrics": parsed.metrics,
            "warnings": parsed.warnings,
            "suggestions": parsed.suggestions,
        }


def build_server(host: DIALSMCPHost) -> MCPServer:
    """Build the MCPServer, registering every tool this host exposes."""
    from .core.base_tools import get_base_tools

    all_schemas = {t["name"]: t for t in get_base_tools() + host.registry.get_all_tools()}
    descriptions = {name: schema["description"] for name, schema in all_schemas.items()}

    exposed = set(all_schemas) - _EXCLUDED_TOOLS
    missing = exposed - {
        "analyze_dials_output", "change_data_directory", "diagnose_problem",
        "check_workflow_status", "list_available_commands", "read_file", "open_file",
        "change_working_directory", "calculate", "get_timing_report",
        "create_markdown_file", "create_html_file", "lookup_phil_params", "load_skill",
    }
    if missing:
        raise RuntimeError(
            f"New tool(s) {missing} appeared in the registry but aren't wired into "
            f"the MCP server — add them to build_server() or _EXCLUDED_TOOLS explicitly."
        )

    server = MCPServer(
        name="dials-agent",
        version=__version__,
        instructions=(
            "Tools for running DIALS macromolecular crystallography data processing "
            "(import, spot finding, indexing, refinement, integration, symmetry, "
            "scaling, export) and inspecting results. Call load_skill for detailed "
            "guidance on a specific processing stage before using it — parameter "
            "choices, troubleshooting heuristics, and file conventions live there, "
            "not in this instructions block."
        ),
    )

    @server.tool(description="Execute a validated DIALS command (e.g. 'dials.index imported.expt strong.refl') "
                             "in the working directory. Runs immediately — there is no separate approval step "
                             "over MCP, so only call this once you intend the command to run.")
    def execute_dials_command(command: str) -> dict[str, Any]:
        return host.execute_dials_command(command)

    @server.tool(description=descriptions["analyze_dials_output"])
    def analyze_dials_output(command: str, output: str, return_code: int = 0) -> dict[str, Any]:
        return host.analyze_dials_output(command, output, return_code)

    @server.tool(description=descriptions["change_data_directory"])
    def change_data_directory(path: str) -> dict[str, Any]:
        return host.dispatch("change_data_directory", {"path": path})

    @server.tool(description=descriptions["diagnose_problem"])
    def diagnose_problem(problem: str, current_stage: str = "", context: str = "") -> dict[str, Any]:
        return host.dispatch(
            "diagnose_problem",
            {"problem": problem, "current_stage": current_stage, "context": context},
        )

    @server.tool(description=descriptions["check_workflow_status"])
    def check_workflow_status(working_directory: str = "") -> dict[str, Any]:
        return host.dispatch("check_workflow_status", {"working_directory": working_directory})

    @server.tool(description=descriptions["list_available_commands"])
    def list_available_commands(category: CommandCategory = "all", current_stage: str = "") -> dict[str, Any]:
        return host.dispatch(
            "list_available_commands", {"category": category, "current_stage": current_stage}
        )

    @server.tool(description=descriptions["read_file"])
    def read_file(filename: str, tail_lines: Optional[int] = None, max_chars: int = 50000) -> dict[str, Any]:
        tool_input: dict[str, Any] = {"filename": filename, "max_chars": max_chars}
        if tail_lines is not None:
            tool_input["tail_lines"] = tail_lines
        return host.dispatch("read_file", tool_input)

    @server.tool(description=descriptions["open_file"])
    def open_file(filename: str) -> dict[str, Any]:
        return host.dispatch("open_file", {"filename": filename})

    @server.tool(description=descriptions["change_working_directory"])
    def change_working_directory(path: str, create: bool = False) -> dict[str, Any]:
        return host.dispatch("change_working_directory", {"path": path, "create": create})

    @server.tool(description=descriptions["calculate"])
    def calculate(expression: str, description: str = "") -> dict[str, Any]:
        return host.dispatch("calculate", {"expression": expression, "description": description})

    @server.tool(description=descriptions["get_timing_report"])
    def get_timing_report() -> dict[str, Any]:
        return host.dispatch("get_timing_report", {})

    @server.tool(description=descriptions["create_markdown_file"])
    def create_markdown_file(filename: str, content: str, overwrite: bool = True) -> dict[str, Any]:
        return host.dispatch(
            "create_markdown_file", {"filename": filename, "content": content, "overwrite": overwrite}
        )

    @server.tool(description=descriptions["create_html_file"])
    def create_html_file(filename: str, content: str, overwrite: bool = True) -> dict[str, Any]:
        return host.dispatch(
            "create_html_file", {"filename": filename, "content": content, "overwrite": overwrite}
        )

    @server.tool(description=descriptions["lookup_phil_params"])
    def lookup_phil_params(command: str, search_term: str = "") -> dict[str, Any]:
        return host.dispatch("lookup_phil_params", {"command": command, "search_term": search_term})

    @server.tool(description=descriptions["load_skill"])
    def load_skill(skill_name: SkillName) -> dict[str, Any]:
        return host.dispatch("load_skill", {"skill_name": skill_name})

    return server


def main() -> None:
    import argparse

    parser = argparse.ArgumentParser(description="DIALS Agent MCP server")
    parser.add_argument(
        "-d", "--directory", default=None,
        help="Working directory for DIALS output (overrides WORKING_DIRECTORY in .env)",
    )
    parser.add_argument("-e", "--env-file", default=None, help="Path to .env file with configuration")
    args = parser.parse_args()

    if args.env_file:
        from .config import configure_from_env_file
        configure_from_env_file(args.env_file)

    settings = get_settings()
    working_directory = args.directory or settings.working_directory or "."

    host = DIALSMCPHost(working_directory=working_directory, settings=settings)
    server = build_server(host)
    server.run(transport="stdio")


if __name__ == "__main__":
    main()
