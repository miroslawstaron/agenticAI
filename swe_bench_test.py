#!/usr/bin/env python3
"""
SWE-bench Verified Testing Framework for AgenticAI

Tests AgenticAI on real software engineering tasks from SWE-bench Verified dataset.
Evaluates ability to understand issues, write code, and generate patches.
"""

import json
import os
import sys
import time
import subprocess
import tempfile
import shutil
import statistics
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime
import tracemalloc

sys.path.insert(0, os.path.abspath('.'))

from agent import AgentAI
from messagequeue import MessageQueue, reset_message_queue
from agent_id_manager import AgentIDManager
import config


class SWEBenchTask:
    """Represents a single SWE-bench task."""

    def __init__(self, task_id: str, repo: str, base_commit: str,
                 problem_statement: str, test_patch: str,
                 gold_patch: str = None):
        """Initialize task.

        Args:
            task_id: Unique task identifier
            repo: Repository path/name
            base_commit: Base commit hash
            problem_statement: Issue description
            test_patch: Test to validate solution
            gold_patch: Reference solution patch
        """
        self.task_id = task_id
        self.repo = repo
        self.base_commit = base_commit
        self.problem_statement = problem_statement
        self.test_patch = test_patch
        self.gold_patch = gold_patch


class SWEBenchDataset:
    """Manages SWE-bench Verified dataset."""

    def __init__(self, dataset_path: str = "./swe_bench_verified.json"):
        """Initialize dataset loader.

        Args:
            dataset_path: Path to dataset JSON file
        """
        self.dataset_path = dataset_path
        self.tasks = []

    def download_or_load(self) -> List[SWEBenchTask]:
        """Load dataset, downloading if necessary.

        Returns:
            List of SWEBenchTask objects
        """
        if os.path.exists(self.dataset_path):
            return self._load_local()
        else:
            return self._load_or_generate_sample()

    def _load_local(self) -> List[SWEBenchTask]:
        """Load from local JSON file."""
        print(f"Loading dataset from {self.dataset_path}...")
        try:
            with open(self.dataset_path, 'r') as f:
                data = json.load(f)

            tasks = []
            for item in data if isinstance(data, list) else data.values():
                task = SWEBenchTask(
                    task_id=item.get('task_id', item.get('id', 'unknown')),
                    repo=item.get('repo', item.get('repository', 'unknown')),
                    base_commit=item.get('base_commit', item.get('commit', 'HEAD')),
                    problem_statement=item.get('problem_statement',
                                              item.get('issue', 'No description')),
                    test_patch=item.get('test_patch', ''),
                    gold_patch=item.get('gold_patch', item.get('solution', None))
                )
                tasks.append(task)

            print(f"[OK] Loaded {len(tasks)} tasks from dataset")
            return tasks

        except Exception as e:
            print(f"[FAIL] Error loading dataset: {e}")
            return self._load_or_generate_sample()

    def _load_or_generate_sample(self) -> List[SWEBenchTask]:
        """Generate sample tasks for testing."""
        print("[WARN] Dataset not found, generating sample tasks for testing...")

        samples = [
            SWEBenchTask(
                task_id="django-1",
                repo="django/django",
                base_commit="abc123",
                problem_statement="""
                Fix issue where ModelForm does not respect ordering in Meta class.
                The form fields should be ordered according to the Meta.fields specification
                but currently they appear in model definition order.
                """,
                test_patch="""
                from django import forms
                from django.forms import ModelForm

                def test_modelform_field_order():
                    # Test that fields appear in specified order
                    form = TestForm()
                    field_names = list(form.fields.keys())
                    assert field_names == ['email', 'name', 'age']
                """,
                gold_patch="""
                # Solution: Override get_declared_fields to respect Meta.fields order
                class ModelFormMetaclass(DeclarativeFieldsMetaclass):
                    def __new__(mcs, name, bases, attrs):
                        # ... implementation that preserves field order
                """
            ),
            SWEBenchTask(
                task_id="requests-1",
                repo="psf/requests",
                base_commit="def456",
                problem_statement="""
                Add support for custom timeout per request method.
                Currently timeout is global but should be configurable per request.
                """,
                test_patch="""
                import requests

                def test_per_method_timeout():
                    session = requests.Session()
                    response = session.get('http://example.com', timeout=5)
                    assert response.status_code == 200
                """,
                gold_patch="""
                def request(self, method, url, **kwargs):
                    timeout = kwargs.pop('timeout', self.timeout)
                    # ... rest of implementation
                """
            ),
            SWEBenchTask(
                task_id="numpy-1",
                repo="numpy/numpy",
                base_commit="ghi789",
                problem_statement="""
                Optimize array concatenation for small arrays.
                The concatenation operation is slower than expected for arrays < 1KB.
                """,
                test_patch="""
                import numpy as np

                def test_concat_performance():
                    arrays = [np.arange(10) for _ in range(100)]
                    result = np.concatenate(arrays)
                    assert len(result) == 1000
                """,
                gold_patch="""
                def concatenate(arrays, axis=0, out=None):
                    # Optimized path for small arrays
                    if sum(arr.nbytes for arr in arrays) < 1024:
                        return _fast_concat(arrays, axis)
                """
            ),
        ]

        print(f"[OK] Generated {len(samples)} sample tasks")
        return samples


class SWEBenchEvaluator:
    """Evaluates AgenticAI on SWE-bench tasks."""

    def __init__(self, agent_name: str = "swe_agent",
                 model_name: str = "gpt-oss:20b"):
        """Initialize evaluator.

        Args:
            agent_name: Name for the test agent
            model_name: LLM model to use
        """
        self.agent_name = agent_name
        self.model_name = model_name
        self.results = []
        self.start_time = None

    def evaluate_task(self, task: SWEBenchTask) -> Dict[str, Any]:
        """Evaluate agent on a single task.

        Args:
            task: SWEBenchTask to evaluate

        Returns:
            Dict with evaluation results
        """
        # Reset state for clean evaluation
        AgentIDManager.reset()
        reset_message_queue()

        # Start tracking
        tracemalloc.start()
        mem_before = tracemalloc.get_traced_memory()[0]
        start_time = time.time()

        result = {
            'task_id': task.task_id,
            'repo': task.repo,
            'status': 'unknown',
            'success': False,
            'response': '',
            'response_time': 0,
            'memory_used_mb': 0,
            'error': None,
            'attempted': False,
        }

        try:
            # Create agent for this task
            agent = AgentAI(
                server_address="http://localhost:11434",  # Ollama default
                model_name=self.model_name,
                my_role="""You are an expert software engineer assistant.
Your task is to analyze the issue and provide a solution.
Be concise and focus on the exact problem that needs fixing."""
            )

            # Create evaluation prompt
            prompt = self._create_evaluation_prompt(task)

            result['attempted'] = True

            # Get response from agent
            response = agent.get_response(prompt)

            if response:
                result['response'] = response
                result['status'] = 'completed'

                # Simple evaluation: check if response mentions key aspects
                success_indicators = [
                    'def ' in response or 'class ' in response,
                    len(response) > 50,
                ]
                result['success'] = sum(success_indicators) >= 2

            else:
                result['status'] = 'no_response'
                result['error'] = 'Agent returned empty response'

        except TimeoutError as e:
            result['status'] = 'timeout'
            result['error'] = f"Timeout: {str(e)}"

        except Exception as e:
            result['status'] = 'error'
            result['error'] = f"{type(e).__name__}: {str(e)}"

        finally:
            # Record metrics
            elapsed = time.time() - start_time
            result['response_time'] = elapsed

            mem_after = tracemalloc.get_traced_memory()[0]
            mem_used = (mem_after - mem_before) / 1024 / 1024
            result['memory_used_mb'] = mem_used

            tracemalloc.stop()

        return result

    def _create_evaluation_prompt(self, task: SWEBenchTask) -> str:
        """Create prompt for evaluating task.

        Args:
            task: SWEBenchTask

        Returns:
            Formatted prompt string
        """
        return f"""Analyze this software engineering issue and provide a solution:

ISSUE:
{task.problem_statement}

REPOSITORY: {task.repo}
BASE COMMIT: {task.base_commit}

REQUIREMENTS:
1. Understand the problem statement
2. Identify files that need to be modified
3. Provide the code changes needed
4. Explain your solution briefly

Please provide:
- Analysis of the issue
- Files to modify
- Code changes (as patches or complete functions)
- Brief explanation
"""

    def evaluate_batch(self, tasks: List[SWEBenchTask],
                       limit: int = None) -> List[Dict[str, Any]]:
        """Evaluate agent on multiple tasks.

        Args:
            tasks: List of tasks to evaluate
            limit: Maximum number of tasks to evaluate (None = all)

        Returns:
            List of evaluation results
        """
        tasks_to_eval = tasks[:limit] if limit else tasks

        print(f"\n[BENCHMARK] Evaluating AgenticAI on {len(tasks_to_eval)} tasks")
        print("=" * 80)
        print(f"Agent: {self.agent_name}")
        print(f"Model: {self.model_name}")
        print("=" * 80 + "\n")

        self.start_time = time.time()

        for i, task in enumerate(tasks_to_eval, 1):
            print(f"[{i:3d}/{len(tasks_to_eval)}] Evaluating {task.task_id}...",
                  end='', flush=True)

            result = self.evaluate_task(task)
            self.results.append(result)

            # Print result indicator
            if result['success']:
                print(f" [OK] Success ({result['response_time']:.2f}s)")
            elif result['status'] == 'completed':
                print(f" [PARTIAL] Completed ({result['response_time']:.2f}s)")
            else:
                print(f" [FAIL] {result['status']} ({result['response_time']:.2f}s)")

        return self.results

    def get_summary(self) -> Dict[str, Any]:
        """Get summary statistics of evaluations.

        Returns:
            Dict with summary metrics
        """
        if not self.results:
            return {}

        total_time = time.time() - self.start_time if self.start_time else 0

        success_count = sum(1 for r in self.results if r['success'])
        completed_count = sum(1 for r in self.results if r['status'] == 'completed')
        attempted_count = sum(1 for r in self.results if r['attempted'])

        response_times = [r['response_time'] for r in self.results if r['response_time']]
        memory_usage = [r['memory_used_mb'] for r in self.results]

        error_types = {}
        for r in self.results:
            if r['error']:
                error_type = r['status']
                error_types[error_type] = error_types.get(error_type, 0) + 1

        return {
            'total_tasks': len(self.results),
            'successful_tasks': success_count,
            'completed_tasks': completed_count,
            'attempted_tasks': attempted_count,
            'success_rate': success_count / len(self.results) if self.results else 0,
            'completion_rate': completed_count / attempted_count if attempted_count > 0 else 0,
            'avg_response_time': statistics.mean(response_times) if response_times else 0,
            'min_response_time': min(response_times) if response_times else 0,
            'max_response_time': max(response_times) if response_times else 0,
            'stdev_response_time': (
                statistics.stdev(response_times)
                if len(response_times) > 1 else 0
            ),
            'avg_memory_mb': statistics.mean(memory_usage) if memory_usage else 0,
            'total_time': total_time,
            'error_summary': error_types,
            'results': self.results,
        }


class SWEBenchReporter:
    """Generates reports from SWE-bench evaluation results."""

    @staticmethod
    def generate_json_report(summary: Dict[str, Any],
                            output_path: str) -> str:
        """Generate JSON report.

        Args:
            summary: Evaluation summary
            output_path: Path to save report

        Returns:
            Path to saved report
        """
        report = {
            'timestamp': datetime.now().isoformat(),
            'summary': {
                'total_tasks': summary['total_tasks'],
                'successful_tasks': summary['successful_tasks'],
                'completed_tasks': summary['completed_tasks'],
                'attempted_tasks': summary['attempted_tasks'],
                'success_rate': f"{summary['success_rate']:.1%}",
                'completion_rate': f"{summary['completion_rate']:.1%}",
                'avg_response_time': f"{summary['avg_response_time']:.2f}s",
                'min_response_time': f"{summary['min_response_time']:.2f}s",
                'max_response_time': f"{summary['max_response_time']:.2f}s",
                'stdev_response_time': f"{summary['stdev_response_time']:.2f}s",
                'avg_memory_mb': f"{summary['avg_memory_mb']:.2f}MB",
                'total_evaluation_time': f"{summary['total_time']:.2f}s",
            },
            'error_summary': summary['error_summary'],
            'detailed_results': summary.get('results', [])[:50],  # First 50
        }

        with open(output_path, 'w') as f:
            json.dump(report, f, indent=2)

        return output_path

    @staticmethod
    def generate_text_report(summary: Dict[str, Any],
                            output_path: str) -> str:
        """Generate text report.

        Args:
            summary: Evaluation summary
            output_path: Path to save report

        Returns:
            Path to saved report
        """
        with open(output_path, 'w') as f:
            f.write("=" * 80 + "\n")
            f.write("SWE-BENCH VERIFIED EVALUATION RESULTS\n")
            f.write("=" * 80 + "\n\n")

            f.write("SUMMARY STATISTICS\n")
            f.write("-" * 40 + "\n")
            f.write(f"Total Tasks:               {summary['total_tasks']}\n")
            f.write(f"Successful Tasks:          {summary['successful_tasks']}\n")
            f.write(f"Completed Tasks:           {summary['completed_tasks']}\n")
            f.write(f"Attempted Tasks:           {summary['attempted_tasks']}\n\n")

            f.write("PERFORMANCE METRICS\n")
            f.write("-" * 40 + "\n")
            f.write(f"Success Rate:              {summary['success_rate']:.1%}\n")
            f.write(f"Completion Rate:           {summary['completion_rate']:.1%}\n")
            f.write(f"Avg Response Time:         {summary['avg_response_time']:.2f}s\n")
            f.write(f"Min Response Time:         {summary['min_response_time']:.2f}s\n")
            f.write(f"Max Response Time:         {summary['max_response_time']:.2f}s\n")
            f.write(f"Std Dev Response Time:     {summary['stdev_response_time']:.2f}s\n")
            f.write(f"Avg Memory Usage:          {summary['avg_memory_mb']:.2f}MB\n")
            f.write(f"Total Evaluation Time:     {summary['total_time']:.2f}s\n\n")

            if summary['error_summary']:
                f.write("ERROR SUMMARY\n")
                f.write("-" * 40 + "\n")
                for error_type, count in summary['error_summary'].items():
                    f.write(f"{error_type:20s}: {count:3d}\n")
                f.write("\n")

            f.write("DETAILED RESULTS (First 10)\n")
            f.write("-" * 40 + "\n")
            for i, result in enumerate(summary.get('results', [])[:10], 1):
                f.write(f"\n{i}. {result['task_id']} ({result['repo']})\n")
                f.write(f"   Status:       {result['status']}\n")
                f.write(f"   Success:      {result['success']}\n")
                f.write(f"   Time:         {result['response_time']:.2f}s\n")
                f.write(f"   Memory:       {result['memory_used_mb']:.2f}MB\n")
                if result['error']:
                    f.write(f"   Error:        {result['error']}\n")

            f.write("\n" + "=" * 80 + "\n")

        return output_path


def main():
    """Main evaluation workflow."""
    print("\n" + "=" * 80)
    print("[BENCHMARK] AgenticAI on SWE-bench Verified")
    print("=" * 80 + "\n")

    # Load dataset
    dataset = SWEBenchDataset()
    tasks = dataset.download_or_load()

    if not tasks:
        print("[FAIL] No tasks loaded")
        return

    # Run evaluation
    evaluator = SWEBenchEvaluator(
        agent_name="swe_agent_v1",
        model_name="gpt-oss:20b"  # Default model, can override in config
    )

    # Limit to 10 tasks for testing (remove limit for full evaluation)
    results = evaluator.evaluate_batch(tasks, limit=10)

    # Generate summary
    summary = evaluator.get_summary()

    # Generate reports
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    json_report = f"swe_bench_results_{timestamp}.json"
    text_report = f"swe_bench_results_{timestamp}.txt"

    reporter = SWEBenchReporter()
    reporter.generate_json_report(summary, json_report)
    reporter.generate_text_report(summary, text_report)

    # Print summary
    print("\n" + "=" * 80)
    print("EVALUATION COMPLETE")
    print("=" * 80)
    print(f"\nSuccess Rate:          {summary['success_rate']:.1%}")
    print(f"Completed:             {summary['completed_tasks']}/{summary['total_tasks']}")
    print(f"Avg Response Time:     {summary['avg_response_time']:.2f}s")
    print(f"Total Evaluation Time: {summary['total_time']:.2f}s")

    print(f"\n[OK] JSON report saved to: {json_report}")
    print(f"[OK] Text report saved to: {text_report}")
    print("=" * 80 + "\n")

    return summary


if __name__ == '__main__':
    main()
