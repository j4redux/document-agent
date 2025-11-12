"""Text transformation tools for demonstration of dynamic tool loading."""

from typing import Any
from tools.base import Tool


class TextTransformTool(Tool):
    """Transform text in various ways."""
    
    def __init__(self):
        super().__init__(
            name="text_transform",
            description="Transform text (uppercase, lowercase, reverse, word count, etc.)",
            input_schema={
                "type": "object",
                "properties": {
                    "text": {
                        "type": "string",
                        "description": "The text to transform"
                    },
                    "operation": {
                        "type": "string",
                        "description": "Operation to perform",
                        "enum": ["uppercase", "lowercase", "reverse", "word_count", "char_count", "capitalize"]
                    }
                },
                "required": ["text", "operation"]
            }
        )
    
    async def execute(self, text: str, operation: str) -> str:
        """Transform the text based on the operation."""
        try:
            if operation == "uppercase":
                return f"Uppercase: {text.upper()}"
            elif operation == "lowercase":
                return f"Lowercase: {text.lower()}"
            elif operation == "reverse":
                return f"Reversed: {text[::-1]}"
            elif operation == "word_count":
                count = len(text.split())
                return f"Word count: {count}"
            elif operation == "char_count":
                return f"Character count: {len(text)} (including spaces)"
            elif operation == "capitalize":
                return f"Capitalized: {text.title()}"
            else:
                return f"Unknown operation: {operation}"
        except Exception as e:
            return f"Error: {str(e)}"


class Base64Tool(Tool):
    """Encode or decode text using Base64."""
    
    def __init__(self):
        super().__init__(
            name="base64",
            description="Encode or decode text using Base64",
            input_schema={
                "type": "object",
                "properties": {
                    "text": {
                        "type": "string",
                        "description": "The text to encode or decode"
                    },
                    "operation": {
                        "type": "string",
                        "description": "Operation to perform",
                        "enum": ["encode", "decode"]
                    }
                },
                "required": ["text", "operation"]
            }
        )
    
    async def execute(self, text: str, operation: str) -> str:
        """Encode or decode the text."""
        import base64
        
        try:
            if operation == "encode":
                encoded = base64.b64encode(text.encode()).decode()
                return f"Base64 encoded: {encoded}"
            elif operation == "decode":
                decoded = base64.b64decode(text).decode()
                return f"Base64 decoded: {decoded}"
            else:
                return f"Unknown operation: {operation}"
        except Exception as e:
            return f"Error: {str(e)}"