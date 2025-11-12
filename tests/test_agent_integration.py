#!/usr/bin/env python3
"""Integration tests for the document agent."""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import asyncio
from agent import Agent
from tools.calculator import CalculatorTool
from tools.text_transform import TextTransformTool
from tools.file_tools import FileReadTool, FileWriteTool


def test_agent_basic_interaction():
    """Test basic agent interaction without API calls."""
    print("=== Testing Agent Setup ===")
    
    # Create agent with minimal tools
    agent = Agent(
        name="Test Agent",
        system="You are a test agent. Be very brief.",
        tools=[CalculatorTool(), TextTransformTool()],
        verbose=False
    )
    
    # Check agent properties
    assert agent.name == "Test Agent"
    assert len(agent.tools) == 2
    print("[PASS] Agent created successfully")
    print("[PASS] Tools loaded correctly")
    print()


def test_tool_discovery():
    """Test that agent can discover tool capabilities."""
    print("=== Testing Tool Discovery ===")
    
    tools = [
        CalculatorTool(),
        TextTransformTool(),
        FileReadTool(),
        FileWriteTool()
    ]
    
    agent = Agent(
        name="Discovery Agent",
        system="Test system",
        tools=tools,
        verbose=False
    )
    
    # Check tool names
    tool_names = [tool.name for tool in agent.tools]
    assert "calculator" in tool_names
    assert "text_transform" in tool_names
    assert "file_read" in tool_names
    assert "file_write" in tool_names
    print("[PASS] All tools discovered")
    
    # Check tool schemas
    for tool in agent.tools:
        schema = tool.to_dict()
        assert "name" in schema
        assert "description" in schema
        assert "input_schema" in schema
        print(f"[PASS] Tool '{tool.name}' has valid schema")
    print()


def test_message_history():
    """Test message history functionality."""
    print("=== Testing Message History ===")
    
    from utils.history_util import MessageHistory
    
    # Mock client
    class MockClient:
        class messages:
            @staticmethod
            def count_tokens(**kwargs):
                class Result:
                    input_tokens = 10
                return Result()
    
    history = MessageHistory(
        model="claude-3",
        system="Test system",
        context_window_tokens=1000,
        client=MockClient()
    )
    
    # Add messages
    asyncio.run(history.add_message("user", "Hello"))
    asyncio.run(history.add_message("assistant", [{"type": "text", "text": "Hi there!"}]))
    
    # Check message count
    assert len(history.messages) == 2
    print("[PASS] Messages added to history")
    
    # Format for API
    api_messages = history.format_for_api()
    assert len(api_messages) == 2
    assert api_messages[0]["role"] == "user"
    assert api_messages[1]["role"] == "assistant"
    print("[PASS] Messages formatted correctly")
    print()


def test_slash_commands():
    """Test slash command handling."""
    print("=== Testing Slash Commands ===")
    
    agent = Agent(
        name="Command Agent",
        system="Test",
        tools=[],
        verbose=False
    )
    
    # Test help command
    help_result = agent._process_command("/help")
    assert help_result is True
    print("[PASS] /help command works")
    
    # Test unknown command
    unknown_result = agent._process_command("/unknown")
    assert unknown_result is False
    print("[PASS] Unknown commands handled")
    print()


def test_tool_integration():
    """Test tool integration without API calls."""
    print("=== Testing Tool Integration ===")
    
    # Create test file
    test_file = "integration_test.txt"
    with open(test_file, "w") as f:
        f.write("Test content")
    
    try:
        # Test file read tool
        read_tool = FileReadTool()
        result = asyncio.run(read_tool.execute(file_path=test_file))
        assert "Test content" in result
        print("[PASS] FileReadTool integration works")
        
        # Test calculator tool
        calc_tool = CalculatorTool()
        result = asyncio.run(calc_tool.execute(expression="10 + 20"))
        assert "30" in result
        print("[PASS] CalculatorTool integration works")
        
    finally:
        # Cleanup
        if os.path.exists(test_file):
            os.remove(test_file)
    print()


def run_all_tests():
    """Run all integration tests."""
    print("Document Agent Integration Tests")
    print("=" * 40)
    print("Note: These tests don't require API calls\n")
    
    try:
        test_agent_basic_interaction()
        test_tool_discovery()
        test_message_history()
        test_slash_commands()
        test_tool_integration()
        
        print("\n[SUCCESS] All integration tests passed!")
        return True
        
    except AssertionError as e:
        print(f"\n[FAIL] Test failed: {e}")
        return False
    except Exception as e:
        print(f"\n[ERROR] Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)