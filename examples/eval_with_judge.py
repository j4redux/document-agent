#!/usr/bin/env python3
"""Advanced evaluation with LLM judge for the Document Agent."""

import asyncio
import json
from typing import List, Dict, Any, Optional
from anthropic import Anthropic
from eval_document_agent import TestCase, EvalResult, DocumentAgentEvaluator


class LLMJudge:
    """LLM-based judge for evaluating agent responses."""
    
    def __init__(self, client: Optional[Anthropic] = None):
        """Initialize the judge."""
        self.client = client or Anthropic()
    
    async def judge_response(
        self, 
        task: str, 
        expected: Optional[str], 
        actual: str,
        rubric: Optional[str] = None
    ) -> Dict[str, Any]:
        """Judge a response using an LLM."""
        
        if rubric:
            judge_prompt = rubric
        else:
            judge_prompt = """You are evaluating an AI agent's response to a task.

Task: {task}
Expected Output (if provided): {expected}
Actual Output: {actual}

Evaluate the response on the following criteria:
1. Correctness: Did the agent complete the task correctly?
2. Completeness: Did the agent address all parts of the task?
3. Efficiency: Did the agent complete the task efficiently?
4. Output Quality: Is the output well-formatted and clear?

Provide your evaluation in JSON format:
{{
    "score": <float between 0 and 1>,
    "correct": <boolean>,
    "complete": <boolean>,
    "efficient": <boolean>,
    "quality": <"excellent"|"good"|"fair"|"poor">,
    "reasoning": "<brief explanation of your evaluation>"
}}"""
        
        prompt = judge_prompt.format(
            task=task,
            expected=expected or "Not specified",
            actual=actual
        )
        
        response = self.client.messages.create(
            model="claude-3-5-haiku-20241022",
            max_tokens=500,
            temperature=0,
            system="You are a precise evaluator. Always respond with valid JSON.",
            messages=[{"role": "user", "content": prompt}]
        )
        
        try:
            # Extract JSON from response
            json_str = response.content[0].text
            return json.loads(json_str)
        except:
            # Fallback if JSON parsing fails
            return {
                "score": 0.5,
                "correct": False,
                "complete": False,
                "efficient": False,
                "quality": "fair",
                "reasoning": "Failed to parse judge response"
            }


class AdvancedDocumentEvaluator(DocumentAgentEvaluator):
    """Enhanced evaluator with LLM judging."""
    
    def __init__(self, verbose: bool = False, use_judge: bool = True):
        """Initialize evaluator."""
        super().__init__(verbose)
        self.use_judge = use_judge
        self.judge = LLMJudge(self.client) if use_judge else None
    
    async def evaluate_single_with_judge(
        self, 
        agent, 
        test_case: TestCase
    ) -> EvalResult:
        """Evaluate with LLM judge."""
        # Get base evaluation
        result = await self.evaluate_single(agent, test_case)
        
        if self.use_judge and result.actual_output:
            # Get judge evaluation
            judge_result = await self.judge.judge_response(
                task=test_case.task,
                expected=test_case.expected_output,
                actual=result.actual_output
            )
            
            # Update success based on judge
            result.success = judge_result["correct"]
            result.similarity_score = judge_result["score"]
            
            # Add judge details to result
            result.judge_evaluation = judge_result
        
        return result
    
    def generate_detailed_report(self, results: List[EvalResult]) -> Dict[str, Any]:
        """Generate detailed report with judge evaluations."""
        base_report = self.generate_report(results)
        
        # Add judge-specific metrics if available
        if self.use_judge:
            judge_scores = []
            quality_distribution = {"excellent": 0, "good": 0, "fair": 0, "poor": 0}
            
            for result in results:
                if hasattr(result, 'judge_evaluation'):
                    judge_eval = result.judge_evaluation
                    judge_scores.append(judge_eval["score"])
                    quality_distribution[judge_eval["quality"]] += 1
            
            if judge_scores:
                base_report["judge_metrics"] = {
                    "average_score": sum(judge_scores) / len(judge_scores),
                    "quality_distribution": quality_distribution,
                    "efficiency_rate": sum(
                        1 for r in results 
                        if hasattr(r, 'judge_evaluation') and r.judge_evaluation["efficient"]
                    ) / len(results)
                }
        
        return base_report


def create_advanced_test_suite() -> List[TestCase]:
    """Create advanced test cases for comprehensive evaluation."""
    return [
        # Document creation
        TestCase(
            id="doc_1",
            task="Create a markdown file called 'summary.md' with a brief summary of artificial intelligence in exactly 3 sentences",
            category="document_creation",
            max_turns=10
        ),
        
        # Document creation with list
        TestCase(
            id="research_1",
            task="Create a file 'facts.md' with 5 bullet points about Python programming language features",
            category="research",
            max_turns=10
        ),
        
        # Multi-step document editing
        TestCase(
            id="edit_1",
            task="Create a file 'report.txt' with 'Initial Report', then append '- Section 1: Overview' and '- Section 2: Analysis'",
            category="document_editing",
            max_turns=10
        ),
        
        # Data processing
        TestCase(
            id="data_1",
            task="Calculate the average of these numbers: 15, 23, 38, 42, 19. Save the result to 'average.txt'",
            expected_output="27.4",
            category="data_processing",
            max_turns=10
        ),
        
        # Complex planning
        TestCase(
            id="plan_1",
            task="Create a project plan with 5 todos for building a website, mark the first two as in_progress",
            category="planning",
            max_turns=10
        ),
        
        # Format conversion
        TestCase(
            id="format_1",
            task="Create a JSON file 'data.json' with user information: name='John Doe', age=30, email='john@example.com'",
            category="formatting",
            max_turns=8
        ),
        
        # Error handling
        TestCase(
            id="error_1",
            task="Try to read a non-existent file 'missing.txt' and handle the error gracefully",
            category="error_handling",
            max_turns=5
        ),
        
        # Batch operations
        TestCase(
            id="batch_1",
            task="Create 3 files: 'file1.txt' with 'Content 1', 'file2.txt' with 'Content 2', 'file3.txt' with 'Content 3'",
            category="batch_ops",
            max_turns=10
        ),
    ]


async def run_advanced_evaluation():
    """Run advanced evaluation with LLM judge."""
    print("Advanced Document Agent Evaluation (with LLM Judge)")
    print("=" * 60)
    
    # Create evaluator
    evaluator = AdvancedDocumentEvaluator(verbose=True, use_judge=True)
    
    # Get test suites
    basic_tests = create_test_suite()
    advanced_tests = create_advanced_test_suite()
    all_tests = basic_tests + advanced_tests
    
    print(f"\nRunning {len(all_tests)} test cases with LLM judge...")
    
    # Run evaluations
    results = []
    for test_case in all_tests:
        agent = evaluator.create_test_agent()
        result = await evaluator.evaluate_single_with_judge(agent, test_case)
        results.append(result)
        
        if evaluator.verbose:
            status = "[PASS]" if result.success else "[FAIL]"
            print(f"{status} {test_case.id}: {test_case.task[:50]}...")
    
    # Generate report
    report = evaluator.generate_detailed_report(results)
    
    # Display enhanced results
    print("\n" + "=" * 60)
    print("EVALUATION RESULTS WITH LLM JUDGE")
    print("=" * 60)
    
    print(f"\nSummary:")
    print(f"  Total Tests: {report['summary']['total_tests']}")
    print(f"  Successful: {report['summary']['successful']}")
    print(f"  Failed: {report['summary']['failed']}")
    print(f"  Success Rate: {report['summary']['success_rate']:.1%}")
    print(f"  Avg Duration: {report['summary']['average_duration_seconds']:.2f}s")
    
    if "judge_metrics" in report:
        print(f"\nJudge Metrics:")
        print(f"  Average Score: {report['judge_metrics']['average_score']:.2f}")
        print(f"  Efficiency Rate: {report['judge_metrics']['efficiency_rate']:.1%}")
        print(f"  Quality Distribution:")
        for quality, count in report['judge_metrics']['quality_distribution'].items():
            print(f"    {quality}: {count}")
    
    print(f"\nSuccess Rate by Category:")
    for category, rate in sorted(report['by_category'].items()):
        print(f"  {category}: {rate:.1%}")
    
    # Save results
    with open("eval_results_advanced.json", 'w') as f:
        json.dump({
            "report": report,
            "detailed_results": [
                {
                    **r.to_dict(),
                    "judge_evaluation": getattr(r, 'judge_evaluation', None)
                }
                for r in results
            ]
        }, f, indent=2)
    
    print(f"\nDetailed results saved to eval_results_advanced.json")
    
    # Cleanup
    import os
    test_files = [
        "test_eval.txt", "calc_result.txt", "eval_test.md",
        "summary.md", "report.txt", "average.txt", "data.json",
        "file1.txt", "file2.txt", "file3.txt", "report.md", "facts.md"
    ]
    for file in test_files:
        if os.path.exists(file):
            os.remove(file)


if __name__ == "__main__":
    # Import base test suite
    from eval_document_agent import create_test_suite
    
    asyncio.run(run_advanced_evaluation())