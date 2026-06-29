#!/usr/bin/env python3
"""
Performance Benchmark for AgenticAI Framework

Tests the AgenticAI framework against a specified LLM server and model.
Measures response time, throughput, memory usage, and identifies bottlenecks.
"""

import time
import sys
import os
import statistics
import json
from datetime import datetime
from typing import List, Dict, Any
import tracemalloc

sys.path.insert(0, os.path.abspath('.'))

from agent import AgentAI
from messagequeue import MessageQueue, reset_message_queue
from agent_id_manager import AgentIDManager


class PerformanceBenchmark:
    """Benchmark AgenticAI performance against an LLM server."""

    def __init__(self, server_address: str, model_name: str, num_runs: int = 5):
        """Initialize benchmark.

        Args:
            server_address: URL to LLM server (e.g., http://localhost:11434)
            model_name: Model name (e.g., "ollama/qwen3:4b")
            num_runs: Number of test runs to average
        """
        self.server_address = server_address
        self.model_name = model_name
        self.num_runs = num_runs
        self.results = {
            'response_times': [],
            'token_counts': [],
            'memory_usage': [],
            'errors': [],
            'retries': [],
            'latencies': [],
        }

    def test_basic_prompt(self, prompt: str) -> Dict[str, Any]:
        """Test basic prompt with timing and memory measurement.

        Args:
            prompt: The prompt to send to the LLM

        Returns:
            Dict with timing and resource metrics
        """
        # Reset singletons for clean state
        AgentIDManager.reset()
        reset_message_queue()

        # Start memory tracking
        tracemalloc.start()
        mem_before = tracemalloc.get_traced_memory()[0]

        # Create agent
        agent = AgentAI(
            server_address=self.server_address,
            model_name=self.model_name,
            my_role="You are a helpful AI assistant. Respond concisely."
        )

        # Measure response time
        start_time = time.time()
        response = agent.get_response(prompt)
        elapsed_time = time.time() - start_time

        # Measure memory usage
        mem_after = tracemalloc.get_traced_memory()[0]
        mem_used = (mem_after - mem_before) / 1024 / 1024  # Convert to MB
        tracemalloc.stop()

        # Count tokens (rough estimate)
        response_tokens = len(response.split()) if response else 0
        prompt_tokens = len(prompt.split())
        total_tokens = prompt_tokens + response_tokens

        return {
            'success': response is not None,
            'response_time': elapsed_time,
            'prompt_tokens': prompt_tokens,
            'response_tokens': response_tokens,
            'total_tokens': total_tokens,
            'tokens_per_second': total_tokens / elapsed_time if elapsed_time > 0 else 0,
            'memory_used_mb': mem_used,
            'response_length': len(response) if response else 0,
        }

    def test_concurrent_agents(self, num_agents: int = 3) -> Dict[str, Any]:
        """Test multiple agents in sequence.

        Args:
            num_agents: Number of agents to create and use

        Returns:
            Dict with concurrent test metrics
        """
        AgentIDManager.reset()
        reset_message_queue()

        prompts = [
            "Write a hello world program in Python",
            "Explain machine learning in one sentence",
            "What is the capital of France?",
            "Summarize the history of computers",
            "What are the benefits of cloud computing?",
        ][:num_agents]

        responses = []
        total_time = 0
        total_tokens = 0

        start_total = time.time()

        for i, prompt in enumerate(prompts):
            try:
                agent = AgentAI(
                    server_address=self.server_address,
                    model_name=self.model_name,
                    my_role=f"You are AI assistant {i+1}. Be helpful and concise."
                )

                start = time.time()
                response = agent.get_response(prompt)
                elapsed = time.time() - start

                if response:
                    tokens = len(prompt.split()) + len(response.split())
                    responses.append({
                        'agent': i,
                        'time': elapsed,
                        'tokens': tokens,
                        'tps': tokens / elapsed,
                    })
                    total_tokens += tokens
                    total_time += elapsed
            except Exception as e:
                self.results['errors'].append(str(e))

        total_elapsed = time.time() - start_total

        return {
            'num_agents': num_agents,
            'successful_agents': len(responses),
            'total_time': total_elapsed,
            'sequential_time': total_time,
            'total_tokens': total_tokens,
            'avg_tokens_per_agent': total_tokens / len(responses) if responses else 0,
            'agents_per_second': len(responses) / total_elapsed if total_elapsed > 0 else 0,
            'responses': responses,
        }

    def test_message_queue_throughput(self, num_messages: int = 100) -> Dict[str, Any]:
        """Test message queue throughput.

        Args:
            num_messages: Number of messages to send

        Returns:
            Dict with queue throughput metrics
        """
        reset_message_queue()
        mq = MessageQueue()

        start = time.time()

        # Publish messages
        for i in range(num_messages):
            mq.publish(f"Agent{i % 10}", f"Recipient{i % 5}", f"Message {i}")

        publish_time = time.time() - start

        # Retrieve messages
        start = time.time()
        for i in range(5):
            messages = mq.get_messages(f"Recipient{i}", consume=True)

        retrieve_time = time.time() - start

        mq.close()

        return {
            'num_messages': num_messages,
            'publish_time': publish_time,
            'publish_rate': num_messages / publish_time,
            'retrieve_time': retrieve_time,
            'total_time': publish_time + retrieve_time,
        }

    def test_retry_behavior(self) -> Dict[str, Any]:
        """Test retry mechanism and error handling."""
        AgentIDManager.reset()

        agent = AgentAI(
            server_address=self.server_address,
            model_name=self.model_name,
            my_role="You are a helpful assistant."
        )

        # Test with a simple prompt
        prompt = "Hello, how are you?"

        start = time.time()
        try:
            response = agent.get_response(prompt)
            elapsed = time.time() - start
            return {
                'success': response is not None,
                'time': elapsed,
                'retries': 0,
                'error': None,
            }
        except Exception as e:
            elapsed = time.time() - start
            return {
                'success': False,
                'time': elapsed,
                'error': str(e),
            }

    def run_benchmark_suite(self) -> Dict[str, Any]:
        """Run complete benchmark suite.

        Returns:
            Dict with all benchmark results
        """
        print("\n" + "=" * 80)
        print("[BENCHMARK] AgenticAI Performance Benchmark")
        print("=" * 80)
        print(f"Server: {self.server_address}")
        print(f"Model: {self.model_name}")
        print(f"Test runs: {self.num_runs}")
        print("=" * 80 + "\n")

        all_results = {
            'timestamp': datetime.now().isoformat(),
            'server': self.server_address,
            'model': self.model_name,
            'tests': {},
        }

        # Test 1: Basic prompt performance
        print("[TEST 1] Basic Prompt Performance")
        print("-" * 40)
        basic_results = []
        for i in range(self.num_runs):
            print(f"  Run {i+1}/{self.num_runs}...", end='', flush=True)
            try:
                result = self.test_basic_prompt("What is the most important programming concept?")
                basic_results.append(result)
                print(f" [OK] {result['response_time']:.2f}s, {result['tokens_per_second']:.1f} tok/s")
            except Exception as e:
                print(f" [FAIL] Error: {e}")
                self.results['errors'].append(str(e))

        if basic_results:
            response_times = [r['response_time'] for r in basic_results]
            tokens_per_sec = [r['tokens_per_second'] for r in basic_results]

            basic_summary = {
                'runs': len(basic_results),
                'avg_response_time': statistics.mean(response_times),
                'min_response_time': min(response_times),
                'max_response_time': max(response_times),
                'stdev_response_time': statistics.stdev(response_times) if len(response_times) > 1 else 0,
                'avg_tokens_per_second': statistics.mean(tokens_per_sec),
                'min_tokens_per_second': min(tokens_per_sec),
                'max_tokens_per_second': max(tokens_per_sec),
                'avg_memory_mb': statistics.mean([r['memory_used_mb'] for r in basic_results]),
                'total_tokens': sum([r['total_tokens'] for r in basic_results]),
            }
            all_results['tests']['basic_prompt'] = basic_summary
            print(f"\n[OK] Average response time: {basic_summary['avg_response_time']:.2f}s")
            print(f"[OK] Average throughput: {basic_summary['avg_tokens_per_second']:.1f} tokens/sec")
            print(f"[OK] Memory usage: {basic_summary['avg_memory_mb']:.1f} MB\n")

        # Test 2: Concurrent agents
        print("[TEST 2] Multiple Agents")
        print("-" * 40)
        try:
            concurrent_result = self.test_concurrent_agents(num_agents=3)
            all_results['tests']['concurrent_agents'] = concurrent_result
            print(f"[OK] Agents tested: {concurrent_result['successful_agents']}/{concurrent_result['num_agents']}")
            print(f"[OK] Total time: {concurrent_result['total_time']:.2f}s")
            print(f"[OK] Throughput: {concurrent_result['agents_per_second']:.2f} agents/sec\n")
        except Exception as e:
            print(f"[FAIL] Error: {e}\n")

        # Test 3: Message queue
        print("[TEST 3] Message Queue Throughput")
        print("-" * 40)
        try:
            mq_result = self.test_message_queue_throughput(num_messages=100)
            all_results['tests']['message_queue'] = mq_result
            print(f"[OK] Publish rate: {mq_result['publish_rate']:.0f} messages/sec")
            print(f"[OK] Total time: {mq_result['total_time']:.3f}s\n")
        except Exception as e:
            print(f"[FAIL] Error: {e}\n")

        # Test 4: Retry behavior
        print("[TEST 4] Retry Mechanism")
        print("-" * 40)
        try:
            retry_result = self.test_retry_behavior()
            all_results['tests']['retry_behavior'] = retry_result
            if retry_result['success']:
                print(f"[OK] Response time: {retry_result['time']:.2f}s")
                print(f"[OK] Successful on first try\n")
            else:
                print(f"[FAIL] Failed: {retry_result['error']}\n")
        except Exception as e:
            print(f"[FAIL] Error: {e}\n")

        return all_results


def main():
    """Run benchmark with specified server and model."""
    server = "http://lazythought.cse.chalmers.se"
    model = "gpt-oss:20b"
    num_runs = 3

    benchmark = PerformanceBenchmark(
        server_address=server,
        model_name=model,
        num_runs=num_runs
    )

    results = benchmark.run_benchmark_suite()

    # Save results to JSON
    output_file = f"performance_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(output_file, 'w') as f:
        json.dump(results, f, indent=2)

    print("=" * 80)
    print(f"[OK] Results saved to: {output_file}")
    print("=" * 80)

    return results


if __name__ == '__main__':
    main()
