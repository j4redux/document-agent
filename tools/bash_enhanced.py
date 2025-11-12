"""Enhanced bash tool with session persistence and streaming output."""

import asyncio
import os
import signal
import subprocess
import sys
import tempfile
import time
from pathlib import Path
from typing import Dict, Optional, List, Tuple

from tools.base import Tool


class BashEnhancedTool(Tool):
    """Enhanced bash tool with session persistence and better features."""

    def __init__(self):
        super().__init__(
            name="bash",
            description="""
            Execute bash commands with session persistence and streaming output.
            
            Features:
            - Session persistence: Environment variables and directory changes persist between calls
            - Streaming output: See output in real-time for long-running commands
            - Command history: Track all executed commands
            - Better error handling and timeout management
            
            Usage:
            - Basic command: bash(command="ls -la")
            - With timeout: bash(command="sleep 10", timeout=5)
            - Change directory: bash(command="cd /tmp && pwd")  # persists
            - Set env var: bash(command="export MY_VAR=123 && echo $MY_VAR")  # persists
            - Stream output: bash(command="for i in {1..5}; do echo $i; sleep 1; done", stream=True)
            
            Session management:
            - reset_session: Clear history and reset to initial state
            - get_history: View command history
            """,
            input_schema={
                "type": "object",
                "properties": {
                    "command": {
                        "type": "string",
                        "description": "Bash command to execute",
                    },
                    "timeout": {
                        "type": "integer",
                        "description": "Timeout in seconds (default: 30)",
                    },
                    "stream": {
                        "type": "boolean",
                        "description": "Stream output in real-time (default: False)",
                    },
                    "reset_session": {
                        "type": "boolean",
                        "description": "Reset the session before executing (default: False)",
                    },
                    "get_history": {
                        "type": "boolean",
                        "description": "Return command history instead of executing (default: False)",
                    },
                },
                "required": [],
            },
        )
        
        # Session state
        self._session_env: Dict[str, str] = os.environ.copy()
        self._session_cwd: str = os.getcwd()
        self._command_history: List[Tuple[str, str, int]] = []  # (command, output, exit_code)
        self._session_file = None
        self._init_session()

    def _init_session(self):
        """Initialize session with a persistent bash script."""
        # Create a temp file for session state
        self._session_file = tempfile.NamedTemporaryFile(
            mode='w', suffix='.sh', delete=False, prefix='bash_session_'
        )
        
        # Write initial session setup
        self._session_file.write(f"""#!/bin/bash
# Bash session state file
cd "{self._session_cwd}"
""")
        self._session_file.flush()

    async def execute(
        self,
        command: Optional[str] = None,
        timeout: int = 30,
        stream: bool = False,
        reset_session: bool = False,
        get_history: bool = False,
    ) -> str:
        """Execute bash command with enhanced features."""
        if get_history:
            return self._get_history()
        
        if reset_session:
            self._reset_session()
            if not command:
                return "Session reset successfully"
        
        if not command:
            return "Error: No command provided"
        
        if stream:
            return await self._execute_streaming(command, timeout)
        else:
            return await self._execute_normal(command, timeout)

    async def _execute_normal(self, command: str, timeout: int) -> str:
        """Execute command and return complete output."""
        try:
            # Prepare command with session state
            full_command = self._prepare_command(command)
            
            # Execute command
            process = await asyncio.create_subprocess_shell(
                full_command,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                env=self._session_env,
                cwd=self._session_cwd,
            )
            
            # Wait for completion with timeout
            try:
                stdout, stderr = await asyncio.wait_for(
                    process.communicate(), timeout=timeout
                )
                exit_code = process.returncode
            except asyncio.TimeoutError:
                # Kill process on timeout
                process.kill()
                await process.wait()
                return f"Error: Command timed out after {timeout} seconds"
            
            # Decode output
            stdout_text = stdout.decode('utf-8', errors='replace') if stdout else ""
            stderr_text = stderr.decode('utf-8', errors='replace') if stderr else ""
            
            # Update session state
            self._update_session_state(command)
            
            # Prepare output
            output_parts = []
            if stdout_text:
                output_parts.append(stdout_text.rstrip())
            if stderr_text:
                output_parts.append(f"STDERR:\n{stderr_text.rstrip()}")
            
            output = "\n".join(output_parts) if output_parts else "(no output)"
            
            # Add to history
            self._command_history.append((command, output[:500], exit_code))
            
            # Add exit code if non-zero
            if exit_code != 0:
                output += f"\n\nExit code: {exit_code}"
            
            return output
            
        except Exception as e:
            return f"Error executing command: {str(e)}"

    async def _execute_streaming(self, command: str, timeout: int) -> str:
        """Execute command with streaming output."""
        try:
            # Prepare command with session state
            full_command = self._prepare_command(command)
            
            # Execute command
            process = await asyncio.create_subprocess_shell(
                full_command,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                env=self._session_env,
                cwd=self._session_cwd,
            )
            
            output_lines = []
            start_time = time.time()
            
            # Stream output
            while True:
                # Check timeout
                if time.time() - start_time > timeout:
                    process.kill()
                    await process.wait()
                    output_lines.append(f"\n[Command timed out after {timeout} seconds]")
                    break
                
                # Try to read stdout
                try:
                    line = await asyncio.wait_for(
                        process.stdout.readline(), timeout=0.1
                    )
                    if line:
                        line_text = line.decode('utf-8', errors='replace').rstrip()
                        output_lines.append(line_text)
                        # Print for streaming effect (when running interactively)
                        print(f"[STREAM] {line_text}", file=sys.stderr)
                except asyncio.TimeoutError:
                    pass
                
                # Check if process has finished
                if process.returncode is not None:
                    # Read any remaining output
                    remaining_stdout = await process.stdout.read()
                    remaining_stderr = await process.stderr.read()
                    
                    if remaining_stdout:
                        output_lines.extend(
                            remaining_stdout.decode('utf-8', errors='replace').rstrip().split('\n')
                        )
                    if remaining_stderr:
                        stderr_text = remaining_stderr.decode('utf-8', errors='replace').rstrip()
                        output_lines.append(f"\nSTDERR:\n{stderr_text}")
                    
                    break
            
            exit_code = process.returncode
            
            # Update session state
            self._update_session_state(command)
            
            # Prepare output
            output = "\n".join(output_lines) if output_lines else "(no output)"
            
            # Add to history
            self._command_history.append((command, output[:500], exit_code))
            
            # Add exit code if non-zero
            if exit_code != 0:
                output += f"\n\nExit code: {exit_code}"
            
            return output
            
        except Exception as e:
            return f"Error executing command: {str(e)}"

    def _prepare_command(self, command: str) -> str:
        """Prepare command with session state."""
        # Source the session file and execute command
        return f'source "{self._session_file.name}" && {command}'

    def _update_session_state(self, command: str):
        """Update session state based on command."""
        # Check for cd commands
        if command.strip().startswith('cd '):
            # Update working directory
            new_dir = command.strip()[3:].strip()
            if new_dir:
                try:
                    # Resolve path
                    if new_dir.startswith('~'):
                        new_dir = os.path.expanduser(new_dir)
                    elif not os.path.isabs(new_dir):
                        new_dir = os.path.join(self._session_cwd, new_dir)
                    
                    # Normalize path
                    new_dir = os.path.normpath(new_dir)
                    
                    if os.path.isdir(new_dir):
                        self._session_cwd = new_dir
                        # Update session file
                        with open(self._session_file.name, 'a') as f:
                            f.write(f'\ncd "{new_dir}"\n')
                except:
                    pass
        
        # Check for export commands
        if 'export ' in command:
            # Simple export parsing (not comprehensive)
            parts = command.split(';')
            for part in parts:
                part = part.strip()
                if part.startswith('export '):
                    var_assignment = part[7:].strip()
                    if '=' in var_assignment:
                        var_name, var_value = var_assignment.split('=', 1)
                        var_name = var_name.strip()
                        var_value = var_value.strip().strip('"').strip("'")
                        self._session_env[var_name] = var_value
                        # Update session file
                        with open(self._session_file.name, 'a') as f:
                            f.write(f'\nexport {var_name}="{var_value}"\n')

    def _reset_session(self):
        """Reset the session to initial state."""
        self._session_env = os.environ.copy()
        self._session_cwd = os.getcwd()
        self._command_history = []
        
        # Recreate session file
        if self._session_file:
            try:
                os.unlink(self._session_file.name)
            except:
                pass
        self._init_session()

    def _get_history(self) -> str:
        """Get command history."""
        if not self._command_history:
            return "No commands executed yet"
        
        result = [
            "Command History",
            "=" * 60,
            f"Session working directory: {self._session_cwd}",
            f"Total commands: {len(self._command_history)}",
            "",
        ]
        
        for i, (cmd, output, exit_code) in enumerate(self._command_history, 1):
            result.append(f"{i}. Command: {cmd}")
            result.append(f"   Exit code: {exit_code}")
            if output:
                # Show first few lines of output
                output_lines = output.split('\n')[:3]
                for line in output_lines:
                    result.append(f"   > {line}")
                if len(output.split('\n')) > 3:
                    result.append("   > ... (output truncated)")
            result.append("")
        
        return "\n".join(result)

    def __del__(self):
        """Cleanup session file on deletion."""
        if hasattr(self, '_session_file') and self._session_file:
            try:
                os.unlink(self._session_file.name)
            except:
                pass