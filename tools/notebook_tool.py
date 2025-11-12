"""Jupyter notebook tools for reading and editing .ipynb files."""

import asyncio
import json
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

from tools.base import Tool


class NotebookTool(Tool):
    """Tool for Jupyter notebook operations."""

    def __init__(self):
        super().__init__(
            name="notebook",
            description="""
            Read and edit Jupyter notebook (.ipynb) files.
            
            Operations:
            1. read: Read notebook cells
               - notebook(operation="read", path="notebook.ipynb")
               - notebook(operation="read", path="notebook.ipynb", cell_index=0)
               
            2. edit: Edit a specific cell
               - notebook(operation="edit", path="notebook.ipynb", cell_index=0, content="new code")
               
            3. add: Add a new cell
               - notebook(operation="add", path="notebook.ipynb", cell_type="code", content="print('hello')")
               - notebook(operation="add", path="notebook.ipynb", cell_type="markdown", content="# Title")
               - Optional: position="after" and after_index=2 to insert after specific cell
               
            Uses JSON to parse .ipynb files with minimal dependencies.
            """,
            input_schema={
                "type": "object",
                "properties": {
                    "operation": {
                        "type": "string",
                        "enum": ["read", "edit", "add"],
                        "description": "Operation to perform: 'read', 'edit', or 'add'",
                    },
                    "path": {
                        "type": "string",
                        "description": "Path to the Jupyter notebook file",
                    },
                    "cell_index": {
                        "type": "integer",
                        "description": "Index of the cell (0-based)",
                    },
                    "cell_type": {
                        "type": "string",
                        "enum": ["code", "markdown"],
                        "description": "Type of cell: 'code' or 'markdown'",
                    },
                    "content": {
                        "type": "string",
                        "description": "New content for the cell",
                    },
                    "position": {
                        "type": "string",
                        "enum": ["end", "after"],
                        "description": "Where to add the cell: 'end' (default) or 'after' a specific index",
                    },
                    "after_index": {
                        "type": "integer",
                        "description": "Insert new cell after this index (for position='after')",
                    },
                },
                "required": ["operation", "path"],
            },
        )

    async def execute(
        self,
        operation: str,
        path: str,
        cell_index: Optional[int] = None,
        cell_type: Optional[str] = None,
        content: Optional[str] = None,
        position: str = "end",
        after_index: Optional[int] = None,
    ) -> str:
        """Execute notebook operations."""
        if operation == "read":
            return await self._read_notebook(path, cell_index)
        elif operation == "edit":
            if cell_index is None:
                return "Error: cell_index is required for edit operation"
            if content is None:
                return "Error: content is required for edit operation"
            return await self._edit_notebook(path, cell_index, content)
        elif operation == "add":
            if cell_type is None:
                return "Error: cell_type is required for add operation"
            if content is None:
                return "Error: content is required for add operation"
            return await self._add_cell(path, cell_type, content, position, after_index)
        else:
            return f"Error: Unknown operation '{operation}'"

    async def _read_notebook(self, path: str, cell_index: Optional[int] = None) -> str:
        """Read notebook cells."""
        try:
            # Check if file exists
            nb_path = Path(path)
            if not nb_path.exists():
                return f"Error: Notebook file not found: {path}"
            
            if not nb_path.suffix == ".ipynb":
                return f"Error: File is not a Jupyter notebook: {path}"
            
            # Read notebook
            notebook_data = await asyncio.to_thread(
                nb_path.read_text, encoding="utf-8"
            )
            
            # Parse JSON
            try:
                notebook = json.loads(notebook_data)
            except json.JSONDecodeError as e:
                return f"Error: Invalid notebook format: {str(e)}"
            
            # Get cells
            cells = notebook.get("cells", [])
            if not cells:
                return f"Notebook '{path}' has no cells"
            
            # Read specific cell or all cells
            if cell_index is not None:
                if 0 <= cell_index < len(cells):
                    return self._format_cell(cells[cell_index], cell_index)
                else:
                    return f"Error: Cell index {cell_index} out of range (notebook has {len(cells)} cells)"
            else:
                # Read all cells
                result = [
                    f"Notebook: {path}",
                    f"Total cells: {len(cells)}",
                    "=" * 60,
                    "",
                ]
                
                for idx, cell in enumerate(cells):
                    result.append(self._format_cell(cell, idx))
                    result.append("")  # Empty line between cells
                
                return "\n".join(result)
                
        except Exception as e:
            return f"Error reading notebook: {str(e)}"

    async def _edit_notebook(self, path: str, cell_index: int, content: str) -> str:
        """Edit a specific cell in the notebook."""
        try:
            # Check if file exists
            nb_path = Path(path)
            if not nb_path.exists():
                return f"Error: Notebook file not found: {path}"
            
            # Read notebook
            notebook_data = await asyncio.to_thread(
                nb_path.read_text, encoding="utf-8"
            )
            
            # Parse JSON
            try:
                notebook = json.loads(notebook_data)
            except json.JSONDecodeError as e:
                return f"Error: Invalid notebook format: {str(e)}"
            
            # Get cells
            cells = notebook.get("cells", [])
            if not cells:
                return f"Error: Notebook has no cells"
            
            # Check cell index
            if not (0 <= cell_index < len(cells)):
                return f"Error: Cell index {cell_index} out of range (notebook has {len(cells)} cells)"
            
            # Update cell content
            cell = cells[cell_index]
            old_content = self._get_cell_source(cell)
            
            # Set new content (as list of lines for compatibility)
            if isinstance(content, str):
                # Split by newlines but preserve them
                lines = content.split('\n')
                if len(lines) > 1:
                    # Add newline to all lines except the last
                    cell["source"] = [line + '\n' for line in lines[:-1]] + [lines[-1]]
                else:
                    cell["source"] = [content]
            else:
                cell["source"] = content
            
            # Save notebook
            await asyncio.to_thread(
                nb_path.write_text,
                json.dumps(notebook, indent=1),
                encoding="utf-8"
            )
            
            return (
                f"Cell {cell_index} edited successfully!\n"
                f"Type: {cell.get('cell_type', 'unknown')}\n"
                f"\n"
                f"Old content:\n"
                f"{old_content}\n"
                f"\n"
                f"New content:\n"
                f"{content}"
            )
            
        except Exception as e:
            return f"Error editing notebook: {str(e)}"

    async def _add_cell(
        self,
        path: str,
        cell_type: str,
        content: str,
        position: str,
        after_index: Optional[int],
    ) -> str:
        """Add a new cell to the notebook."""
        try:
            # Check if file exists
            nb_path = Path(path)
            if not nb_path.exists():
                # Create new notebook if it doesn't exist
                notebook = self._create_empty_notebook()
            else:
                # Read existing notebook
                notebook_data = await asyncio.to_thread(
                    nb_path.read_text, encoding="utf-8"
                )
                
                try:
                    notebook = json.loads(notebook_data)
                except json.JSONDecodeError as e:
                    return f"Error: Invalid notebook format: {str(e)}"
            
            # Get cells
            cells = notebook.get("cells", [])
            
            # Create new cell
            new_cell = self._create_cell(cell_type, content)
            
            # Determine where to insert
            if position == "after" and after_index is not None:
                if not (0 <= after_index < len(cells)):
                    return f"Error: after_index {after_index} out of range (notebook has {len(cells)} cells)"
                insert_index = after_index + 1
                cells.insert(insert_index, new_cell)
                location_msg = f"after cell {after_index} (new index: {insert_index})"
            else:
                # Add to end
                cells.append(new_cell)
                insert_index = len(cells) - 1
                location_msg = f"at the end (index: {insert_index})"
            
            # Update notebook
            notebook["cells"] = cells
            
            # Save notebook
            await asyncio.to_thread(
                nb_path.write_text,
                json.dumps(notebook, indent=1),
                encoding="utf-8"
            )
            
            return (
                f"New {cell_type} cell added successfully {location_msg}!\n"
                f"Total cells: {len(cells)}\n"
                f"\n"
                f"Content:\n"
                f"{content}"
            )
            
        except Exception as e:
            return f"Error adding cell: {str(e)}"

    def _format_cell(self, cell: Dict[str, Any], index: int) -> str:
        """Format a cell for display."""
        cell_type = cell.get("cell_type", "unknown")
        source = self._get_cell_source(cell)
        
        # Format based on cell type
        if cell_type == "code":
            execution_count = cell.get("execution_count", "[ ]")
            if execution_count is None:
                execution_count = "[ ]"
            else:
                execution_count = f"[{execution_count}]"
            
            result = [
                f"Cell {index} (code) {execution_count}:",
                "-" * 40,
                source,
            ]
            
            # Add outputs if present
            outputs = cell.get("outputs", [])
            if outputs:
                result.append("\nOutputs:")
                for output in outputs:
                    output_text = self._format_output(output)
                    if output_text:
                        result.append(output_text)
            
        elif cell_type == "markdown":
            result = [
                f"Cell {index} (markdown):",
                "-" * 40,
                source,
            ]
        else:
            result = [
                f"Cell {index} ({cell_type}):",
                "-" * 40,
                source,
            ]
        
        return "\n".join(result)

    def _get_cell_source(self, cell: Dict[str, Any]) -> str:
        """Extract source from a cell."""
        source = cell.get("source", [])
        if isinstance(source, list):
            return "".join(source)
        else:
            return str(source)

    def _format_output(self, output: Dict[str, Any]) -> str:
        """Format cell output for display."""
        output_type = output.get("output_type", "unknown")
        
        if output_type == "stream":
            text = output.get("text", [])
            if isinstance(text, list):
                return "".join(text)
            return str(text)
            
        elif output_type == "execute_result" or output_type == "display_data":
            data = output.get("data", {})
            # Prefer plain text
            if "text/plain" in data:
                text = data["text/plain"]
                if isinstance(text, list):
                    return "".join(text)
                return str(text)
            # Otherwise show available mime types
            return f"[{output_type} with mime types: {', '.join(data.keys())}]"
            
        elif output_type == "error":
            ename = output.get("ename", "Error")
            evalue = output.get("evalue", "")
            return f"{ename}: {evalue}"
            
        else:
            return f"[{output_type} output]"

    def _create_empty_notebook(self) -> Dict[str, Any]:
        """Create an empty notebook structure."""
        return {
            "cells": [],
            "metadata": {
                "kernelspec": {
                    "display_name": "Python 3",
                    "language": "python",
                    "name": "python3"
                },
                "language_info": {
                    "name": "python",
                    "version": "3.8.0"
                }
            },
            "nbformat": 4,
            "nbformat_minor": 4
        }

    def _create_cell(self, cell_type: str, content: str) -> Dict[str, Any]:
        """Create a new cell structure."""
        # Split content into lines for proper notebook format
        if isinstance(content, str):
            lines = content.split('\n')
            if len(lines) > 1:
                # Add newline to all lines except the last
                source = [line + '\n' for line in lines[:-1]] + [lines[-1]]
            else:
                source = [content]
        else:
            source = content
        
        if cell_type == "code":
            return {
                "cell_type": "code",
                "execution_count": None,
                "metadata": {},
                "outputs": [],
                "source": source
            }
        else:  # markdown
            return {
                "cell_type": "markdown",
                "metadata": {},
                "source": source
            }