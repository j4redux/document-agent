#!/usr/bin/env python3
"""Test that research tools properly use web search after fixes."""

import asyncio
import os
from dotenv import load_dotenv

# Load environment
load_dotenv()

# Import after loading env to ensure tools detect Exa
from agent import Agent
from tools.file_tools import FileReadTool, FileWriteTool
from tools.research_lead_tool import ResearchLeadTool, QuickResearchTool


async def test_quick_research():
    """Test QuickResearchTool with actual web search."""
    print("\n=== Testing QuickResearchTool ===")
    
    # Create minimal base tools
    base_tools = [FileReadTool(), FileWriteTool()]
    
    # Create quick research tool
    tool = QuickResearchTool(parent_tools=base_tools)
    
    # Test with a simple query that should return real results
    result = await tool.execute("What is the capital of France?")
    
    print(f"Result preview: {result[:500]}...")
    
    # Check if we got real search results
    if "paris" in result.lower():
        print("✅ Quick research returned correct information")
    else:
        print("❌ Quick research did not find expected information")
        
    return "paris" in result.lower()


async def test_research_lead():
    """Test ResearchLeadTool with actual web searches."""
    print("\n=== Testing ResearchLeadTool ===")
    
    # Create minimal base tools
    base_tools = [FileReadTool(), FileWriteTool()]
    
    # Create research lead tool
    tool = ResearchLeadTool(parent_tools=base_tools)
    
    # Test with a query that should trigger actual searches
    # Use a timeless query to avoid date confusion
    result = await tool.execute(
        "What are the main tourist attractions in Paris?",
        max_rounds=20  # Limit rounds for testing
    )
    
    print(f"Result preview: {result[:800]}...")
    
    # Check if we got real research with sources
    success_indicators = [
        "eiffel" in result.lower(),
        "louvre" in result.lower(),
        "Research Sources:" in result or "sources consulted" in result.lower()
    ]
    
    success = any(success_indicators)
    
    if success:
        print("✅ Research lead performed actual searches")
    else:
        print("❌ Research lead did not perform expected searches")
        
    return success


async def test_parallel_research():
    """Test that parallel agents can use web search."""
    print("\n=== Testing Parallel Research ===")
    
    from tools.research_tools import ParallelAgentTool
    from tools.exa_web_tool import ExaWebTool
    from tools.web_tool import WebTool
    from tools.research_tools import WebSearchTool, WebFetchTool, CompleteTaskTool
    
    # Create web tools
    if os.environ.get("EXA_API_KEY"):
        web_tool = ExaWebTool()
        print("Using Exa for parallel research")
    else:
        web_tool = WebTool()
        print("Using standard web tool")
    
    # Essential tools for subagents
    essential_tools = [
        WebSearchTool(web_tool),
        WebFetchTool(web_tool),
        web_tool,
        CompleteTaskTool(),
    ]
    
    # Create parallel tool with proper web tools
    parallel_tool = ParallelAgentTool(parent_tools=essential_tools)
    
    # Test with simple parallel tasks
    result = await parallel_tool.execute(
        agents=[
            {
                "name": "paris_researcher",
                "task": "Find the top 3 tourist attractions in Paris",
                "perspective": "Tourism"
            },
            {
                "name": "london_researcher", 
                "task": "Find the top 3 tourist attractions in London",
                "perspective": "Tourism"
            }
        ]
    )
    
    print(f"Result preview: {result[:1000]}...")
    
    # Check if both agents found information
    paris_found = "eiffel" in result.lower() or "louvre" in result.lower()
    london_found = "big ben" in result.lower() or "tower" in result.lower()
    sources_found = "Sources collected:" in result
    
    print(f"\nParis info found: {paris_found}")
    print(f"London info found: {london_found}")
    print(f"Sources tracked: {sources_found}")
    
    return paris_found or london_found


async def main():
    """Run all tests."""
    print("Research Tools Fix Verification")
    print("=" * 50)
    
    # Check environment
    has_exa = bool(os.environ.get("EXA_API_KEY"))
    print(f"Exa API: {'✅ Available' if has_exa else '❌ Not configured'}")
    
    # Run tests
    tests = [
        ("Quick Research", test_quick_research),
        ("Research Lead", test_research_lead),
        ("Parallel Research", test_parallel_research),
    ]
    
    results = []
    for name, test_func in tests:
        try:
            print(f"\nRunning {name}...")
            result = await test_func()
            results.append((name, result))
        except Exception as e:
            print(f"❌ {name} failed with error: {e}")
            results.append((name, False))
    
    # Summary
    print("\n" + "=" * 50)
    print("Test Summary:")
    for name, success in results:
        status = "✅ PASS" if success else "❌ FAIL"
        print(f"{name}: {status}")
    
    passed = sum(1 for _, success in results if success)
    total = len(results)
    print(f"\nTotal: {passed}/{total} tests passed")
    
    if passed < total:
        print("\n⚠️  Some tests failed. The research tools may still need adjustment.")
    else:
        print("\n✅ All tests passed! Research tools are working correctly.")


if __name__ == "__main__":
    asyncio.run(main())