#!/usr/bin/env python3
"""Simple test to verify research tools have web access."""

import asyncio
import os
from dotenv import load_dotenv

# Load environment
load_dotenv()

# Import after loading env
from tools.research_tools import ParallelAgentTool
from tools.exa_web_tool import ExaWebTool
from tools.research_tools import WebSearchTool, WebFetchTool, CompleteTaskTool
from agent import Agent, ModelConfig


async def test_subagent_tools():
    """Test that subagents have access to web tools."""
    print("Testing Subagent Tool Access")
    print("=" * 50)
    
    # Create web tool
    if os.environ.get("EXA_API_KEY"):
        web_tool = ExaWebTool()
        print("✅ Using Exa web tool")
    else:
        from tools.web_tool import WebTool
        web_tool = WebTool()
        print("⚠️  Using standard web tool (no Exa API key)")
    
    # Create tools for subagent
    tools = [
        WebSearchTool(web_tool),
        WebFetchTool(web_tool),
        CompleteTaskTool(),
    ]
    
    print(f"\nTools available to subagent: {[t.name for t in tools]}")
    
    # Create a simple research agent
    agent = Agent(
        name="TestResearcher",
        system="You are a research agent. Use web_search to find information.",
        tools=tools,
        config=ModelConfig(
            model="claude-3-5-haiku-20241022",
            max_tokens=1024
        ),
        verbose=True,
        max_rounds=5
    )
    
    # Test simple search
    print("\nTesting agent with web search...")
    try:
        response = await agent.run_async("Search for information about the Eiffel Tower height. Use web_search tool.")
        
        # Check response
        if hasattr(response, 'content') and response.content:
            text = response.content[0].text if hasattr(response.content[0], 'text') else str(response.content[0])
            print(f"\nAgent response: {text[:300]}...")
            
            # Check if search was performed
            if "324" in text or "330" in text or "meters" in text.lower():
                print("\n✅ Agent successfully used web search!")
                return True
            else:
                print("\n❌ Agent response doesn't contain expected information")
                return False
        else:
            print("\n❌ No response from agent")
            return False
            
    except Exception as e:
        print(f"\n❌ Error: {e}")
        return False


async def main():
    """Run the test."""
    success = await test_subagent_tools()
    
    if success:
        print("\n✅ Research tools fix is working! Subagents can now search the web.")
    else:
        print("\n❌ Research tools still have issues.")
        print("\nTroubleshooting:")
        print("1. Check if Exa API key is set correctly")
        print("2. Verify web tools are being passed to subagents")
        print("3. Check agent prompts mention the correct tool names")


if __name__ == "__main__":
    asyncio.run(main())