"""Image tools for capturing screenshots and reading images."""

import asyncio
import base64
import os
import platform
import subprocess
import tempfile
from pathlib import Path
from typing import Optional

from tools.base import Tool


class ImageTool(Tool):
    """Tool for image operations like screenshots and reading images."""

    def __init__(self):
        super().__init__(
            name="image",
            description="""
            Perform image operations like taking screenshots and reading images.
            
            Operations:
            1. screenshot: Capture a screenshot
               - image(operation="screenshot", output_path="screenshot.png")
               - Platform-aware: uses appropriate command for macOS/Linux/Windows
               
            2. read: Read an image file and return base64 data
               - image(operation="read", path="image.png")
               - Returns base64 encoded image data for use in other tools
            
            Clear error messages for unsupported platforms or operations.
            """,
            input_schema={
                "type": "object",
                "properties": {
                    "operation": {
                        "type": "string",
                        "enum": ["screenshot", "read"],
                        "description": "Operation to perform: 'screenshot' or 'read'",
                    },
                    "path": {
                        "type": "string",
                        "description": "Image file path (for read operation)",
                    },
                    "output_path": {
                        "type": "string",
                        "description": "Output path for screenshot (optional, defaults to temp file)",
                    },
                    "delay": {
                        "type": "integer",
                        "description": "Delay in seconds before taking screenshot (default: 0)",
                    },
                },
                "required": ["operation"],
            },
        )

    async def execute(
        self,
        operation: str,
        path: Optional[str] = None,
        output_path: Optional[str] = None,
        delay: int = 0,
    ) -> str:
        """Execute image operations."""
        if operation == "screenshot":
            return await self._take_screenshot(output_path, delay)
        elif operation == "read":
            if not path:
                return "Error: Path is required for read operation"
            return await self._read_image(path)
        else:
            return f"Error: Unknown operation '{operation}'"

    async def _take_screenshot(self, output_path: Optional[str], delay: int) -> str:
        """Take a screenshot using platform-specific commands."""
        system = platform.system().lower()
        
        # Determine output path
        if not output_path:
            # Create temp file
            with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as tmp:
                output_path = tmp.name
        else:
            # Ensure directory exists
            output_dir = os.path.dirname(output_path)
            if output_dir and not os.path.exists(output_dir):
                os.makedirs(output_dir, exist_ok=True)
        
        # Add delay if specified
        if delay > 0:
            await asyncio.sleep(delay)
        
        try:
            if system == "darwin":  # macOS
                # Use screencapture command
                cmd = ["screencapture", "-x", output_path]  # -x: no sound
                
            elif system == "linux":
                # Try multiple Linux screenshot tools in order of preference
                # Check for available tools
                tools = [
                    (["import", output_path], "imagemagick"),  # ImageMagick
                    (["scrot", output_path], "scrot"),  # scrot
                    (["gnome-screenshot", "-f", output_path], "gnome-screenshot"),
                    (["spectacle", "-b", "-n", "-o", output_path], "spectacle"),  # KDE
                ]
                
                cmd = None
                available_tool = None
                
                for tool_cmd, tool_name in tools:
                    # Check if tool exists
                    check_result = await asyncio.to_thread(
                        subprocess.run,
                        ["which", tool_cmd[0]],
                        capture_output=True,
                        text=True
                    )
                    if check_result.returncode == 0:
                        cmd = tool_cmd
                        available_tool = tool_name
                        break
                
                if not cmd:
                    return (
                        "Error: No screenshot tool found on Linux.\n"
                        "Please install one of: imagemagick, scrot, gnome-screenshot, or spectacle\n"
                        "Example: sudo apt-get install scrot"
                    )
                    
            elif system == "windows":
                # Use PowerShell to take screenshot
                ps_script = f"""
                Add-Type -AssemblyName System.Windows.Forms
                Add-Type -AssemblyName System.Drawing
                $screen = [System.Windows.Forms.SystemInformation]::VirtualScreen
                $bitmap = New-Object System.Drawing.Bitmap $screen.Width, $screen.Height
                $graphics = [System.Drawing.Graphics]::FromImage($bitmap)
                $graphics.CopyFromScreen($screen.Left, $screen.Top, 0, 0, $bitmap.Size)
                $bitmap.Save('{output_path}', [System.Drawing.Imaging.ImageFormat]::Png)
                $graphics.Dispose()
                $bitmap.Dispose()
                """
                cmd = ["powershell", "-Command", ps_script]
                
            else:
                return f"Error: Unsupported platform '{system}' for screenshots"
            
            # Execute screenshot command
            result = await asyncio.to_thread(
                subprocess.run,
                cmd,
                capture_output=True,
                text=True
            )
            
            if result.returncode != 0:
                error_msg = result.stderr.strip() if result.stderr else "Unknown error"
                return f"Error taking screenshot: {error_msg}"
            
            # Verify file was created
            if not os.path.exists(output_path):
                return "Error: Screenshot file was not created"
            
            # Get file size for info
            file_size = os.path.getsize(output_path)
            file_size_kb = file_size / 1024
            
            return (
                f"Screenshot saved successfully!\n"
                f"Path: {output_path}\n"
                f"Size: {file_size_kb:.1f} KB\n"
                f"Platform: {system}"
                + (f" (using {available_tool})" if system == "linux" else "")
            )
            
        except Exception as e:
            return f"Error taking screenshot: {str(e)}"

    async def _read_image(self, path: str) -> str:
        """Read an image file and return base64 encoded data."""
        try:
            # Check if file exists
            if not os.path.exists(path):
                return f"Error: Image file not found: {path}"
            
            # Check if it's a file
            if not os.path.isfile(path):
                return f"Error: Path is not a file: {path}"
            
            # Check file extension
            valid_extensions = {'.png', '.jpg', '.jpeg', '.gif', '.bmp', '.webp', '.svg'}
            file_ext = Path(path).suffix.lower()
            if file_ext not in valid_extensions:
                return f"Error: Unsupported image format '{file_ext}'. Supported: {', '.join(valid_extensions)}"
            
            # Read file
            file_data = await asyncio.to_thread(
                lambda: Path(path).read_bytes()
            )
            
            # Get file info
            file_size = len(file_data)
            file_size_kb = file_size / 1024
            
            # Encode to base64
            base64_data = base64.b64encode(file_data).decode('utf-8')
            
            # Determine MIME type
            mime_types = {
                '.png': 'image/png',
                '.jpg': 'image/jpeg',
                '.jpeg': 'image/jpeg',
                '.gif': 'image/gif',
                '.bmp': 'image/bmp',
                '.webp': 'image/webp',
                '.svg': 'image/svg+xml',
            }
            mime_type = mime_types.get(file_ext, 'image/png')
            
            # Create data URL
            data_url = f"data:{mime_type};base64,{base64_data}"
            
            # Return info and data
            return (
                f"Image read successfully!\n"
                f"Path: {path}\n"
                f"Format: {file_ext[1:].upper()}\n"
                f"Size: {file_size_kb:.1f} KB\n"
                f"Base64 length: {len(base64_data)} characters\n"
                f"\n"
                f"Data URL (first 100 chars):\n"
                f"{data_url[:100]}...\n"
                f"\n"
                f"Full data URL:\n"
                f"{data_url}"
            )
            
        except PermissionError:
            return f"Error: Permission denied reading file: {path}"
        except Exception as e:
            return f"Error reading image: {str(e)}"