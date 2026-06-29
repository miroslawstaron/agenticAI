#!/usr/bin/env python3
"""
Detailed SWE-bench test with prompt, expected output, and agent response logging
"""

import sys
import os
sys.path.insert(0, os.path.abspath('.'))

import requests
import time
import json
from datetime import datetime

def run_detailed_test(server, model, num_tasks=3):
    """Run detailed SWE-bench test"""

    # Detailed SWE-bench tasks with expected outputs
    tasks = [
        {
            "id": "django-1",
            "repo": "django/django",
            "problem": "Fix issue where ModelForm does not preserve field order from Meta.fields.",
            "description": "The form fields should be ordered according to the Meta.fields specification but currently they appear in model definition order.",
            "expected_output": "Fields should appear in the order specified in Meta.fields, not in the model's field definition order. The fix should modify how form fields are ordered when Meta.fields is specified."
        },
        {
            "id": "requests-1",
            "repo": "psf/requests",
            "problem": "Add support for custom timeout per request in Session.",
            "description": "Currently timeout is global but should be configurable per request.",
            "expected_output": "The Session.request() method should accept a timeout parameter that overrides the session's default timeout. This allows per-request timeout configuration."
        },
        {
            "id": "numpy-1",
            "repo": "numpy/numpy",
            "problem": "Optimize array concatenation for small arrays.",
            "description": "The concatenation operation is slower than expected for arrays < 1KB.",
            "expected_output": "For small arrays (< 1KB total size), use a faster concatenation path that avoids unnecessary memory allocations and copies."
        },
    ][:num_tasks]

    print(f"Testing with {len(tasks)} tasks\n")

    results = []
    start_time = time.time()

    for i, task in enumerate(tasks, 1):
        task_id = task["id"]
        repo = task["repo"]
        problem = task["problem"]
        description = task["description"]
        expected = task["expected_output"]

        print("\n" + "="*80)
        print(f"[{i}/{len(tasks)}] {task_id} - {repo}")
        print("="*80)
        print(f"Problem: {problem}")
        print(f"Description: {description}")
        print(f"Expected: {expected}")
        print(f"\nCalling agent...", end=' ', flush=True)

        try:
            # Build comprehensive prompt
            full_prompt = f"""You are an expert software engineer tasked with fixing a GitHub issue.

REPOSITORY: {repo}

ISSUE TITLE: {problem}

ISSUE DESCRIPTION:
{description}

EXPECTED OUTCOME:
{expected}

TASK:
1. Analyze the issue described above
2. Identify the files that need to be modified
3. Provide a detailed solution with code changes
4. Explain how your solution addresses the issue

Please provide your analysis and solution:"""

            # Call Ollama API
            payload = {
                "model": model,
                "messages": [
                    {
                        "role": "system",
                        "content": "You are an expert software engineer who solves GitHub issues. Provide detailed, actionable solutions with code examples."
                    },
                    {
                        "role": "user",
                        "content": full_prompt
                    }
                ],
                "stream": False
            }

            task_start = time.time()
            response = requests.post(
                f"{server}/api/chat",
                json=payload,
                timeout=60,
                headers={"Content-Type": "application/json"}
            )
            task_time = time.time() - task_start

            if response.status_code == 200:
                data = response.json()
                agent_output = data.get("message", {}).get("content", "")

                if agent_output and len(agent_output) > 10:
                    print(f"[OK] ({task_time:.2f}s)\n")
                    print(f"AGENT OUTPUT:")
                    print("-"*80)
                    preview = agent_output[:500] + ("..." if len(agent_output) > 500 else "")
                    print(preview)
                    print("-"*80 + "\n")

                    results.append({
                        "task": task_id,
                        "repo": repo,
                        "status": "success",
                        "time": task_time,
                        "prompt": {
                            "problem": problem,
                            "description": description,
                            "full_prompt": full_prompt
                        },
                        "expected_output": expected,
                        "agent_output": agent_output,
                        "output_length": len(agent_output)
                    })
                else:
                    print(f"[FAIL] Empty response\n")
                    results.append({
                        "task": task_id,
                        "repo": repo,
                        "status": "empty",
                        "time": task_time,
                        "prompt": {
                            "problem": problem,
                            "description": description
                        },
                        "expected_output": expected,
                        "agent_output": None,
                        "error": "Empty response"
                    })
            else:
                error_msg = f"HTTP {response.status_code}"
                if response.text:
                    try:
                        error_data = response.json()
                        error_msg = error_data.get("error", error_msg)
                    except:
                        pass

                print(f"[FAIL] {error_msg}\n")
                results.append({
                    "task": task_id,
                    "repo": repo,
                    "status": "error",
                    "http_code": response.status_code,
                    "error": error_msg,
                    "prompt": {
                        "problem": problem,
                        "description": description
                    },
                    "expected_output": expected,
                    "agent_output": None
                })

        except requests.exceptions.Timeout:
            print(f"[TIMEOUT]\n")
            results.append({
                "task": task_id,
                "repo": repo,
                "status": "timeout",
                "prompt": {"problem": problem, "description": description},
                "expected_output": expected,
                "agent_output": None,
                "error": "Request timeout"
            })
        except requests.exceptions.ConnectionError as e:
            print(f"[CONNECTION ERROR]\n")
            results.append({
                "task": task_id,
                "repo": repo,
                "status": "connection_error",
                "prompt": {"problem": problem, "description": description},
                "expected_output": expected,
                "agent_output": None,
                "error": str(e)[:200]
            })
        except Exception as e:
            print(f"[ERROR] {str(e)[:50]}\n")
            results.append({
                "task": task_id,
                "repo": repo,
                "status": "error",
                "prompt": {"problem": problem, "description": description},
                "expected_output": expected,
                "agent_output": None,
                "error": str(e)[:200]
            })

    total_time = time.time() - start_time

    # Summary
    print("\n" + "="*80)
    print("SUMMARY")
    print("="*80 + "\n")

    success = sum(1 for r in results if r["status"] == "success")
    total = len(results)
    success_rate = (success / total * 100) if total > 0 else 0

    print(f"Successful:      {success}/{total}")
    print(f"Success Rate:    {success_rate:.1f}%")
    print(f"Total Time:      {total_time:.2f}s")
    if total > 0:
        print(f"Avg Time/Task:   {total_time/total:.2f}s")
    print("")

    # Save detailed results
    output_dir = "swe_bench_results"
    os.makedirs(output_dir, exist_ok=True)

    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    results_file = os.path.join(output_dir, f"swe_bench_detailed_{timestamp}.json")

    detailed_results = {
        "timestamp": timestamp,
        "configuration": {
            "server": server,
            "model": model,
            "num_tasks": total
        },
        "summary": {
            "success_rate": success_rate,
            "total_tasks": total,
            "successful_tasks": success,
            "total_time": total_time,
            "avg_time_per_task": total_time / total if total > 0 else 0
        },
        "results": results
    }

    with open(results_file, 'w') as f:
        json.dump(detailed_results, f, indent=2, ensure_ascii=False)

    print(f"[OK] Detailed results saved to: {results_file}")

    # Also save a formatted text report
    text_file = os.path.join(output_dir, f"swe_bench_detailed_{timestamp}.txt")
    with open(text_file, 'w') as f:
        f.write("SWE-BENCH TEST RESULTS\n")
        f.write("="*80 + "\n")
        f.write(f"Timestamp: {timestamp}\n")
        f.write(f"Server: {server}\n")
        f.write(f"Model: {model}\n")
        f.write(f"Total Time: {total_time:.2f}s\n\n")

        f.write("SUMMARY\n")
        f.write("="*80 + "\n")
        f.write(f"Success Rate: {success_rate:.1f}%\n")
        f.write(f"Tasks: {success}/{total}\n\n")

        for i, result in enumerate(results, 1):
            f.write("\n" + "="*80 + "\n")
            f.write(f"[{i}] {result['task']} - {result.get('repo', 'N/A')}\n")
            f.write("="*80 + "\n")
            f.write(f"Status: {result['status']}\n")
            time_val = result.get('time', 'N/A')
            if isinstance(time_val, (int, float)):
                f.write(f"Time: {time_val:.2f}s\n\n")
            else:
                f.write(f"Time: {time_val}\n\n")

            f.write("PROBLEM:\n")
            prompt_data = result.get('prompt', {})
            f.write(f"{prompt_data.get('problem', 'N/A')}\n\n")

            f.write("EXPECTED OUTPUT:\n")
            f.write(f"{result.get('expected_output', 'N/A')}\n\n")

            if result.get('agent_output'):
                f.write("AGENT OUTPUT:\n")
                f.write(f"{result['agent_output']}\n\n")
            else:
                error = result.get('error', 'No output')
                f.write(f"AGENT OUTPUT: [ERROR] {error}\n\n")

    print(f"[OK] Text report saved to: {text_file}")

    return results_file, text_file

if __name__ == "__main__":
    server = "http://lazythought.cse.chalmers.se"
    model = "qwen2.5:14b"
    num_tasks = 3

    # Allow command-line overrides
    if len(sys.argv) > 1:
        num_tasks = int(sys.argv[1])
    if len(sys.argv) > 2:
        model = sys.argv[2]
    if len(sys.argv) > 3:
        server = sys.argv[3]

    json_file, text_file = run_detailed_test(server, model, num_tasks)

    print("\n" + "="*80)
    print("TEST COMPLETE")
    print("="*80)
    print(f"\nResults saved to:")
    print(f"  JSON:  {json_file}")
    print(f"  Text:  {text_file}\n")
