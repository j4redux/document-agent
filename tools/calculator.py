"""Simple calculator tool for demonstration of dynamic tool loading."""

from typing import Any
from tools.base import Tool


class CalculatorTool(Tool):
    """A simple calculator tool that can perform basic arithmetic operations."""
    
    def __init__(self):
        super().__init__(
            name="calculator",
            description="Perform basic arithmetic calculations",
            input_schema={
                "type": "object",
                "properties": {
                    "expression": {
                        "type": "string",
                        "description": "Mathematical expression to evaluate (e.g., '2 + 2', '10 * 5', '100 / 4')"
                    }
                },
                "required": ["expression"]
            }
        )
    
    async def execute(self, expression: str) -> str:
        """Execute the calculation safely."""
        try:
            # Only allow basic arithmetic operations for safety
            allowed_chars = "0123456789+-*/()., "
            if not all(c in allowed_chars for c in expression):
                return "Error: Invalid characters in expression. Only numbers and basic operators (+, -, *, /, parentheses) are allowed."
            
            # Evaluate the expression
            result = eval(expression)
            return f"Result: {expression} = {result}"
            
        except ZeroDivisionError:
            return "Error: Division by zero"
        except Exception as e:
            return f"Error evaluating expression: {str(e)}"


class RandomNumberTool(Tool):
    """Generate random numbers within a specified range."""
    
    def __init__(self):
        super().__init__(
            name="random_number",
            description="Generate a random number within a specified range",
            input_schema={
                "type": "object",
                "properties": {
                    "min": {
                        "type": "integer",
                        "description": "Minimum value (inclusive)",
                        "default": 1
                    },
                    "max": {
                        "type": "integer", 
                        "description": "Maximum value (inclusive)",
                        "default": 100
                    }
                },
                "required": []
            }
        )
    
    async def execute(self, min: int = 1, max: int = 100) -> str:
        """Generate a random number."""
        import random
        
        if min > max:
            return f"Error: min ({min}) cannot be greater than max ({max})"
            
        number = random.randint(min, max)
        return f"Random number between {min} and {max}: {number}"