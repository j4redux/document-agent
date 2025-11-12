"""Git tool for version control operations."""

import subprocess
import os
from typing import Optional
from tools.base import Tool


class GitTool(Tool):
    """Git tool for version control operations."""
    
    def __init__(self):
        super().__init__(
            name="git",
            description="Execute git commands for version control operations",
            input_schema={
                "type": "object",
                "properties": {
                    "operation": {
                        "type": "string",
                        "enum": ["status", "diff", "add", "commit", "log", "branch", "checkout"],
                        "description": "Git operation to perform"
                    },
                    "args": {
                        "type": "string",
                        "description": "Additional arguments for the git command (e.g., file paths, branch names)"
                    },
                    "message": {
                        "type": "string",
                        "description": "Commit message (required for commit operation)"
                    },
                    "number": {
                        "type": "integer",
                        "description": "Number of log entries to show (for log operation)",
                        "default": 10
                    }
                },
                "required": ["operation"]
            }
        )
    
    async def execute(self, operation: str, args: Optional[str] = None, 
                     message: Optional[str] = None, number: int = 10) -> str:
        """Execute git command safely."""
        try:
            # Check if we're in a git repository
            if not os.path.exists(".git"):
                return "Error: Not in a git repository. Run 'git init' first."
            
            # Build command based on operation
            if operation == "status":
                cmd = ["git", "status", "--porcelain" if args == "short" else "--short"]
                
            elif operation == "diff":
                cmd = ["git", "diff"]
                if args:
                    cmd.extend(args.split())
                    
            elif operation == "add":
                if not args:
                    return "Error: Please specify files to add (use '.' for all files)"
                cmd = ["git", "add"] + args.split()
                
            elif operation == "commit":
                if not message:
                    return "Error: Commit message is required"
                # Format commit message with tool signature
                formatted_message = f"{message}\n\n🤖 Committed using GitTool"
                cmd = ["git", "commit", "-m", formatted_message]
                
            elif operation == "log":
                cmd = ["git", "log", f"-{number}", "--oneline", "--graph", "--decorate"]
                if args:
                    cmd.extend(args.split())
                    
            elif operation == "branch":
                if args:
                    # Create or switch branch
                    if args.startswith("-"):
                        cmd = ["git", "branch"] + args.split()
                    else:
                        cmd = ["git", "branch", args]
                else:
                    # List branches
                    cmd = ["git", "branch", "-v"]
                    
            elif operation == "checkout":
                if not args:
                    return "Error: Please specify branch name or file to checkout"
                cmd = ["git", "checkout"] + args.split()
                
            else:
                return f"Error: Unknown operation '{operation}'"
            
            # Execute command
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=30
            )
            
            # Handle output
            if result.returncode == 0:
                output = result.stdout.strip()
                if not output:
                    if operation == "add":
                        return f"Successfully added files: {args}"
                    elif operation == "commit":
                        # Get commit hash
                        commit_hash = subprocess.run(
                            ["git", "rev-parse", "HEAD"],
                            capture_output=True,
                            text=True
                        ).stdout.strip()[:7]
                        return f"Successfully committed with hash: {commit_hash}"
                    else:
                        return f"Command '{' '.join(cmd)}' completed successfully"
                return output
            else:
                error = result.stderr.strip()
                return f"Git error: {error}"
                
        except subprocess.TimeoutExpired:
            return "Error: Git command timed out after 30 seconds"
        except Exception as e:
            return f"Error executing git command: {str(e)}"