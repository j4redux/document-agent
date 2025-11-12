#!/usr/bin/env python3
"""Advanced evaluation with LLM judge for the Research capabilities."""

import asyncio
import json
import os
import time
from typing import List, Dict, Any, Optional
from anthropic import Anthropic
from dataclasses import dataclass, field
from datetime import datetime

# Import agent components
from agent import Agent
from tools.calculator import CalculatorTool
from tools.file_tools import FileReadTool, FileWriteTool, FileSearchTool
from tools.system_tools import create_linked_todo_tools
from tools.text_transform import TextTransformTool
from tools.anthropic_web_tool import AnthropicWebSearchTool, AnthropicWebTool
from tools.agent_tool import AgentTool
from tools.research_lead_tool import ResearchLeadTool, QuickResearchTool


@dataclass
class ResearchTestCase:
    """Test case for research evaluation."""
    id: str
    task: str
    category: str
    research_type: str  # "quick", "comprehensive", "web_search", "multi_agent"
    expected_elements: List[str] = field(default_factory=list)  # Elements that should be present
    quality_rubric: Optional[str] = None
    max_turns: int = 30
    timeout_seconds: int = 120


@dataclass
class ResearchEvalResult:
    """Result of a research evaluation."""
    test_id: str
    success: bool
    duration_seconds: float
    turns_used: int
    actual_output: Optional[str] = None
    error: Optional[str] = None
    judge_evaluation: Optional[Dict[str, Any]] = None
    sources_found: int = 0
    web_searches_performed: int = 0
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "test_id": self.test_id,
            "success": self.success,
            "duration_seconds": self.duration_seconds,
            "turns_used": self.turns_used,
            "actual_output": self.actual_output[:500] if self.actual_output else None,
            "error": self.error,
            "judge_evaluation": self.judge_evaluation,
            "sources_found": self.sources_found,
            "web_searches_performed": self.web_searches_performed
        }


class ResearchJudge:
    """LLM-based judge for evaluating research quality."""
    
    def __init__(self, client: Optional[Anthropic] = None):
        """Initialize the judge."""
        self.client = client or Anthropic()
    
    async def judge_research(
        self, 
        task: str, 
        output: str,
        expected_elements: List[str],
        custom_rubric: Optional[str] = None
    ) -> Dict[str, Any]:
        """Judge research output quality."""
        
        if custom_rubric:
            judge_prompt = custom_rubric.format(
                task=task,
                output=output,
                expected_elements=", ".join(expected_elements) if expected_elements else "None specified"
            )
        else:
            judge_prompt = """You are evaluating the quality of research output from an AI agent.

Research Task: {task}
Expected Elements: {expected_elements}

Research Output:
{output}

Evaluate the research on these criteria:

1. **Accuracy**: Are the facts and information accurate?
2. **Completeness**: Does it thoroughly address the research question?
3. **Sources**: Are sources cited or is information verifiable?
4. **Organization**: Is the information well-structured and easy to follow?
5. **Depth**: Does it go beyond surface-level information?
6. **Relevance**: Is all information relevant to the task?

Provide your evaluation in JSON format:
{{
    "overall_score": <float between 0 and 1>,
    "accuracy": <float between 0 and 1>,
    "completeness": <float between 0 and 1>,
    "sources_quality": <float between 0 and 1>,
    "organization": <float between 0 and 1>,
    "depth": <float between 0 and 1>,
    "relevance": <float between 0 and 1>,
    "missing_elements": [<list of expected elements that are missing>],
    "strengths": "<brief description of strengths>",
    "weaknesses": "<brief description of weaknesses>",
    "overall_quality": "<excellent|good|fair|poor>"
}}"""
        
        prompt = judge_prompt.format(
            task=task,
            expected_elements=", ".join(expected_elements) if expected_elements else "None specified",
            output=output[:3000] if len(output) > 3000 else output  # Limit length
        )
        
        response = self.client.messages.create(
            model="claude-3-5-sonnet-20241022",  # Use better model for judging
            max_tokens=1000,
            temperature=0,
            system="You are an expert research evaluator. Always respond with valid JSON.",
            messages=[{"role": "user", "content": prompt}]
        )
        
        try:
            json_str = response.content[0].text
            return json.loads(json_str)
        except:
            return {
                "overall_score": 0.5,
                "accuracy": 0.5,
                "completeness": 0.5,
                "sources_quality": 0.5,
                "organization": 0.5,
                "depth": 0.5,
                "relevance": 0.5,
                "missing_elements": [],
                "strengths": "Unable to parse evaluation",
                "weaknesses": "Evaluation failed",
                "overall_quality": "fair"
            }


class ResearchEvaluator:
    """Evaluator for research capabilities."""
    
    def __init__(self, verbose: bool = True):
        """Initialize evaluator."""
        self.verbose = verbose
        self.client = Anthropic()
        self.judge = ResearchJudge(self.client)
    
    def create_research_agent(self) -> Agent:
        """Create agent configured for research."""
        # Create base tools
        todo_read, todo_write = create_linked_todo_tools()
        
        base_tools = [
            FileReadTool(),
            FileWriteTool(),
            FileSearchTool(),
            todo_read,
            todo_write,
            TextTransformTool(),
            CalculatorTool(),
        ]
        
        # Add Anthropic web search tools
        web_search_tool = AnthropicWebSearchTool()
        web_tool = AnthropicWebTool()
        if self.verbose:
            print("  Using Anthropic's built-in web search")
        
        base_tools.extend([web_search_tool, web_tool])
        
        # Create agent tool and research tools
        agent_tool = AgentTool(parent_tools=base_tools)
        research_lead_tool = ResearchLeadTool(parent_tools=base_tools)
        quick_research_tool = QuickResearchTool(parent_tools=base_tools)
        
        # All tools
        all_tools = base_tools + [agent_tool, research_lead_tool, quick_research_tool]
        
        # Create agent with research-focused prompt
        system_prompt = """You are a research assistant specializing in finding, analyzing, and synthesizing information. 

Key behaviors:
- Use appropriate research tools (quick_research for simple queries, research_lead for complex topics)
- Always cite sources when available
- Provide structured, well-organized responses
- Be thorough but concise
- Verify information accuracy

Available research tools:
- quick_research: For straightforward fact-finding
- research_lead: For comprehensive research requiring multiple perspectives
- web_search/web: For direct web searches and fetching

Current date: {date}
""".format(date=datetime.now().strftime("%Y-%m-%d"))
        
        return Agent(
            name="Research Evaluator",
            system=system_prompt,
            tools=all_tools,
            verbose=False,  # Reduce output during tests
            max_rounds=30  # Set default max rounds
        )
    
    async def evaluate_single(
        self, 
        test_case: ResearchTestCase
    ) -> ResearchEvalResult:
        """Evaluate a single research test case."""
        if self.verbose:
            print(f"\nEvaluating {test_case.id}: {test_case.task[:60]}...")
        
        start_time = time.time()
        agent = self.create_research_agent()
        
        try:
            # Run the research task
            response = await asyncio.wait_for(
                agent.run_async(test_case.task),
                timeout=test_case.timeout_seconds
            )
            
            # Extract response text
            if hasattr(response, 'content') and response.content:
                output = response.content[0].text if hasattr(response.content[0], 'text') else str(response.content[0])
            else:
                output = str(response)
            
            # Count sources and searches (basic heuristic)
            sources_found = output.lower().count('http') + output.lower().count('source:')
            web_searches = output.lower().count('search results') + output.lower().count('exa search')
            
            # Judge the research quality
            judge_result = await self.judge.judge_research(
                task=test_case.task,
                output=output,
                expected_elements=test_case.expected_elements,
                custom_rubric=test_case.quality_rubric
            )
            
            # Determine success based on judge score
            success = judge_result["overall_score"] >= 0.7
            
            result = ResearchEvalResult(
                test_id=test_case.id,
                success=success,
                duration_seconds=time.time() - start_time,
                turns_used=getattr(agent, 'turn_count', 0),
                actual_output=output,
                judge_evaluation=judge_result,
                sources_found=sources_found,
                web_searches_performed=web_searches
            )
            
        except asyncio.TimeoutError:
            result = ResearchEvalResult(
                test_id=test_case.id,
                success=False,
                duration_seconds=test_case.timeout_seconds,
                turns_used=0,
                error=f"Timeout after {test_case.timeout_seconds}s"
            )
        except Exception as e:
            result = ResearchEvalResult(
                test_id=test_case.id,
                success=False,
                duration_seconds=time.time() - start_time,
                turns_used=0,
                error=str(e)
            )
        
        return result
    
    def generate_report(self, results: List[ResearchEvalResult]) -> Dict[str, Any]:
        """Generate comprehensive report."""
        total = len(results)
        successful = sum(1 for r in results if r.success)
        
        # Calculate metrics
        avg_duration = sum(r.duration_seconds for r in results) / total
        avg_turns = sum(r.turns_used for r in results) / total
        avg_sources = sum(r.sources_found for r in results) / total
        
        # Judge metrics
        judge_scores = {}
        quality_dist = {"excellent": 0, "good": 0, "fair": 0, "poor": 0}
        
        for r in results:
            if r.judge_evaluation:
                for metric, score in r.judge_evaluation.items():
                    if isinstance(score, (int, float)) and metric != "overall_score":
                        if metric not in judge_scores:
                            judge_scores[metric] = []
                        judge_scores[metric].append(score)
                
                quality = r.judge_evaluation.get("overall_quality", "fair")
                quality_dist[quality] += 1
        
        # Average judge scores
        avg_judge_scores = {
            metric: sum(scores) / len(scores) 
            for metric, scores in judge_scores.items()
        }
        
        return {
            "summary": {
                "total_tests": total,
                "successful": successful,
                "failed": total - successful,
                "success_rate": successful / total if total > 0 else 0,
                "average_duration_seconds": avg_duration,
                "average_turns": avg_turns,
                "average_sources": avg_sources
            },
            "judge_metrics": {
                "average_scores": avg_judge_scores,
                "quality_distribution": quality_dist,
                "overall_average": sum(
                    r.judge_evaluation.get("overall_score", 0) 
                    for r in results if r.judge_evaluation
                ) / total
            },
            "timestamp": datetime.now().isoformat()
        }


def create_research_test_suite() -> List[ResearchTestCase]:
    """Create comprehensive research test cases."""
    return [
        # Quick research tests
        ResearchTestCase(
            id="quick_1",
            task="Use quick_research to find the current population of Tokyo",
            category="facts",
            research_type="quick",
            expected_elements=["million", "Tokyo", "population"],
            max_turns=15
        ),
        
        ResearchTestCase(
            id="quick_2",
            task="Use quick_research to find when Python programming language was created",
            category="facts",
            research_type="quick",
            expected_elements=["1991", "Guido van Rossum"],
            max_turns=15
        ),
        
        # Comprehensive research tests
        ResearchTestCase(
            id="comprehensive_1",
            task="Use research_lead to analyze the environmental impact of electric vehicles compared to gasoline vehicles",
            category="analysis",
            research_type="comprehensive",
            expected_elements=["emissions", "battery", "manufacturing", "lifecycle"],
            max_turns=50,
            timeout_seconds=180
        ),
        
        ResearchTestCase(
            id="comprehensive_2",
            task="Use research_lead to research the top 3 cloud computing providers and compare their strengths",
            category="comparison",
            research_type="comprehensive",
            expected_elements=["AWS", "Azure", "Google Cloud", "comparison", "features"],
            max_turns=50,
            timeout_seconds=180
        ),
        
        # Web search tests
        ResearchTestCase(
            id="web_1",
            task="Search for the latest AI breakthroughs in 2024",
            category="current_events",
            research_type="web_search",
            expected_elements=["2024", "AI", "breakthrough"],
            max_turns=20
        ),
        
        ResearchTestCase(
            id="web_2",
            task="Find and summarize the main features of the latest iPhone model",
            category="product_research",
            research_type="web_search",
            expected_elements=["iPhone", "features", "camera", "processor"],
            max_turns=20
        ),
        
        # Multi-agent research
        ResearchTestCase(
            id="multi_1",
            task="Use research_lead to investigate the history, current state, and future of renewable energy",
            category="comprehensive_analysis",
            research_type="multi_agent",
            expected_elements=["solar", "wind", "history", "future", "trends"],
            max_turns=60,
            timeout_seconds=240
        ),
        
        # Research with specific output requirements
        ResearchTestCase(
            id="structured_1",
            task="Research the top 5 programming languages in 2024 and create a markdown report with rankings",
            category="structured_output",
            research_type="comprehensive",
            expected_elements=["Python", "JavaScript", "ranking", "#", "1.", "2."],
            max_turns=30
        ),
        
        # Error handling in research
        ResearchTestCase(
            id="error_1",
            task="Research information about a made-up technology called 'QuantumFlux Processors'",
            category="error_handling",
            research_type="quick",
            expected_elements=["not found", "no information", "does not exist"],
            max_turns=15
        ),
        
        # Citation and source tracking
        ResearchTestCase(
            id="citation_1",
            task="Research the GDP of the United States and provide sources",
            category="citations",
            research_type="quick",
            expected_elements=["GDP", "trillion", "source", "http"],
            max_turns=20
        )
    ]


async def run_research_evaluation():
    """Run comprehensive research evaluation."""
    print("Research Capabilities Evaluation with LLM Judge")
    print("=" * 60)
    
    print(f"\nConfiguration:")
    print(f"  Using: Anthropic's built-in web search")
    print(f"  API Key: {'✓' if os.environ.get('ANTHROPIC_API_KEY') else '✗'}")
    
    # Create evaluator
    evaluator = ResearchEvaluator(verbose=True)
    
    # Get test cases
    test_cases = create_research_test_suite()
    print(f"\nRunning {len(test_cases)} research test cases...")
    print("-" * 60)
    
    # Run evaluations
    results = []
    for test_case in test_cases:
        result = await evaluator.evaluate_single(test_case)
        results.append(result)
        
        # Display progress
        status = "✅" if result.success else "❌"
        score = result.judge_evaluation.get("overall_score", 0) if result.judge_evaluation else 0
        print(f"{status} {test_case.id}: Score={score:.2f}, Time={result.duration_seconds:.1f}s")
    
    # Generate report
    report = evaluator.generate_report(results)
    
    # Display results
    print("\n" + "=" * 60)
    print("RESEARCH EVALUATION RESULTS")
    print("=" * 60)
    
    print(f"\nOverall Summary:")
    print(f"  Success Rate: {report['summary']['success_rate']:.1%}")
    print(f"  Average Duration: {report['summary']['average_duration_seconds']:.1f}s")
    print(f"  Average Turns: {report['summary']['average_turns']:.1f}")
    print(f"  Average Sources: {report['summary']['average_sources']:.1f}")
    
    print(f"\nQuality Metrics (Judge Scores):")
    print(f"  Overall Average: {report['judge_metrics']['overall_average']:.2f}")
    for metric, score in sorted(report['judge_metrics']['average_scores'].items()):
        print(f"  {metric.title()}: {score:.2f}")
    
    print(f"\nQuality Distribution:")
    for quality, count in report['judge_metrics']['quality_distribution'].items():
        percentage = (count / len(results)) * 100 if results else 0
        print(f"  {quality.title()}: {count} ({percentage:.1f}%)")
    
    # Save detailed results
    output_file = "research_eval_results.json"
    with open(output_file, 'w') as f:
        json.dump({
            "configuration": {
                "web_search": "Anthropic built-in",
                "timestamp": datetime.now().isoformat()
            },
            "report": report,
            "detailed_results": [r.to_dict() for r in results]
        }, f, indent=2)
    
    print(f"\nDetailed results saved to {output_file}")
    
    # Show failed tests
    failed = [r for r in results if not r.success]
    if failed:
        print(f"\nFailed Tests ({len(failed)}):")
        for r in failed:
            print(f"  - {r.test_id}: {r.error or 'Low quality score'}")
    
    # Cleanup any created files
    cleanup_files = ["research_output.md", "research_report.md", "facts.md"]
    for file in cleanup_files:
        if os.path.exists(file):
            os.remove(file)


if __name__ == "__main__":
    # Load .env first
    from dotenv import load_dotenv
    load_dotenv()
    
    # Check for API key
    if not os.environ.get("ANTHROPIC_API_KEY"):
        print("Error: ANTHROPIC_API_KEY not found in environment")
        print("Please ensure your .env file contains ANTHROPIC_API_KEY")
        exit(1)
    
    # Run evaluation
    asyncio.run(run_research_evaluation())