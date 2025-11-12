"""Basic system tools for file operations."""

import asyncio
import json
import os
import subprocess
from pathlib import Path
from typing import List, Optional, Dict, Any

from tools.base import Tool


class CatTool(Tool):
    """Tool for concatenating and displaying file contents."""

    def __init__(self):
        super().__init__(
            name="cat",
            description="""
            Display contents of one or more files (like Unix cat command).
            
            Usage:
            - Single file: cat(files=["file.txt"])
            - Multiple files: cat(files=["file1.txt", "file2.txt"])
            - With line numbers: cat(files=["file.txt"], number_lines=True)
            """,
            input_schema={
                "type": "object",
                "properties": {
                    "files": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "List of file paths to display",
                    },
                    "number_lines": {
                        "type": "boolean",
                        "description": "Show line numbers (like cat -n)",
                    },
                },
                "required": ["files"],
            },
        )

    async def execute(
        self,
        files: List[str],
        number_lines: bool = False,
    ) -> str:
        """Display contents of files."""
        results = []
        
        for file_path in files:
            try:
                path = Path(file_path)
                
                if not path.exists():
                    results.append(f"cat: {file_path}: No such file or directory")
                    continue
                    
                if not path.is_file():
                    results.append(f"cat: {file_path}: Is a directory")
                    continue
                
                # Read file
                content = await asyncio.to_thread(path.read_text, encoding="utf-8", errors="replace")
                
                if number_lines:
                    # Add line numbers
                    lines = content.splitlines()
                    numbered_lines = [f"{i+1:6d}\t{line}" for i, line in enumerate(lines)]
                    content = "\n".join(numbered_lines)
                
                # Add file header if multiple files
                if len(files) > 1:
                    results.append(f"==> {file_path} <==")
                
                results.append(content)
                
            except Exception as e:
                results.append(f"cat: {file_path}: {str(e)}")
        
        return "\n".join(results)


class LsTool(Tool):
    """Tool for listing directory contents."""

    def __init__(self):
        super().__init__(
            name="ls",
            description="""
            List directory contents (like Unix ls command).
            
            Usage:
            - List current dir: ls()
            - List specific dir: ls(path="./src")
            - Long format: ls(long_format=True)
            - Show hidden files: ls(all_files=True)
            - Human readable sizes: ls(human_readable=True)
            """,
            input_schema={
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "Directory path to list (default: current directory)",
                    },
                    "long_format": {
                        "type": "boolean",
                        "description": "Use long listing format (like ls -l)",
                    },
                    "all_files": {
                        "type": "boolean",
                        "description": "Show hidden files (like ls -a)",
                    },
                    "human_readable": {
                        "type": "boolean",
                        "description": "Show sizes in human readable format (like ls -h)",
                    },
                },
                "required": [],
            },
        )

    async def execute(
        self,
        path: str = ".",
        long_format: bool = False,
        all_files: bool = False,
        human_readable: bool = False,
    ) -> str:
        """List directory contents."""
        try:
            dir_path = Path(path)
            
            if not dir_path.exists():
                return f"ls: cannot access '{path}': No such file or directory"
                
            if not dir_path.is_dir():
                # If it's a file, just show the file
                return str(path)
            
            # Build ls command
            cmd = ["ls"]
            if long_format:
                cmd.append("-l")
            if all_files:
                cmd.append("-a")
            if human_readable and long_format:
                cmd.append("-h")
            cmd.append(str(dir_path))
            
            # Run ls command
            result = await asyncio.to_thread(
                subprocess.run,
                cmd,
                capture_output=True,
                text=True,
                cwd=os.getcwd()
            )
            
            if result.returncode == 0:
                return result.stdout.strip()
            else:
                return f"ls: {result.stderr.strip()}"
                
        except Exception as e:
            return f"ls: {str(e)}"


class FindTool(Tool):
    """Tool for finding files and directories."""

    def __init__(self):
        super().__init__(
            name="find",
            description="""
            Find files and directories (like Unix find command).
            
            Usage:
            - Find by name: find(name="*.py")
            - Find by type: find(type="f")  # f=file, d=directory
            - Find in specific dir: find(path="./src", name="*.js")
            - Limit depth: find(maxdepth=2, name="*.txt")
            - Execute command: find(name="*.py", exec="wc -l {}")
            """,
            input_schema={
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "Starting directory for search (default: current directory)",
                    },
                    "name": {
                        "type": "string",
                        "description": "Name pattern to match (e.g., '*.py', 'test_*')",
                    },
                    "type": {
                        "type": "string",
                        "enum": ["f", "d"],
                        "description": "Type: 'f' for files, 'd' for directories",
                    },
                    "maxdepth": {
                        "type": "integer",
                        "description": "Maximum depth to search",
                    },
                    "exec": {
                        "type": "string",
                        "description": "Command to execute on each found item (use {} as placeholder)",
                    },
                },
                "required": [],
            },
        )

    async def execute(
        self,
        path: str = ".",
        name: Optional[str] = None,
        type: Optional[str] = None,
        maxdepth: Optional[int] = None,
        exec: Optional[str] = None,
    ) -> str:
        """Find files and directories."""
        try:
            # Build find command
            cmd = ["find", path]
            
            # Add maxdepth early (must come before other options)
            if maxdepth is not None:
                cmd.extend(["-maxdepth", str(maxdepth)])
            
            # Add type filter
            if type:
                cmd.extend(["-type", type])
            
            # Add name filter
            if name:
                cmd.extend(["-name", name])
            
            # Add exec command
            if exec:
                # Split exec command and replace {} with placeholder
                exec_parts = exec.split()
                cmd.extend(["-exec"] + exec_parts + [";"])
            
            # Run find command
            result = await asyncio.to_thread(
                subprocess.run,
                cmd,
                capture_output=True,
                text=True,
                cwd=os.getcwd()
            )
            
            if result.returncode == 0:
                if result.stdout:
                    return result.stdout.strip()
                else:
                    return "No files found"
            else:
                return f"find: {result.stderr.strip()}"
                
        except Exception as e:
            return f"find: {str(e)}"


class GrepTool(Tool):
    """Tool for searching text patterns in files."""

    def __init__(self):
        super().__init__(
            name="grep",
            description="""
            Search for patterns in files (like Unix grep command).
            Uses ripgrep (rg) for better performance.
            
            Usage:
            - Basic search: grep(pattern="TODO")
            - Search in files: grep(pattern="error", files=["*.log"])
            - Case insensitive: grep(pattern="error", ignore_case=True)
            - Show line numbers: grep(pattern="def", line_numbers=True)
            - Recursive search: grep(pattern="import", recursive=True)
            """,
            input_schema={
                "type": "object",
                "properties": {
                    "pattern": {
                        "type": "string",
                        "description": "Pattern to search for",
                    },
                    "files": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Files or patterns to search in",
                    },
                    "ignore_case": {
                        "type": "boolean",
                        "description": "Case insensitive search (like grep -i)",
                    },
                    "line_numbers": {
                        "type": "boolean",
                        "description": "Show line numbers (like grep -n)",
                    },
                    "recursive": {
                        "type": "boolean",
                        "description": "Recursive search (like grep -r)",
                    },
                    "count": {
                        "type": "boolean",
                        "description": "Only show count of matches (like grep -c)",
                    },
                },
                "required": ["pattern"],
            },
        )

    async def execute(
        self,
        pattern: str,
        files: Optional[List[str]] = None,
        ignore_case: bool = False,
        line_numbers: bool = True,
        recursive: bool = False,
        count: bool = False,
    ) -> str:
        """Search for patterns in files."""
        try:
            # Use ripgrep for better performance
            cmd = ["rg", pattern]
            
            if ignore_case:
                cmd.append("-i")
            
            if not line_numbers:
                cmd.append("--no-line-number")
            
            if count:
                cmd.append("-c")
            
            # Add files/patterns
            if files:
                for file_pattern in files:
                    if "*" in file_pattern:
                        cmd.extend(["--glob", file_pattern])
                    else:
                        cmd.append(file_pattern)
            elif recursive:
                # Search current directory recursively (default for rg)
                pass
            else:
                # If not recursive and no files specified, search stdin behavior
                return "grep: Please specify files to search or use recursive=True"
            
            # Run ripgrep
            result = await asyncio.to_thread(
                subprocess.run,
                cmd,
                capture_output=True,
                text=True,
                cwd=os.getcwd()
            )
            
            if result.returncode == 0:
                return result.stdout.strip()
            elif result.returncode == 1:
                return "No matches found"
            else:
                return f"grep: {result.stderr.strip()}"
                
        except Exception as e:
            return f"grep: {str(e)}"


class ContextPrimeTool(Tool):
    """Tool for gathering project context efficiently."""

    def __init__(self):
        super().__init__(
            name="context_prime",
            description="""
            Gather key project context by reading essential files and understanding structure.
            
            IMPORTANT: This is typically part of a larger task - consider using todo_write first 
            to organize the full workflow before calling context_prime.
            
            This tool helps quickly understand a project by reading documentation, 
            configuration, and key source files.
            
            Usage:
            - Basic: context_prime() - reads README, CLAUDE.md, and shows structure
            - With specific focus: context_prime(focus="tools") - also reads relevant source files
            - Custom files: context_prime(additional_files=["config.py", "setup.py"])
            
            Best practice: Create a todo list first that includes context_prime as step 1,
            followed by your analysis/implementation tasks.
            """,
            input_schema={
                "type": "object",
                "properties": {
                    "focus": {
                        "type": "string",
                        "description": "Area to focus on (e.g., 'tools', 'tests', 'examples')",
                    },
                    "additional_files": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Additional files to read beyond the defaults",
                    },
                    "show_structure": {
                        "type": "boolean",
                        "description": "Show project structure (default: True)",
                    },
                    "max_depth": {
                        "type": "integer",
                        "description": "Maximum depth for structure display (default: 3)",
                    },
                },
                "required": [],
            },
        )

    async def execute(
        self,
        focus: Optional[str] = None,
        additional_files: Optional[List[str]] = None,
        show_structure: bool = True,
        max_depth: int = 3,
    ) -> str:
        """Gather project context."""
        results = []
        results.append("=== PROJECT CONTEXT PRIMER ===\n")
        
        # 1. Read core documentation files
        doc_files = [
            "README.md",
            "CLAUDE.md", 
            ".claude/CLAUDE.md",
            "pyproject.toml",
            "package.json",
            "requirements.txt",
        ]
        
        results.append("DOCUMENTATION & CONFIG")
        results.append("-" * 40)
        
        for doc_file in doc_files:
            for possible_path in [doc_file, f"./{doc_file}", f"../{doc_file}"]:
                try:
                    path = Path(possible_path)
                    if path.exists() and path.is_file():
                        content = await asyncio.to_thread(
                            path.read_text, 
                            encoding="utf-8", 
                            errors="replace"
                        )
                        
                        # Truncate very long files
                        if len(content) > 2000:
                            content = content[:2000] + "\n... (truncated)"
                        
                        results.append(f"\nFile: {possible_path}:")
                        results.append(content)
                        break
                except Exception:
                    continue
        
        # 2. Show project structure
        if show_structure:
            results.append("\n\nPROJECT STRUCTURE")
            results.append("-" * 40)
            
            # Use find to show structure
            try:
                cmd = ["find", ".", "-type", "f", "-name", "*.py"]
                if max_depth:
                    cmd = ["find", ".", "-maxdepth", str(max_depth), "-type", "f", "-name", "*.py"]
                
                result = await asyncio.to_thread(
                    subprocess.run,
                    cmd,
                    capture_output=True,
                    text=True,
                    cwd=os.getcwd()
                )
                
                if result.returncode == 0 and result.stdout:
                    files = sorted(result.stdout.strip().split('\n'))
                    
                    # Group by directory
                    from collections import defaultdict
                    by_dir = defaultdict(list)
                    
                    for file in files:
                        if "__pycache__" in file or ".pyc" in file:
                            continue
                        dir_name = os.path.dirname(file)
                        file_name = os.path.basename(file)
                        by_dir[dir_name].append(file_name)
                    
                    for dir_name in sorted(by_dir.keys()):
                        results.append(f"\n{dir_name}/")
                        for file_name in sorted(by_dir[dir_name]):
                            results.append(f"  - {file_name}")
                            
            except Exception as e:
                results.append(f"Error getting structure: {str(e)}")
        
        # 3. Read focus area files
        if focus:
            results.append(f"\n\nFOCUS AREA: {focus.upper()}")
            results.append("-" * 40)
            
            focus_patterns = {
                "tools": ["tools/base.py", "tools/__init__.py"],
                "tests": ["test_*.py", "tests/*.py"],
                "examples": ["example_*.py"],
                "agent": ["agent.py", "utils/tool_util.py"],
            }
            
            if focus.lower() in focus_patterns:
                for pattern in focus_patterns[focus.lower()]:
                    try:
                        # Use glob to find files
                        import glob
                        matching_files = glob.glob(pattern, recursive=True)
                        
                        for file_path in matching_files[:3]:  # Limit to 3 files
                            try:
                                path = Path(file_path)
                                if path.exists():
                                    content = await asyncio.to_thread(
                                        path.read_text,
                                        encoding="utf-8",
                                        errors="replace"
                                    )
                                    
                                    # Show first 50 lines
                                    lines = content.splitlines()[:50]
                                    content = "\n".join(lines)
                                    if len(lines) == 50:
                                        content += "\n... (truncated)"
                                    
                                    results.append(f"\nFile: {file_path}:")
                                    results.append(content)
                            except Exception:
                                continue
                    except Exception:
                        continue
        
        # 4. Read additional requested files
        if additional_files:
            results.append("\n\nADDITIONAL FILES")
            results.append("-" * 40)
            
            for file_path in additional_files:
                try:
                    path = Path(file_path)
                    if path.exists() and path.is_file():
                        content = await asyncio.to_thread(
                            path.read_text,
                            encoding="utf-8",
                            errors="replace"
                        )
                        
                        # Show first 100 lines
                        lines = content.splitlines()[:100]
                        content = "\n".join(lines)
                        if len(lines) == 100:
                            content += "\n... (truncated)"
                        
                        results.append(f"\nFile: {file_path}:")
                        results.append(content)
                    else:
                        results.append(f"\nERROR: {file_path}: Not found")
                except Exception as e:
                    results.append(f"\nERROR: {file_path}: Error reading - {str(e)}")
        
        # 5. Summary of key findings
        results.append("\n\nCONTEXT SUMMARY")
        results.append("-" * 40)
        
        # Try to detect project type
        project_type = "Unknown"
        if Path("pyproject.toml").exists() or Path("setup.py").exists():
            project_type = "Python"
        elif Path("package.json").exists():
            project_type = "Node.js"
        elif Path("Cargo.toml").exists():
            project_type = "Rust"
        elif Path("go.mod").exists():
            project_type = "Go"
        
        results.append(f"Project Type: {project_type}")
        
        # Check for test commands in CLAUDE.md
        test_commands = []
        for claude_path in ["CLAUDE.md", ".claude/CLAUDE.md"]:
            try:
                if Path(claude_path).exists():
                    content = Path(claude_path).read_text()
                    
                    # Look for test commands
                    for line in content.splitlines():
                        if any(cmd in line.lower() for cmd in ["test", "pytest", "lint", "ruff", "format"]):
                            if ":" in line or "`" in line:
                                test_commands.append(line.strip())
            except Exception:
                continue
        
        if test_commands:
            results.append("\nDetected Commands:")
            for cmd in test_commands[:5]:  # Show up to 5 commands
                results.append(f"  {cmd}")
        
        results.append("\n=== END CONTEXT PRIMER ===")
        
        return "\n".join(results)


class TodoReadTool(Tool):
    """Tool for reading the current todo list."""

    def __init__(self):
        super().__init__(
            name="todo_read",
            description="""
            Read the current to-do list for the session.
            
            This tool helps track tasks and their status throughout the conversation.
            Returns a list of todos with their status, priority, and content.
            
            Usage:
            - todo_read() - Shows all todos with their current status
            """,
            input_schema={
                "type": "object",
                "properties": {},
                "required": [],
            },
        )
        # In-memory storage for todos (persists during agent session)
        self._todos: List[Dict[str, Any]] = []

    async def execute(self) -> str:
        """Read and display the current todo list."""
        if not self._todos:
            return "No todos yet. Use todo_write to create your first task!"
        
        # Format todos nicely
        result = ["TODO LIST", "=" * 40]
        
        # Group by status
        by_status = {
            "in_progress": [],
            "pending": [],
            "completed": []
        }
        
        for todo in self._todos:
            status = todo.get("status", "pending")
            if status in by_status:
                by_status[status].append(todo)
        
        # Show in progress first
        if by_status["in_progress"]:
            result.append("\nIN PROGRESS:")
            for todo in by_status["in_progress"]:
                priority = todo.get("priority", "medium").upper()
                result.append(f"  [{priority}] [{todo.get('id', '?')}] {todo.get('content', 'No content')}")
        
        # Then pending
        if by_status["pending"]:
            result.append("\nPENDING:")
            for todo in by_status["pending"]:
                priority = todo.get("priority", "medium").upper()
                result.append(f"  [{priority}] [{todo.get('id', '?')}] {todo.get('content', 'No content')}")
        
        # Finally completed
        if by_status["completed"]:
            result.append("\nCOMPLETED:")
            for todo in by_status["completed"]:
                result.append(f"  [DONE] [{todo.get('id', '?')}] {todo.get('content', 'No content')}")
        
        # Summary
        total = len(self._todos)
        completed = len(by_status["completed"])
        in_progress = len(by_status["in_progress"])
        pending = len(by_status["pending"])
        
        result.append(f"\nSummary: {total} total | {in_progress} in progress | {pending} pending | {completed} completed")
        
        return "\n".join(result)


class TodoWriteTool(Tool):
    """Tool for creating and managing a todo list."""

    def __init__(self):
        super().__init__(
            name="todo_write",
            description="""
            Create and manage a structured task list for your current session.
            
            WHEN TO USE: Automatically use for requests involving multiple steps, analysis + creation,
            documentation tasks, or anything starting with context_prime. Break complex work into 3-7
            specific tasks before execution.
            
            This helps track progress, organize complex tasks, and maintain focus.
            Each todo has: id, content, status (pending/in_progress/completed), and priority (high/medium/low).
            
            AUTOMATIC TRIGGERS - Use todo_write when:
            - Request contains "and" (e.g., "analyze and create")
            - Using context_prime tool
            - Creating documentation or reports
            - Request involves >2 distinct operations
            - Keywords: "create", "implement", "analyze", "document", "build"
            
            Usage:
            - Create new list: todo_write(todos=[{"id": "1", "content": "Task", "status": "pending", "priority": "high"}])
            - Update existing: Pass the full updated list
            - Mark complete: Change status to "completed"
            
            Best practices:
            - Start with "Let me organize this work first"
            - Only one task should be "in_progress" at a time
            - Update status immediately when starting/completing tasks
            - Use clear, actionable task descriptions
            """,
            input_schema={
                "type": "object",
                "properties": {
                    "todos": {
                        "type": "array",
                        "description": "The complete todo list (replaces existing)",
                        "items": {
                            "type": "object",
                            "properties": {
                                "id": {"type": "string", "description": "Unique identifier"},
                                "content": {"type": "string", "description": "Task description"},
                                "status": {
                                    "type": "string",
                                    "enum": ["pending", "in_progress", "completed"],
                                    "description": "Current status"
                                },
                                "priority": {
                                    "type": "string", 
                                    "enum": ["high", "medium", "low"],
                                    "description": "Task priority"
                                }
                            },
                            "required": ["id", "content", "status", "priority"]
                        }
                    }
                },
                "required": ["todos"],
            },
        )
        # Will be shared with TodoReadTool instance
        self._todos: List[Dict[str, Any]] = []

    async def execute(self, todos: List[Dict[str, Any]]) -> str:
        """Update the todo list."""
        # Validate todos
        for todo in todos:
            if not all(key in todo for key in ["id", "content", "status", "priority"]):
                return "Error: Each todo must have id, content, status, and priority"
            
            if todo["status"] not in ["pending", "in_progress", "completed"]:
                return f"Error: Invalid status '{todo['status']}' for todo {todo['id']}"
            
            if todo["priority"] not in ["high", "medium", "low"]:
                return f"Error: Invalid priority '{todo['priority']}' for todo {todo['id']}"
        
        # Check for duplicate IDs
        ids = [todo["id"] for todo in todos]
        if len(ids) != len(set(ids)):
            return "Error: Duplicate todo IDs found"
        
        # Warn if multiple in_progress
        in_progress = [todo for todo in todos if todo["status"] == "in_progress"]
        if len(in_progress) > 1:
            warning = f"Warning: {len(in_progress)} tasks marked as in_progress. Consider having only one active task.\n"
        else:
            warning = ""
        
        # Update the todos
        old_count = len(self._todos)
        self._todos = todos.copy()
        
        # Find a way to share with TodoReadTool
        # This is a bit hacky but works for our purposes
        if hasattr(self, '_read_tool_ref'):
            self._read_tool_ref._todos = self._todos
        
        # Provide feedback
        new_count = len(self._todos)
        completed_count = len([t for t in self._todos if t["status"] == "completed"])
        in_progress_count = len([t for t in self._todos if t["status"] == "in_progress"])
        
        result = [
            warning + "Todos updated successfully!",
            f"Total: {new_count} tasks ({new_count - old_count:+d} change)",
            f"In Progress: {in_progress_count}",
            f"Completed: {completed_count}",
        ]
        
        if in_progress_count == 1:
            current = in_progress[0]
            result.append(f"\nCurrent task: [{current['id']}] {current['content']}")
        
        return "\n".join(result)


# Helper function to link TodoRead and TodoWrite tools
def create_linked_todo_tools():
    """Create a pair of linked TodoRead and TodoWrite tools that share state."""
    read_tool = TodoReadTool()
    write_tool = TodoWriteTool()
    
    # Link them together
    write_tool._read_tool_ref = read_tool
    read_tool._todos = write_tool._todos
    
    return read_tool, write_tool