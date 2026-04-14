"""
CLI interface for the DIALS AI Agent.

This module provides an interactive command-line interface for users
to interact with the DIALS AI agent using natural language.
"""

import argparse
import logging
import os
import sys
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
        settings: Optional[Settings] = None
    ):
        """
        Initialize the DIALS Agent.
        
        Args:
            working_directory: Directory for DIALS processing
            settings: Application settings
        """
        self.working_directory = Path(working_directory).absolute()
        self.settings = settings or get_settings()
        
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
        
        # Parse the output
        parsed = self.parser.parse(result)
        
        # Record in workflow
        self.workflow.record_command(result, parsed.metrics)
        
        # Update Claude's context
        self.claude.update_context(
            existing_files=self.workflow.get_available_files()
        )
        
        return result
    
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
        content.append(f"Duration: {result.duration:.1f}s\n")
        
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
        
        # Show next step suggestion if command was successful
        if result.success:
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
                
                elif lower_input.startswith('cd '):
                    new_dir = user_input[3:].strip()
                    self._change_directory(new_dir)
                    continue
                
                # Send to Claude
                with console.status("[bold green]Thinking..."):
                    response = self.chat(user_input)
                
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
                            output_summary = result.stdout[:2000] if result.stdout else result.stderr[:2000]
                            with console.status("[bold green]Analyzing results..."):
                                analysis = self.chat(
                                    f"The command completed with return code {result.return_code}. "
                                    f"Here's the output:\n\n{output_summary}"
                                )
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
- **clear** - Clear conversation history
- **multi** - Enable multi-crystal mode (uses joint=false, dials.cosym)
- **single** - Enable single-crystal mode (default)
- **cd <path>** - Change working directory
- **quit** / **exit** - Exit the agent

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
        table.add_column("Duration", style="white")
        
        for i, cmd in enumerate(history[-10:], 1):  # Last 10 commands
            status = "[green]✓[/green]" if cmd.success else "[red]✗[/red]"
            table.add_row(str(i), cmd.command[:50], status, f"{cmd.duration:.1f}s")
        
        console.print(table)
    
    def _change_directory(self, new_dir: str):
        """Change the working directory."""
        new_path = Path(new_dir).expanduser().absolute()
        
        if not new_path.exists():
            console.print(f"[red]Directory does not exist: {new_path}[/red]")
            return
        
        self.working_directory = new_path
        self.workflow = create_workflow_manager(str(new_path))
        self.executor = create_executor(str(new_path))
        self.claude.update_context(
            working_directory=str(new_path),
            existing_files=self.workflow.get_available_files()
        )
        
        console.print(f"[green]Changed to: {new_path}[/green]")
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
        if settings.api_provider == "openai":
            console.print("[red]Error: OPENAI_API_KEY not configured.[/red]")
        else:
            console.print("[red]Error: ANTHROPIC_API_KEY not configured.[/red]")
        console.print("Set the environment variable or add it to .env file.")
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
    console.print(f"[dim]API provider: {settings.api_provider} ({settings.model})[/dim]")
    
    # Create and run agent
    try:
        agent = DIALSAgent(
            working_directory=working_dir,
            settings=settings
        )
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
