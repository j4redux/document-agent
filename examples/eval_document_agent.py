#!/usr/bin/env python3
"""Evaluation framework for the Document Agent based on agent patterns."""

import asyncio
import json
import os
import time
from dataclasses import dataclass
from typing import List, Dict, Any, Optional, Tuple
from pathlib import Path
import difflib
from anthropic import Anthropic

# Load environment variables
from dotenv import load_dotenv
load_dotenv()

from agent import Agent, ModelConfig
from tools.file_tools import FileWriteTool, FileReadTool
from tools.text_transform import TextTransformTool
from tools.web_tool import WebTool
from tools.calculator import CalculatorTool
from tools.system_tools import create_linked_todo_tools


@dataclass
class TestCase:
    """Single test case for evaluation."""
    id: str
    task: str
    expected_output: Optional[str] = None
    expected_actions: Optional[List[str]] = None
    category: str = "general"
    max_turns: int = 10
    
    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return {
            "id": self.id,
            "task": self.task,
            "expected_output": self.expected_output,
            "expected_actions": self.expected_actions,
            "category": self.category,
            "max_turns": self.max_turns
        }


@dataclass
class EvalResult:
    """Result of a single evaluation."""
    test_case: TestCase
    success: bool
    actual_output: str
    tool_calls: List[Dict[str, Any]]
    duration_seconds: float
    error: Optional[str] = None
    similarity_score: Optional[float] = None
    
    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return {
            "test_case": self.test_case.to_dict(),
            "success": self.success,
            "actual_output": self.actual_output,
            "tool_calls": self.tool_calls,
            "duration_seconds": self.duration_seconds,
            "error": self.error,
            "similarity_score": self.similarity_score
        }


class DocumentAgentEvaluator:
    """Evaluator for the Document Agent."""
    
    def __init__(self, verbose: bool = False):
        """Initialize evaluator."""
        self.verbose = verbose
        self.client = Anthropic()
        
    def create_test_agent(self) -> Agent:
        """Create the actual document agent for testing."""
        # Import the actual document agent creation logic
        from document_agent import main
        
        # Create linked todo tools
        todo_read, todo_write = create_linked_todo_tools()
        
        # Create list of base tools (same as in document_agent.py)
        from tools.calculator import CalculatorTool, RandomNumberTool
        from tools.file_tools import FileReadTool, FileWriteTool, FileSearchTool
        from tools.system_tools import CatTool, LsTool, FindTool, GrepTool, ContextPrimeTool
        from tools.text_transform import TextTransformTool, Base64Tool
        from tools.think import ThinkTool
        from tools.weather import WeatherTool
        from tools.web_tool import WebTool
        from tools.image_tool import ImageTool
        from tools.notebook_tool import NotebookTool
        from tools.bash_enhanced import BashEnhancedTool
        from tools.multi_edit import MultiEditTool
        from tools.git_tool import GitTool
        from tools.agent_tool import AgentTool
        
        base_tools = [
            CalculatorTool(),
            RandomNumberTool(),
            FileReadTool(),
            FileWriteTool(),
            FileSearchTool(),
            CatTool(),
            LsTool(),
            FindTool(),
            GrepTool(),
            ContextPrimeTool(),
            todo_read,
            todo_write,
            TextTransformTool(),
            Base64Tool(),
            ThinkTool(),
            WeatherTool(),
            WebTool(),
            ImageTool(),
            NotebookTool(),
            BashEnhancedTool(),
            MultiEditTool(),
            GitTool(),
        ]
        
        # Create AgentTool with access to all other tools
        agent_tool = AgentTool(parent_tools=base_tools)
        
        # Add AgentTool to the full list
        all_tools = base_tools + [agent_tool]
        
        # Use the actual document agent system prompt with evaluation-specific adjustments
        general_purpose_prompt = """You are an interactive CLI tool that helps users with document editing, research, and writing tasks. Use the instructions below and the tools available to you to assist the user.

# Tone and style
You should be concise, direct, and to the point. When you run a non-trivial bash command, you should explain what the command does and why you are running it, to make sure the user understands what you are doing (this is especially important when you are running a command that will make changes to the user's system).
Remember that your output will be displayed on a command line interface. Your responses can use Github-flavored markdown for formatting, and will be rendered in a monospace font using the CommonMark specification.
Output text to communicate with the user; all text you output outside of tool use is displayed to the user. Only use tools to complete tasks. Never use tools like Bash or code comments as means to communicate with the user during the session.
If you cannot or will not help the user with something, please do not say why or what it could lead to, since this comes across as preachy and annoying. Please offer helpful alternatives if possible, and otherwise keep your response to 1-2 sentences.
Only use emojis if the user explicitly requests it. Avoid using emojis in all communication unless asked.
IMPORTANT: You should minimize output tokens as much as possible while maintaining helpfulness, quality, and accuracy. Only address the specific query or task at hand, avoiding tangential information unless absolutely critical for completing the request. If you can answer in 1-3 sentences or a short paragraph, please do.
IMPORTANT: You should NOT answer with unnecessary preamble or postamble (such as explaining your code or summarizing your action), unless the user asks you to.
IMPORTANT: Keep your responses short, since they will be displayed on a command line interface. You MUST answer concisely with fewer than 4 lines (not including tool use or code generation), unless user asks for detail. Answer the user's question directly, without elaboration, explanation, or details. One word answers are best. Avoid introductions, conclusions, and explanations. You MUST avoid text before/after your response, such as "The answer is <answer>.", "Here is the content of the file..." or "Based on the information provided, the answer is..." or "Here is what I will do next...". 

EVALUATION MODE: When completing tasks, provide minimal confirmation of what was accomplished. For file operations, briefly confirm the file and key content. For calculations, show the result. For lists or plans, show the items created. Here are some examples to demonstrate appropriate verbosity:
<example>
user: 2 + 2
assistant: 4
</example>

<example>
user: what is 2+2?
assistant: 4
</example>

<example>
user: is 11 a prime number?
assistant: Yes
</example>

<example>
user: what command should I run to list files in the current directory?
assistant: ls
</example>

<example>
user: what command should I run to watch files in the current directory?
assistant: [use the ls tool to list the files in the current directory, then read docs/commands in the relevant file to find out how to watch files]
npm run dev
</example>

<example>
user: How many golf balls fit inside a jetta?
assistant: 150000
</example>

<example>
user: what files are in the directory src/?
assistant: [runs ls and sees foo.c, bar.c, baz.c]
user: which file contains the implementation of foo?
assistant: src/foo.c
</example>

<example>
user: write tests for new feature
assistant: [uses grep and glob search tools to find where similar tests are defined, uses concurrent read file tool use blocks in one tool call to read relevant files at the same time, uses edit file tool to write new tests]
</example>

# Proactiveness
You are allowed to be proactive, but only when the user asks you to do something. You should strive to strike a balance between:
1. Doing the right thing when asked, including taking actions and follow-up actions
2. Not surprising the user with actions you take without asking
For example, if the user asks you how to approach something, you should do your best to answer their question first, and not immediately jump into taking actions.
3. Do not add additional explanation summary unless requested by the user. After working on a file, just stop, rather than providing an explanation of what you did.

# Following conventions
When making changes to files, first understand the file's conventions. Mimic writing style, use existing document structure, and follow existing patterns.
- When you create a new document, first look at existing documents to see how they're written; then consider structure, tone, formatting conventions.
- When you edit a document, first look at the document's surrounding context to understand the writing style and formatting choices.
- Always follow best practices for the type of document you're working with (emails, reports, essays, etc.).

# Task Management
You have access to the TodoWrite and TodoRead tools to help you manage and plan tasks. Use these tools for COMPLEX TASKS that have multiple steps or require coordination.

DO use todos when:
- Task has 3+ distinct steps
- Multiple files need to be created/modified
- Research + implementation is required
- User explicitly lists multiple numbered tasks

DON'T use todos for:
- Simple calculations
- Single file operations
- Basic text transformations
- Direct questions with simple answers

It is critical that you mark todos as completed as soon as you are done with a task. Do not batch up multiple tasks before marking them as completed.

Examples:

<example>
user: Run the build and fix any type errors
assistant: I'm going to use the TodoWrite tool to write the following items to the todo list: 
- Run the build
- Fix any type errors

I'm now going to run the build using Bash.

Looks like I found 10 type errors. I'm going to use the TodoWrite tool to write 10 items to the todo list.

marking the first todo as in_progress

Let me start working on the first item...

The first item has been fixed, let me mark the first todo as completed, and move on to the second item...
..
..
</example>
In the above example, the assistant completes all the tasks, including the 10 error fixes and running the build and fixing all errors.

<example>
user: Help me write a new feature that allows users to track their usage metrics and export them to various formats

assistant: I'll help you implement a usage metrics tracking and export feature. Let me first use the TodoWrite tool to plan this task.
Adding the following todos to the todo list:
1. Research existing metrics tracking in the codebase
2. Design the metrics collection system
3. Implement core metrics tracking functionality
4. Create export functionality for different formats

Let me start by researching the existing codebase to understand what metrics we might already be tracking and how we can build on that.

I'm going to search for any existing metrics or telemetry code in the project.

I've found some existing telemetry code. Let me mark the first todo as in_progress and start designing our metrics tracking system based on what I've learned...

[Assistant continues implementing the feature step by step, marking todos as in_progress and completed as they go]
</example>

# Doing tasks
The user will primarily request you perform document editing, research, and writing tasks. This includes creating reports, editing markdown files, researching topics, writing emails, and more. For these tasks the following steps are recommended:
- Use the TodoWrite tool to plan the task if required
- Use the available search tools to understand existing documents and the user's query. You are encouraged to use the search tools extensively both in parallel and sequentially.
- Implement the solution using all tools available to you
- When researching online, use the web tool to gather information from multiple sources
- When editing documents, maintain consistency with existing style and formatting

# Tool usage policy
- When doing file search, prefer to use the Task tool in order to reduce context usage.
- You have the capability to call multiple tools in a single response. When multiple independent pieces of information are requested, batch your tool calls together for optimal performance. When making multiple bash tool calls, you MUST send a single message with multiple tools calls to run the calls in parallel. For example, if you need to run "git status" and "git diff", send a single message with two tool calls to run the calls in parallel.

You MUST answer concisely with fewer than 4 lines of text (not including tool use or code generation), unless user asks for detail.

IMPORTANT: Always use the TodoWrite tool to plan and track tasks throughout the conversation.

# Document References

When referencing specific sections or content include the pattern `file_path:line_number` to allow the user to easily navigate to the source location.

<example>
user: Where is the executive summary in the report?
assistant: The executive summary is in report.md:15.
</example>"""
        
        return Agent(
            name="Document Agent",
            system=general_purpose_prompt,
            tools=all_tools,
            verbose=self.verbose,
            config=ModelConfig(
                model="claude-3-5-haiku-20241022",  # Use faster model for eval
                max_tokens=1024,
                temperature=0.5
            )
        )
    
    def calculate_similarity(self, expected: str, actual: str) -> float:
        """Calculate similarity between expected and actual output."""
        # Use difflib for sequence matching
        return difflib.SequenceMatcher(None, expected.lower(), actual.lower()).ratio()
    
    async def evaluate_single(self, agent: Agent, test_case: TestCase) -> EvalResult:
        """Evaluate a single test case."""
        start_time = time.time()
        tool_calls = []
        
        try:
            # Clear agent history for fresh evaluation
            agent.history.messages = []
            agent.history.message_tokens = []
            agent.history.total_tokens = 0
            # Clear tool metrics for this test
            agent.tool_metrics.clear()
            
            # Run the test
            response = await agent.run_async(test_case.task)
            
            # Extract text output
            actual_output = ""
            for block in response.content:
                if block.type == "text":
                    actual_output += block.text
            
            # Extract tool calls from metrics
            for tool_name in agent.tool_metrics:
                if agent.tool_metrics[tool_name].total_calls > 0:
                    tool_calls.append({
                        "name": tool_name,
                        "input": {}  # We don't track inputs in metrics
                    })
            
            # Calculate success
            success = True
            similarity_score = None
            
            # Evaluate based on task completion
            if test_case.expected_output:
                # Strip whitespace and punctuation for comparison
                expected_clean = test_case.expected_output.strip().lower()
                actual_clean = actual_output.strip().lower()
                
                # Check for exact match first
                if expected_clean == actual_clean:
                    similarity_score = 1.0
                    success = True
                # Check if expected is contained in actual (for verbose responses)
                elif expected_clean in actual_clean:
                    similarity_score = 0.9
                    success = True
                else:
                    similarity_score = self.calculate_similarity(
                        test_case.expected_output, 
                        actual_output
                    )
                    success = similarity_score > 0.7  # 70% similarity threshold for doc agent
            
            # For tasks without expected output, check if key tools were used
            if test_case.expected_actions and not test_case.expected_output:
                tool_names = [tc["name"] for tc in tool_calls]
                # Success if at least one expected tool was used
                success = any(action in tool_names for action in test_case.expected_actions)
                
            # Special handling for different task types
            if test_case.category == "file_ops" or test_case.category == "document_creation":
                # File operations succeed if file_write was used
                if "file_write" in [tc["name"] for tc in tool_calls]:
                    success = True
            elif test_case.category == "planning":
                # Planning tasks succeed if todo_write was used
                if "todo_write" in [tc["name"] for tc in tool_calls]:
                    success = True
            elif test_case.category == "calculation" or test_case.category == "data_processing":
                # Calc tasks need calculator tool
                if "calculator" in [tc["name"] for tc in tool_calls]:
                    if not test_case.expected_output or similarity_score >= 0.7:
                        success = True
            
            duration = time.time() - start_time
            
            return EvalResult(
                test_case=test_case,
                success=success,
                actual_output=actual_output,
                tool_calls=tool_calls,
                duration_seconds=duration,
                similarity_score=similarity_score
            )
            
        except Exception as e:
            duration = time.time() - start_time
            return EvalResult(
                test_case=test_case,
                success=False,
                actual_output="",
                tool_calls=tool_calls,
                duration_seconds=duration,
                error=str(e)
            )
    
    async def evaluate_batch(
        self, 
        test_cases: List[TestCase], 
        max_concurrent: int = 3
    ) -> List[EvalResult]:
        """Evaluate multiple test cases concurrently."""
        results = []
        
        # Process in batches to avoid overwhelming the API
        for i in range(0, len(test_cases), max_concurrent):
            batch = test_cases[i:i + max_concurrent]
            
            # Create separate agents for concurrent execution
            tasks = []
            for test_case in batch:
                agent = self.create_test_agent()
                tasks.append(self.evaluate_single(agent, test_case))
            
            # Run batch concurrently
            batch_results = await asyncio.gather(*tasks)
            results.extend(batch_results)
            
            if self.verbose:
                print(f"Completed {len(results)}/{len(test_cases)} evaluations")
        
        return results
    
    def generate_report(self, results: List[EvalResult]) -> Dict[str, Any]:
        """Generate evaluation report."""
        total = len(results)
        successful = sum(1 for r in results if r.success)
        
        # Group by category
        by_category = {}
        for result in results:
            category = result.test_case.category
            if category not in by_category:
                by_category[category] = {"total": 0, "successful": 0}
            by_category[category]["total"] += 1
            if result.success:
                by_category[category]["successful"] += 1
        
        # Calculate category success rates
        category_rates = {}
        for category, stats in by_category.items():
            category_rates[category] = stats["successful"] / stats["total"] if stats["total"] > 0 else 0
        
        # Tool usage statistics
        tool_usage = {}
        for result in results:
            for tool_call in result.tool_calls:
                tool_name = tool_call["name"]
                tool_usage[tool_name] = tool_usage.get(tool_name, 0) + 1
        
        # Average duration
        avg_duration = sum(r.duration_seconds for r in results) / total if total > 0 else 0
        
        return {
            "summary": {
                "total_tests": total,
                "successful": successful,
                "failed": total - successful,
                "success_rate": successful / total if total > 0 else 0,
                "average_duration_seconds": avg_duration
            },
            "by_category": category_rates,
            "tool_usage": tool_usage,
            "failures": [
                {
                    "test_id": r.test_case.id,
                    "task": r.test_case.task,
                    "error": r.error,
                    "actual_output": r.actual_output[:200] + "..." if len(r.actual_output) > 200 else r.actual_output
                }
                for r in results if not r.success
            ]
        }


def create_test_suite() -> List[TestCase]:
    """Create a comprehensive test suite for the document agent."""
    return [
        # Basic calculations - document agent should be concise
        TestCase(
            id="calc_1",
            task="What is 15 * 23?",
            expected_output="345",
            expected_actions=["calculator"],
            category="calculation"
        ),
        
        # Text transformation
        TestCase(
            id="text_1",
            task="Convert 'hello world' to uppercase",
            expected_output="HELLO WORLD",
            expected_actions=["text_transform"],
            category="text"
        ),
        
        # File operations - document agent should handle file tasks
        TestCase(
            id="file_1",
            task="Create a file called test_eval.txt with the content 'Evaluation test'",
            expected_actions=["file_write"],
            category="file_ops"
        ),
        
        # Complex task - document agent should use todos for multi-step tasks
        TestCase(
            id="complex_1",
            task="Create a report with: 1) Calculate 50 * 30, 2) Save result to calc_result.txt, 3) Create a summary file report.md",
            expected_actions=["todo_write"],  # Should at least use todo_write
            category="complex",
            max_turns=15
        ),
        
        # Document creation test
        TestCase(
            id="doc_1",
            task="Create a markdown file called summary.md with a brief 2-line summary about Python programming",
            expected_actions=["file_write"],
            category="document_creation"
        ),
        
        # Weather task - test tool usage
        TestCase(
            id="weather_1",
            task="Check the weather in New York and tell me the temperature",
            expected_actions=["weather"],  # Should use weather tool
            category="research"
        ),
        
        # Text analysis
        TestCase(
            id="text_2",
            task="Count the words in 'The quick brown fox jumps over the lazy dog'",
            expected_output="9",
            expected_actions=["text_transform"],
            category="text"
        ),
        
        # Todo planning - document agent should use todos
        TestCase(
            id="todo_1",
            task="Create a todo list with these 3 items: analyze data, write summary, review results",
            expected_actions=["todo_write"],
            category="planning"
        ),
    ]


async def main():
    """Run the evaluation."""
    print("Document Agent Evaluation")
    print("=" * 60)
    
    # Create evaluator and test suite
    evaluator = DocumentAgentEvaluator(verbose=True)
    test_cases = create_test_suite()
    
    print(f"\nRunning {len(test_cases)} test cases...")
    
    # Run evaluations
    results = await evaluator.evaluate_batch(test_cases, max_concurrent=2)
    
    # Generate report
    report = evaluator.generate_report(results)
    
    # Display results
    print("\n" + "=" * 60)
    print("EVALUATION RESULTS")
    print("=" * 60)
    
    print(f"\nSummary:")
    print(f"  Total Tests: {report['summary']['total_tests']}")
    print(f"  Successful: {report['summary']['successful']}")
    print(f"  Failed: {report['summary']['failed']}")
    print(f"  Success Rate: {report['summary']['success_rate']:.1%}")
    print(f"  Avg Duration: {report['summary']['average_duration_seconds']:.2f}s")
    
    print(f"\nSuccess Rate by Category:")
    for category, rate in report['by_category'].items():
        print(f"  {category}: {rate:.1%}")
    
    print(f"\nTool Usage:")
    for tool, count in sorted(report['tool_usage'].items(), key=lambda x: x[1], reverse=True):
        print(f"  {tool}: {count} calls")
    
    if report['failures']:
        print(f"\nFailed Tests:")
        for failure in report['failures']:
            print(f"\n  Test: {failure['test_id']}")
            print(f"  Task: {failure['task']}")
            if failure['error']:
                print(f"  Error: {failure['error']}")
            else:
                print(f"  Output: {failure['actual_output']}")
    
    # Save detailed results
    results_file = "eval_results.json"
    with open(results_file, 'w') as f:
        json.dump({
            "report": report,
            "detailed_results": [r.to_dict() for r in results]
        }, f, indent=2)
    
    print(f"\nDetailed results saved to {results_file}")
    
    # Cleanup test files
    test_files = ["test_eval.txt", "calc_result.txt", "eval_test.md"]
    for file in test_files:
        if os.path.exists(file):
            os.remove(file)


if __name__ == "__main__":
    asyncio.run(main())