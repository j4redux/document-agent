"""Multi-edit tool for making multiple edits to a single file atomically."""

import asyncio
from pathlib import Path
from typing import Any, List, Tuple
from tools.base import Tool
from .file_tools import FileWriteTool


class MultiEditTool(Tool):
    """Tool for making multiple edits to a single file in one atomic operation."""

    def __init__(self):
        super().__init__(
            name="multi_edit",
            description="""
            Make multiple edits to a single file atomically.
            
            This tool allows you to specify multiple find-and-replace operations
            that will all be validated before any changes are made. If any edit
            cannot be applied, no changes will be made to the file.
            
            All edits are applied in sequence, with each edit operating on the
            result of the previous edit.
            """,
            input_schema={
                "type": "object",
                "properties": {
                    "file_path": {
                        "type": "string",
                        "description": "Path to the file to edit",
                    },
                    "edits": {
                        "type": "array",
                        "description": "List of edit operations to perform",
                        "items": {
                            "type": "object",
                            "properties": {
                                "old_string": {
                                    "type": "string",
                                    "description": "Text to find and replace",
                                },
                                "new_string": {
                                    "type": "string", 
                                    "description": "Text to replace with",
                                },
                            },
                            "required": ["old_string", "new_string"],
                        },
                        "minItems": 1,
                    },
                },
                "required": ["file_path", "edits"],
            },
        )

    async def execute(
        self, file_path: str, edits: List[dict[str, str]]
    ) -> str:
        """Execute multiple edits to a file atomically.

        Args:
            file_path: Path to the file to edit
            edits: List of edit operations, each with 'old_string' and 'new_string'

        Returns:
            Success message or error description
        """
        try:
            path = Path(file_path)
            abs_path = str(path.resolve())
            
            # Check if file exists
            if not path.exists():
                return f"Error: File not found at {file_path}"
            if not path.is_file():
                return f"Error: {file_path} is not a file"
            
            # Check if file has been read first
            if abs_path not in FileWriteTool._read_files:
                return (
                    f"Error: Cannot edit file {file_path} without reading it first. "
                    f"Use the file_read tool to read the file before modifying it."
                )
            
            # Read the file content
            def read_sync():
                with open(path, encoding="utf-8", errors="replace") as f:
                    return f.read()
            
            original_content = await asyncio.to_thread(read_sync)
            
            # Validate all edits can be applied
            validation_result = self._validate_edits(original_content, edits)
            if validation_result is not None:
                return validation_result
            
            # Apply all edits in sequence
            content = original_content
            edit_summary = []
            
            for i, edit in enumerate(edits):
                old_string = edit["old_string"]
                new_string = edit["new_string"]
                
                # Check if old_string exists in current content
                if old_string not in content:
                    # This shouldn't happen if validation passed, but double-check
                    return f"Error: Edit {i+1} failed - text not found: {repr(old_string)}"
                
                # Count occurrences
                count = content.count(old_string)
                
                # Apply the edit
                content = content.replace(old_string, new_string)
                
                # Record what was done
                if count > 1:
                    edit_summary.append(
                        f"Edit {i+1}: Replaced {count} occurrences"
                    )
                else:
                    edit_summary.append(f"Edit {i+1}: Replaced 1 occurrence")
            
            # Write the final content back to file
            def write_sync():
                with open(path, "w", encoding="utf-8") as f:
                    f.write(content)
            
            await asyncio.to_thread(write_sync)
            
            # Return success message with summary
            summary = "\n".join(edit_summary)
            return f"Successfully applied {len(edits)} edits to {file_path}:\n{summary}"
            
        except UnicodeDecodeError:
            return f"Error: {file_path} appears to be a binary file"
        except Exception as e:
            return f"Error editing {file_path}: {str(e)}"
    
    def _validate_edits(
        self, content: str, edits: List[dict[str, str]]
    ) -> str | None:
        """Validate that all edits can be applied successfully.
        
        Args:
            content: The original file content
            edits: List of edit operations
            
        Returns:
            Error message if validation fails, None if all edits are valid
        """
        # Check for empty edits list
        if not edits:
            return "Error: No edits provided"
        
        # Simulate applying edits to check they will all work
        test_content = content
        
        for i, edit in enumerate(edits):
            # Validate edit structure
            if "old_string" not in edit or "new_string" not in edit:
                return f"Error: Edit {i+1} missing required fields"
            
            old_string = edit["old_string"]
            new_string = edit["new_string"]
            
            # Check for empty strings
            if not old_string:
                return f"Error: Edit {i+1} has empty old_string"
            
            # Check if old_string exists in current test content
            if old_string not in test_content:
                return f"Error: Edit {i+1} cannot be applied - text not found: {repr(old_string)}"
            
            # Check if old_string and new_string are the same
            if old_string == new_string:
                return f"Error: Edit {i+1} has identical old_string and new_string"
            
            # Apply edit to test content for next iteration
            test_content = test_content.replace(old_string, new_string)
        
        return None  # All validations passed