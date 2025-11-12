"""Tool for creating sub-agents to handle specific tasks."""

import asyncio
import json
from typing import Dict, Any, List, Optional
from tools.base import Tool


class AgentTool(Tool):
    """Create sub-agents to handle specific tasks independently."""
    
    def __init__(self, parent_tools: Optional[List[Tool]] = None):
        super().__init__(
            name="agent",
            description="""Create a sub-agent to handle a specific task independently.
            
            Use this when you need to:
            - Delegate a complex sub-task
            - Search through many files for specific patterns
            - Perform multi-step operations autonomously
            - Research a topic thoroughly
            
            The sub-agent has access to the same tools and will return a summary of its work.
            
            Example: agent(task="Find all TODO comments in the codebase and categorize them", plan="1. Search for TODO patterns 2. Group by file 3. Categorize by type")""",
            input_schema={
                "type": "object",
                "properties": {
                    "task": {
                        "type": "string",
                        "description": "Clear description of what the sub-agent should accomplish"
                    },
                    "plan": {
                        "type": "string", 
                        "description": "Suggested approach or steps for the sub-agent to follow"
                    },
                    "max_iterations": {
                        "type": "integer",
                        "description": "Maximum number of tool calls the sub-agent can make",
                        "default": 10
                    }
                },
                "required": ["task"]
            }
        )
        self.parent_tools = parent_tools or []
        
    async def execute(self, task: str, plan: str = "", max_iterations: int = 10) -> str:
        """Create and run a sub-agent for the specified task."""
        try:
            # Import here to avoid circular dependency
            from agent import Agent
            
            # Create sub-agent with focused system prompt
            system_prompt = f"""You are a focused sub-agent with a specific task.

YOUR TASK: {task}

{f"SUGGESTED APPROACH: {plan}" if plan else ""}

IMPORTANT INSTRUCTIONS:
1. Focus ONLY on completing the assigned task
2. Use tools efficiently - batch operations when possible
3. Be thorough but concise in your approach
4. Return a clear summary of what you accomplished
5. If you cannot complete the task, explain why

You have access to the same tools as the main agent. Work autonomously to complete your task."""

            # Create sub-agent with same tools but focused prompt
            sub_agent = Agent(
                name=f"Sub-Agent: {task[:30]}...",
                system=system_prompt,
                tools=self.parent_tools,
                max_rounds=max_iterations,  # Now this parameter exists!
                verbose=False  # Less verbose for sub-agents
            )
            
            # Run the sub-agent
            result = await sub_agent.run_async(f"Complete this task: {task}")
            
            # Format the response
            # Extract text from Message object
            if hasattr(result, 'content'):
                result_text = ""
                for block in result.content:
                    if hasattr(block, 'text'):
                        result_text += block.text + "\n"
            else:
                result_text = str(result)
                
            return f"""Sub-agent completed task: {task}

Result:
{result_text}

Tool calls made: {len(sub_agent.history.messages) // 2}"""
            
        except Exception as e:
            return f"Sub-agent failed: {str(e)}"