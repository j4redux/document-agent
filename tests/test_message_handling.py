#!/usr/bin/env python3
"""Test message handling and edge cases."""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import asyncio
from utils.history_util import MessageHistory
from anthropic.types import TextBlock, ToolUseBlock


def test_pydantic_object_handling():
    """Test that MessageHistory properly handles Pydantic objects."""
    print("=== Testing Pydantic Object Handling ===")
    
    # Create a mock client
    class MockClient:
        class messages:
            @staticmethod
            def count_tokens(**kwargs):
                class Result:
                    input_tokens = 100
                return Result()
    
    # Create MessageHistory
    history = MessageHistory(
        model="claude-3",
        system="Test system",
        context_window_tokens=4096,
        client=MockClient(),
        enable_caching=True
    )
    
    # Test 1: Add message with Pydantic objects
    print("1. Testing Pydantic object addition...")
    pydantic_content = [
        TextBlock(type="text", text="Hello world"),
        ToolUseBlock(type="tool_use", id="123", name="test_tool", input={"param": "value"})
    ]
    
    asyncio.run(history.add_message("assistant", pydantic_content))
    print("[PASS] Successfully added Pydantic content")
    
    # Test 2: Format for API
    print("2. Testing format_for_api with Pydantic objects...")
    api_messages = history.format_for_api()
    assert len(api_messages) == 1
    print(f"[PASS] Successfully formatted {len(api_messages)} messages")
    
    # Test 3: Test with empty text
    print("3. Testing empty text handling...")
    empty_content = [
        TextBlock(type="text", text="   "),  # Just whitespace
        ToolUseBlock(type="tool_use", id="456", name="another_tool", input={})
    ]
    
    asyncio.run(history.add_message("assistant", empty_content))
    api_messages = history.format_for_api()
    print(f"[PASS] Messages after empty text: {len(api_messages)}")
    
    # Test 4: Test with mixed dict and Pydantic
    print("4. Testing mixed content types...")
    mixed_content = [
        {"type": "text", "text": "Dict text"},
        TextBlock(type="text", text="Pydantic text")
    ]
    
    asyncio.run(history.add_message("user", mixed_content))
    api_messages = history.format_for_api()
    print("[PASS] Successfully handled mixed content types")
    print()


def test_tool_message_pairing():
    """Test that tool_use/tool_result pairs are properly maintained."""
    print("=== Testing Tool Message Pairing ===")
    
    # Create a mock client
    class MockClient:
        class messages:
            @staticmethod
            def count_tokens(**kwargs):
                class Result:
                    input_tokens = 100
                return Result()
    
    # Create MessageHistory
    history = MessageHistory(
        model="claude-3",
        system="Test system",
        context_window_tokens=4096,
        client=MockClient(),
        enable_caching=False
    )
    
    # Test 1: Add user message
    print("1. Adding user message...")
    asyncio.run(history.add_message("user", "Test user message"))
    
    # Test 2: Add assistant message with only tool calls (no text)
    print("2. Adding assistant message with only tool calls...")
    tool_only_content = [
        ToolUseBlock(
            type="tool_use", 
            id="test_tool_id_123", 
            name="test_tool", 
            input={"param": "value"}
        )
    ]
    asyncio.run(history.add_message("assistant", tool_only_content))
    
    # Test 3: Add tool result
    print("3. Adding tool result...")
    tool_result = [
        {
            "type": "tool_result",
            "tool_use_id": "test_tool_id_123",
            "content": "Tool executed successfully"
        }
    ]
    asyncio.run(history.add_message("user", tool_result))
    
    # Test 4: Format for API and verify all messages are included
    print("4. Formatting for API...")
    api_messages = history.format_for_api()
    
    # Verify we have all 3 messages
    assert len(api_messages) == 3, f"Expected 3 messages, got {len(api_messages)}"
    assert api_messages[0]['role'] == 'user'
    assert api_messages[1]['role'] == 'assistant'
    assert api_messages[2]['role'] == 'user'
    
    print("[PASS] All messages preserved correctly")
    print("[PASS] Tool message pairing maintained")
    print()


def test_context_window_truncation():
    """Test message truncation when context window is exceeded."""
    print("=== Testing Context Window Truncation ===")
    
    class MockClient:
        class messages:
            @staticmethod
            def count_tokens(**kwargs):
                class Result:
                    input_tokens = 50  # Small tokens for testing
                return Result()
    
    # Create history with small context window
    history = MessageHistory(
        model="claude-3",
        system="Test",
        context_window_tokens=200,  # Small window for testing
        client=MockClient()
    )
    
    # Add multiple messages
    for i in range(10):
        asyncio.run(history.add_message("user", f"Message {i}"))
        asyncio.run(history.add_message("assistant", [{"type": "text", "text": f"Response {i}"}]))
    
    # Check truncation happened
    messages = history.format_for_api()
    assert len(messages) < 20  # Should be truncated
    print(f"[PASS] Messages truncated to {len(messages)} (from 20)")
    
    # Verify truncation notice
    first_message = messages[0]
    if "truncated" in str(first_message).lower():
        print("[PASS] Truncation notice added")
    print()


def run_all_tests():
    """Run all message handling tests."""
    print("Document Agent Message Handling Tests")
    print("=" * 40)
    
    try:
        test_pydantic_object_handling()
        test_tool_message_pairing()
        test_context_window_truncation()
        
        print("\n[SUCCESS] All message handling tests passed!")
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