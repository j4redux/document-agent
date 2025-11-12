#!/usr/bin/env python3
"""Basic tests for core document agent tools."""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import asyncio
from tools.file_tools import FileReadTool, FileWriteTool, FileSearchTool
from tools.text_transform import TextTransformTool
from tools.calculator import CalculatorTool


def test_calculator_tool():
    """Test calculator functionality."""
    print("=== Testing Calculator Tool ===")
    calc = CalculatorTool()
    
    # Test basic arithmetic
    result = asyncio.run(calc.execute(expression="2 + 2"))
    assert "4" in result
    print("[PASS] Basic addition works")
    
    # Test complex expression
    result = asyncio.run(calc.execute(expression="(10 * 5) / 2 + 3"))
    assert "28" in result
    print("[PASS] Complex expressions work")
    
    # Test error handling
    result = asyncio.run(calc.execute(expression="1 / 0"))
    assert "error" in result.lower()
    print("[PASS] Error handling works")
    print()


def test_text_transform_tool():
    """Test text transformation functionality."""
    print("=== Testing Text Transform Tool ===")
    transform = TextTransformTool()
    
    # Test uppercase
    result = asyncio.run(transform.execute(
        text="hello world",
        operation="uppercase"
    ))
    assert result == "HELLO WORLD"
    print("[PASS] Uppercase transformation works")
    
    # Test reverse
    result = asyncio.run(transform.execute(
        text="hello",
        operation="reverse"
    ))
    assert result == "olleh"
    print("[PASS] Reverse transformation works")
    
    # Test word count
    result = asyncio.run(transform.execute(
        text="This is a test sentence",
        operation="count_words"
    ))
    assert "5" in result
    print("[PASS] Word count works")
    print()


def test_file_operations():
    """Test file read/write operations."""
    print("=== Testing File Operations ===")
    
    # Create test file
    test_file = "test_document.md"
    test_content = "# Test Document\n\nThis is a test document for the agent."
    
    # Test write
    write_tool = FileWriteTool()
    result = asyncio.run(write_tool.execute(
        file_path=test_file,
        content=test_content
    ))
    assert "successfully" in result.lower()
    print("[PASS] File write works")
    
    # Test read
    read_tool = FileReadTool()
    result = asyncio.run(read_tool.execute(file_path=test_file))
    assert "Test Document" in result
    print("[PASS] File read works")
    
    # Cleanup
    os.remove(test_file)
    print("[PASS] Test file cleaned up")
    print()


def test_file_search():
    """Test file search functionality."""
    print("=== Testing File Search ===")
    
    # Create test files
    os.makedirs("test_docs", exist_ok=True)
    with open("test_docs/doc1.md", "w") as f:
        f.write("# Document One\n\nThis contains information about Python.")
    with open("test_docs/doc2.md", "w") as f:
        f.write("# Document Two\n\nThis contains information about JavaScript.")
    
    search_tool = FileSearchTool()
    
    # Test search
    result = asyncio.run(search_tool.execute(
        pattern="Python",
        file_pattern="*.md",
        search_type="text"
    ))
    assert "doc1.md" in result
    assert "doc2.md" not in result
    print("[PASS] Text search works")
    
    # Cleanup
    import shutil
    shutil.rmtree("test_docs")
    print("[PASS] Test files cleaned up")
    print()


def run_all_tests():
    """Run all basic tests."""
    print("Document Agent Basic Tests")
    print("=" * 40)
    
    try:
        test_calculator_tool()
        test_text_transform_tool()
        test_file_operations()
        test_file_search()
        
        print("\n[SUCCESS] All tests passed!")
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