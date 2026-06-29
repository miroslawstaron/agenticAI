<#
.SYNOPSIS
    Enhanced SWE-bench test with detailed results (prompt, expected output, agent output)
#>

param(
    [string]$Server = "http://lazythought.cse.chalmers.se",
    [string]$Model = "qwen2.5:14b",
    [int]$Tasks = 3
)

Write-Host "`n" + ("="*80) -ForegroundColor Magenta
Write-Host "SWE-BENCH TEST WITH DETAILED RESULTS" -ForegroundColor Magenta
Write-Host ("="*80) -ForegroundColor Magenta + "`n"

Write-Host "Server: $Server" -ForegroundColor Cyan
Write-Host "Model: $Model" -ForegroundColor Cyan
Write-Host "Tasks: $Tasks" -ForegroundColor Cyan
Write-Host ""

# Create Python test script with detailed output
$pythonScript = @"
import sys
sys.path.insert(0, '.')

import requests
import time
import json
from datetime import datetime

server = "$Server"
model = "$Model"
num_tasks = $Tasks

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

    sep = "="*76
    print(f"\n[{sep}]")
    print(f"[{i}/{len(tasks)}] {task_id} - {repo}")
    print(f"[{sep}]")
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
                {{
                    "role": "system",
                    "content": "You are an expert software engineer who solves GitHub issues. Provide detailed, actionable solutions with code examples."
                }},
                {{
                    "role": "user",
                    "content": full_prompt
                }}
            ],
            "stream": False
        }

        task_start = time.time()
        response = requests.post(
            f"{server}/api/chat",
            json=payload,
            timeout=60,
            headers={{"Content-Type": "application/json"}}
        )
        task_time = time.time() - task_start

        if response.status_code == 200:
            data = response.json()
            agent_output = data.get("message", {{}}).get("content", "")

            if agent_output and len(agent_output) > 10:
                print(f"[OK] ({task_time:.2f}s)\n")
                print(f"AGENT OUTPUT:")
                print(f"{'-'*76}")
                preview = agent_output[:500] + ("..." if len(agent_output) > 500 else "")
                print(preview)
                print(f"{'-'*76}\n")

                results.append({{
                    "task": task_id,
                    "repo": repo,
                    "status": "success",
                    "time": task_time,
                    "prompt": {{
                        "problem": problem,
                        "description": description,
                        "full_prompt": full_prompt
                    }},
                    "expected_output": expected,
                    "agent_output": agent_output,
                    "output_length": len(agent_output)
                }})
            else:
                print(f"[FAIL] Empty response\n")
                results.append({{
                    "task": task_id,
                    "repo": repo,
                    "status": "empty",
                    "time": task_time,
                    "prompt": {{
                        "problem": problem,
                        "description": description
                    }},
                    "expected_output": expected,
                    "agent_output": None,
                    "error": "Empty response"
                }})
        else:
            error_msg = f"HTTP {response.status_code}"
            if response.text:
                try:
                    error_data = response.json()
                    error_msg = error_data.get("error", error_msg)
                except:
                    pass

            print(f"[FAIL] {error_msg}\n")
            results.append({{
                "task": task_id,
                "repo": repo,
                "status": "error",
                "http_code": response.status_code,
                "error": error_msg,
                "prompt": {{
                    "problem": problem,
                    "description": description
                }},
                "expected_output": expected,
                "agent_output": None
            }})

    except requests.exceptions.Timeout:
        print(f"[TIMEOUT]\n")
        results.append({{
            "task": task_id,
            "repo": repo,
            "status": "timeout",
            "prompt": {{"problem": problem, "description": description}},
            "expected_output": expected,
            "agent_output": None,
            "error": "Request timeout"
        }})
    except requests.exceptions.ConnectionError as e:
        print(f"[CONNECTION ERROR]\n")
        results.append({{
            "task": task_id,
            "repo": repo,
            "status": "connection_error",
            "prompt": {{"problem": problem, "description": description}},
            "expected_output": expected,
            "agent_output": None,
            "error": str(e)[:200]
        }})
    except Exception as e:
        print(f"[ERROR] {str(e)[:50]}\n")
        results.append({{
            "task": task_id,
            "repo": repo,
            "status": "error",
            "prompt": {{"problem": problem, "description": description}},
            "expected_output": expected,
            "agent_output": None,
            "error": str(e)[:200]
        }})

total_time = time.time() - start_time

# Summary
sep = "="*80
print(f"\n{sep}")
print("SUMMARY")
print(f"{sep}\n")

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
import os
os.makedirs(output_dir, exist_ok=True)

timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
results_file = os.path.join(output_dir, f"swe_bench_detailed_{timestamp}.json")

detailed_results = {{
    "timestamp": timestamp,
    "configuration": {{
        "server": server,
        "model": model,
        "num_tasks": total
    }},
    "summary": {{
        "success_rate": success_rate,
        "total_tasks": total,
        "successful_tasks": success,
        "total_time": total_time,
        "avg_time_per_task": total_time / total if total > 0 else 0
    }},
    "results": results
}}

with open(results_file, 'w') as f:
    json.dump(detailed_results, f, indent=2, ensure_ascii=False)

print(f"[OK] Detailed results saved to: {results_file}")

# Also save a formatted text report
text_file = os.path.join(output_dir, f"swe_bench_detailed_{timestamp}.txt")
with open(text_file, 'w') as f:
    sep = "="*80
    f.write(f"SWE-BENCH TEST RESULTS\n")
    f.write(f"{sep}\n")
    f.write(f"Timestamp: {timestamp}\n")
    f.write(f"Server: {server}\n")
    f.write(f"Model: {model}\n")
    f.write(f"Total Time: {total_time:.2f}s\n\n")

    f.write(f"SUMMARY\n")
    f.write(f"{sep}\n")
    f.write(f"Success Rate: {success_rate:.1f}%\n")
    f.write(f"Tasks: {success}/{total}\n\n")

    for i, result in enumerate(results, 1):
        sep = "="*80
        f.write(f"\n{sep}\n")
        f.write(f"[{i}] {result['task']} - {result.get('repo', 'N/A')}\n")
        f.write(f"{sep}\n")
        f.write(f"Status: {result['status']}\n")
        time_val = result.get('time', 'N/A')
        if isinstance(time_val, (int, float)):
            f.write(f"Time: {time_val:.2f}s\n\n")
        else:
            f.write(f"Time: {time_val}\n\n")

        f.write(f"PROBLEM:\n")
        prompt_data = result.get('prompt', {{}})
        f.write(f"{prompt_data.get('problem', 'N/A')}\n\n")

        f.write(f"EXPECTED OUTPUT:\n")
        f.write(f"{result.get('expected_output', 'N/A')}\n\n")

        if result.get('agent_output'):
            f.write(f"AGENT OUTPUT:\n")
            f.write(f"{result['agent_output']}\n\n")
        else:
            error = result.get('error', 'No output')
            f.write(f"AGENT OUTPUT: [ERROR] {error}\n\n")

print(f"[OK] Text report saved to: {text_file}")
"@

$pythonScript | Out-File -FilePath "test_detailed.py" -Encoding UTF8

Write-Host "[*] Running detailed test..." -ForegroundColor Yellow
Write-Host ""

python test_detailed.py 2>&1 | ForEach-Object {
    Write-Host $_
}

Remove-Item "test_detailed.py" -ErrorAction SilentlyContinue

Write-Host ""
Write-Host ("="*80) -ForegroundColor Magenta
Write-Host "TEST COMPLETE" -ForegroundColor Magenta
Write-Host ("="*80) -ForegroundColor Magenta
Write-Host ""

# Show results file location
$latestResult = Get-ChildItem -Path "swe_bench_results" -Filter "swe_bench_detailed_*.json" -ErrorAction SilentlyContinue | Sort-Object LastWriteTime -Descending | Select-Object -First 1

if ($latestResult) {
    Write-Host "Results saved to:" -ForegroundColor Green
    Write-Host "  JSON:  $($latestResult.FullName)" -ForegroundColor White
    Write-Host "  Text:  $($latestResult.FullName -replace '.json', '.txt')" -ForegroundColor White
}

Write-Host ""
