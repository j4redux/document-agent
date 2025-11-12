#!/usr/bin/env python3
"""Test the research system fixes."""

import asyncio
import os

from example_research_agent import create_research_document_agent


async def test_simple_search():
    """Test that web search works."""
    print("\n=== Testing Web Search ===")
    agent = create_research_document_agent(enable_research=True)
    
    response = await agent.run_async(
        "Use web_search to find information about Python programming"
    )
    
    # Extract response text
    if hasattr(response, 'content'):
        for block in response.content:
            if hasattr(block, 'text'):
                print(f"Response: {block.text[:300]}...")
                if "No results found" not in block.text:
                    print("✓ Web search working")
                else:
                    print("✗ Web search still returning no results")
                break


async def test_subagent():
    """Test that subagents work."""
    print("\n\n=== Testing Subagent Creation ===")
    agent = create_research_document_agent(enable_research=True)
    
    response = await agent.run_async(
        "Use run_blocking_subagent to create a subagent that says hello"
    )
    
    # Extract response text
    if hasattr(response, 'content'):
        for block in response.content:
            if hasattr(block, 'text'):
                print(f"Response: {block.text[:300]}...")
                if "Sub-agent completed task" in block.text:
                    print("✓ Subagent working")
                else:
                    print("✗ Subagent failed")
                break


async def test_parallel_agents():
    """Test parallel agent execution."""
    print("\n\n=== Testing Parallel Agents ===")
    agent = create_research_document_agent(enable_research=True)
    
    response = await agent.run_async("""
Use run_parallel_agents to create 2 agents:
1. Agent that counts to 5
2. Agent that lists colors
""")
    
    # Extract response text
    if hasattr(response, 'content'):
        for block in response.content:
            if hasattr(block, 'text'):
                print(f"Response: {block.text[:500]}...")
                if "Parallel Research Results" in block.text:
                    print("✓ Parallel agents working")
                else:
                    print("✗ Parallel agents failed")
                break


def main():
    """Run all tests."""
    print("Testing Research System Fixes")
    print("=" * 50)
    
    if not os.environ.get("ANTHROPIC_API_KEY"):
        print("Error: Please set ANTHROPIC_API_KEY environment variable")
        return
    
    # Run tests
    asyncio.run(test_simple_search())
    asyncio.run(test_subagent())
    asyncio.run(test_parallel_agents())


if __name__ == "__main__":
    main()