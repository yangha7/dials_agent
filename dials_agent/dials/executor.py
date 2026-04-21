"""
DIALS command executor.

This module handles the execution of DIALS commands as subprocesses,
capturing output and handling timeouts.
"""

import asyncio
import logging
import os
import shlex
import subprocess
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable, Optional

from ..config import Settings, get_settings
from .commands import validate_command

logger = logging.getLogger(__name__)

# GUI commands that should be launched in background (non-blocking)
GUI_COMMANDS = {
    "dials.image_viewer",
    "dials.reciprocal_lattice_viewer",
    "dials.rlv",  # alias for reciprocal_lattice_viewer
}


def is_gui_command(command_str: str) -> bool:
    """Check if a command is a GUI command that should run in background."""
    parts = command_str.split()
    if parts:
        cmd = parts[0]
        return cmd in GUI_COMMANDS
    return False


@dataclass
class CommandResult:
    """Result of a command execution."""
    command: str
    return_code: int
    stdout: str
    stderr: str
    duration: float  # seconds
    success: bool
    working_directory: str
    output_files: list[str] = field(default_factory=list)
    error_message: Optional[str] = None


class CommandExecutor:
    """
    Executes DIALS commands as subprocesses.
    
    Handles command validation, execution, output capture, and timeout management.
    """
    
    def __init__(
        self,
        settings: Optional[Settings] = None,
        working_directory: Optional[str] = None
    ):
        """
        Initialize the command executor.
        
        Args:
            settings: Application settings
            working_directory: Directory to run commands in
        """
        self.settings = settings or get_settings()
        self.working_directory = working_directory or self.settings.working_directory
        self._ensure_working_directory()
    
    def _ensure_working_directory(self):
        """Ensure the working directory exists."""
        path = Path(self.working_directory)
        if not path.exists():
            path.mkdir(parents=True, exist_ok=True)
            logger.info(f"Created working directory: {self.working_directory}")
    
    def _get_command_path(self, command: str) -> str:
        """
        Get the full path to a DIALS command.
        
        Args:
            command: Command name (e.g., 'dials.import')
            
        Returns:
            Full path to command or just the command name if using system PATH
        """
        if self.settings.dials_path:
            return str(Path(self.settings.dials_path) / command)
        return command
    
    def _prepare_command(self, command_str: str) -> list[str]:
        """
        Prepare a command string for execution.
        
        Args:
            command_str: The command string
            
        Returns:
            List of command parts for subprocess
        """
        parts = shlex.split(command_str)
        if parts:
            # Replace the command name with full path if needed
            parts[0] = self._get_command_path(parts[0])
        return parts
    
    def _get_files_before(self) -> set[str]:
        """Get set of files in working directory before command execution."""
        path = Path(self.working_directory)
        return set(f.name for f in path.iterdir() if f.is_file())
    
    def _get_new_files(self, files_before: set[str]) -> list[str]:
        """Get list of new files created after command execution."""
        path = Path(self.working_directory)
        files_after = set(f.name for f in path.iterdir() if f.is_file())
        return sorted(files_after - files_before)
    
    def launch_gui(self, command_str: str) -> CommandResult:
        """
        Launch a GUI command in the background (non-blocking).
        
        GUI commands like dials.image_viewer open a window that stays open
        until the user closes it. This method launches them without blocking
        the CLI.
        
        Args:
            command_str: The GUI command to launch
            
        Returns:
            CommandResult indicating the launch status
        """
        # Validate command
        is_valid, error_msg = validate_command(command_str)
        if not is_valid:
            return CommandResult(
                command=command_str,
                return_code=-1,
                stdout="",
                stderr=error_msg,
                duration=0.0,
                success=False,
                working_directory=self.working_directory,
                error_message=error_msg
            )
        
        cmd_parts = self._prepare_command(command_str)
        
        logger.info(f"Launching GUI: {command_str}")
        
        try:
            # Launch in background - don't wait for it to complete
            # Use start_new_session=True on Unix to detach from terminal
            # Capture stderr to detect startup errors
            process = subprocess.Popen(
                cmd_parts,
                cwd=self.working_directory,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.PIPE,
                start_new_session=True  # Detach from parent process
            )
            
            # Give it more time to start and check if it failed immediately
            # Some GUI apps (especially reciprocal_lattice_viewer with OpenGL)
            # take longer to initialize
            time.sleep(2.0)
            
            # Check if process is still running (poll returns None if running)
            poll_result = process.poll()
            if poll_result is not None and poll_result != 0:
                stderr_output = ""
                try:
                    stderr_output = process.stderr.read().decode('utf-8', errors='replace')[:500]
                except Exception:
                    pass
                
                error_detail = f"GUI failed to start (exit code {poll_result})"
                if stderr_output:
                    error_detail += f": {stderr_output}"
                
                return CommandResult(
                    command=command_str,
                    return_code=poll_result,
                    stdout="",
                    stderr=error_detail,
                    duration=2.0,
                    success=False,
                    working_directory=self.working_directory,
                    error_message=error_detail
                )
            
            # Detach stderr now that we know it started OK
            try:
                process.stderr.close()
            except Exception:
                pass
            
            return CommandResult(
                command=command_str,
                return_code=0,
                stdout=f"GUI launched successfully (PID: {process.pid}). Close the window when done.",
                stderr="",
                duration=2.0,
                success=True,
                working_directory=self.working_directory
            )
            
        except FileNotFoundError as e:
            error_msg = f"Command not found: {cmd_parts[0]}. Is DIALS installed and in PATH?"
            logger.error(error_msg)
            
            return CommandResult(
                command=command_str,
                return_code=-1,
                stdout="",
                stderr=str(e),
                duration=0.0,
                success=False,
                working_directory=self.working_directory,
                error_message=error_msg
            )
            
        except Exception as e:
            error_msg = f"Failed to launch GUI: {str(e)}"
            logger.error(error_msg)
            
            return CommandResult(
                command=command_str,
                return_code=-1,
                stdout="",
                stderr=str(e),
                duration=0.0,
                success=False,
                working_directory=self.working_directory,
                error_message=error_msg
            )
    
    def execute(
        self,
        command_str: str,
        timeout: Optional[int] = None,
        capture_output: bool = True,
        progress_callback: Optional[Callable[[str], None]] = None
    ) -> CommandResult:
        """
        Execute a DIALS command synchronously.
        
        For GUI commands (dials.image_viewer, dials.reciprocal_lattice_viewer),
        this will launch them in the background and return immediately.
        
        Args:
            command_str: The command to execute
            timeout: Timeout in seconds (uses settings default if not provided)
            capture_output: Whether to capture stdout/stderr
            progress_callback: Optional callback for progress updates
            
        Returns:
            CommandResult with execution details
        """
        # Check if this is a GUI command - launch in background
        if is_gui_command(command_str):
            return self.launch_gui(command_str)
        
        # Validate command
        is_valid, error_msg = validate_command(command_str)
        if not is_valid:
            return CommandResult(
                command=command_str,
                return_code=-1,
                stdout="",
                stderr=error_msg,
                duration=0.0,
                success=False,
                working_directory=self.working_directory,
                error_message=error_msg
            )
        
        if error_msg:  # Warning
            logger.warning(error_msg)
        
        # Prepare command
        cmd_parts = self._prepare_command(command_str)
        timeout = timeout or self.settings.command_timeout
        
        # Track files before execution
        files_before = self._get_files_before()
        
        logger.info(f"Executing: {command_str}")
        logger.debug(f"Working directory: {self.working_directory}")
        
        start_time = time.time()
        
        try:
            if capture_output:
                result = subprocess.run(
                    cmd_parts,
                    cwd=self.working_directory,
                    capture_output=True,
                    text=True,
                    timeout=timeout
                )
                stdout = result.stdout
                stderr = result.stderr
                return_code = result.returncode
            else:
                # Stream output in real-time
                process = subprocess.Popen(
                    cmd_parts,
                    cwd=self.working_directory,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,
                    text=True,
                    bufsize=1
                )
                
                stdout_lines = []
                for line in iter(process.stdout.readline, ''):
                    stdout_lines.append(line)
                    if progress_callback:
                        progress_callback(line.rstrip())
                
                process.wait(timeout=timeout)
                stdout = ''.join(stdout_lines)
                stderr = ""
                return_code = process.returncode
            
            duration = time.time() - start_time
            success = return_code == 0
            
            # Get new files
            new_files = self._get_new_files(files_before)
            
            if success:
                logger.info(f"Command completed successfully in {duration:.1f}s")
                if new_files:
                    logger.info(f"Created files: {', '.join(new_files)}")
            else:
                logger.warning(f"Command failed with return code {return_code}")
            
            return CommandResult(
                command=command_str,
                return_code=return_code,
                stdout=stdout,
                stderr=stderr,
                duration=duration,
                success=success,
                working_directory=self.working_directory,
                output_files=new_files
            )
            
        except subprocess.TimeoutExpired:
            duration = time.time() - start_time
            error_msg = f"Command timed out after {timeout} seconds"
            logger.error(error_msg)
            
            return CommandResult(
                command=command_str,
                return_code=-1,
                stdout="",
                stderr=error_msg,
                duration=duration,
                success=False,
                working_directory=self.working_directory,
                error_message=error_msg
            )
            
        except FileNotFoundError as e:
            duration = time.time() - start_time
            error_msg = f"Command not found: {cmd_parts[0]}. Is DIALS installed and in PATH?"
            logger.error(error_msg)
            
            return CommandResult(
                command=command_str,
                return_code=-1,
                stdout="",
                stderr=str(e),
                duration=duration,
                success=False,
                working_directory=self.working_directory,
                error_message=error_msg
            )
            
        except Exception as e:
            duration = time.time() - start_time
            error_msg = f"Execution error: {str(e)}"
            logger.error(error_msg)
            
            return CommandResult(
                command=command_str,
                return_code=-1,
                stdout="",
                stderr=str(e),
                duration=duration,
                success=False,
                working_directory=self.working_directory,
                error_message=error_msg
            )
    
    async def execute_async(
        self,
        command_str: str,
        timeout: Optional[int] = None,
        progress_callback: Optional[Callable[[str], None]] = None
    ) -> CommandResult:
        """
        Execute a DIALS command asynchronously.
        
        Args:
            command_str: The command to execute
            timeout: Timeout in seconds
            progress_callback: Optional callback for progress updates
            
        Returns:
            CommandResult with execution details
        """
        # Validate command
        is_valid, error_msg = validate_command(command_str)
        if not is_valid:
            return CommandResult(
                command=command_str,
                return_code=-1,
                stdout="",
                stderr=error_msg,
                duration=0.0,
                success=False,
                working_directory=self.working_directory,
                error_message=error_msg
            )
        
        # Prepare command
        cmd_parts = self._prepare_command(command_str)
        timeout = timeout or self.settings.command_timeout
        
        # Track files before execution
        files_before = self._get_files_before()
        
        logger.info(f"Executing async: {command_str}")
        
        start_time = time.time()
        
        try:
            process = await asyncio.create_subprocess_exec(
                *cmd_parts,
                cwd=self.working_directory,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            stdout_data = []
            stderr_data = []
            
            async def read_stream(stream, data_list, callback=None):
                while True:
                    line = await stream.readline()
                    if not line:
                        break
                    decoded = line.decode()
                    data_list.append(decoded)
                    if callback:
                        callback(decoded.rstrip())
            
            # Read stdout and stderr concurrently
            await asyncio.gather(
                read_stream(process.stdout, stdout_data, progress_callback),
                read_stream(process.stderr, stderr_data)
            )
            
            # Wait for process with timeout
            try:
                await asyncio.wait_for(process.wait(), timeout=timeout)
            except asyncio.TimeoutError:
                process.kill()
                await process.wait()
                raise subprocess.TimeoutExpired(cmd_parts, timeout)
            
            duration = time.time() - start_time
            return_code = process.returncode
            success = return_code == 0
            
            # Get new files
            new_files = self._get_new_files(files_before)
            
            return CommandResult(
                command=command_str,
                return_code=return_code,
                stdout=''.join(stdout_data),
                stderr=''.join(stderr_data),
                duration=duration,
                success=success,
                working_directory=self.working_directory,
                output_files=new_files
            )
            
        except subprocess.TimeoutExpired:
            duration = time.time() - start_time
            error_msg = f"Command timed out after {timeout} seconds"
            
            return CommandResult(
                command=command_str,
                return_code=-1,
                stdout="",
                stderr=error_msg,
                duration=duration,
                success=False,
                working_directory=self.working_directory,
                error_message=error_msg
            )
            
        except Exception as e:
            duration = time.time() - start_time
            error_msg = f"Execution error: {str(e)}"
            
            return CommandResult(
                command=command_str,
                return_code=-1,
                stdout="",
                stderr=str(e),
                duration=duration,
                success=False,
                working_directory=self.working_directory,
                error_message=error_msg
            )
    
    def check_dials_available(self) -> tuple[bool, str]:
        """
        Check if DIALS is available and working.
        
        Returns:
            Tuple of (is_available, version_or_error)
        """
        try:
            result = subprocess.run(
                [self._get_command_path("dials.version")],
                capture_output=True,
                text=True,
                timeout=10
            )
            
            if result.returncode == 0:
                version = result.stdout.strip()
                return True, version
            else:
                return False, result.stderr or "Unknown error"
                
        except FileNotFoundError:
            return False, "DIALS not found. Please ensure DIALS is installed and in PATH."
        except subprocess.TimeoutExpired:
            return False, "Timeout checking DIALS version"
        except Exception as e:
            return False, str(e)
    
    def list_dials_files(self) -> dict[str, list[str]]:
        """
        List DIALS-related files in the working directory.
        
        Returns:
            Dictionary with file categories
        """
        path = Path(self.working_directory)
        
        files = {
            "experiments": [],
            "reflections": [],
            "mtz": [],
            "html": [],
            "json": [],
            "log": [],
            "other": []
        }
        
        for f in path.iterdir():
            if not f.is_file():
                continue
            
            name = f.name
            suffix = f.suffix.lower()
            
            if suffix == ".expt":
                files["experiments"].append(name)
            elif suffix == ".refl":
                files["reflections"].append(name)
            elif suffix == ".mtz":
                files["mtz"].append(name)
            elif suffix == ".html":
                files["html"].append(name)
            elif suffix == ".json":
                files["json"].append(name)
            elif suffix == ".log":
                files["log"].append(name)
            elif name.endswith(".expt") or name.endswith(".refl"):
                # Handle files without standard extensions
                if ".expt" in name:
                    files["experiments"].append(name)
                elif ".refl" in name:
                    files["reflections"].append(name)
        
        return files
    
    def get_working_directory_info(self) -> dict:
        """
        Get information about the working directory.
        
        Returns:
            Dictionary with directory information
        """
        path = Path(self.working_directory)
        
        return {
            "path": str(path.absolute()),
            "exists": path.exists(),
            "files": self.list_dials_files() if path.exists() else {},
            "total_files": len(list(path.iterdir())) if path.exists() else 0
        }


def create_executor(
    working_directory: Optional[str] = None
) -> CommandExecutor:
    """
    Create a new command executor instance.
    
    Args:
        working_directory: Directory to run commands in
        
    Returns:
        Configured CommandExecutor instance
    """
    return CommandExecutor(working_directory=working_directory)
