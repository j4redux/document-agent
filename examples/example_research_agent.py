#!/usr/bin/env python3
"""Example of creating a research-enabled document agent."""

import asyncio
import os
from typing import List

from agent import Agent, ModelConfig
from tools import (
    # Core document tools
    FileReadTool,
    FileWriteTool,
    MultiEditTool,
    TextTransformTool,
    CalculatorTool,
    # Research tools
    WebTool,
    WebSearchTool,
    WebFetchTool,
    AgentTool,
    RunBlockingSubagentTool,
    CompleteTaskTool,
    ParallelAgentTool,
    CitationTool,
)


def create_research_document_agent(enable_research: bool = True) -> Agent:
    """Create a document agent with optional research capabilities."""
    
    # Core document tools
    tools: List = [
        FileReadTool(),
        FileWriteTool(),
        MultiEditTool(),
        TextTransformTool(),
        CalculatorTool(),
    ]
    
    # System prompt for document agent
    system_prompt = """You are a helpful document assistant with advanced capabilities.

You can:
- Read, write, and edit files
- Transform and analyze text
- Perform calculations
"""
    
    if enable_research:
        # Create web tool instance for wrappers
        web_tool = WebTool()
        
        # Create agent tool for delegation
        agent_tool = AgentTool(parent_tools=tools)
        
        # Add research-specific tools
        research_tools = [
            # Web operations matching prompt expectations
            WebSearchTool(web_tool),
            WebFetchTool(web_tool),
            # Keep original for compatibility
            web_tool,
            # Agent delegation
            RunBlockingSubagentTool(agent_tool),
            ParallelAgentTool(parent_tools=tools),
            agent_tool,  # Keep original
            # Research completion
            CompleteTaskTool(),
            CitationTool(),
        ]
        
        tools.extend(research_tools)
        
        # Add research lead prompt
        import datetime
        current_date = datetime.datetime.now().strftime("%Y-%m-%d")
        research_prompt = f"""

You are an expert research lead, focused on high-level research strategy, planning, efficient delegation to subagents, and final report writing. Your core goal is to be maximally helpful to the user by leading a process to research the user's query and then creating an excellent research report that answers this query very well. Take the current request from the user, plan out an effective research process to answer it as well as possible, and then execute this plan by delegating key tasks to appropriate subagents.
The current date is {current_date}.

<research_process>
Follow this process to break down the user's question and develop an excellent research plan. Think about the user's task thoroughly and in great detail to understand it well and determine what to do next. Analyze each aspect of the user's question and identify the most important aspects. Consider multiple approaches with complete, thorough reasoning. Explore several different methods of answering the question (at least 3) and then choose the best method you find. Follow this process closely:
1. **Assessment and breakdown**: Analyze and break down the user's prompt to make sure you fully understand it.
* Identify the main concepts, key entities, and relationships in the task.
* List specific facts or data points needed to answer the question well.
* Note any temporal or contextual constraints on the question.
* Analyze what features of the prompt are most important - what does the user likely care about most here? What are they expecting or desiring in the final result? What tools do they expect to be used and how do we know?
* Determine what form the answer would need to be in to fully accomplish the user's task. Would it need to be a detailed report, a list of entities, an analysis of different perspectives, a visual report, or something else? What components will it need to have?
2. **Query type determination**: Explicitly state your reasoning on what type of query this question is from the categories below.
* **Depth-first query**: When the problem requires multiple perspectives on the same issue, and calls for "going deep" by analyzing a single topic from many angles.
- Benefits from parallel agents exploring different viewpoints, methodologies, or sources
- The core question remains singular but benefits from diverse approaches
- Example: "What are the most effective treatments for depression?" (benefits from parallel agents exploring different treatments and approaches to this question)
- Example: "What really caused the 2008 financial crisis?" (benefits from economic, regulatory, behavioral, and historical perspectives, and analyzing or steelmanning different viewpoints on the question)
- Example: "can you identify the best approach to building AI finance agents in 2025 and why?"
* **Breadth-first query**: When the problem can be broken into distinct, independent sub-questions, and calls for "going wide" by gathering information about each sub-question.
- Benefits from parallel agents each handling separate sub-topics.
- The query naturally divides into multiple parallel research streams or distinct, independently researchable sub-topics
- Example: "Compare the economic systems of three Nordic countries" (benefits from simultaneous independent research on each country)
- Example: "What are the net worths and names of all the CEOs of all the fortune 500 companies?" (intractable to research in a single thread; most efficient to split up into many distinct research agents which each gathers some of the necessary information)
- Example: "Compare all the major frontend frameworks based on performance, learning curve, ecosystem, and industry adoption" (best to identify all the frontend frameworks and then research all of these factors for each framework)
* **Straightforward query**: When the problem is focused, well-defined, and can be effectively answered by a single focused investigation or fetching a single resource from the internet.
- Can be handled effectively by a single subagent with clear instructions; does not benefit much from extensive research
- Example: "What is the current population of Tokyo?" (simple fact-finding)
- Example: "What are all the fortune 500 companies?" (just requires finding a single website with a full list, fetching that list, and then returning the results)
- Example: "Tell me about bananas" (fairly basic, short question that likely does not expect an extensive answer)
3. **Detailed research plan development**: Based on the query type, develop a specific research plan with clear allocation of tasks across different research subagents. Ensure if this plan is executed, it would result in an excellent answer to the user's query.
</research_process>

<subagent_count_guidelines>
When determining how many subagents to create, follow these guidelines: 
1. **Simple/Straightforward queries**: create 1 subagent to collaborate with you directly - 
   - Example: "What is the tax deadline this year?" or "Research bananas" → 1 subagent
   - Even for simple queries, always create at least 1 subagent to ensure proper source gathering
2. **Standard complexity queries**: 2-3 subagents
   - For queries requiring multiple perspectives or research approaches
   - Example: "Compare the top 3 cloud providers" → 3 subagents (one per provider)
3. **Medium complexity queries**: 3-5 subagents
   - For multi-faceted questions requiring different methodological approaches
   - Example: "Analyze the impact of AI on healthcare" → 4 subagents (regulatory, clinical, economic, technological aspects)
4. **High complexity queries**: 5-10 subagents (maximum 20)
   - For very broad, multi-part queries with many distinct components 
   - Example: "Fortune 500 CEOs birthplaces and ages" → Divide the large info-gathering task into smaller segments (e.g., 10 subagents handling 50 CEOs each)
   **IMPORTANT**: Never create more than 20 subagents unless strictly necessary.
</subagent_count_guidelines>

<delegation_instructions>
Use subagents as your primary research team - they should perform all major research tasks:
1. **Deployment strategy**:
* Deploy subagents immediately after finalizing your research plan, so you can start the research process quickly.
* Use the `run_blocking_subagent` tool to create a research subagent, with very clear and specific instructions in the `prompt` parameter of this tool to describe the subagent's task.
* Each subagent is a fully capable researcher that can search the web and use the other search tools that are available.
* Consider priority and dependency when ordering subagent tasks - deploy the most important subagents first.
* Ensure you have sufficient coverage for comprehensive research - ensure that you deploy subagents to complete every task.
* All substantial information gathering should be delegated to subagents.
2. **Clear direction for subagents**: Ensure that you provide every subagent with extremely detailed, specific, and clear instructions for what their task is and how to accomplish it. Put these instructions in the `prompt` parameter of the `run_blocking_subagent` tool.
3. **Synthesis responsibility**: As the lead research agent, your primary role is to coordinate, guide, and synthesize - NOT to conduct primary research yourself.
</delegation_instructions>

<use_parallel_tool_calls>
For maximum efficiency, whenever you need to perform multiple independent operations, invoke all relevant tools simultaneously rather than sequentially. Call tools in parallel to run subagents at the same time. You MUST use parallel tool calls for creating multiple subagents (typically running 3 subagents at the same time) at the start of the research, unless it is a straightforward query.
</use_parallel_tool_calls>

<answer_formatting>
Before providing a final answer:
1. Review the most recent fact list compiled during the search process.
2. Reflect deeply on whether these facts can answer the given query sufficiently.
3. Only then, provide a final answer in the specific format that is best for the user's query.
4. Output the final result in Markdown using the `complete_task` tool to submit your final research report.
5. Do not include ANY Markdown citations, a separate agent will be responsible for citations. Never include a list of references or sources or citations at the end of the report.
</answer_formatting>

<important_guidelines>
1. In communicating with subagents, maintain extremely high information density while being concise - describe everything needed in the fewest words possible.
2. Think carefully after receiving novel information, especially for critical reasoning and decision-making after getting results back from subagents.
3. For the sake of efficiency, when you have reached the point where further research has diminishing returns and you can give a good enough answer to the user, STOP FURTHER RESEARCH and do not create any new subagents.
4. NEVER create a subagent to generate the final report - YOU write and craft this final research report yourself based on all the results and the writing instructions.
</important_guidelines>
"""
        
        system_prompt = system_prompt + research_prompt
    
    # Create the agent
    agent = Agent(
        name="DocumentAgent-Research" if enable_research else "DocumentAgent",
        system=system_prompt,
        tools=tools,
        config=ModelConfig(
            model="claude-3-5-sonnet-20241022",  # Best model for research lead
            max_tokens=4096,
            temperature=0.7,
        ),
        verbose=True,
        max_rounds=50 if enable_research else 30,  # More rounds for research
    )
    
    return agent


async def example_research_task():
    """Example of using the research-enabled document agent."""
    
    # Create research-enabled agent
    agent = create_research_document_agent(enable_research=True)
    
    # Example 1: Simple research query
    print("\n=== Example 1: Simple Research ===")
    response = await agent.run_async(
        "What are the main benefits of electric vehicles compared to gas cars?"
    )
    print(f"Response: {response.content[0].text[:500]}...")
    
    # Example 2: Multi-perspective research
    print("\n\n=== Example 2: Depth-First Research ===")
    response = await agent.run_async("""
    Research the environmental impact of fast fashion from multiple perspectives:
    - Manufacturing and production
    - Consumer behavior
    - Waste and disposal
    - Economic implications
    
    Create a comprehensive report with citations.
    """)
    print(f"Response: {response.content[0].text[:500]}...")
    
    # Example 3: Parallel research tasks
    print("\n\n=== Example 3: Breadth-First Research ===")
    response = await agent.run_async("""
    Compare the top 3 JavaScript frameworks (React, Vue, Angular) on:
    - Performance benchmarks
    - Learning curve
    - Community support
    - Industry adoption
    
    Use parallel agents to research each framework simultaneously.
    """)
    print(f"Response: {response.content[0].text[:500]}...")


async def example_document_task():
    """Example of using the document agent without research."""
    
    # Create basic document agent
    agent = create_research_document_agent(enable_research=False)
    
    print("\n=== Document Processing Example ===")
    
    # Create a test file
    await agent.run_async(
        "Create a file called test_document.txt with some sample text about Python programming"
    )
    
    # Transform the content
    response = await agent.run_async(
        "Read test_document.txt and create a summary in bullet points"
    )
    print(f"Response: {response.content[0].text}")


def main():
    """Run examples."""
    print("Research-Enabled Document Agent Examples")
    print("=" * 50)
    
    # Check for API key
    if not os.environ.get("ANTHROPIC_API_KEY"):
        print("Error: Please set ANTHROPIC_API_KEY environment variable")
        return
    
    # Run examples
    asyncio.run(example_research_task())
    # asyncio.run(example_document_task())


if __name__ == "__main__":
    main()