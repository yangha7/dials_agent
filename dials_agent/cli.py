"""
CLI interface for the DIALS AI Agent.

This module provides an interactive command-line interface for users
to interact with the DIALS AI agent using natural language.
"""

import argparse
import logging
import os
import sys
import time
from pathlib import Path
from typing import Optional

from rich.console import Console
from rich.markdown import Markdown
from rich.panel import Panel
from rich.prompt import Confirm, Prompt
from rich.table import Table
from rich.text import Text

from .config import Settings, get_settings, configure_from_env_file
from .core.claude_client import ClaudeClient, ToolCall, create_client
from .core.tools import determine_workflow_stage
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
            existing_files=self.workflow.get_available_files()
        )
        
        # Pending command for approval
        self.pending_command: Optional[dict] = None
        
        # Timing tracker for all executed commands
        self.command_timings: list[dict] = []
        
        # Active status spinner (set during "Thinking..." to allow tool handlers to pause it)
        self._active_status = None
    
    def _handle_tool_call(self, tool_call: ToolCall) -> dict:
        """
        Handle a tool call from Claude.
        
        Args:
            tool_call: The tool call to handle
            
        Returns:
            Result dictionary
        """
        if tool_call.name == "suggest_dials_command":
            # Store the command for user approval
            self.pending_command = tool_call.input
            return {
                "status": "pending_approval",
                "command": tool_call.input.get("command"),
                "message": "Command suggested, awaiting user approval"
            }
        
        elif tool_call.name == "check_workflow_status":
            self.workflow.refresh()
            return self.workflow.get_workflow_context()
        
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
        
        elif tool_call.name == "suggest_troubleshooting":
            # Claude will provide troubleshooting in its response
            return {
                "status": "troubleshooting_requested",
                "problem": tool_call.input.get("problem")
            }
        
        elif tool_call.name == "list_available_commands":
            from .dials.commands import get_commands_by_category, CommandCategory
            
            category = tool_call.input.get("category", "all")
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
                "current_stage": self.workflow.get_stage_name()
            }
        
        elif tool_call.name == "read_file":
            filename = tool_call.input.get("filename", "")
            tail_lines = tool_call.input.get("tail_lines")
            max_chars = tool_call.input.get("max_chars", 50000)
            
            filepath = self.working_directory / filename
            if not filepath.exists():
                return {
                    "error": f"File not found: {filename}",
                    "available_files": [
                        f.name for f in self.working_directory.iterdir()
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
                
                console.print(f"[dim]📄 Reading {filename} ({len(content)} chars)[/dim]")
                return {
                    "filename": filename,
                    "content": content,
                    "size_bytes": filepath.stat().st_size
                }
            except Exception as e:
                return {"error": f"Error reading {filename}: {str(e)}"}
        
        elif tool_call.name == "open_file":
            import subprocess as sp
            
            filename = tool_call.input.get("filename", "")
            filepath = self.working_directory / filename
            
            if not filepath.exists():
                return {"error": f"File not found: {filename}"}
            
            suffix = filepath.suffix.lower()
            
            if suffix == ".html":
                # Open HTML files in a web browser (background, non-blocking)
                try:
                    # Try firefox first (common on Linux servers), then xdg-open
                    for browser_cmd in ["firefox", "xdg-open", "open"]:
                        try:
                            sp.Popen(
                                [browser_cmd, str(filepath)],
                                stdout=sp.DEVNULL,
                                stderr=sp.DEVNULL,
                                start_new_session=True
                            )
                            console.print(f"[green]🌐 Opened {filename} in browser[/green]")
                            return {
                                "status": "opened",
                                "filename": filename,
                                "viewer": browser_cmd
                            }
                        except FileNotFoundError:
                            continue
                    
                    return {"error": f"No web browser found to open {filename}. Try: firefox {filepath}"}
                except Exception as e:
                    return {"error": f"Error opening {filename}: {str(e)}"}
            
            elif suffix in {".expt", ".refl"}:
                # Suggest appropriate DIALS viewer
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
        
        elif tool_call.name == "run_shell_command":
            import subprocess as sp
            
            command = tool_call.input.get("command", "")
            explanation = tool_call.input.get("explanation", "")
            
            if not command:
                return {"error": "No command provided"}
            
            # Check for destructive commands that need confirmation
            destructive_keywords = ["rm ", "rm\t", "rmdir", "mv ", "mv\t", "> ", ">> "]
            is_destructive = any(kw in command for kw in destructive_keywords) or command.startswith("rm ")
            
            if is_destructive:
                # Stop the spinner so the confirmation prompt is clearly visible
                if self._active_status:
                    self._active_status.stop()
                
                console.print(f"\n[bold yellow]⚠  Shell command (destructive):[/bold yellow] {command}")
                if explanation:
                    console.print(f"[dim]{explanation}[/dim]")
                if not Confirm.ask("[bold red]Allow this command?[/bold red]", default=False):
                    # Restart spinner
                    if self._active_status:
                        self._active_status.start()
                    return {"status": "cancelled", "message": "User declined to run destructive command"}
                
                # Restart spinner after confirmation
                if self._active_status:
                    self._active_status.start()
            else:
                console.print(f"\n[dim]$ {command}[/dim]")
            
            try:
                result = sp.run(
                    command,
                    shell=True,
                    cwd=str(self.working_directory),
                    capture_output=True,
                    text=True,
                    timeout=60
                )
                
                output = result.stdout
                if result.stderr:
                    output += f"\n[stderr]: {result.stderr}"
                
                # Truncate very long output
                if len(output) > 10000:
                    output = output[:5000] + "\n\n[... output truncated ...]\n\n" + output[-5000:]
                
                # Refresh workflow state after shell commands (files may have changed)
                self.workflow.refresh()
                self.claude.update_context(
                    existing_files=self.workflow.get_available_files()
                )
                
                return {
                    "status": "success" if result.returncode == 0 else "error",
                    "return_code": result.returncode,
                    "output": output,
                    "command": command
                }
            except sp.TimeoutExpired:
                return {"error": f"Command timed out after 60 seconds: {command}"}
            except Exception as e:
                return {"error": f"Failed to run command: {str(e)}"}
        
        else:
            return {"error": f"Unknown tool: {tool_call.name}"}
    
    def execute_command(self, command: str) -> CommandResult:
        """
        Execute a DIALS command.
        
        Args:
            command: The command to execute
            
        Returns:
            CommandResult with execution details
        """
        console.print(f"\n[bold blue]Executing:[/bold blue] {command}")
        
        with console.status("[bold green]Running command..."):
            result = self.executor.execute(command)
        
        # Record timing
        cmd_name = command.split()[0] if command else command
        self.command_timings.append({
            "command": command,
            "command_name": cmd_name,
            "duration": result.duration,
            "success": result.success,
        })
        
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
    
    def _display_timing(self, cmd_name: str, duration: float):
        """Display timing information for a command."""
        if duration >= 60:
            minutes = int(duration // 60)
            seconds = duration % 60
            time_str = f"{minutes}m {seconds:.1f}s"
        else:
            time_str = f"{duration:.1f}s"
        console.print(f"[bold magenta]⏱  {cmd_name} completed in {time_str}[/bold magenta]")
    
    def display_timing_summary(self):
        """Display a summary table of all command timings."""
        if not self.command_timings:
            console.print("[yellow]No commands executed yet.[/yellow]")
            return
        
        table = Table(title="⏱  Command Timing Summary", border_style="magenta")
        table.add_column("#", style="dim", justify="right")
        table.add_column("Command", style="cyan")
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
            
            table.add_row(str(i), entry["command"][:60], status, time_str)
        
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
        content.append(f"{command}\n\n", style="cyan")
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
        
        # Show next step suggestion if command was successful (skip in auto mode)
        if result.success and not self.auto_mode:
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
        table.add_row("Current Stage", self.workflow.get_stage_name())
        table.add_row("Progress", f"{self.workflow.get_progress_percentage():.0f}%")
        table.add_row("Experiment Files", ", ".join(self.workflow.get_experiment_files()) or "None")
        table.add_row("Reflection Files", ", ".join(self.workflow.get_reflection_files()) or "None")
        
        next_cmd = self.workflow.get_next_command()
        table.add_row("Suggested Next", next_cmd or "Workflow complete!")
        
        console.print(table)
    
    def chat(self, user_message: str) -> str:
        """
        Send a message to the agent and get a response.
        
        Args:
            user_message: The user's message
            
        Returns:
            The agent's response
        """
        # Clear any pending command
        self.pending_command = None
        
        # Send message to Claude
        response = self.claude.send_message(
            user_message,
            tool_handler=self._handle_tool_call
        )
        
        return response.message
    
    def run_auto(self, initial_message: str = None, skip_dials_check: bool = False):
        """
        Run the agent in auto mode — process the entire workflow without user interruption.
        
        The agent will ask Claude for each step, automatically approve and execute
        commands, feed results back, and continue until the workflow is complete
        or an error occurs.
        
        Args:
            initial_message: The initial instruction to send to Claude
            skip_dials_check: Skip DIALS availability check (already done in interactive mode)
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
        
        console.print(Panel.fit(
            "[bold blue]DIALS AI Agent — Auto Mode[/bold blue]\n"
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
        max_iterations = 30  # Safety limit to prevent infinite loops
        iteration = 0
        self.auto_mode = True
        
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
                        break
                    
                    # Ask Claude to continue — be very explicit
                    current_message = (
                        "AUTO MODE: You must use the suggest_dials_command tool NOW to suggest the next DIALS command. "
                        "Do not present options or ask questions. Skip GUI commands (image_viewer, reciprocal_lattice_viewer). "
                        "Just suggest the next processing command."
                    )
            
            if iteration >= max_iterations:
                console.print(f"\n[yellow]Reached maximum iterations ({max_iterations}). Stopping auto mode.[/yellow]")
        
        except KeyboardInterrupt:
            console.print("\n[yellow]Auto mode interrupted by user.[/yellow]")
        except Exception as e:
            console.print(f"\n[red]Error in auto mode: {e}[/red]")
            logger.exception("Error in auto mode")
        
        # Exit auto mode
        self.auto_mode = False
        
        # Show final timing summary
        auto_duration = time.time() - auto_start_time
        console.print()
        self.display_timing_summary()
        
        if auto_duration >= 60:
            total_minutes = int(auto_duration // 60)
            total_seconds = auto_duration % 60
            console.print(f"\n[bold]Total wall-clock time: {total_minutes}m {total_seconds:.1f}s[/bold]")
        else:
            console.print(f"\n[bold]Total wall-clock time: {auto_duration:.1f}s[/bold]")
    
    def run_interactive(self):
        """Run the interactive CLI loop."""
        console.print(Panel.fit(
            "[bold blue]DIALS AI Agent[/bold blue]\n"
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
                # Get user input
                user_input = Prompt.ask("\n[bold cyan]You[/bold cyan]")
                
                if not user_input.strip():
                    continue
                
                # Handle special commands
                lower_input = user_input.lower().strip()
                
                if lower_input in ['quit', 'exit', 'q']:
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
                
                # Detect autonomous processing requests and switch to auto mode
                auto_keywords = [
                    "automatically", "autonomous", "on your own", "without interruption",
                    "run through", "process everything", "all steps", "complete workflow",
                    "start to finish", "end to end", "no confirmation", "unattended",
                    "run all", "do everything", "full pipeline", "whole workflow",
                ]
                if any(kw in lower_input for kw in auto_keywords):
                    console.print("[bold blue]Detected autonomous processing request — entering auto mode...[/bold blue]")
                    self.run_auto(initial_message=user_input, skip_dials_check=True)
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
- **auto** - Run through the entire workflow automatically (no confirmations)
- **auto <message>** - Auto mode with custom instruction (e.g., `auto process insulin data fast version`)
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
        table.add_column("Command", style="cyan")
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
            
            table.add_row(str(i), cmd.command[:50], status, time_str)
        
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
        help="Run through the entire workflow automatically without user confirmation"
    )
    parser.add_argument(
        "--auto-message",
        default=None,
        help="Initial message for auto mode (default: 'Process my data through the complete workflow')"
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
