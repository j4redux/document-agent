"""File operation tools for reading and writing files."""

import asyncio
import glob
import os
import subprocess
from pathlib import Path
from typing import Optional

from tools.base import Tool


class FileReadTool(Tool):
    """Tool for reading files and listing directories."""

    def __init__(self):
        super().__init__(
            name="file_read",
            description="""
            Read files or list directory contents.

            Operations:
            - read: Read the contents of a file
            - list: List files in a directory
            """,
            input_schema={
                "type": "object",
                "properties": {
                    "operation": {
                        "type": "string",
                        "enum": ["read", "list"],
                        "description": "File operation to perform",
                    },
                    "path": {
                        "type": "string",
                        "description": "File path for read or directory path",
                    },
                    "max_lines": {
                        "type": "integer",
                        "description": "Maximum lines to read (0 means no limit)",
                    },
                    "pattern": {
                        "type": "string",
                        "description": "File pattern to match",
                    },
                },
                "required": ["operation", "path"],
            },
        )

    async def execute(
        self,
        operation: str,
        path: str,
        max_lines: int = 0,
        pattern: str = "*",
    ) -> str:
        """Execute a file read operation.

        Args:
            operation: The operation to perform (read or list)
            path: The file or directory path
            max_lines: Maximum lines to read (for read operation, 0 means no limit)
            pattern: File pattern to match (for list operation)

        Returns:
            Result of the operation as string
        """
        if operation == "read":
            return await self._read_file(path, max_lines)
        elif operation == "list":
            return await self._list_files(path, pattern)
        else:
            return f"Error: Unsupported operation '{operation}'"

    async def _read_file(self, path: str, max_lines: int = 0) -> str:
        """Read a file from disk.
        
        Args:
            path: Path to the file to read
            max_lines: Maximum number of lines to read (0 means read entire file)
        """
        try:
            file_path = Path(path)

            if not file_path.exists():
                return f"Error: File not found at {path}"
            if not file_path.is_file():
                return f"Error: {path} is not a file"

            def read_sync():
                with open(file_path, encoding="utf-8", errors="replace") as f:
                    if max_lines > 0:
                        lines = []
                        for i, line in enumerate(f):
                            if i >= max_lines:
                                break
                            lines.append(line)
                        return "".join(lines)
                    return f.read()

            content = await asyncio.to_thread(read_sync)
            
            # Track that this file has been read (use absolute path)
            abs_path = str(file_path.resolve())
            FileWriteTool._read_files.add(abs_path)
            
            return content
        except Exception as e:
            return f"Error reading {path}: {str(e)}"

    async def _list_files(self, directory: str, pattern: str = "*") -> str:
        """List files in a directory."""
        try:
            dir_path = Path(directory)

            if not dir_path.exists():
                return f"Error: Directory not found at {directory}"
            if not dir_path.is_dir():
                return f"Error: {directory} is not a directory"

            def list_sync():
                search_pattern = f"{directory}/{pattern}"
                files = glob.glob(search_pattern)

                if not files:
                    return f"No files found matching {directory}/{pattern}"

                file_list = []
                for file_path in sorted(files):
                    path_obj = Path(file_path)
                    rel_path = str(file_path).replace(str(dir_path) + "/", "")

                    if path_obj.is_dir():
                        file_list.append(f"[DIR] {rel_path}/")
                    else:
                        file_list.append(f"     {rel_path}")

                return "\n".join(file_list)

            return await asyncio.to_thread(list_sync)
        except Exception as e:
            return f"Error listing files in {directory}: {str(e)}"


class FileWriteTool(Tool):
    """Tool for writing and editing files."""
    
    # Class variable to track which files have been read
    _read_files: set[str] = set()

    def __init__(self):
        super().__init__(
            name="file_write",
            description="""
            Write or edit files.

            Operations:
            - write: Create or completely replace a file
            - edit: Make targeted changes to parts of a file
            """,
            input_schema={
                "type": "object",
                "properties": {
                    "operation": {
                        "type": "string",
                        "enum": ["write", "edit"],
                        "description": "File operation to perform",
                    },
                    "path": {
                        "type": "string",
                        "description": "File path to write to or edit",
                    },
                    "content": {
                        "type": "string",
                        "description": "Content to write",
                    },
                    "old_text": {
                        "type": "string",
                        "description": "Text to replace (for edit operation)",
                    },
                    "new_text": {
                        "type": "string",
                        "description": "Replacement text (for edit operation)",
                    },
                },
                "required": ["operation", "path"],
            },
        )

    async def execute(
        self,
        operation: str,
        path: str,
        content: str = "",
        old_text: str = "",
        new_text: str = "",
    ) -> str:
        """Execute a file write operation.

        Args:
            operation: The operation to perform (write or edit)
            path: The file path
            content: Content to write (for write operation)
            old_text: Text to replace (for edit operation)
            new_text: Replacement text (for edit operation)

        Returns:
            Result of the operation as string
        """
        if operation == "write":
            if not content:
                return "Error: content parameter is required"
            return await self._write_file(path, content)
        elif operation == "edit":
            if not old_text or not new_text:
                return (
                    "Error: both old_text and new_text parameters "
                    "are required for edit operation"
                )
            return await self._edit_file(path, old_text, new_text)
        else:
            return f"Error: Unsupported operation '{operation}'"

    async def _write_file(self, path: str, content: str) -> str:
        """Write content to a file."""
        try:
            file_path = Path(path)
            abs_path = str(file_path.resolve())
            
            # Check if file exists and requires read permission
            if file_path.exists() and abs_path not in self._read_files:
                return (
                    f"Error: Cannot write to existing file {path} without reading it first. "
                    f"Use the file_read tool to read the file before modifying it."
                )
            
            os.makedirs(file_path.parent, exist_ok=True)

            def write_sync():
                with open(file_path, "w", encoding="utf-8") as f:
                    f.write(content)
                return (
                    f"Successfully wrote {len(content)} "
                    f"characters to {path}"
                )

            return await asyncio.to_thread(write_sync)
        except Exception as e:
            return f"Error writing to {path}: {str(e)}"

    async def _edit_file(self, path: str, old_text: str, new_text: str) -> str:
        """Make targeted changes to a file."""
        try:
            file_path = Path(path)
            abs_path = str(file_path.resolve())

            if not file_path.exists():
                return f"Error: File not found at {path}"
            if not file_path.is_file():
                return f"Error: {path} is not a file"
            
            # Check if file has been read first
            if abs_path not in self._read_files:
                return (
                    f"Error: Cannot edit file {path} without reading it first. "
                    f"Use the file_read tool to read the file before modifying it."
                )

            def edit_sync():
                try:
                    with open(
                        file_path, encoding="utf-8", errors="replace"
                    ) as f:
                        content = f.read()

                    if old_text not in content:
                        return (
                            f"Error: The specified text was not "
                            f"found in {path}"
                        )

                    # Count occurrences to warn about multiple matches
                    count = content.count(old_text)
                    if count > 1:
                        # Edit with warning about multiple occurrences
                        new_content = content.replace(old_text, new_text)
                        with open(file_path, "w", encoding="utf-8") as f:
                            f.write(new_content)
                        return (
                            f"Warning: Found {count} occurrences. "
                            f"All were replaced in {path}"
                        )
                    else:
                        # One occurrence, straightforward replacement
                        new_content = content.replace(old_text, new_text)
                        with open(file_path, "w", encoding="utf-8") as f:
                            f.write(new_content)
                        return f"Successfully edited {path}"
                except UnicodeDecodeError:
                    return f"Error: {path} appears to be a binary file"

            return await asyncio.to_thread(edit_sync)
        except Exception as e:
            return f"Error editing {path}: {str(e)}"


class FileSearchTool(Tool):
    """Tool for searching files using ast-grep for syntax-aware search or ripgrep for plain text."""

    def __init__(self):
        super().__init__(
            name="file_search",
            description="""
            Search for patterns in files using syntax-aware (ast-grep) or plain text search (ripgrep).

            Mode is auto-detected:
            - If only file_pattern is provided (no pattern), uses text mode to find files
            - Otherwise defaults to syntax mode for code searches
            - Can override with mode parameter
            
            Usage examples:
            - Find files: file_search(file_pattern="*.go")
            - Search in files: file_search(pattern="TODO", file_pattern="*.py")
            - Find specific file: file_search(file_pattern="main.go")
            - Syntax search: file_search(pattern="function $NAME")
            
            Supported languages for syntax search:
            Python, JavaScript, TypeScript, Java, C, C++, C#, Go, Rust, Ruby, PHP, Swift, Kotlin, Scala, etc.
            
            Requirements: ast-grep and ripgrep must be installed
            """,
            input_schema={
                "type": "object",
                "properties": {
                    "pattern": {
                        "type": "string",
                        "description": "Search pattern (ast-grep pattern for syntax mode, regex for text mode). Leave empty to just find files.",
                    },
                    "path": {
                        "type": "string",
                        "description": "Directory or file path to search in (default: current directory)",
                    },
                    "mode": {
                        "type": "string",
                        "enum": ["syntax", "text"],
                        "description": "Search mode: 'syntax' for ast-grep, 'text' for ripgrep (auto-detected if not specified)",
                    },
                    "language": {
                        "type": "string",
                        "description": "Programming language for syntax search (e.g., python, rust, javascript)",
                    },
                    "file_pattern": {
                        "type": "string",
                        "description": "File pattern to include (e.g., '*.py', '*.rs')",
                    },
                },
                "required": [],
            },
        )

    async def execute(
        self,
        pattern: str = "",
        path: str = ".",
        mode: Optional[str] = None,
        language: Optional[str] = None,
        file_pattern: Optional[str] = None,
    ) -> str:
        """Execute a file search operation.

        Args:
            pattern: The search pattern
            path: Directory or file to search in
            mode: Search mode ('syntax' or 'text', auto-detected if not specified)
            language: Programming language for syntax search
            file_pattern: File pattern to include

        Returns:
            Search results as string
        """
        # Auto-detect mode if not specified
        if mode is None:
            if not pattern and file_pattern:
                # Just looking for files, use text mode
                mode = "text"
            else:
                # Default to syntax mode for code searches
                mode = "syntax"
        
        if mode == "syntax":
            # Syntax mode requires a pattern
            if not pattern:
                return "Error: Syntax search requires a pattern. Use mode='text' to find files by name."
            return await self._syntax_search(pattern, path, language, file_pattern)
        elif mode == "text":
            return await self._text_search(pattern, path, file_pattern)
        else:
            return f"Error: Unsupported search mode '{mode}'"

    async def _syntax_search(
        self,
        pattern: str,
        path: str,
        language: Optional[str] = None,
        file_pattern: Optional[str] = None,
    ) -> str:
        """Perform syntax-aware search using ast-grep."""
        # Build ast-grep command
        cmd = ["ast-grep", "-p", pattern]
        
        # Add language if specified
        if language:
            cmd.extend(["--lang", language])
        elif file_pattern:
            # Try to infer language from file pattern
            lang = self._infer_language(file_pattern)
            if lang:
                cmd.extend(["--lang", lang])
        
        # Add file pattern if specified
        if file_pattern:
            cmd.extend(["--include", file_pattern])
        
        # Add path
        cmd.append(path)
        
        # Run ast-grep
        result = await asyncio.to_thread(
            subprocess.run,
            cmd,
            capture_output=True,
            text=True,
            cwd=os.getcwd()
        )
        
        if result.returncode == 0:
            if result.stdout:
                # Format the output
                lines = result.stdout.strip().split('\n')
                formatted_results = []
                current_file = None
                
                for line in lines:
                    if line and not line.startswith(' '):
                        # This is a file path
                        current_file = line.rstrip(':')
                        formatted_results.append(f"\n{current_file}:")
                    elif line.strip():
                        # This is a match
                        formatted_results.append(f"   {line}")
                
                return f"Found {len([l for l in lines if l and not l.startswith(' ')])} matches:\n" + '\n'.join(formatted_results)
            else:
                return "No matches found"
        else:
            if result.stderr:
                return f"Error running ast-grep: {result.stderr}"
            else:
                return "No matches found"

    async def _text_search(
        self,
        pattern: str,
        path: str,
        file_pattern: Optional[str] = None,
    ) -> str:
        """Perform plain text search using ripgrep."""
        # Special case: if pattern is empty and file_pattern is provided, list matching files
        if not pattern and file_pattern:
            cmd = ["rg", "--files", "--glob", file_pattern, path]
        else:
            # Build normal ripgrep command
            cmd = ["rg", pattern, path, "--no-heading", "--line-number", "--color=never"]
            
            # Add file pattern if specified
            if file_pattern:
                cmd.extend(["--glob", file_pattern])
        
        # Run ripgrep
        result = await asyncio.to_thread(
            subprocess.run,
            cmd,
            capture_output=True,
            text=True,
            cwd=os.getcwd()
        )
        
        if result.returncode == 0:
            if result.stdout:
                lines = result.stdout.strip().split('\n')
                
                # Check if we're listing files or showing matches
                if not pattern and file_pattern:
                    # Just listing files
                    formatted_results = [f"{line}" for line in lines if line]
                    return f"Found {len(lines)} files:\n" + '\n'.join(formatted_results)
                else:
                    # Format search results
                    formatted_results = []
                    current_file = None
                    
                    for line in lines:
                        if ':' in line:
                            parts = line.split(':', 2)
                            if len(parts) >= 3:
                                file_path, line_num, content = parts[0], parts[1], parts[2]
                                if file_path != current_file:
                                    current_file = file_path
                                    formatted_results.append(f"\n{file_path}:")
                                formatted_results.append(f"   {line_num}: {content.strip()}")
                    
                    match_count = len(lines)
                    return f"Found {match_count} matches:\n" + '\n'.join(formatted_results)
            else:
                return "No matches found"
        else:
            if result.stderr:
                return f"Error running ripgrep: {result.stderr}"
            else:
                return "No matches found"


    def _infer_language(self, file_pattern: str) -> Optional[str]:
        """Infer programming language from file pattern."""
        extension_map = {
            "*.py": "python",
            "*.js": "javascript",
            "*.jsx": "javascript",
            "*.ts": "typescript",
            "*.tsx": "typescript",
            "*.java": "java",
            "*.c": "c",
            "*.cpp": "cpp",
            "*.cc": "cpp",
            "*.cxx": "cpp",
            "*.cs": "csharp",
            "*.go": "go",
            "*.rs": "rust",
            "*.rb": "ruby",
            "*.php": "php",
            "*.swift": "swift",
            "*.kt": "kotlin",
            "*.scala": "scala",
            "*.r": "r",
            "*.lua": "lua",
            "*.dart": "dart",
            "*.elm": "elm",
            "*.ex": "elixir",
            "*.exs": "elixir",
        }
        
        for pattern, lang in extension_map.items():
            if file_pattern.endswith(pattern[1:]):  # Remove the * from pattern
                return lang
        
        return None
