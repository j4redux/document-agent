"""Research-specific tools for multi-agent research system."""

import asyncio
import json
import os
from datetime import datetime
from typing import List, Dict, Any, Optional
import uuid

from tools.base import Tool
from tools.web_tool import WebTool
from tools.agent_tool import AgentTool


class WebSearchTool(Tool):
    """Standalone web search tool matching research prompt expectations."""
    
    def __init__(self, web_tool):
        """Initialize with a web tool (WebTool or ExaWebTool)."""
        super().__init__(
            name="web_search",
            description="Search the web and return results with sources",
            input_schema={
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Search query"
                    },
                    "max_results": {
                        "type": "integer",
                        "description": "Maximum number of results to return",
                        "default": 10
                    }
                },
                "required": ["query"]
            }
        )
        self.web_tool = web_tool
        
    async def execute(self, query: str, max_results: int = 10) -> str:
        """Execute web search and track sources."""
        try:
            # Use num_results parameter if web tool supports it (ExaWebTool)
            if hasattr(self.web_tool, 'exa_client'):
                result = await self.web_tool.execute(
                    operation="search",
                    query=query,
                    num_results=max_results
                )
            else:
                result = await self.web_tool.execute(
                    operation="search",
                    query=query
                )
            
            # Track sources if agent has source tracking enabled
            if hasattr(self, 'agent') and hasattr(self.agent, 'sources'):
                # Parse search results and add to sources
                lines = result.split('\n')
                for line in lines:
                    if line.strip().startswith('URL:'):
                        url = line.replace('URL:', '').strip()
                        # Find associated title
                        title = "Search Result"
                        for i, l in enumerate(lines):
                            if l.strip().startswith(str(lines.index(line) // 4 + 1) + '.'):
                                title = l.strip()
                                break
                        
                        self.agent.sources.append({
                            "url": url,
                            "title": title,
                            "tool": "web_search",
                            "timestamp": datetime.now().isoformat()
                        })
                        
            return result
            
        except Exception as e:
            return f"Error searching web: {str(e)}"


class WebFetchTool(Tool):
    """Standalone web fetch tool with source tracking."""
    
    def __init__(self, web_tool: WebTool):
        super().__init__(
            name="web_fetch",
            description="Fetch complete content from a URL",
            input_schema={
                "type": "object",
                "properties": {
                    "url": {
                        "type": "string",
                        "description": "URL to fetch content from"
                    }
                },
                "required": ["url"]
            }
        )
        self.web_tool = web_tool
        
    async def execute(self, url: str) -> str:
        """Fetch URL content and track as source."""
        try:
            result = await self.web_tool.execute(
                operation="fetch",
                url=url
            )
            
            # Track source if agent has source tracking
            if hasattr(self, 'agent') and hasattr(self.agent, 'sources'):
                # Extract title from result
                title = url
                lines = result.split('\n')
                for line in lines:
                    if line.startswith('# '):
                        title = line[2:].strip()
                        break
                
                self.agent.sources.append({
                    "url": url,
                    "title": title,
                    "content_preview": result[:500] + "...",
                    "tool": "web_fetch",
                    "timestamp": datetime.now().isoformat()
                })
                
            return result
            
        except Exception as e:
            return f"Error fetching URL: {str(e)}"


class RunBlockingSubagentTool(Tool):
    """Create a single research subagent (matches prompt interface)."""
    
    def __init__(self, agent_tool: AgentTool):
        super().__init__(
            name="run_blocking_subagent",
            description="Create a research subagent with specific task",
            input_schema={
                "type": "object",
                "properties": {
                    "prompt": {
                        "type": "string",
                        "description": "Task description for the subagent"
                    },
                    "name": {
                        "type": "string",
                        "description": "Name for the subagent"
                    },
                    "max_tokens": {
                        "type": "integer",
                        "description": "Maximum tokens for response",
                        "default": 4096
                    }
                },
                "required": ["prompt"]
            }
        )
        self.agent_tool = agent_tool
        
    async def execute(self, prompt: str, name: Optional[str] = None, max_tokens: int = 4096) -> str:
        """Create and run subagent with research focus."""
        try:
            # Adapt prompt to agent_tool interface
            task = prompt
            plan = "Follow the research process to gather information and report findings"
            
            # Use agent_tool with higher iteration limit for research
            result = await self.agent_tool.execute(
                task=task,
                plan=plan,
                max_iterations=20  # Research needs more iterations
            )
            
            # Add agent name if provided
            if name:
                result = f"[{name}] {result}"
                
            return result
            
        except Exception as e:
            return f"Subagent error: {str(e)}"


class CompleteTaskTool(Tool):
    """Submit final research results in markdown format."""
    
    def __init__(self):
        super().__init__(
            name="complete_task",
            description="Submit final research report in markdown format",
            input_schema={
                "type": "object",
                "properties": {
                    "result": {
                        "type": "string",
                        "description": "Final research report in markdown"
                    },
                    "include_sources": {
                        "type": "boolean",
                        "description": "Include source references",
                        "default": True
                    }
                },
                "required": ["result"]
            }
        )
        
    async def execute(self, result: str, include_sources: bool = True) -> str:
        """Format and submit final research report."""
        output = []
        
        # Add markdown header
        output.append("# Research Report\n")
        output.append(f"*Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}*\n")
        
        # Add the main content
        output.append(result)
        
        # Add sources if requested and available
        if include_sources and hasattr(self, 'agent') and hasattr(self.agent, 'sources'):
            sources = self.agent.sources
            if sources:
                output.append("\n\n## Sources\n")
                for i, source in enumerate(sources, 1):
                    output.append(f"{i}. [{source.get('title', 'Untitled')}]({source.get('url', '#')})")
                    output.append(f"   - Tool: {source.get('tool', 'unknown')}")
                    output.append(f"   - Accessed: {source.get('timestamp', 'unknown')}")
                    output.append("")
                    
        return "\n".join(output)


class ParallelAgentTool(Tool):
    """Execute multiple research agents in parallel."""
    
    def __init__(self, parent_tools: Optional[List[Tool]] = None, max_concurrent: int = 20):
        super().__init__(
            name="run_parallel_agents",
            description="Run multiple research agents concurrently for comprehensive research",
            input_schema={
                "type": "object",
                "properties": {
                    "agents": {
                        "type": "array",
                        "description": "List of agent configurations",
                        "items": {
                            "type": "object",
                            "properties": {
                                "task": {
                                    "type": "string",
                                    "description": "Research task for this agent"
                                },
                                "name": {
                                    "type": "string",
                                    "description": "Agent identifier"
                                },
                                "perspective": {
                                    "type": "string",
                                    "description": "Research perspective or angle"
                                }
                            },
                            "required": ["task"]
                        }
                    }
                },
                "required": ["agents"]
            }
        )
        self.parent_tools = parent_tools or []
        self.max_concurrent = max_concurrent
        
    async def execute(self, agents: List[Dict[str, Any]]) -> str:
        """Run multiple agents in parallel and collect results."""
        if not agents:
            return "Error: No agents specified"
            
        if len(agents) > self.max_concurrent:
            return f"Error: Too many agents ({len(agents)}). Maximum is {self.max_concurrent}"
            
        # Import here to avoid circular dependency
        from agent import Agent, ModelConfig
        
        # Create semaphore for concurrency control
        semaphore = asyncio.Semaphore(self.max_concurrent)
        
        async def run_single_agent(agent_config: Dict[str, Any]) -> str:
            """Run a single research agent."""
            async with semaphore:
                try:
                    # Embed research subagent prompt directly
                    current_date = datetime.now().strftime("%Y-%m-%d")
                    subagent_prompt = f"""You are a research subagent working as part of a team. The current date is {current_date}. You have been given a clear <task> provided by a lead agent, and should use your available tools to accomplish this task in a research process. Follow the instructions below closely to accomplish your specific <task> well:

<research_process>
1. **Planning**: First, think through the task thoroughly. Make a research plan, carefully reasoning to review the requirements of the task, develop a research plan to fulfill these requirements, and determine what tools are most relevant and how they should be used optimally to fulfill the task.
- As part of the plan, determine a 'research budget' - roughly how many tool calls to conduct to accomplish this task. Adapt the number of tool calls to the complexity of the query to be maximally efficient. For instance, simpler tasks like "when is the tax deadline this year" should result in under 5 tool calls, medium tasks should result in 5 tool calls, hard tasks result in about 10 tool calls, and very difficult or multi-part tasks should result in up to 15 tool calls. Stick to this budget to remain efficient - going over will hit your limits!
2. **Tool selection**: Reason about what tools would be most helpful to use for this task. Use the right tools when a task implies they would be helpful. For instance, web_search (getting snippets of web results from a query), web_fetch (retrieving full webpages).
- ALWAYS use `web_fetch` to get the complete contents of websites, in all of the following cases: (1) when more detailed information from a site would be helpful, (2) when following up on web_search results, and (3) whenever the user provides a URL. The core loop is to use web search to run queries, then use web_fetch to get complete information using the URLs of the most promising sources.
3. **Research loop**: Execute an excellent OODA (observe, orient, decide, act) loop by (a) observing what information has been gathered so far, what still needs to be gathered to accomplish the task, and what tools are available currently; (b) orienting toward what tools and queries would be best to gather the needed information and updating beliefs based on what has been learned so far; (c) making an informed, well-reasoned decision to use a specific tool in a certain way; (d) acting to use this tool. Repeat this loop in an efficient way to research well and learn based on new results.
- Execute a MINIMUM of five distinct tool calls, up to ten for complex queries. Avoid using more than ten tool calls.
- Reason carefully after receiving tool results. Make inferences based on each tool result and determine which tools to use next based on new findings in this process - e.g. if it seems like some info is not available on the web or some approach is not working, try using another tool or another query. Evaluate the quality of the sources in search results carefully. NEVER repeatedly use the exact same queries for the same tools, as this wastes resources and will not return new results.
Follow this process well to complete the task. Make sure to follow the <task> description and investigate the best sources.
</research_process>

<research_guidelines>
1. Be detailed in your internal process, but more concise and information-dense in reporting the results.
2. Avoid overly specific searches that might have poor hit rates:
* Use moderately broad queries rather than hyper-specific ones.
* Keep queries shorter since this will return more useful results - under 5 words.
* If specific searches yield few results, broaden slightly.
* Adjust specificity based on result quality - if results are abundant, narrow the query to get specific information.
* Find the right balance between specific and general.
3. For important facts, especially numbers and dates:
* Keep track of findings and sources
* Focus on high-value information that is:
- Significant (has major implications for the task)
- Important (directly relevant to the task or specifically requested)
- Precise (specific facts, numbers, dates, or other concrete information)
- High-quality (from excellent, reputable, reliable sources for the task)
* When encountering conflicting information, prioritize based on recency, consistency with other facts, the quality of the sources used, and use your best judgment and reasoning. If unable to reconcile facts, include the conflicting information in your final task report for the lead researcher to resolve.
4. Be specific and precise in your information gathering approach.
</research_guidelines>

<think_about_source_quality>
After receiving results from web searches or other tools, think critically, reason about the results, and determine what to do next. Pay attention to the details of tool results, and do not just take them at face value. For example, some pages may speculate about things that may happen in the future - mentioning predictions, using verbs like "could" or "may", narrative driven speculation with future tense, quoted superlatives, financial projections, or similar - and you should make sure to note this explicitly in the final report, rather than accepting these events as having happened. Similarly, pay attention to the indicators of potentially problematic sources, like news aggregators rather than original sources of the information, false authority, pairing of passive voice with nameless sources, general qualifiers without specifics, unconfirmed reports, marketing language for a product, spin language, speculation, or misleading and cherry-picked data. Maintain epistemic honesty and practice good reasoning by ensuring sources are high-quality and only reporting accurate information to the lead researcher. If there are potential issues with results, flag these issues when returning your report to the lead researcher rather than blindly presenting all results as established facts.
</think_about_source_quality>

<use_parallel_tool_calls>
For maximum efficiency, whenever you need to perform multiple independent operations, invoke 2 relevant tools simultaneously rather than sequentially. Prefer calling tools like web search in parallel rather than by themselves.
</use_parallel_tool_calls>

<maximum_tool_call_limit>
To prevent overloading the system, it is required that you stay under a limit of 20 tool calls and under about 100 sources. This is the absolute maximum upper limit. If you exceed this limit, the subagent will be terminated. Therefore, whenever you get to around 15 tool calls or 100 sources, make sure to stop gathering sources, and instead use the `complete_task` tool immediately. Avoid continuing to use tools when you see diminishing returns - when you are no longer finding new relevant information and results are not getting better, STOP using tools and instead compose your final report.
</maximum_tool_call_limit>

Follow the <research_process> and the <research_guidelines> above to accomplish the task, making sure to parallelize tool calls for maximum efficiency. Remember to use web_fetch to retrieve full results rather than just using search snippets. Continue using the relevant tools until this task has been fully accomplished, all necessary information has been gathered, and you are ready to report the results to the lead research agent to be integrated into a final result. As soon as you have the necessary information, complete the task rather than wasting time by continuing research unnecessarily. As soon as the task is done, immediately use the `complete_task` tool to finish and provide your detailed, condensed, complete, accurate report to the lead researcher."""
                    
                    # Add specific task
                    task_prompt = f"{subagent_prompt}\n\n<task>{agent_config['task']}</task>"
                    
                    # Create agent
                    agent_name = agent_config.get('name', f"Research-{uuid.uuid4().hex[:8]}")
                    agent = Agent(
                        name=agent_name,
                        system=task_prompt,
                        tools=self.parent_tools,
                        config=ModelConfig(
                            model="claude-3-5-haiku-20241022",  # Cost-effective for subagents
                            max_tokens=4096
                        ),
                        max_rounds=20,  # Research may need many rounds
                        verbose=False
                    )
                    
                    # Run the research
                    perspective = agent_config.get('perspective', '')
                    prompt = "Complete the research task assigned to you."
                    if perspective:
                        prompt += f" Focus on the {perspective} perspective."
                        
                    result = await agent.run_async(prompt)
                    
                    # Format result
                    output = [
                        f"=== {agent_name} ===",
                        f"Task: {agent_config['task']}",
                    ]
                    if perspective:
                        output.append(f"Perspective: {perspective}")
                    output.append("")
                    
                    # Extract text from result
                    if hasattr(result, 'content'):
                        for block in result.content:
                            if hasattr(block, 'text'):
                                output.append(block.text)
                    else:
                        output.append(str(result))
                        
                    output.append(f"\nSources collected: {len(agent.sources)}")
                    output.append("")
                    
                    return "\n".join(output)
                    
                except Exception as e:
                    return f"=== Error in {agent_config.get('name', 'agent')} ===\n{str(e)}\n"
        
        # Run all agents in parallel
        results = await asyncio.gather(
            *[run_single_agent(config) for config in agents],
            return_exceptions=False
        )
        
        # Combine results
        final_output = [
            f"# Parallel Research Results",
            f"Executed {len(agents)} agents in parallel\n",
            *results
        ]
        
        return "\n".join(final_output)


class CitationTool(Tool):
    """Add citations to research text using the citation agent prompt."""
    
    def __init__(self):
        super().__init__(
            name="add_citations",
            description="Add proper citations to research text",
            input_schema={
                "type": "object",
                "properties": {
                    "text": {
                        "type": "string",
                        "description": "Text to add citations to"
                    },
                    "sources": {
                        "type": "array",
                        "description": "List of sources used",
                        "items": {
                            "type": "object"
                        }
                    }
                },
                "required": ["text", "sources"]
            }
        )
        
    async def execute(self, text: str, sources: List[Dict[str, Any]]) -> str:
        """Add citations using the citation agent."""
        try:
            # Import here to avoid circular dependency
            from agent import Agent, ModelConfig
            
            # Embed citation agent prompt directly
            citation_prompt = """You are an agent for adding correct citations to a research report. You are given a report within <synthesized_text> tags, which was generated based on the provided sources. However, the sources are not cited in the <synthesized_text>. Your task is to enhance user trust by generating correct, appropriate citations for this report.

Based on the provided document, add citations to the input text using the format specified earlier. Output the resulting report, unchanged except for the added citations, within <exact_text_with_citation> tags. 

**Rules:**
- Do NOT modify the <synthesized_text> in any way - keep all content 100% identical, only add citations
- Pay careful attention to whitespace: DO NOT add or remove any whitespace
- ONLY add citations where the source documents directly support claims in the text

**Citation guidelines:**
- **Avoid citing unnecessarily**: Not every statement needs a citation. Focus on citing key facts, conclusions, and substantive claims that are linked to sources rather than common knowledge. Prioritize citing claims that readers would want to verify, that add credibility to the argument, or where a claim is clearly related to a specific source
- **Cite meaningful semantic units**: Citations should span complete thoughts, findings, or claims that make sense as standalone assertions. Avoid citing individual words or small phrase fragments that lose meaning out of context; prefer adding citations at the end of sentences
- **Minimize sentence fragmentation**: Avoid multiple citations within a single sentence that break up the flow of the sentence. Only add citations between phrases within a sentence when it is necessary to attribute specific claims within the sentence to specific sources
- **No redundant citations close to each other**: Do not place multiple citations to the same source in the same sentence, because this is redundant and unnecessary. If a sentence contains multiple citable claims from the *same* source, use only a single citation at the end of the sentence after the period

**Technical requirements:**
- Citations result in a visual, interactive element being placed at the closing tag. Be mindful of where the closing tag is, and do not break up phrases and sentences unnecessarily
- Output text with citations between <exact_text_with_citation> and </exact_text_with_citation> tags
- Include any of your preamble, thinking, or planning BEFORE the opening <exact_text_with_citation> tag, to avoid breaking the output
- ONLY add the citation tags to the text within <synthesized_text> tags for your <exact_text_with_citation> output
- Text without citations will be collected and compared to the original report from the <synthesized_text>. If the text is not identical, your result will be rejected.

Now, add the citations to the research report and output the <exact_text_with_citation>."""
                
            # Create citation agent
            citation_agent = Agent(
                name="Citation-Agent",
                system=citation_prompt,
                tools=[],  # No tools needed for citations
                config=ModelConfig(
                    model="claude-3-5-haiku-20241022",
                    temperature=0.3,  # Low temperature for accuracy
                    max_tokens=8000
                ),
                verbose=False
            )
            
            # Format prompt
            prompt = f"""<synthesized_text>
{text}
</synthesized_text>

<sources>
{json.dumps(sources, indent=2)}
</sources>

Please add citations to the text following the guidelines."""
            
            # Run citation agent
            result = await citation_agent.run_async(prompt)
            
            # Extract cited text from response
            if hasattr(result, 'content'):
                for block in result.content:
                    if hasattr(block, 'text'):
                        response_text = block.text
                        # Look for cited text between tags
                        if "<exact_text_with_citation>" in response_text:
                            start = response_text.find("<exact_text_with_citation>") + 26
                            end = response_text.find("</exact_text_with_citation>")
                            if end > start:
                                return response_text[start:end]
                                
            # Fallback - return original text
            return text
            
        except Exception as e:
            return f"Citation error: {str(e)}\n\n{text}"