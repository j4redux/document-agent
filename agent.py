"""Agent implementation with Claude API, Pydantic Logfire Observability, and tools."""

import asyncio
import json
import os
import sys
from collections import defaultdict
from contextlib import AsyncExitStack, nullcontext
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict, List, Optional

from anthropic import Anthropic
from anthropic.types import Message

try:
    import logfire
    LOGFIRE_AVAILABLE = True
except ImportError:
    logfire = None
    LOGFIRE_AVAILABLE = False

from tools.base import Tool
from utils.history_util import MessageHistory
from utils.tool_util import execute_tools

# MCP connections are optional
try:
    from utils.connections import setup_mcp_connections
    MCP_AVAILABLE = True
except ImportError:
    MCP_AVAILABLE = False
    setup_mcp_connections = None


@dataclass
class ModelConfig:
    """Configuration settings for Claude model parameters."""

    model: str = "claude-sonnet-4-20250514"
    max_tokens: int = 4096
    temperature: float = 1.0
    context_window_tokens: int = 180000


@dataclass
class ToolResult:
    """Structured result from tool execution (internal use only)."""
    
    tool_name: str
    tool_use_id: str
    content: str
    error: Optional[str] = None
    is_error: bool = False
    duration_ms: Optional[float] = None


@dataclass
class ToolMetrics:
    """Metrics for tool execution."""
    
    total_calls: int = 0
    successful_calls: int = 0
    failed_calls: int = 0
    total_duration_ms: float = 0
    min_duration_ms: Optional[float] = None
    max_duration_ms: Optional[float] = None
    
    @property
    def avg_duration_ms(self) -> float:
        """Calculate average duration."""
        return self.total_duration_ms / self.total_calls if self.total_calls > 0 else 0
    
    @property
    def error_rate(self) -> float:
        """Calculate error rate as percentage."""
        return (self.failed_calls / self.total_calls * 100) if self.total_calls > 0 else 0
    
    def record_execution(self, duration_ms: float, is_error: bool = False) -> None:
        """Record a tool execution."""
        self.total_calls += 1
        self.total_duration_ms += duration_ms
        
        if is_error:
            self.failed_calls += 1
        else:
            self.successful_calls += 1
        
        # Update min/max
        if self.min_duration_ms is None or duration_ms < self.min_duration_ms:
            self.min_duration_ms = duration_ms
        if self.max_duration_ms is None or duration_ms > self.max_duration_ms:
            self.max_duration_ms = duration_ms


class Agent:
    """Claude-powered agent with tool use capabilities."""

    def __init__(
        self,
        name: str,
        system: str,
        tools: Optional[List[Tool]] = None,
        mcp_servers: Optional[List[Dict[str, Any]]] = None,
        config: Optional[ModelConfig] = None,
        verbose: bool = False,
        client: Optional[Anthropic] = None,
        message_params: Optional[Dict[str, Any]] = None,
        enable_logfire: bool = False,
        logfire_token: Optional[str] = None,
        max_rounds: Optional[int] = None,
    ) -> None:
        """Initialize an Agent.
        
        Args:
            name: Agent identifier for logging
            system: System prompt for the agent
            tools: List of tools available to the agent
            mcp_servers: MCP server configurations
            config: Model configuration with defaults
            verbose: Enable detailed logging
            client: Anthropic client instance
            message_params: Additional parameters for client.messages.create().
                           These override any conflicting parameters from config.
            enable_logfire: Enable Logfire observability
            logfire_token: Optional Logfire token (uses env var if not provided)
            max_rounds: Maximum number of tool-use rounds (None for unlimited)
        """
        self.name = name
        # Add task organization instructions to all agents
        task_organization = """

TASK ORGANIZATION:
- For complex requests (multiple steps, analysis + creation, or >2 tool calls), use todo_write to break down work before starting
- Always use todos when: using context_prime, creating documentation, multi-step analysis, or requests with "and" in them
- Start complex tasks with: "Let me organize this work first" and create a todo list
- Update todo status as you progress to show transparency

Before executing complex tasks, you MUST:
1. If the request involves multiple distinct steps → use todo_write first
2. If using context_prime → create todos for the full workflow
3. If creating deliverables → plan the structure with todos
4. Show your organized approach before jumping into execution

DEFAULT BEHAVIOR: When in doubt, use todo_write. Better to over-organize than under-organize.
Ask yourself: "Should I break this down into steps?" The answer is almost always YES.

MANDATORY TODO TRIGGERS:
- ANY multi-tool usage
- Context analysis requests  
- File creation/modification tasks
- Research + implementation combos
- Documentation generation
- User requests with conjunctions ("and", "then", "also")"""
        self.base_system = system + task_organization  # Store enhanced system prompt
        # Enhance system prompt with current date and time
        current_time = datetime.now()
        time_context = f"\n\nCurrent date and time: {current_time.strftime('%A, %B %d, %Y at %I:%M %p')}"
        self.system = self.base_system + time_context
        self.verbose = verbose
        self.tools = list(tools or [])
        self.config = config or ModelConfig()
        self.mcp_servers = mcp_servers or []
        self.message_params = message_params or {}
        self.client = client or Anthropic(
            api_key=os.environ.get("ANTHROPIC_API_KEY", "")
        )
        self.history = MessageHistory(
            model=self.config.model,
            system=self.system,
            context_window_tokens=self.config.context_window_tokens,
            client=self.client,
        )
        self.tool_metrics: Dict[str, ToolMetrics] = defaultdict(ToolMetrics)
        self.max_rounds = max_rounds
        self.sources: List[Dict[str, Any]] = []  # For source tracking
        
        # Configure Logfire if enabled
        self._logfire_configured = False
        if enable_logfire and LOGFIRE_AVAILABLE:
            if logfire_token:
                logfire.configure(token=logfire_token)
            else:
                logfire.configure()  # Uses LOGFIRE_TOKEN env var
            logfire.info(f"Agent {name} initialized with Logfire")
            self._logfire_configured = True

        if self.verbose:
            print(f"\n[{self.name}] Agent initialized")

    def _update_system_time(self) -> None:
        """Update the system prompt with current date and time."""
        current_time = datetime.now()
        time_context = f"\n\nCurrent date and time: {current_time.strftime('%A, %B %d, %Y at %I:%M %p')}"
        self.system = self.base_system + time_context

    def _prepare_message_params(self) -> Dict[str, Any]:
        """Prepare parameters for client.messages.create() call.
        
        Returns a dict with base parameters from config, with any
        message_params overriding conflicting keys.
        """
        return {
            "model": self.config.model,
            "max_tokens": self.config.max_tokens,
            "temperature": self.config.temperature,
            "system": self.system,
            "messages": self.history.format_for_api(),
            "tools": [tool.to_dict() for tool in self.tools],
            **self.message_params,
        }

    async def _agent_loop(self, user_input: str) -> Message:
        """Process user input and handle tool calls in a loop"""
        # Update system time for each new interaction
        self._update_system_time()
        
        if self.verbose:
            print(f"\n[{self.name}] Received: {user_input}")
        
        # Create Logfire span for the entire agent loop
        with logfire.span(f"agent.{self.name}.loop", user_input=user_input) if self._logfire_configured else nullcontext():
            if self._logfire_configured:
                logfire.info(f"User: {user_input}")
            
            await self.history.add_message("user", user_input, None)

            tool_dict = {tool.name: tool for tool in self.tools}
            
            rounds = 0
            while True:
                # Check max rounds limit
                if self.max_rounds and rounds >= self.max_rounds:
                    if self.verbose:
                        print(f"\n[{self.name}] Reached max rounds limit ({self.max_rounds})")
                    return Message(content=[{
                        "type": "text", 
                        "text": f"I've reached my maximum number of rounds ({self.max_rounds}). Here's what I've accomplished so far."
                    }])
                    
                self.history.truncate()
                params = self._prepare_message_params()

                # Log API call
                with logfire.span("anthropic.messages.create", 
                                 model=params.get("model"),
                                 max_tokens=params.get("max_tokens")) if self._logfire_configured else nullcontext():
                    response = self.client.messages.create(**params)
                    
                    if self._logfire_configured:
                        # Log the actual response content
                        for block in response.content:
                            if block.type == "text":
                                logfire.info(f"Assistant: {block.text}")
                            elif block.type == "tool_use":
                                logfire.info(f"Assistant requests tool: {block.name}",
                                           tool_name=block.name,
                                           tool_input=str(block.input))
                
                tool_calls = [
                    block for block in response.content if block.type == "tool_use"
                ]

                if self.verbose:
                    for block in response.content:
                        if block.type == "text":
                            print(f"\n[{self.name}] Output: {block.text}")
                        elif block.type == "tool_use":
                            params_str = ", ".join(
                                [f"{k}={v}" for k, v in block.input.items()]
                            )
                            print(
                                f"\n[{self.name}] Tool call: "
                                f"{block.name}({params_str})"
                            )

                # Always add assistant message to history
                # This is required to maintain tool_use/tool_result pairing
                await self.history.add_message(
                    "assistant", response.content, response.usage
                )

                if tool_calls:
                    rounds += 1  # Increment round counter
                    # Log tool execution
                    with logfire.span("tools.execute", 
                                     tool_count=len(tool_calls)) if self._logfire_configured else nullcontext():
                        tool_results = await execute_tools(
                            tool_calls,
                            tool_dict,
                            agent=self,
                        )
                        
                        if self._logfire_configured:
                            for call, result in zip(tool_calls, tool_results):
                                content = result.get("content", "")
                                logfire.info(f"Tool {call.name}: {content}")
                    
                    if self.verbose:
                        for block in tool_results:
                            print(
                                f"\n[{self.name}] Tool result: "
                                f"{block.get('content')}"
                            )
                    await self.history.add_message("user", tool_results)
                else:
                    if self._logfire_configured:
                        logfire.info(f"Agent {self.name} completed",
                                    total_tokens=self.history.total_tokens)
                    
                    return response

    async def run_async(self, user_input: str) -> Message:
        """Run agent with MCP tools asynchronously."""
        async with AsyncExitStack() as stack:
            original_tools = list(self.tools)

            try:
                # Only try to setup MCP if it's available
                if MCP_AVAILABLE and setup_mcp_connections and self.mcp_servers:
                    mcp_tools = await setup_mcp_connections(
                        self.mcp_servers, stack
                    )
                    self.tools.extend(mcp_tools)
                return await self._agent_loop(user_input)
            finally:
                self.tools = original_tools

    def run(self, user_input: str) -> Message:
        """Run agent synchronously"""
        return asyncio.run(self.run_async(user_input))
    
    def get_tool_metrics(self) -> Dict[str, Dict[str, Any]]:
        """Get metrics for all tools.
        
        Returns:
            Dictionary mapping tool names to their metrics
        """
        metrics = {}
        for tool_name, tool_metric in self.tool_metrics.items():
            if tool_metric.total_calls > 0:
                metrics[tool_name] = {
                    "total_calls": tool_metric.total_calls,
                    "successful_calls": tool_metric.successful_calls,
                    "failed_calls": tool_metric.failed_calls,
                    "error_rate": f"{tool_metric.error_rate:.1f}%",
                    "avg_duration_ms": f"{tool_metric.avg_duration_ms:.3f}",
                    "min_duration_ms": f"{tool_metric.min_duration_ms:.3f}" if tool_metric.min_duration_ms is not None else "N/A",
                    "max_duration_ms": f"{tool_metric.max_duration_ms:.3f}" if tool_metric.max_duration_ms is not None else "N/A",
                    "total_duration_ms": f"{tool_metric.total_duration_ms:.3f}"
                }
        return metrics
    
    def save_conversation(self, filename: str) -> str:
        """Save the current conversation history to a JSON file.
        
        Args:
            filename: Path to save the conversation
            
        Returns:
            Success or error message
        """
        try:
            # Prepare conversation data
            conversation_data = {
                "agent_name": self.name,
                "model": self.config.model,
                "timestamp": datetime.now().isoformat(),
                "total_tokens": self.history.total_tokens,
                "messages": self.history.messages,
                "system_prompt": self.base_system,
                "config": {
                    "max_tokens": self.config.max_tokens,
                    "temperature": self.config.temperature,
                    "context_window_tokens": self.config.context_window_tokens
                }
            }
            
            # Ensure .json extension
            if not filename.endswith('.json'):
                filename += '.json'
            
            # Save to file
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(conversation_data, f, indent=2, ensure_ascii=False)
            
            return f"Conversation saved to {filename}"
            
        except Exception as e:
            return f"Error saving conversation: {str(e)}"
    
    def load_conversation(self, filename: str) -> str:
        """Load a conversation history from a JSON file.
        
        Args:
            filename: Path to load the conversation from
            
        Returns:
            Success or error message
        """
        try:
            # Ensure .json extension
            if not filename.endswith('.json'):
                filename += '.json'
            
            # Load from file
            with open(filename, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            # Restore conversation state
            self.history.messages = data.get("messages", [])
            self.history.total_tokens = data.get("total_tokens", 0)
            
            # Rebuild message tokens list (approximate)
            self.history.message_tokens = []
            for i in range(0, len(self.history.messages), 2):
                if i + 1 < len(self.history.messages):
                    # Approximate tokens
                    user_msg = self.history.messages[i]
                    assistant_msg = self.history.messages[i + 1]
                    user_tokens = len(str(user_msg)) // 4
                    assistant_tokens = len(str(assistant_msg)) // 4
                    self.history.message_tokens.append((user_tokens, assistant_tokens))
            
            loaded_info = [
                f"Loaded conversation from {filename}",
                f"  Original agent: {data.get('agent_name', 'Unknown')}",
                f"  Timestamp: {data.get('timestamp', 'Unknown')}",
                f"  Messages: {len(self.history.messages)}",
                f"  Total tokens: {self.history.total_tokens}"
            ]
            
            return "\n".join(loaded_info)
            
        except FileNotFoundError:
            return f"Error: File '{filename}' not found"
        except json.JSONDecodeError:
            return f"Error: Invalid JSON in file '{filename}'"
        except Exception as e:
            return f"Error loading conversation: {str(e)}"
    
    def export_markdown(self, filename: Optional[str] = None) -> str:
        """Export the conversation as a markdown file.
        
        Args:
            filename: Optional filename to save to. If not provided, generates one.
            
        Returns:
            Success or error message
        """
        try:
            # Generate filename if not provided
            if not filename:
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                filename = f"conversation_{self.name}_{timestamp}.md"
            elif not filename.endswith('.md'):
                filename += '.md'
            
            # Build markdown content
            lines = [
                f"# Conversation with {self.name}",
                f"\n**Model**: {self.config.model}",
                f"**Date**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
                f"**Total tokens**: {self.history.total_tokens}",
                "\n---\n"
            ]
            
            # Add messages
            for msg in self.history.messages:
                role = msg["role"].capitalize()
                content_blocks = msg["content"]
                
                if role == "User":
                    lines.append(f"\n## 👤 {role}\n")
                else:
                    lines.append(f"\n## 🤖 {role}\n")
                
                for block in content_blocks:
                    if block.get("type") == "text":
                        lines.append(block["text"])
                    elif block.get("type") == "tool_use":
                        lines.append(f"\n**Tool Call**: `{block.get('name', 'unknown')}()`\n")
                        lines.append("```json")
                        lines.append(json.dumps(block.get('input', {}), indent=2))
                        lines.append("```\n")
                    elif block.get("type") == "tool_result":
                        lines.append(f"\n**Tool Result**:\n")
                        lines.append("```")
                        lines.append(block.get('content', ''))
                        lines.append("```\n")
            
            # Save to file
            with open(filename, 'w', encoding='utf-8') as f:
                f.write("\n".join(lines))
            
            return f"Conversation exported to {filename}"
            
        except Exception as e:
            return f"Error exporting conversation: {str(e)}"
    
    def summarize_conversation(self) -> str:
        """Use the API to generate a summary of the current conversation.
        
        Returns:
            Summary text or error message
        """
        try:
            if not self.history.messages:
                return "No conversation to summarize"
            
            # Prepare a summary request
            summary_messages = [
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "text",
                            "text": "Please provide a concise summary of our conversation so far, highlighting the main topics discussed and any key decisions or outcomes."
                        }
                    ]
                }
            ]
            
            # Create a summary using the API
            response = self.client.messages.create(
                model=self.config.model,
                max_tokens=500,
                temperature=0.5,
                system="You are a helpful assistant that creates concise summaries of conversations.",
                messages=self.history.messages + summary_messages
            )
            
            # Extract summary text
            for block in response.content:
                if block.type == "text":
                    return block.text
            
            return "Could not generate summary"
            
        except Exception as e:
            return f"Error generating summary: {str(e)}"
    
    def interactive_mode(self) -> None:
        """Run the agent in interactive mode with markdown rendering."""
        from rich.console import Console
        from rich.markdown import Markdown
        
        console = Console()
        
        console.print(f"[bold]Chat with Claude - {self.name}[/bold]")
        console.print(f"[dim]Model: {self.config.model}[/dim]")
        if self.tools:
            console.print(f"[dim]Tools: {', '.join([tool.name for tool in self.tools])}[/dim]")
        console.print("[dim]Type /help for commands or Ctrl+C to quit[/dim]")
        console.rule()
        
        # Reset history for fresh conversation with updated time
        self._update_system_time()
        self.history = MessageHistory(
            model=self.config.model,
            system=self.system,
            context_window_tokens=self.config.context_window_tokens,
            client=self.client,
        )
        
        # Ensure Logfire is configured if it was enabled
        if self._logfire_configured:
            # Logfire is already configured, just log the start of interactive mode
            logfire.info(f"Agent {self.name} started interactive mode")
            # Ensure all output is flushed before showing the prompt
            console.print()  # Empty line to ensure Logfire output appears first
            sys.stdout.flush()
            sys.stderr.flush()
        
        # Initialize retry message attribute
        self._retry_message = None
        
        while True:
            try:
                # Check if we have a retry message
                if self._retry_message:
                    user_input = self._retry_message
                    self._retry_message = None
                else:
                    # Get user input
                    console.print("[blue]You:[/blue] ", end="")
                    user_input = input().strip()
                    
                    if not user_input:
                        continue
                    
                    # Check for commands
                    if user_input.startswith("/"):
                        if self._process_command(user_input):
                            continue
                
                # Run agent
                response = self.run(user_input)
                
                # Display response
                for block in response.content:
                    if block.type == "text":
                        console.print(f"\n[yellow]{self.name}:[/yellow]")
                        md = Markdown(block.text)
                        console.print(md)
                        
            except (EOFError, KeyboardInterrupt):
                console.print("\n\n[dim]Goodbye![/dim]")
                break
            except Exception as e:
                console.print(f"\n[red]Error: {str(e)}[/red]")
                if self.verbose:
                    import traceback
                    traceback.print_exc()
    
    def _process_command(self, command_input: str) -> bool:
        """Process special commands in interactive mode.
        
        Returns:
            True if command was processed, False otherwise
        """
        parts = command_input[1:].split(maxsplit=1)
        if not parts:
            return False
            
        command = parts[0].lower()
        
        if command == "help":
            print("\nAvailable commands:")
            print("  /help          - Show this help message")
            print("  /tools         - List available tools")
            print("  /clear         - Clear conversation history")
            print("  /history       - Show conversation history stats")
            print("  /system        - Show system prompt")
            print("  /model         - Show model configuration")
            print("  /metrics       - Show tool execution metrics")
            print("  /save <file>   - Save conversation to file")
            print("  /load <file>   - Load conversation from file")
            print("  /export        - Export conversation as markdown")
            print("  /summarize     - Summarize current conversation")
            print("  /retry         - Retry the last response")
            print("  /config        - Show current agent configuration")
            return True
            
        elif command == "tools":
            if not self.tools:
                print("No tools available")
            else:
                print("\nAvailable tools:")
                for tool in self.tools:
                    print(f"  • {tool.name}: {tool.description}")
            return True
            
        elif command == "clear":
            # Update system time when clearing conversation
            self._update_system_time()
            self.history = MessageHistory(
                model=self.config.model,
                system=self.system,
                context_window_tokens=self.config.context_window_tokens,
                client=self.client,
            )
            if self._logfire_configured:
                logfire.info(f"Agent {self.name} conversation cleared")
            print("Conversation history cleared")
            return True
            
        elif command == "history":
            print(f"\nConversation history:")
            print(f"  Messages: {len(self.history.messages)}")
            print(f"  Total tokens: {self.history.total_tokens}")
            print(f"  Context window: {self.config.context_window_tokens}")
            return True
            
        elif command == "system":
            print(f"\nBase system prompt:")
            print(f"  {self.base_system}")
            print(f"\nCurrent enhanced prompt includes:")
            current_time = datetime.now()
            print(f"  Date/time: {current_time.strftime('%A, %B %d, %Y at %I:%M %p')}")
            return True
            
        elif command == "model":
            print(f"\nModel configuration:")
            print(f"  Model: {self.config.model}")
            print(f"  Max tokens: {self.config.max_tokens}")
            print(f"  Temperature: {self.config.temperature}")
            return True
            
        elif command == "metrics":
            metrics = self.get_tool_metrics()
            if not metrics:
                print("\nNo tool metrics available yet")
            else:
                print("\nTool Execution Metrics:")
                print("-" * 60)
                for tool_name, tool_stats in metrics.items():
                    print(f"\n{tool_name}:")
                    print(f"  Total calls: {tool_stats['total_calls']}")
                    print(f"  Successful: {tool_stats['successful_calls']}")
                    print(f"  Failed: {tool_stats['failed_calls']}")
                    print(f"  Error rate: {tool_stats['error_rate']}")
                    print(f"  Avg duration: {tool_stats['avg_duration_ms']}ms")
                    print(f"  Min duration: {tool_stats['min_duration_ms']}ms")
                    print(f"  Max duration: {tool_stats['max_duration_ms']}ms")
            return True
            
        elif command == "save":
            if len(parts) < 2:
                print("Error: Please specify a filename (e.g., /save conversation.json)")
                return True
            filename = parts[1]
            result = self.save_conversation(filename)
            print(result)
            return True
            
        elif command == "load":
            if len(parts) < 2:
                print("Error: Please specify a filename (e.g., /load conversation.json)")
                return True
            filename = parts[1]
            result = self.load_conversation(filename)
            print(result)
            return True
            
        elif command == "export":
            result = self.export_markdown()
            print(result)
            return True
            
        elif command == "summarize":
            print("\nSummarizing conversation...")
            summary = self.summarize_conversation()
            print(f"\nSummary:\n{summary}")
            return True
            
        elif command == "retry":
            if len(self.history.messages) < 2:
                print("No previous message to retry")
                return True
            # Remove last assistant message and re-run with last user message
            last_user_msg = None
            for i in range(len(self.history.messages) - 1, -1, -1):
                if self.history.messages[i]["role"] == "user":
                    last_user_msg = self.history.messages[i]["content"]
                    break
            if last_user_msg and isinstance(last_user_msg, list) and last_user_msg[0].get("type") == "text":
                # Remove messages after last user message
                while self.history.messages and self.history.messages[-1]["role"] != "user":
                    self.history.messages.pop()
                    if self.history.message_tokens:
                        self.history.message_tokens.pop()
                print("\nRetrying last response...")
                # Return False to let the main loop handle it as a regular message
                # But we need to inject the message back
                self._retry_message = last_user_msg[0]["text"]
                return False
            else:
                print("Could not find a valid user message to retry")
                return True
                
        elif command == "config":
            print("\nCurrent Agent Configuration:")
            print(f"  Name: {self.name}")
            print(f"  Model: {self.config.model}")
            print(f"  Max tokens: {self.config.max_tokens}")
            print(f"  Temperature: {self.config.temperature}")
            print(f"  Context window: {self.config.context_window_tokens} tokens")
            print(f"  Verbose mode: {self.verbose}")
            print(f"  Logfire enabled: {self._logfire_configured}")
            print(f"  Number of tools: {len(self.tools)}")
            if self.message_params:
                print(f"  Custom message params: {list(self.message_params.keys())}")
            return True
            
        else:
            print(f"Unknown command: /{command}")
            print("Type /help for available commands")
            return True
