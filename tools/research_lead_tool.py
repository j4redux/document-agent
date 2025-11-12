"""Research Lead Tool - Orchestrates comprehensive research using multiple agents."""

import asyncio
from datetime import datetime
from typing import List, Dict, Any, Optional

from tools.base import Tool
from tools.research_tools import (
    WebSearchTool,
    WebFetchTool,
    RunBlockingSubagentTool,
    ParallelAgentTool,
    CompleteTaskTool,
    CitationTool,
)
from tools.web_tool import WebTool
from tools.anthropic_web_tool import AnthropicWebTool, AnthropicWebSearchTool
from tools.agent_tool import AgentTool


class ResearchLeadTool(Tool):
    """
    A tool that creates a research lead agent to orchestrate comprehensive research.
    
    This tool spawns a specialized research agent that can:
    - Analyze research queries and develop strategies
    - Delegate to multiple sub-agents for parallel research
    - Synthesize findings into comprehensive reports
    - Track sources and add citations
    """
    
    def __init__(self, parent_tools: List[Tool]):
        """Initialize the research lead tool with parent tools for sub-agents."""
        super().__init__(
            name="research_lead",
            description=(
                "Conduct comprehensive research on a topic using a specialized research lead agent. "
                "The research lead will analyze your query, develop a research strategy, delegate to "
                "multiple sub-agents for parallel information gathering, and synthesize findings into "
                "a comprehensive report with citations. Use this for complex research tasks that require "
                "multiple perspectives, deep analysis, or broad information gathering."
            ),
            input_schema={
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "The research question or topic to investigate"
                    },
                    "max_rounds": {
                        "type": "integer",
                        "description": "Maximum rounds for the research process",
                        "default": 50
                    },
                    "require_citations": {
                        "type": "boolean",
                        "description": "Whether to include citations in the final report",
                        "default": True
                    }
                },
                "required": ["query"]
            }
        )
        self.parent_tools = parent_tools
        self._research_tools = None
        
    def _get_research_tools(self) -> List[Tool]:
        """Get or create research-specific tools."""
        if self._research_tools is None:
            # Check if we already have a web tool in parent_tools
            web_tool = None
            web_search_tool = None
            
            for tool in self.parent_tools:
                if hasattr(tool, 'name'):
                    if tool.name == 'web':
                        web_tool = tool
                    elif tool.name == 'web_search':
                        web_search_tool = tool
            
            # If no web tools found, create them using Anthropic's web search
            if web_tool is None:
                web_tool = AnthropicWebTool()
            if web_search_tool is None:
                web_search_tool = AnthropicWebSearchTool()
            
            # Create core research tools that subagents will need
            web_search_tool = WebSearchTool(web_tool)
            web_fetch_tool = WebFetchTool(web_tool)
            
            # Essential tools for subagents (avoiding duplicates)
            essential_subagent_tools = [
                web_search_tool,
                web_fetch_tool,
                web_tool,
                CompleteTaskTool(),
            ]
            
            # Filter out any web tools from parent_tools to avoid duplicates
            filtered_parent_tools = [
                tool for tool in self.parent_tools 
                if not (hasattr(tool, 'name') and tool.name in ['web', 'exa_web', 'web_search', 'web_fetch'])
            ]
            
            # Create agent tool for delegation
            agent_tool = AgentTool(parent_tools=filtered_parent_tools + essential_subagent_tools)
            
            # Build research tool suite (excluding web_tool as it's in parent_tools)
            self._research_tools = [
                # Web operations
                web_search_tool,
                web_fetch_tool,
                # Agent delegation with proper tools
                RunBlockingSubagentTool(agent_tool),
                ParallelAgentTool(parent_tools=filtered_parent_tools + essential_subagent_tools),
                agent_tool,
                # Research completion
                CompleteTaskTool(),
                CitationTool(),
            ]
            
        return self._research_tools
    
    def _get_research_prompt(self) -> str:
        """Get the research lead system prompt."""
        current_date = datetime.now().strftime("%Y-%m-%d")
        
        return f"""You are an expert research lead, focused on high-level research strategy, planning, efficient delegation to subagents, and final report writing. Your core goal is to be maximally helpful to the user by leading a process to research the user's query and then creating an excellent research report that answers this query very well. Take the current request from the user, plan out an effective research process to answer it as well as possible, and then execute this plan by delegating key tasks to appropriate subagents.
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

Remember: You are the research lead. Your job is to understand the query, develop a strategy, delegate research tasks, and synthesize the findings into an excellent report."""
    
    async def execute(self, query: str, max_rounds: int = 50, require_citations: bool = True) -> str:
        """Execute comprehensive research on the given query."""
        try:
            # Import here to avoid circular import
            from agent import Agent, ModelConfig
            
            # Get research tools
            research_tools = self._get_research_tools()
            
            # Debug: Check for duplicate tool names
            tool_names = {}
            for tool in self.parent_tools:
                if hasattr(tool, 'name'):
                    if tool.name in tool_names:
                        print(f"WARNING: Duplicate tool '{tool.name}' from parent_tools")
                    tool_names[tool.name] = tool
            
            for tool in research_tools:
                if hasattr(tool, 'name'):
                    if tool.name in tool_names:
                        print(f"WARNING: Duplicate tool '{tool.name}' from research_tools")
                    tool_names[tool.name] = tool
            
            # Use only unique tools
            all_tools = list(tool_names.values())
            
            # Create the research lead agent
            research_agent = Agent(
                name="Research Lead",
                system=self._get_research_prompt(),
                tools=all_tools,
                config=ModelConfig(
                    model="claude-3-5-sonnet-20241022",  # Best model for research lead
                    max_tokens=4096,
                    temperature=0.7,
                ),
                verbose=True,
                max_rounds=max_rounds,
            )
            
            # Execute the research
            response = await research_agent.run_async(query)
            
            # Extract the response text
            if hasattr(response, 'content') and response.content:
                text_parts = []
                for block in response.content:
                    if hasattr(block, 'text'):
                        text_parts.append(block.text)
                result = '\n'.join(text_parts)
            else:
                result = str(response)
            
            # Add source information if available
            if hasattr(research_agent, 'sources') and research_agent.sources:
                result += f"\n\n**Research Sources:** {len(research_agent.sources)} sources consulted"
            
            return result
            
        except Exception as e:
            return f"Error conducting research: {str(e)}"


class QuickResearchTool(Tool):
    """
    A lightweight research tool for simpler research tasks.
    
    This tool creates a single research agent without the full orchestration
    capabilities of the ResearchLeadTool. Suitable for straightforward research
    questions that don't require multiple perspectives or parallel agents.
    """
    
    def __init__(self, parent_tools: List[Tool]):
        """Initialize the quick research tool."""
        super().__init__(
            name="quick_research",
            description=(
                "Conduct quick research on a straightforward topic. "
                "For simple fact-finding or basic information gathering that doesn't require "
                "multiple perspectives or complex orchestration. For comprehensive research "
                "with multiple agents, use the research_lead tool instead."
            ),
            input_schema={
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "The research question or topic"
                    }
                },
                "required": ["query"]
            }
        )
        self.parent_tools = parent_tools
        
        # Check if we already have a web tool in parent_tools
        self.web_tool = None
        for tool in self.parent_tools:
            if hasattr(tool, 'name') and tool.name == 'web':
                self.web_tool = tool
                break
        
        # If no web tool found, create one using Anthropic
        if self.web_tool is None:
            self.web_tool = AnthropicWebTool()
        
    async def execute(self, query: str) -> str:
        """Execute quick research on the given query."""
        try:
            # Import here to avoid circular import
            from agent import Agent, ModelConfig
            
            # Create a focused research agent
            research_agent = Agent(
                name="Quick Researcher",
                system=f"""You are a research assistant tasked with finding information about: {query}

Search for relevant information, verify facts from multiple sources if possible, and provide a clear, concise answer.
Focus on accuracy and cite your sources when providing information.
Current date: {datetime.now().strftime("%Y-%m-%d")}""",
                tools=[
                    self.web_tool,
                    WebSearchTool(self.web_tool),
                    WebFetchTool(self.web_tool),
                ],
                config=ModelConfig(
                    model="claude-3-5-haiku-20241022",  # Faster model for quick research
                    max_tokens=2048,
                    temperature=0.3,
                ),
                verbose=False,
                max_rounds=10,
            )
            
            # Execute the research
            response = await research_agent.run_async(f"Research and provide information about: {query}")
            
            # Extract response
            if hasattr(response, 'content') and response.content:
                text_parts = []
                for block in response.content:
                    if hasattr(block, 'text'):
                        text_parts.append(block.text)
                return '\n'.join(text_parts)
            
            return str(response)
            
        except Exception as e:
            return f"Error conducting quick research: {str(e)}"