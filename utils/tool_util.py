"""Tool execution utility with parallel execution support."""

import asyncio
import time
from typing import Any, Dict, List, Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from agent import Agent
    from tools.base import Tool


async def _execute_single_tool(
    call: Any, 
    tool_dict: Dict[str, "Tool"],
    agent: Optional["Agent"] = None
) -> Dict[str, Any]:
    """Execute a single tool and handle errors."""
    start_time = time.perf_counter()
    response: Dict[str, Any] = {"type": "tool_result", "tool_use_id": call.id}

    try:
        # Validate tool exists
        if call.name not in tool_dict:
            raise KeyError(f"Tool '{call.name}' not found")
            
        tool = tool_dict[call.name]
        
        # Execute the tool
        result = await tool.execute(**call.input)
        
        # Ensure result is string
        if result is None:
            result = "Tool returned no output"
        elif not isinstance(result, str):
            result = str(result)
            
        response["content"] = result
        
    except KeyError as e:
        response["content"] = str(e)
        response["is_error"] = True
    except TypeError as e:
        response["content"] = f"Tool error in {call.name}: Invalid arguments - {str(e)}"
        response["is_error"] = True
    except Exception as e:
        response["content"] = f"Tool error in {call.name}: {str(e)}"
        response["is_error"] = True

    # Calculate execution time
    duration_ms = (time.perf_counter() - start_time) * 1000
    
    # Track metrics if agent provided
    if agent and hasattr(agent, 'tool_metrics'):
        is_error = response.get("is_error", False)
        agent.tool_metrics[call.name].record_execution(duration_ms, is_error)
    
    return response


async def execute_tools(
    tool_calls: List[Any], 
    tool_dict: Dict[str, "Tool"], 
    parallel: bool = True,
    agent: Optional["Agent"] = None
) -> List[Dict[str, Any]]:
    """Execute multiple tools sequentially or in parallel.
    
    Args:
        tool_calls: List of tool call requests
        tool_dict: Dictionary mapping tool names to Tool instances
        parallel: Whether to execute tools in parallel
    
    Returns:
        List of tool results with type, content, and metadata
    """
    if parallel:
        results = await asyncio.gather(
            *[_execute_single_tool(call, tool_dict, agent) for call in tool_calls]
        )
        return results
    else:
        return [
            await _execute_single_tool(call, tool_dict, agent) for call in tool_calls
        ]
