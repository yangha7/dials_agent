"""
CLI interface for the DIALS AI Agent.

This module provides an interactive command-line interface for users
to interact with the DIALS AI agent using natural language.
"""

import argparse
import logging
import os
import readline
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Optional

from rich.console import Console
from rich.markdown import Markdown
from rich.panel import Panel
from rich.prompt import Confirm, Prompt
from rich.table import Table
from rich.text import Text

from . import __version__
from .config import Settings, get_settings, configure_from_env_file
from .core.claude_client import ClaudeClient, ToolCall, create_client
from .core.tools import is_recognized_data_file
from .skills import SkillContext
from .dials.compare import (
    compare_runs,
    display_comparison,
    display_comparison_markdown,
    save_comparison_markdown,
    save_comparison_html,
)
from .dials.executor import CommandExecutor, CommandResult, create_executor
from .dials.parser import OutputParser, create_parser
from .dials.workflow import WorkflowManager, create_workflow_manager

logger = logging.getLogger(__name__)

# Rich console for formatted output
console = Console()


class DIALSAgent:
    """
    Main DIALS AI Agent class that coordinates all components.
    """
    
    def __init__(
        self,
        working_directory: str = ".",
        settings: Optional[Settings] = None,
        auto_mode: bool = False
    ):
        """
        Initialize the DIALS Agent.
        
        Args:
            working_directory: Directory for DIALS processing
            settings: Application settings
            auto_mode: If True, run through workflow without user confirmation
        """
        self.working_directory = Path(working_directory).absolute()
        self.base_directory = self.working_directory  # Remember the starting directory
        self.settings = settings or get_settings()
        self.auto_mode = auto_mode
        
        # Track all directories where work was done
        self.used_directories: list[Path] = []
        
        # Initialize components
        self.workflow = create_workflow_manager(str(self.working_directory))
        self.executor = create_executor(str(self.working_directory))
        self.parser = create_parser()
        
        # Initialize Claude client with context
        self.claude = create_client(
            working_directory=str(self.working_directory),
            existing_files=self.workflow.get_available_files(),
            settings=self.settings,
        )
        
        # Pending command for approval
        self.pending_command: Optional[dict] = None

        # Whether the workflow was already complete before the most recently executed
        # command ran -- see execute_command/display_result.
        self._workflow_was_complete_before_last_command: bool = False
        
        # Timing tracker for all executed commands
        self.command_timings: list[dict] = []
        
        # Active status spinner (set during "Thinking..." to allow tool handlers to pause it)
        self._active_status = None
    
    def _build_skill_context(self) -> SkillContext:
        """Build the read-only context passed to skill handlers."""
        return SkillContext(
            working_directory=str(self.working_directory),
            data_directory=self.settings.data_directory,
            existing_files=self.workflow.get_available_files(),
            executor=self.executor,
            parser=self.parser,
            workflow=self.workflow,
            command_timings=self.command_timings,
            session_usage=self.claude.session_usage,
            token_budget=self.settings.token_budget,
        )

    @staticmethod
    def _emit_cli_print(result: dict) -> None:
        """Print any CLI-only display messages a skill handler attached, then drop them."""
        for line in result.pop("_cli_print", None) or []:
            console.print(line)

    @staticmethod
    def _strip_host_keys(result: dict) -> dict:
        """Strip host-only metadata (leading underscore) before sending a result to the LLM."""
        return {k: v for k, v in result.items() if not k.startswith("_")}

    def _handle_tool_call(self, tool_call: ToolCall) -> dict:
        """
        Handle a tool call from Claude.

        The three tools every skill shares (suggest_dials_command,
        explain_dials_concept, analyze_dials_output) are handled directly
        here. Everything else is dispatched to whichever skill owns it via
        the ClaudeClient's SkillRegistry — see `dials_agent/skills/`.

        Args:
            tool_call: The tool call to handle

        Returns:
            Result dictionary
        """
        if tool_call.name == "suggest_dials_command":
            # Only one command can actually be pending at a time -- self.pending_command
            # is a single field, not a queue. Calling this twice in one turn (which does
            # happen) used to silently overwrite the first suggestion: the CLI would only
            # ever confirm/run the second one, while the LLM -- having gotten a
            # "pending_approval" acknowledgment for the first call too -- kept believing
            # both were still awaiting approval on later turns, producing a repeating
            # "still pending on my end, please confirm" loop that burned real turns/tokens
            # for zero benefit. Reject the second call explicitly instead, so the LLM gets
            # accurate feedback rather than a silent, confusing overwrite.
            if self.pending_command is not None:
                return {
                    "status": "error",
                    "message": (
                        f"A command is already pending approval "
                        f"('{self.pending_command.get('command')}') -- only one command can "
                        "be pending at a time. Wait for it to be approved and executed "
                        "(you'll get its real output in the next turn) before suggesting "
                        "another."
                    )
                }
            self.pending_command = tool_call.input
            return {
                "status": "pending_approval",
                "command": tool_call.input.get("command"),
                "message": "Command suggested, awaiting user approval"
            }

        elif tool_call.name == "explain_dials_concept":
            # Claude will provide the explanation in its response
            return {
                "status": "explanation_requested",
                "concept": tool_call.input.get("concept")
            }

        elif tool_call.name == "analyze_dials_output":
            # Parse the output if provided
            output = tool_call.input.get("output", "")
            command = tool_call.input.get("command", "")
            return_code = tool_call.input.get("return_code", 0)

            # Create a mock result for parsing
            result = CommandResult(
                command=command,
                return_code=return_code,
                stdout=output,
                stderr="",
                duration=0,
                success=return_code == 0,
                working_directory=str(self.working_directory)
            )

            parsed = self.parser.parse(result)
            return {
                "summary": parsed.summary,
                "metrics": parsed.metrics,
                "warnings": parsed.warnings,
                "suggestions": parsed.suggestions
            }

        context = self._build_skill_context()
        registry = self.claude.registry

        if tool_call.name == "change_working_directory":
            result = registry.handle_tool_call(tool_call.name, tool_call.input, context)
            if result.get("status") == "success":
                new_path = Path(result["working_directory"])
                self.working_directory = new_path
                self.workflow = create_workflow_manager(str(new_path))
                self.executor = create_executor(str(new_path))
                self.claude.update_context(
                    working_directory=str(new_path),
                    existing_files=self.workflow.get_available_files()
                )
                if new_path not in self.used_directories:
                    self.used_directories.append(new_path)
            self._emit_cli_print(result)
            return self._strip_host_keys(result)

        if tool_call.name == "change_data_directory":
            result = registry.handle_tool_call(tool_call.name, tool_call.input, context)
            if result.get("status") == "success":
                self.settings.data_directory = result["data_directory"]
                self.claude.update_context(
                    existing_files=self.workflow.get_available_files()
                )
            self._emit_cli_print(result)
            return self._strip_host_keys(result)

        if tool_call.name == "run_shell_command":
            result = registry.handle_tool_call(tool_call.name, tool_call.input, context)

            if result.get("status") == "requires_confirmation":
                # Stop the spinner so the confirmation prompt is clearly visible
                if self._active_status:
                    self._active_status.stop()

                console.print(f"\n[bold yellow]⚠  {result['message']}[/bold yellow]")
                if result.get("explanation"):
                    console.print(f"[dim]{result['explanation']}[/dim]")

                if not Confirm.ask("[bold red]Allow this command?[/bold red]", default=False):
                    if self._active_status:
                        self._active_status.start()
                    return {"status": "cancelled", "message": "User declined to run destructive command"}

                if self._active_status:
                    self._active_status.start()

                result = registry.handle_tool_call(
                    tool_call.name, {**tool_call.input, "_confirmed": True}, context
                )

            if result.pop("_files_may_have_changed", False):
                # Files may have changed — refresh workflow state
                self.workflow.refresh()
                self.claude.update_context(
                    existing_files=self.workflow.get_available_files()
                )

            self._emit_cli_print(result)
            return self._strip_host_keys(result)

        if registry.owns_tool(tool_call.name):
            result = registry.handle_tool_call(tool_call.name, tool_call.input, context)
            self._emit_cli_print(result)
            return self._strip_host_keys(result)

        return {"error": f"Unknown tool: {tool_call.name}"}
    
    def execute_command(self, command: str) -> CommandResult:
        """
        Execute a DIALS command.
        
        Args:
            command: The command to execute
            
        Returns:
            CommandResult with execution details
        """
        # Display-only shortening (e.g. dials.python's absolute script path -> just the
        # filename) -- the real, full command string below is what actually executes.
        console.print(f"\n[bold blue]Executing:[/bold blue] {self._display_command_label(command)}")

        # Snapshot completion state *before* running this command, so display_result can
        # tell "this command just finished the workflow" apart from "the workflow was
        # already complete before this command ran" (e.g. resuming in a directory copied
        # from a prior finished run for further investigation) -- see its use below.
        self._workflow_was_complete_before_last_command = self.workflow.is_complete()

        with console.status("[bold green]Running command..."):
            result = self.executor.execute(command)
        
        # Record timing
        cmd_name = command.split()[0] if command else command
        now = datetime.now()
        start_time = now.timestamp() - result.duration
        timing_entry = {
            "command": command,
            "command_name": cmd_name,
            "duration": result.duration,
            "success": result.success,
            "start_time": datetime.fromtimestamp(start_time).strftime("%Y-%m-%d %H:%M:%S"),
            "end_time": now.strftime("%Y-%m-%d %H:%M:%S"),
        }
        self.command_timings.append(timing_entry)
        
        # Save timing to file
        self._save_timing_to_file(timing_entry)
        
        # Display timing prominently
        self._display_timing(cmd_name, result.duration)
        
        # Parse the output
        parsed = self.parser.parse(result)
        
        # Record in workflow
        self.workflow.record_command(result, parsed.metrics)
        
        # Update Claude's context
        self.claude.update_context(
            existing_files=self.workflow.get_available_files()
        )
        
        return result
    
    def _save_timing_to_file(self, entry: dict):
        """Append a timing entry to the timing log file in the working directory."""
        timing_file = self.working_directory / "dials_agent_timing.log"
        
        # Format duration
        duration = entry["duration"]
        if duration >= 60:
            minutes = int(duration // 60)
            seconds = duration % 60
            duration_str = f"{minutes}m {seconds:.1f}s"
        else:
            duration_str = f"{duration:.1f}s"
        
        status = "OK" if entry["success"] else "FAILED"
        
        line = (
            f"{entry['start_time']}  →  {entry['end_time']}  "
            f"[{duration_str:>10}]  {status:6}  {entry['command']}\n"
        )
        
        with open(timing_file, "a") as f:
            f.write(line)
    
    def _display_timing(self, cmd_name: str, duration: float):
        """Display timing information for a command."""
        if duration >= 60:
            minutes = int(duration // 60)
            seconds = duration % 60
            time_str = f"{minutes}m {seconds:.1f}s"
        else:
            time_str = f"{duration:.1f}s"
        console.print(f"[bold magenta]⏱  {cmd_name} completed in {time_str}[/bold magenta]")
    
    @staticmethod
    def _display_command_label(command: str) -> str:
        """
        Shorten a `dials.python`/`cctbx.python`/`libtbx.python <script>.py ...`
        invocation to just the script's filename (dropping the installation's
        absolute path, which is boilerplate and pushes the actually useful
        part -- which script, and its arguments -- out of a narrow table
        column). Anything else is returned unchanged.

        Callers should NOT also hard-truncate the result with something like
        `command[:60]` -- that silently drops information with no ellipsis
        to show it happened. Let Rich wrap the full text within the column
        instead; wrapping preserves the information, a blind slice doesn't.
        """
        parts = command.split(maxsplit=2)
        if len(parts) >= 2 and parts[0] in ("dials.python", "cctbx.python", "libtbx.python") and parts[1].endswith(".py"):
            script_name = Path(parts[1]).name
            rest = parts[2] if len(parts) > 2 else ""
            return f"{parts[0]} {script_name}" + (f" {rest}" if rest else "")
        return command

    def display_timing_summary(self):
        """Display a summary table of all command timings."""
        if not self.command_timings:
            console.print("[yellow]No commands executed yet.[/yellow]")
            return
        
        table = Table(title="⏱  Command Timing Summary", border_style="magenta")
        table.add_column("#", style="dim", justify="right")
        # overflow="fold": wrap at any character rather than falling back to
        # an ellipsis cut on a long unbroken token (e.g. a glob path with no
        # spaces) in a narrow terminal -- ensures nothing is ever silently
        # dropped, at the cost of an occasional mid-word line break.
        table.add_column("Command", style="cyan", overflow="fold")
        table.add_column("Status", justify="center")
        table.add_column("Duration", style="magenta", justify="right")
        
        total_duration = 0.0
        for i, entry in enumerate(self.command_timings, 1):
            status = "[green]✓[/green]" if entry["success"] else "[red]✗[/red]"
            duration = entry["duration"]
            total_duration += duration
            
            if duration >= 60:
                minutes = int(duration // 60)
                seconds = duration % 60
                time_str = f"{minutes}m {seconds:.1f}s"
            else:
                time_str = f"{duration:.1f}s"
            
            table.add_row(str(i), self._display_command_label(entry["command"]), status, time_str)
        
        # Add total row
        if total_duration >= 60:
            total_minutes = int(total_duration // 60)
            total_seconds = total_duration % 60
            total_str = f"{total_minutes}m {total_seconds:.1f}s"
        else:
            total_str = f"{total_duration:.1f}s"
        
        table.add_section()
        table.add_row("", "[bold]Total[/bold]", "", f"[bold]{total_str}[/bold]")
        
        console.print(table)
    
    def display_command_suggestion(self, suggestion: dict):
        """Display a command suggestion to the user."""
        command = suggestion.get("command", "")
        explanation = suggestion.get("explanation", "")
        expected_output = suggestion.get("expected_output", "")
        warnings = suggestion.get("warnings", "")
        
        # Create a panel with the suggestion
        content = Text()
        content.append("Command: ", style="bold")
        content.append(f"{self._display_command_label(command)}\n\n", style="cyan")
        content.append("Explanation: ", style="bold")
        content.append(f"{explanation}\n\n")
        content.append("Expected output: ", style="bold")
        content.append(f"{expected_output}")
        
        if warnings:
            content.append("\n\n")
            content.append("⚠️ Warning: ", style="bold yellow")
            content.append(warnings, style="yellow")
        
        console.print(Panel(content, title="[bold]Suggested Command[/bold]", border_style="blue"))
    
    def display_result(self, result: CommandResult):
        """Display command execution result."""
        parsed = self.parser.parse(result)
        
        if result.success:
            style = "green"
            title = "✓ Command Successful"
        else:
            style = "red"
            title = "✗ Command Failed"
        
        content = Text()
        content.append(f"{parsed.summary}\n\n", style=style)
        
        # Prominent timing display
        content.append("⏱  Duration: ", style="bold")
        duration = result.duration
        if duration >= 60:
            minutes = int(duration // 60)
            seconds = duration % 60
            content.append(f"{minutes}m {seconds:.1f}s", style="bold magenta")
        else:
            content.append(f"{duration:.1f}s", style="bold magenta")
        content.append("\n")
        
        if result.output_files:
            content.append("Created files: ", style="bold")
            content.append(", ".join(result.output_files))
        
        if parsed.warnings:
            content.append("\n\nWarnings:\n", style="yellow bold")
            for warning in parsed.warnings[:5]:  # Limit to 5 warnings
                content.append(f"  • {warning}\n", style="yellow")
        
        if parsed.suggestions:
            content.append("\n\nSuggestions:\n", style="cyan bold")
            for suggestion in parsed.suggestions:
                content.append(f"  • {suggestion}\n", style="cyan")
        
        console.print(Panel(content, title=f"[bold]{title}[/bold]", border_style=style))
        
        # Show next step suggestion if command was successful (skip in auto mode).
        # Also skip if the workflow was already complete before this command ran --
        # e.g. resuming in a directory copied from a prior finished run to investigate
        # something further (scaled.mtz etc. already present from the start). Without
        # this, "🎉 Workflow Complete!" fires after every single command, including
        # read-only diagnostic scripts that have nothing to do with finishing anything,
        # which is confusing noise rather than useful signal. The explicit `next`
        # command still shows it on request regardless -- this only suppresses the
        # automatic, unsolicited repeat.
        if result.success and not self.auto_mode and not self._workflow_was_complete_before_last_command:
            self.display_next_step_suggestion()
    
    def display_next_step_suggestion(self):
        """Display the suggested next step in the workflow."""
        self.workflow.refresh()
        suggestion = self.workflow.get_next_step_suggestion()
        
        if suggestion["next_command"] is None:
            # Workflow complete
            console.print(Panel(
                "[bold green]🎉 Workflow Complete![/bold green]\n\n"
                f"{suggestion['explanation']}\n\n"
                f"💡 [cyan]{suggestion['tip']}[/cyan]",
                title="[bold]Next Step[/bold]",
                border_style="green"
            ))
        else:
            content = Text()
            content.append("Suggested command:\n", style="bold")
            content.append(f"  {suggestion['next_command']}\n\n", style="cyan")
            content.append(f"{suggestion['explanation']}\n\n")
            
            if suggestion.get("tip"):
                content.append("💡 Tip: ", style="bold")
                content.append(f"{suggestion['tip']}\n", style="dim")
            
            if suggestion.get("is_multi_crystal"):
                content.append("\n📊 ", style="bold")
                content.append("Multi-crystal mode detected", style="magenta")
            
            console.print(Panel(
                content,
                title=f"[bold]Next Step ({suggestion['progress']} complete)[/bold]",
                border_style="blue"
            ))
    
    def display_workflow_status(self):
        """Display current workflow status."""
        self.workflow.refresh()
        
        table = Table(title="Workflow Status")
        table.add_column("Property", style="cyan")
        table.add_column("Value", style="white")
        
        table.add_row("Working Directory", str(self.working_directory))
        table.add_row("Data Directory", self.settings.data_directory or "(not configured)")
        table.add_row("Current Stage", self.workflow.get_stage_name())
        table.add_row("Progress", f"{self.workflow.get_progress_percentage():.0f}%")
        table.add_row("Experiment Files", ", ".join(self.workflow.get_experiment_files()) or "None")
        table.add_row("Reflection Files", ", ".join(self.workflow.get_reflection_files()) or "None")
        
        next_cmd = self.workflow.get_next_command()
        table.add_row("Suggested Next", next_cmd or "Workflow complete!")
        
        console.print(table)
    
    # stop_reason values meaning "cut off by the output token limit" -- "length" from
    # OpenAI-compatible providers (CBORG/OpenAI/Gemini), "max_tokens" from native Anthropic.
    _TRUNCATED_STOP_REASONS = ("length", "max_tokens")

    def chat(self, user_message: str) -> str:
        """
        Send a message to the agent, display token usage, and return the text.
        """
        self.pending_command = None

        response = self.claude.send_message(
            user_message,
            tool_handler=self._handle_tool_call
        )

        self._display_token_usage(response.usage)
        self._warn_if_response_truncated(response)
        return response.message

    def _warn_if_response_truncated(self, response) -> None:
        """
        Surface a clear warning when a turn was cut off by MAX_TOKENS, instead of
        silently showing nothing (or a silently-incomplete answer) with no indication
        anything went wrong.

        A real failure mode found live: a long, context-heavy analysis turn hit the
        output token limit with no visible text and no tool call in the final round --
        `response.stop_reason` is captured on every response but was never actually
        checked anywhere, so the turn just silently did nothing (no "Agent" header, no
        text, no next step) despite a full-price, maximum-length API call having just
        run (visible only as a token-usage line with output tokens exactly equal to
        the configured MAX_TOKENS).
        """
        if response.stop_reason not in self._TRUNCATED_STOP_REASONS:
            return
        if not (response.message or "").strip() and not response.tool_calls:
            console.print(
                "\n[bold red]⚠ Response cut off — no output[/bold red]\n"
                "[red]The model hit the output token limit (MAX_TOKENS="
                f"{self.settings.get_resolved_max_tokens()}) before producing any visible text or a "
                "tool call this turn -- that's why nothing appeared above. This tends to "
                "happen in long, context-heavy investigations. Try a more focused "
                "follow-up (e.g. \"just tell me your conclusion so far\"), or raise "
                "MAX_TOKENS in .env.[/red]"
            )
        else:
            console.print(
                f"\n[yellow]⚠ Note: this response was cut off by the output token limit "
                f"(MAX_TOKENS={self.settings.get_resolved_max_tokens()}) -- it may be incomplete.[/yellow]"
            )

    def _display_token_usage(self, usage) -> None:
        """Print a compact dim token-usage line after each turn."""
        if usage is None:
            return

        parts = []

        # Per-turn counts
        if usage.input_tokens or usage.output_tokens:
            parts.append(f"{usage.input_tokens:,} in / {usage.output_tokens:,} out")

        # Cache info (Anthropic only — both fields are 0 on OpenAI-compat)
        if usage.cache_read_tokens:
            parts.append(f"{usage.cache_read_tokens:,} cached")
        if usage.cache_creation_tokens:
            parts.append(f"{usage.cache_creation_tokens:,} cache write")

        # Session running total
        session = self.claude.session_usage
        parts.append(f"session {session.total:,} tok")

        # Optional budget
        budget = self.settings.token_budget
        if budget > 0:
            used = session.total
            remaining = max(0, budget - used)
            pct = 100 * remaining / budget
            parts.append(f"budget {remaining:,} left ({pct:.0f}%)")

        console.print(f"[dim]↳ {' | '.join(parts)}[/dim]")
    
    def _directory_has_data_files(self, directory: Path, max_depth: int = 2) -> bool:
        """Shallow check for any recognized diffraction data file under `directory`."""
        def scan(d: Path, depth: int) -> bool:
            if depth > max_depth:
                return False
            try:
                for item in d.iterdir():
                    if item.is_file() and is_recognized_data_file(item):
                        return True
                    if item.is_dir() and not item.name.startswith("."):
                        if scan(item, depth + 1):
                            return True
            except PermissionError:
                pass
            return False
        return scan(directory, 0)

    def _discover_dataset_subdirectories(self) -> list[Path]:
        """
        Look for multiple independent datasets under the configured data
        directory: immediate subdirectories that themselves contain
        recognized diffraction data files.

        Used by `run_auto` to decide whether to process a single dataset
        (unchanged default behavior) or loop over several, each into its
        own output subdirectory.
        """
        data_dir = self.settings.data_directory
        if not data_dir:
            return []
        base = Path(data_dir)
        if not base.is_dir():
            return []

        found = []
        try:
            for entry in sorted(base.iterdir()):
                if entry.is_dir() and not entry.name.startswith(".") and self._directory_has_data_files(entry):
                    found.append(entry)
        except PermissionError:
            pass
        return found

    def _switch_to_dataset(self, dataset_dir: Path, output_dir: Path):
        """
        Point the agent at one dataset for multi-dataset auto processing:
        input is read from `dataset_dir`, output is written to `output_dir`
        (created if it doesn't exist yet). Conversation history is cleared
        so context from a previous dataset doesn't bleed into this one.
        """
        output_dir.mkdir(parents=True, exist_ok=True)
        self.working_directory = output_dir
        self.workflow = create_workflow_manager(str(output_dir))
        self.executor = create_executor(str(output_dir))
        self.settings.data_directory = str(dataset_dir)

        self.claude.clear_history()
        self.claude.update_context(
            working_directory=str(output_dir),
            existing_files=self.workflow.get_available_files(),
        )
        if output_dir not in self.used_directories:
            self.used_directories.append(output_dir)

    def run_auto(self, initial_message: str = None, skip_dials_check: bool = False):
        """
        Run the agent in auto mode — process the entire workflow without user interruption.

        If the configured data directory contains multiple subdirectories that each
        look like independent datasets (and the user hasn't named one specifically),
        each one is processed in turn into its own output subdirectory, rather than
        assuming there's exactly one dataset to process.

        Args:
            initial_message: The initial instruction to send to Claude
            skip_dials_check: Skip DIALS availability check (already done in interactive mode)
        """
        console.print(Panel.fit(
            f"[bold blue]DIALS AI Agent — Auto Mode[/bold blue] [dim]v{__version__}[/dim]\n"
            "Running through the complete workflow without interruption.\n"
            "Press Ctrl+C to abort.",
            border_style="blue"
        ))

        if not skip_dials_check:
            # Check DIALS availability
            available, version = self.executor.check_dials_available()
            if available:
                console.print(f"[green]✓ DIALS available: {version}[/green]")
            else:
                console.print(f"[red]✗ DIALS not found: {version}[/red]")
                console.print("[red]Cannot run in auto mode without DIALS installed.[/red]")
                return

            # Show initial status
            self.display_workflow_status()
            console.print()

        auto_start_time = time.time()

        dataset_dirs = self._discover_dataset_subdirectories()
        if len(dataset_dirs) < 2:
            # Single dataset — unchanged, original behavior.
            try:
                self._run_auto_single(initial_message)
            except KeyboardInterrupt:
                console.print("\n[yellow]Auto mode interrupted by user.[/yellow]")
        else:
            # Multiple candidate datasets found. If the user's message names
            # exactly one of them, treat that as "specifically suggested" and
            # process only it; otherwise process all of them, one at a time.
            named = [
                d for d in dataset_dirs
                if initial_message and d.name.lower() in initial_message.lower()
            ]
            targets = named if len(named) == 1 else dataset_dirs

            console.print(
                f"[bold blue]Found {len(dataset_dirs)} dataset subdirectories under "
                f"{self.settings.data_directory}[/bold blue]"
            )
            if targets is dataset_dirs:
                console.print(f"[dim]No single dataset named in the request — processing all {len(targets)}.[/dim]\n")
            else:
                console.print(f"[dim]Processing the one named in the request: {targets[0].name}[/dim]\n")

            results = []
            base_output_dir = self.base_directory
            try:
                for i, dataset_dir in enumerate(targets, 1):
                    output_dir = (base_output_dir / dataset_dir.name).resolve()
                    console.print(Panel.fit(
                        f"[bold blue]Dataset {i}/{len(targets)}: {dataset_dir.name}[/bold blue]\n"
                        f"Data:   {dataset_dir}\n"
                        f"Output: {output_dir}",
                        border_style="blue"
                    ))
                    self._switch_to_dataset(dataset_dir, output_dir)
                    completed = self._run_auto_single(initial_message)
                    results.append((dataset_dir.name, output_dir, completed))
            except KeyboardInterrupt:
                console.print("\n[yellow]Auto mode interrupted by user — stopping before remaining datasets.[/yellow]")

            # Restore to the original base directory for any subsequent interactive use.
            self.working_directory = base_output_dir
            self.workflow = create_workflow_manager(str(base_output_dir))
            self.executor = create_executor(str(base_output_dir))

            console.print("\n[bold]Multi-dataset summary:[/bold]")
            for name, output_dir, completed in results:
                status = "[green]complete[/green]" if completed else "[yellow]incomplete (hit iteration limit or error)[/yellow]"
                console.print(f"  [cyan]{name}[/cyan] → {output_dir}  [{status}]")

        # Show final timing summary (aggregated across all datasets processed above)
        auto_duration = time.time() - auto_start_time
        console.print()
        self.display_timing_summary()

        if auto_duration >= 60:
            total_minutes = int(auto_duration // 60)
            total_seconds = auto_duration % 60
            console.print(f"\n[bold]Total wall-clock time: {total_minutes}m {total_seconds:.1f}s[/bold]")
        else:
            console.print(f"\n[bold]Total wall-clock time: {auto_duration:.1f}s[/bold]")

    def _run_auto_single(self, initial_message: str = None, max_iterations: int = 30) -> bool:
        """
        Run the complete DIALS workflow, unattended, for whatever dataset is
        currently configured (`self.working_directory` / `self.settings.data_directory`).

        Returns True if the workflow completed within the iteration budget,
        False if it hit the limit, errored, or was interrupted.
        """
        # Build the auto-mode instruction
        auto_instruction = (
            "You are now in AUTO MODE. Execute the complete DIALS workflow automatically. "
            "Rules for auto mode:\n"
            "1. Suggest one DIALS command at a time using suggest_dials_command\n"
            "2. Do NOT suggest GUI commands (dials.image_viewer, dials.reciprocal_lattice_viewer) — skip them\n"
            "3. Do NOT ask the user for confirmation or choices — just proceed with sensible defaults\n"
            "4. After each command completes, briefly analyze the output and immediately suggest the next step\n"
            "5. Continue until the workflow is complete (through export/merge)\n"
            "6. Keep explanations brief in auto mode\n\n"
        )

        if initial_message:
            auto_instruction += f"User's request: {initial_message}"
        else:
            auto_instruction += "Process the data through the complete workflow with default settings."

        iteration = 0
        self.auto_mode = True
        completed = False

        # Start with the auto instruction
        current_message = auto_instruction

        try:
            while iteration < max_iterations:
                iteration += 1
                console.print(f"\n[dim]── Auto step {iteration} ──[/dim]")

                # Send message to Claude
                with console.status("[bold green]Thinking...") as status:
                    self._active_status = status
                    response = self.chat(current_message)
                    self._active_status = None

                # Display response
                if response:
                    console.print(f"\n[bold green]Agent[/bold green]")
                    console.print(Markdown(response))

                # Handle pending command — auto-approve
                if self.pending_command:
                    self.display_command_suggestion(self.pending_command)
                    console.print("[bold yellow]Auto-approving command...[/bold yellow]")

                    result = self.execute_command(self.pending_command["command"])
                    self.display_result(result)

                    if not result.success:
                        console.print("[red]Command failed. Asking agent for troubleshooting...[/red]")
                        current_message = (
                            f"The command '{self.pending_command['command']}' failed with return code {result.return_code}. "
                            f"Error output:\n{result.stderr[:2000] if result.stderr else result.stdout[:2000]}\n\n"
                            f"Please troubleshoot and suggest a fix, or skip this step if appropriate."
                        )
                        self.pending_command = None
                        continue

                    # Send result back to Claude for analysis and next step
                    cmd_name = self.pending_command["command"].split()[0] if self.pending_command["command"] else ""
                    if cmd_name in ("dials.scale", "dials.symmetry", "dials.cosym", "dials.merge", "dials.index"):
                        max_output = 8000
                    else:
                        max_output = 3000

                    output_text = result.stdout if result.stdout else result.stderr
                    if len(output_text) > max_output:
                        head = output_text[:max_output // 3]
                        tail = output_text[-(max_output * 2 // 3):]
                        output_summary = f"{head}\n\n[... output truncated ...]\n\n{tail}"
                    else:
                        output_summary = output_text

                    self.pending_command = None

                    # Check if workflow is complete
                    self.workflow.refresh()
                    if self.workflow.is_complete():
                        console.print("\n[bold green]🎉 Workflow complete![/bold green]")
                        completed = True
                        break

                    # Ask Claude to analyze and continue
                    current_message = (
                        f"AUTO MODE: The command '{cmd_name}' completed successfully (return code {result.return_code}). "
                        f"Output:\n\n{output_summary}\n\n"
                        f"Briefly analyze, then IMMEDIATELY use suggest_dials_command to suggest the next step. "
                        f"Skip GUI commands. Do not ask for confirmation or present options."
                    )
                else:
                    # No pending command — check if workflow is done
                    self.workflow.refresh()
                    if self.workflow.is_complete():
                        console.print("\n[bold green]🎉 Workflow complete![/bold green]")
                        completed = True
                        break

                    # Ask Claude to continue — be very explicit
                    current_message = (
                        "AUTO MODE: You must use the suggest_dials_command tool NOW to suggest the next DIALS command. "
                        "Do not present options or ask questions. Skip GUI commands (image_viewer, reciprocal_lattice_viewer). "
                        "Just suggest the next processing command."
                    )

            if iteration >= max_iterations and not completed:
                console.print(f"\n[yellow]Reached maximum iterations ({max_iterations}). Stopping auto mode.[/yellow]")

        except KeyboardInterrupt:
            self.auto_mode = False
            raise
        except Exception as e:
            console.print(f"\n[red]Error in auto mode: {e}[/red]")
            logger.exception("Error in auto mode")

        # Exit auto mode
        self.auto_mode = False
        return completed
    
    def run_interactive(self):
        """Run the interactive CLI loop."""
        console.print(Panel.fit(
            f"[bold blue]DIALS AI Agent[/bold blue] [dim]v{__version__}[/dim]\n"
            "Natural language interface for DIALS crystallography data processing.\n"
            "Type 'help' for commands, 'quit' to exit.",
            border_style="blue"
        ))
        
        # Check DIALS availability
        available, version = self.executor.check_dials_available()
        if available:
            console.print(f"[green]✓ DIALS available: {version}[/green]")
        else:
            console.print(f"[yellow]⚠ DIALS not found: {version}[/yellow]")
            console.print("[yellow]Commands will be suggested but may not execute.[/yellow]")
        
        # Show initial status
        self.display_workflow_status()
        console.print()
        
        while True:
            try:
                # Get user input (with readline history support for up/down arrows)
                try:
                    # Use \001 and \002 to mark invisible chars for readline
                    # This prevents line wrapping issues with long prompts
                    user_input = input("\n\001\033[1;36m\002You\001\033[0m\002: ")
                except EOFError:
                    break
                
                if not user_input.strip():
                    continue
                
                # Handle special commands
                lower_input = user_input.lower().strip()
                
                if lower_input in ['quit', 'exit', 'q', 'bye', 'goodbye']:
                    # Show timing summary on exit if any commands were run
                    if self.command_timings:
                        self.display_timing_summary()
                    # Show where data was saved
                    self._display_exit_info()
                    console.print("[yellow]Goodbye![/yellow]")
                    break
                
                elif lower_input == 'help':
                    self._show_help()
                    continue
                
                elif lower_input == 'status':
                    self.display_workflow_status()
                    continue
                
                elif lower_input == 'next':
                    self.display_next_step_suggestion()
                    continue
                
                elif lower_input == 'history':
                    self._show_history()
                    continue
                
                elif lower_input == 'timing':
                    self.display_timing_summary()
                    continue
                
                elif lower_input == 'auto' or lower_input.startswith('auto '):
                    # 'auto' alone or 'auto <message>' to pass a custom instruction
                    if lower_input.startswith('auto '):
                        auto_msg = user_input[5:].strip()
                    else:
                        auto_msg = None
                    console.print("[bold blue]Entering auto mode...[/bold blue]")
                    self.run_auto(initial_message=auto_msg, skip_dials_check=True)
                    continue
                
                elif lower_input == 'clear':
                    self.claude.clear_history()
                    console.print("[green]Conversation history cleared.[/green]")
                    continue
                
                elif lower_input == 'multi':
                    self.workflow.set_multi_crystal(True)
                    console.print("[green]Multi-crystal mode enabled.[/green]")
                    console.print("[dim]Commands will use joint=false for indexing and dials.cosym for symmetry.[/dim]")
                    continue
                
                elif lower_input == 'single':
                    self.workflow.set_multi_crystal(False)
                    console.print("[green]Single-crystal mode enabled.[/green]")
                    continue
                
                elif lower_input in ['reset', 'clean', 'start over']:
                    self._reset_working_directory()
                    continue
                
                elif lower_input == 'cd':
                    # cd with no args → go back to base directory
                    self._change_directory(str(self.base_directory))
                    continue
                
                elif lower_input.startswith('cd '):
                    new_dir = user_input[3:].strip()
                    self._change_directory(new_dir)
                    continue
                
                elif lower_input.startswith('mkdir '):
                    dir_name = user_input[6:].strip()
                    self._make_directory(dir_name)
                    continue
                
                elif lower_input in ['pwd', 'workspace']:
                    console.print(f"[cyan]Current directory:[/cyan] {self.working_directory}")
                    console.print(f"[dim]Base directory:    {self.base_directory}[/dim]")
                    continue
                
                elif lower_input.startswith('compare ') or lower_input == 'compare':
                    if lower_input == 'compare':
                        console.print("[yellow]Usage: compare <dir1> <dir2> [dir3 ...][/yellow]")
                        console.print("[dim]Compare DIALS processing results across multiple directories.[/dim]")
                        console.print("[dim]Runs dials.report on each directory and shows HTML report paths.[/dim]")
                        console.print("[dim]Options: --labels name1,name2  --output report.json  --no-report[/dim]")
                        console.print("[dim]Example: compare run_agent run_human run_v2[/dim]")
                    else:
                        args_str = user_input[8:].strip()
                        self._run_compare(args_str)
                    continue
                
                # Detect autonomous processing requests and switch to auto mode
                auto_keywords = [
                    "automatically", "autonomous", "on your own", "without interruption",
                    "run through", "process everything", "all steps", "complete workflow",
                    "start to finish", "end to end", "no confirmation", "unattended",
                    "run all", "do everything", "full pipeline", "whole workflow",
                ]
                if any(kw in lower_input for kw in auto_keywords):
                    console.print(Panel.fit(
                        "[bold blue]Auto Mode Detected[/bold blue]\n\n"
                        "This will run the entire DIALS workflow without interruption.\n"
                        "Each command will be auto-approved and executed.\n"
                        "This may take 10-20 minutes depending on your data.",
                        border_style="blue"
                    ))
                    if Confirm.ask("[bold]Run in auto mode?[/bold]", default=True):
                        self.run_auto(initial_message=user_input, skip_dials_check=True)
                    else:
                        console.print("[yellow]Auto mode cancelled. Sending your request to the agent instead...[/yellow]")
                        # Fall through to normal Claude processing below
                        with console.status("[bold green]Thinking...") as status:
                            self._active_status = status
                            response = self.chat(user_input)
                            self._active_status = None
                        if response:
                            console.print(f"\n[bold green]Agent[/bold green]")
                            console.print(Markdown(response))
                    continue
                
                # Direct DIALS command execution — if input starts with "dials."
                if user_input.strip().startswith("dials."):
                    command = user_input.strip()
                    result = self.execute_command(command)
                    self.display_result(result)
                    
                    # Send result to Claude for analysis
                    if result.stdout or result.stderr:
                        cmd_name = command.split()[0] if command else ""
                        if cmd_name in ("dials.scale", "dials.symmetry", "dials.cosym", "dials.merge", "dials.index"):
                            max_output = 8000
                        else:
                            max_output = 3000
                        
                        output_text = result.stdout if result.stdout else result.stderr
                        if len(output_text) > max_output:
                            head = output_text[:max_output // 3]
                            tail = output_text[-(max_output * 2 // 3):]
                            output_summary = f"{head}\n\n[... output truncated ...]\n\n{tail}"
                        else:
                            output_summary = output_text
                        
                        log_hint = ""
                        if cmd_name == "dials.scale":
                            log_hint = "\n\nIMPORTANT: Please read dials.scale.log to get the full merging statistics table and present them to the user. Also mention the dials.scale.html report."
                        elif cmd_name == "dials.symmetry":
                            log_hint = "\n\nIMPORTANT: Please read dials.symmetry.log to get the full symmetry analysis results and present them to the user."
                        elif cmd_name == "dials.index":
                            log_hint = "\n\nIMPORTANT: Please read dials.index.log to get the full indexing results including unit cell, space group, and indexed percentage."
                        elif cmd_name == "dials.integrate":
                            log_hint = "\n\nIMPORTANT: Please read dials.integrate.log to get the integration statistics."
                        
                        with console.status("[bold green]Analyzing results...") as status:
                            self._active_status = status
                            analysis = self.chat(
                                f"I directly ran the command '{command}' which completed with return code {result.return_code}. "
                                f"Here's the output:\n\n{output_summary}{log_hint}"
                            )
                            self._active_status = None
                        if analysis:
                            console.print(f"\n[bold green]Agent[/bold green]")
                            console.print(Markdown(analysis))
                    continue
                
                # Send to Claude
                with console.status("[bold green]Thinking...") as status:
                    self._active_status = status
                    response = self.chat(user_input)
                    self._active_status = None
                
                # Display response
                if response:
                    console.print(f"\n[bold green]Agent[/bold green]")
                    console.print(Markdown(response))
                
                # Handle pending command
                if self.pending_command:
                    self.display_command_suggestion(self.pending_command)
                    
                    if Confirm.ask("Execute this command?", default=True):
                        result = self.execute_command(self.pending_command["command"])
                        self.display_result(result)
                        
                        # Send result back to Claude for analysis
                        if result.stdout or result.stderr:
                            # Use more output for scaling/symmetry commands that have important statistics
                            cmd_name = self.pending_command["command"].split()[0] if self.pending_command["command"] else ""
                            if cmd_name in ("dials.scale", "dials.symmetry", "dials.cosym", "dials.merge", "dials.index"):
                                max_output = 8000  # More output for commands with important statistics
                            else:
                                max_output = 3000
                            
                            output_text = result.stdout if result.stdout else result.stderr
                            # For long output, include both the beginning and end (statistics are often at the end)
                            if len(output_text) > max_output:
                                head = output_text[:max_output // 3]
                                tail = output_text[-(max_output * 2 // 3):]
                                output_summary = f"{head}\n\n[... output truncated ...]\n\n{tail}"
                            else:
                                output_summary = output_text
                            
                            # Also instruct Claude to read the log file for full details
                            log_hint = ""
                            if cmd_name == "dials.scale":
                                log_hint = "\n\nIMPORTANT: Please read dials.scale.log to get the full merging statistics table and present them to the user. Also mention the dials.scale.html report."
                            elif cmd_name == "dials.symmetry":
                                log_hint = "\n\nIMPORTANT: Please read dials.symmetry.log to get the full symmetry analysis results and present them to the user."
                            elif cmd_name == "dials.index":
                                log_hint = "\n\nIMPORTANT: Please read dials.index.log to get the full indexing results including unit cell, space group, and indexed percentage."
                            elif cmd_name == "dials.integrate":
                                log_hint = "\n\nIMPORTANT: Please read dials.integrate.log to get the integration statistics."
                            
                            with console.status("[bold green]Analyzing results...") as status:
                                self._active_status = status
                                analysis = self.chat(
                                    f"The command '{cmd_name}' completed with return code {result.return_code}. "
                                    f"Here's the output:\n\n{output_summary}{log_hint}"
                                )
                                self._active_status = None
                            if analysis:
                                console.print(f"\n[bold green]Agent[/bold green]")
                                console.print(Markdown(analysis))
                    else:
                        console.print("[yellow]Command skipped.[/yellow]")
                    
                    self.pending_command = None
                
            except KeyboardInterrupt:
                console.print("\n[yellow]Use 'quit' to exit.[/yellow]")
            except Exception as e:
                console.print(f"[red]Error: {e}[/red]")
                logger.exception("Error in interactive loop")
    
    def _show_help(self):
        """Show help information."""
        help_text = """
## Available Commands

- **help** - Show this help message
- **status** - Show current workflow status
- **next** - Show suggested next step
- **history** - Show command history
- **timing** - Show timing summary for all executed commands
- **auto** - Run through the entire workflow automatically (no confirmations). If the data directory has multiple dataset subdirectories, each is processed in turn into its own output subdirectory, unless you name one specifically
- **auto <message>** - Auto mode with custom instruction (e.g., `auto process insulin data fast version`, or `auto process the lysozyme dataset` to process just that one subdirectory)
- **compare <dir1> <dir2> [...]** - Compare results from multiple processing runs
- **reset** / **clean** / **start over** - Remove DIALS output files and start fresh
- **clear** - Clear conversation history
- **multi** - Enable multi-crystal mode (uses joint=false, dials.cosym)
- **single** - Enable single-crystal mode (default)
- **mkdir <name>** - Create a subdirectory and switch to it
- **cd <path>** - Change working directory (relative or absolute)
- **cd** - Return to the base (starting) directory
- **pwd** / **workspace** - Show current and base directory
- **quit** / **exit** - Exit the agent (shows where data was saved)

## Natural Language Examples

- "Import my images from /data/insulin"
- "Find spots on the imported data"
- "Index the spots"
- "What's the current unit cell?"
- "Why did indexing fail?"
- "Process my data with default settings"
- "What should I do next?"

## Tutorial Workflow (Cows, Pigs, People)

For multi-crystal datasets like the tutorial:
1. Type **multi** to enable multi-crystal mode
2. Import: `dials.import ../data/CIX*gz`
3. Find spots: `dials.find_spots imported.expt`
4. Index: `dials.index imported.expt strong.refl joint=false`
5. Refine: `dials.refine indexed.expt indexed.refl`
6. Integrate: `dials.integrate refined.expt refined.refl`
7. Symmetry: `dials.cosym integrated.expt integrated.refl`
8. Scale: `dials.scale symmetrized.expt symmetrized.refl`
9. Export: `dials.export scaled.expt scaled.refl`

## Comparing Runs

To compare results from multiple processing runs (e.g., human vs agent):
```
compare run_agent run_human run_v2
```
Or from the command line:
```
dials-agent --compare run1 run2 run3
dials-agent --compare run1 run2 --compare-output report.json
```
This extracts metrics from each directory's log files and shows a
side-by-side comparison with consistency assessment.
"""
        console.print(Markdown(help_text))
    
    def _show_history(self):
        """Show command history."""
        history = self.workflow.state.command_history
        
        if not history:
            console.print("[yellow]No commands executed yet.[/yellow]")
            return
        
        table = Table(title="Command History")
        table.add_column("#", style="dim")
        table.add_column("Command", style="cyan", overflow="fold")
        table.add_column("Status", style="white")
        table.add_column("Duration", style="magenta")
        
        total_duration = 0.0
        for i, cmd in enumerate(history[-10:], 1):  # Last 10 commands
            status = "[green]✓[/green]" if cmd.success else "[red]✗[/red]"
            duration = cmd.duration
            total_duration += duration
            
            if duration >= 60:
                minutes = int(duration // 60)
                seconds = duration % 60
                time_str = f"{minutes}m {seconds:.1f}s"
            else:
                time_str = f"{duration:.1f}s"
            
            table.add_row(str(i), self._display_command_label(cmd.command), status, time_str)
        
        # Add total row
        if total_duration >= 60:
            total_minutes = int(total_duration // 60)
            total_seconds = total_duration % 60
            total_str = f"{total_minutes}m {total_seconds:.1f}s"
        else:
            total_str = f"{total_duration:.1f}s"
        
        table.add_section()
        table.add_row("", "[bold]Total[/bold]", "", f"[bold]{total_str}[/bold]")
        
        console.print(table)
    
    def _change_directory(self, new_dir: str):
        """Change the working directory.
        
        Supports:
        - Absolute paths: cd /path/to/dir
        - Relative to current directory: cd subdir
        - Relative to base directory: cd ~/subdir (~ = base directory)
        - Back to base: cd (no args)
        """
        if new_dir.startswith("~"):
            # ~ refers to the base directory, not home
            new_path = self.base_directory / new_dir[1:].lstrip("/")
        elif not Path(new_dir).is_absolute():
            # Relative path — resolve relative to current working directory
            new_path = (self.working_directory / new_dir).resolve()
        else:
            new_path = Path(new_dir).expanduser().absolute()
        
        if not new_path.exists():
            # Offer to create it
            console.print(f"[yellow]Directory does not exist: {new_path}[/yellow]")
            if Confirm.ask("Create it?", default=True):
                new_path.mkdir(parents=True, exist_ok=True)
                console.print(f"[green]Created: {new_path}[/green]")
            else:
                return
        
        self.working_directory = new_path
        self.workflow = create_workflow_manager(str(new_path))
        self.executor = create_executor(str(new_path))
        self.claude.update_context(
            working_directory=str(new_path),
            existing_files=self.workflow.get_available_files()
        )
        
        # Track this directory
        if new_path not in self.used_directories:
            self.used_directories.append(new_path)
        
        console.print(f"[green]Changed to: {new_path}[/green]")
        self.display_workflow_status()
    
    def _make_directory(self, dir_name: str):
        """Create a subdirectory under the current working directory and switch to it."""
        if Path(dir_name).is_absolute():
            new_path = Path(dir_name)
        else:
            new_path = self.working_directory / dir_name
        
        new_path = new_path.resolve()
        
        if new_path.exists():
            console.print(f"[yellow]Directory already exists: {new_path}[/yellow]")
            if Confirm.ask("Switch to it?", default=True):
                self._change_directory(str(new_path))
            return
        
        new_path.mkdir(parents=True, exist_ok=True)
        console.print(f"[green]Created: {new_path}[/green]")
        
        # Automatically switch to the new directory
        self._change_directory(str(new_path))
    
    def _display_exit_info(self):
        """Display information about where data was saved on exit."""
        # Collect all directories that have DIALS output files
        dirs_with_data = []
        
        # Always check current working directory
        all_dirs = set(self.used_directories)
        all_dirs.add(self.working_directory)
        all_dirs.add(self.base_directory)
        
        dials_extensions = {".expt", ".refl", ".mtz", ".html", ".log"}
        
        for d in sorted(all_dirs):
            if not d.exists():
                continue
            dials_files = [f.name for f in d.iterdir() if f.is_file() and f.suffix in dials_extensions]
            if dials_files:
                dirs_with_data.append((d, dials_files))
        
        if dirs_with_data:
            console.print("\n[bold]📁 Your processed data is saved in:[/bold]")
            for d, files in dirs_with_data:
                n_expt = sum(1 for f in files if f.endswith(".expt"))
                n_refl = sum(1 for f in files if f.endswith(".refl"))
                n_mtz = sum(1 for f in files if f.endswith(".mtz"))
                n_log = sum(1 for f in files if f.endswith(".log"))
                
                summary_parts = []
                if n_expt: summary_parts.append(f"{n_expt} .expt")
                if n_refl: summary_parts.append(f"{n_refl} .refl")
                if n_mtz: summary_parts.append(f"{n_mtz} .mtz")
                if n_log: summary_parts.append(f"{n_log} .log")
                
                summary = ", ".join(summary_parts)
                console.print(f"  [cyan]{d}[/cyan]")
                console.print(f"    [dim]{summary}[/dim]")
            console.print()
    
    def _reset_working_directory(self):
        """Remove DIALS output files from the working directory and start fresh."""
        # Define file patterns that are DIALS output (safe to remove)
        dials_output_extensions = {".expt", ".refl", ".mtz", ".html", ".log", ".json"}
        dials_output_prefixes = {"bravais_setting_", "dials.", "reindexed", "indexed",
                                 "refined", "integrated", "symmetrized", "scaled",
                                 "imported", "strong"}
        # Also match the workflow state file
        extra_files = {".dials_workflow.json"}
        
        # Collect files to remove
        files_to_remove = []
        for f in self.working_directory.iterdir():
            if not f.is_file():
                continue
            name = f.name
            suffix = f.suffix.lower()
            
            # Match by extension
            if suffix in dials_output_extensions:
                files_to_remove.append(f)
            # Match by known prefix
            elif any(name.startswith(prefix) for prefix in dials_output_prefixes):
                files_to_remove.append(f)
            # Match extra files
            elif name in extra_files:
                files_to_remove.append(f)
        
        if not files_to_remove:
            console.print("[yellow]No DIALS output files found in the working directory.[/yellow]")
            return
        
        # Show what will be removed
        console.print(f"\n[bold yellow]⚠  The following {len(files_to_remove)} file(s) will be removed from:[/bold yellow]")
        console.print(f"   [dim]{self.working_directory}[/dim]\n")
        
        table = Table(border_style="yellow")
        table.add_column("File", style="cyan")
        table.add_column("Size", style="dim", justify="right")
        
        total_size = 0
        for f in sorted(files_to_remove, key=lambda x: x.name):
            size = f.stat().st_size
            total_size += size
            if size >= 1024 * 1024:
                size_str = f"{size / (1024 * 1024):.1f} MB"
            elif size >= 1024:
                size_str = f"{size / 1024:.1f} KB"
            else:
                size_str = f"{size} B"
            table.add_row(f.name, size_str)
        
        if total_size >= 1024 * 1024:
            total_str = f"{total_size / (1024 * 1024):.1f} MB"
        elif total_size >= 1024:
            total_str = f"{total_size / 1024:.1f} KB"
        else:
            total_str = f"{total_size} B"
        
        table.add_section()
        table.add_row(f"[bold]{len(files_to_remove)} files[/bold]", f"[bold]{total_str}[/bold]")
        
        console.print(table)
        
        if not Confirm.ask("\n[bold red]Delete these files and start over?[/bold red]", default=False):
            console.print("[yellow]Reset cancelled.[/yellow]")
            return
        
        # Remove files
        removed = 0
        for f in files_to_remove:
            try:
                f.unlink()
                removed += 1
            except Exception as e:
                console.print(f"[red]Failed to remove {f.name}: {e}[/red]")
        
        console.print(f"[green]✓ Removed {removed} file(s).[/green]")
        
        # Reset workflow state
        self.workflow = create_workflow_manager(str(self.working_directory))
        self.command_timings.clear()
        
        # Clear conversation history so Claude starts fresh
        self.claude.clear_history()
        self.claude.update_context(
            existing_files=self.workflow.get_available_files()
        )
        
        console.print("[green]✓ Workflow state and conversation history reset.[/green]")
        self.display_workflow_status()
    
    def _run_compare(self, args_str: str):
        """
        Run comparison of multiple DIALS processing directories.

        Flags: --labels name1,name2,...
               --output report.json
               --output-md report.md
               --output-html report.html
               --no-report   (skip running dials.report)
        """
        import shlex

        try:
            parts = shlex.split(args_str)
        except ValueError:
            parts = args_str.split()

        if not parts:
            console.print("[yellow]Usage: compare <dir1> <dir2> [dir3 ...][/yellow]")
            console.print("[dim]Options: --labels name1,name2,... --output report.json "
                          "--output-md report.md --output-html report.html[/dim]")
            return

        # Parse flags
        directories = []
        labels = None
        output_file = None
        output_md = None
        output_html = None
        generate_reports = True
        i = 0
        while i < len(parts):
            if parts[i] == "--labels" and i + 1 < len(parts):
                labels = parts[i + 1].split(",")
                i += 2
            elif parts[i] == "--output" and i + 1 < len(parts):
                output_file = parts[i + 1]
                i += 2
            elif parts[i] == "--output-md" and i + 1 < len(parts):
                output_md = parts[i + 1]
                i += 2
            elif parts[i] == "--output-html" and i + 1 < len(parts):
                output_html = parts[i + 1]
                i += 2
            elif parts[i] == "--no-report":
                generate_reports = False
                i += 1
            else:
                directories.append(parts[i])
                i += 1
        
        if len(directories) < 2:
            console.print("[yellow]Need at least 2 directories to compare.[/yellow]")
            return
        
        # Resolve directories relative to working directory or base directory
        resolved_dirs = []
        for d in directories:
            path = Path(d)
            if not path.is_absolute():
                # Try relative to current working directory first
                candidate = self.working_directory / d
                if not candidate.exists():
                    # Try relative to base directory
                    candidate = self.base_directory / d
                if not candidate.exists():
                    # Try as-is (might be relative to cwd)
                    candidate = Path(d).resolve()
                path = candidate
            else:
                path = path.resolve()
            
            if not path.exists():
                console.print(f"[red]Directory not found: {d}[/red]")
                return
            
            resolved_dirs.append(str(path))
        
        # Run comparison
        console.print(f"[dim]Comparing {len(resolved_dirs)} directories...[/dim]")
        if generate_reports:
            console.print("[dim]Running dials.report on each directory...[/dim]")

        try:
            result = compare_runs(resolved_dirs, labels, generate_reports=generate_reports)
            display_comparison(result, console)

            if output_file:
                result.save_json(output_file)
                console.print(f"[green]JSON saved:  {output_file}[/green]")
            if output_md:
                save_comparison_markdown(result, output_md)
                console.print(f"[green]MD saved:    {output_md}[/green]")
            if output_html:
                save_comparison_html(result, output_html)
                console.print(f"[green]HTML saved:  {output_html}[/green]")
        except Exception as e:
            console.print(f"[red]Comparison failed: {e}[/red]")
            logger.exception("Error in compare")


def setup_logging(level: str = "INFO", log_file: Optional[str] = None):
    """Configure logging."""
    log_level = getattr(logging, level.upper(), logging.INFO)
    
    handlers = [logging.StreamHandler()]
    if log_file:
        handlers.append(logging.FileHandler(log_file))
    
    logging.basicConfig(
        level=log_level,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        handlers=handlers
    )


def main():
    """Main entry point for the CLI."""
    parser = argparse.ArgumentParser(
        description="DIALS AI Agent - Natural language interface for DIALS"
    )
    parser.add_argument(
        "-d", "--directory",
        default=None,
        help="Working directory for DIALS output (overrides WORKING_DIRECTORY in .env)"
    )
    parser.add_argument(
        "-e", "--env-file",
        default=None,
        help="Path to .env file with configuration"
    )
    parser.add_argument(
        "-v", "--verbose",
        action="store_true",
        help="Enable verbose logging"
    )
    parser.add_argument(
        "--log-file",
        help="Log file path"
    )
    parser.add_argument(
        "--check-dials",
        action="store_true",
        help="Check DIALS availability and exit"
    )
    parser.add_argument(
        "--auto",
        action="store_true",
        help=(
            "Run through the entire workflow automatically without user confirmation. "
            "If DATA_DIRECTORY has multiple dataset subdirectories, each is processed "
            "in turn into its own output subdirectory, unless --auto-message names one."
        )
    )
    parser.add_argument(
        "--auto-message",
        default=None,
        help="Initial message for auto mode (default: 'Process my data through the complete workflow')"
    )
    parser.add_argument(
        "--compare",
        nargs="+",
        metavar="DIR",
        help="Compare results from multiple DIALS processing directories and exit"
    )
    parser.add_argument(
        "--compare-labels",
        default=None,
        help="Comma-separated labels for compared runs (e.g., 'agent,human,v2')"
    )
    parser.add_argument(
        "--compare-output",
        default=None,
        metavar="FILE",
        help="Save comparison to a JSON file"
    )
    parser.add_argument(
        "--compare-output-md",
        default=None,
        metavar="FILE",
        help="Save comparison to a Markdown file"
    )
    parser.add_argument(
        "--compare-output-html",
        default=None,
        metavar="FILE",
        help="Save comparison to a self-contained HTML file"
    )
    parser.add_argument(
        "--no-report",
        action="store_true",
        default=False,
        help="Skip running dials.report when comparing directories"
    )
    
    args = parser.parse_args()
    
    # Setup logging
    log_level = "DEBUG" if args.verbose else "INFO"
    setup_logging(log_level, args.log_file)
    
    # Find and load .env file
    # Priority: CLI arg > ./dials_agent/.env > ./.env > package directory .env
    env_file = args.env_file
    if env_file is None:
        # Search for .env in common locations
        candidates = [
            Path(".env"),
            Path("dials_agent/.env"),
            Path(__file__).parent / ".env",
        ]
        for candidate in candidates:
            if candidate.exists():
                env_file = str(candidate)
                break
    
    if env_file and Path(env_file).exists():
        configure_from_env_file(env_file)
    
    settings = get_settings()
    
    # Check API key
    if not settings.validate_api_key():
        provider_name = settings.get_provider_display_name()
        console.print(f"[red]Error: No API key configured for {provider_name}.[/red]")
        console.print("Set the appropriate API key in your .env file.")
        console.print("See .env.example for configuration options.")
        console.print(f"[dim]Searched for .env in: {env_file or 'default locations'}[/dim]")
        sys.exit(1)
    
    # Determine working directory: CLI arg > .env setting > current directory
    working_dir = args.directory or settings.working_directory or "."
    
    # Compare mode — standalone, no API key needed
    if args.compare:
        if len(args.compare) < 2:
            console.print("[red]Need at least 2 directories to compare.[/red]")
            sys.exit(1)
        
        labels = args.compare_labels.split(",") if args.compare_labels else None
        
        # Resolve directories
        resolved = []
        for d in args.compare:
            p = Path(d).resolve()
            if not p.exists():
                console.print(f"[red]Directory not found: {d}[/red]")
                sys.exit(1)
            resolved.append(str(p))
        
        if not args.no_report:
            console.print("[dim]Running dials.report on each directory...[/dim]")
        try:
            result = compare_runs(resolved, labels, generate_reports=not args.no_report)
            display_comparison(result, console)

            if args.compare_output:
                result.save_json(args.compare_output)
                console.print(f"[green]JSON saved:  {args.compare_output}[/green]")
            if args.compare_output_md:
                save_comparison_markdown(result, args.compare_output_md)
                console.print(f"[green]MD saved:    {args.compare_output_md}[/green]")
            if args.compare_output_html:
                save_comparison_html(result, args.compare_output_html)
                console.print(f"[green]HTML saved:  {args.compare_output_html}[/green]")

            sys.exit(0)
        except Exception as e:
            console.print(f"[red]Comparison failed: {e}[/red]")
            logger.exception("Comparison error")
            sys.exit(1)
    
    # Check DIALS only mode
    if args.check_dials:
        executor = create_executor(working_dir)
        available, version = executor.check_dials_available()
        if available:
            console.print(f"[green]DIALS available: {version}[/green]")
            sys.exit(0)
        else:
            console.print(f"[red]DIALS not available: {version}[/red]")
            sys.exit(1)
    
    # Show configuration summary
    console.print(f"[dim]Working directory: {Path(working_dir).absolute()}[/dim]")
    if settings.data_directory:
        console.print(f"[dim]Data directory: {settings.data_directory}[/dim]")
    if settings.dials_path:
        console.print(f"[dim]DIALS path: {settings.dials_path}[/dim]")
    console.print(f"[dim]LLM provider: {settings.get_provider_display_name()} ({settings.get_resolved_model()})[/dim]")
    
    # Create and run agent
    try:
        agent = DIALSAgent(
            working_directory=working_dir,
            settings=settings,
            auto_mode=args.auto
        )
        if args.auto:
            initial_msg = args.auto_message or "Process my data through the complete workflow with default settings"
            agent.run_auto(initial_message=initial_msg)
        else:
            agent.run_interactive()
    except ValueError as e:
        console.print(f"[red]Configuration error: {e}[/red]")
        sys.exit(1)
    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")
        logger.exception("Fatal error")
        sys.exit(1)


if __name__ == "__main__":
    main()
