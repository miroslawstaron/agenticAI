<#
.SYNOPSIS
    Simple SWE-bench test that works directly with Ollama
#>

param(
    [string]$Server = "http://lazythought.cse.chalmers.se",
    [string]$Model = "gpt-oss:20b",
    [int]$Tasks = 3
)

Write-Host "`n" + ("="*80) -ForegroundColor Magenta
Write-Host "SWE-BENCH OLLAMA TEST (SIMPLIFIED)" -ForegroundColor Magenta
Write-Host ("="*80) -ForegroundColor Magenta + "`n"

Write-Host "Server: $Server" -ForegroundColor Cyan
Write-Host "Model: $Model" -ForegroundColor Cyan
Write-Host "Tasks: $Tasks" -ForegroundColor Cyan
Write-Host ""

# Create Python test script
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

# Sample SWE-bench tasks
tasks = [
    {
        "id": "django-1",
        "repo": "django/django",
        "problem": "Fix issue where ModelForm does not preserve field order from Meta.fields."
    },
    {
        "id": "requests-1",
        "repo": "psf/requests",
        "problem": "Add support for custom timeout per request in Session."
    },
    {
        "id": "numpy-1",
        "repo": "numpy/numpy",
        "problem": "Optimize array concatenation for small arrays."
    },
][:num_tasks]

print(f"Testing with {len(tasks)} tasks\n")

results = []
start_time = time.time()

for i, task in enumerate(tasks, 1):
    task_id = task["id"]
    problem = task["problem"]

    print(f"[{i}/{len(tasks)}] {task_id}...", end=' ', flush=True)

    try:
        # Call Ollama API
        payload = {
            "model": model,
            "messages": [
                {"role": "system", "content": "You are a helpful software engineer."},
                {"role": "user", "content": f"Issue: {problem}\n\nAnalyze and propose a solution."}
            ],
            "stream": False
        }

        task_start = time.time()
        response = requests.post(
            f"{server}/api/chat",
            json=payload,
            timeout=30,
            headers={"Content-Type": "application/json"}
        )
        task_time = time.time() - task_start

        if response.status_code == 200:
            data = response.json()
            content = data.get("message", {}).get("content", "")

            if content and len(content) > 10:
                print(f"[OK] ({task_time:.2f}s)")
                results.append({
                    "task": task_id,
                    "status": "success",
                    "time": task_time,
                    "length": len(content)
                })
            else:
                print(f"[FAIL] Empty response")
                results.append({
                    "task": task_id,
                    "status": "empty",
                    "time": task_time
                })
        else:
            print(f"[FAIL] Status {response.status_code}")
            results.append({
                "task": task_id,
                "status": "error",
                "code": response.status_code
            })

    except requests.exceptions.Timeout:
        print("[TIMEOUT]")
        results.append({
            "task": task_id,
            "status": "timeout"
        })
    except requests.exceptions.ConnectionError as e:
        print(f"[CONNECTION ERROR]")
        results.append({
            "task": task_id,
            "status": "connection_error",
            "error": str(e)
        })
    except Exception as e:
        print(f"[ERROR] {str(e)[:50]}")
        results.append({
            "task": task_id,
            "status": "error",
            "error": str(e)[:100]
        })

total_time = time.time() - start_time

# Summary
print(f"\n{'='*80}")
print("RESULTS")
print(f"{'='*80}\n")

success = sum(1 for r in results if r["status"] == "success")
total = len(results)
success_rate = (success / total * 100) if total > 0 else 0

print(f"Successful:      {success}/{total}")
print(f"Success Rate:    {success_rate:.1f}%")
print(f"Total Time:      {total_time:.2f}s")
print(f"Avg Time/Task:   {total_time/total:.2f}s" if total > 0 else "")
print("")

# Details
if results:
    print("Task Results:")
    for r in results:
        status = r["status"]
        task = r["task"]
        time_str = f", {r.get('time', 0):.2f}s" if "time" in r else ""
        print(f"  {task}: {status}{time_str}")

print("")

# Save results
output_dir = "swe_bench_results"
import os
os.makedirs(output_dir, exist_ok=True)

timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
results_file = os.path.join(output_dir, f"swe_bench_results_{timestamp}.json")

with open(results_file, 'w') as f:
    json.dump({
        "timestamp": timestamp,
        "server": server,
        "model": model,
        "success_rate": success_rate,
        "total_tasks": total,
        "successful_tasks": success,
        "total_time": total_time,
        "results": results
    }, f, indent=2)

print(f"[OK] Results saved to: {results_file}")
"@

$pythonScript | Out-File -FilePath "test_simple.py" -Encoding UTF8

Write-Host "[*] Running test..." -ForegroundColor Yellow
Write-Host ""

python test_simple.py 2>&1 | ForEach-Object {
    if ($_ -match "^\[OK\]") {
        Write-Host $_ -ForegroundColor Green
    } elseif ($_ -match "^\[FAIL\]|ERROR|TIMEOUT|CONNECTION") {
        Write-Host $_ -ForegroundColor Red
    } elseif ($_ -match "^\[") {
        Write-Host $_ -ForegroundColor Cyan
    } else {
        Write-Host $_
    }
}

Remove-Item "test_simple.py" -ErrorAction SilentlyContinue

Write-Host ""
Write-Host ("="*80) -ForegroundColor Magenta
Write-Host "TEST COMPLETE" -ForegroundColor Magenta
Write-Host ("="*80) -ForegroundColor Magenta
Write-Host ""

# Show results
$latestResult = Get-ChildItem -Path "swe_bench_results" -Filter "swe_bench_results_*.json" -ErrorAction SilentlyContinue | Sort-Object LastWriteTime -Descending | Select-Object -First 1

if ($latestResult) {
    Write-Host "Results saved to: $($latestResult.FullName)" -ForegroundColor Green
    $content = Get-Content $latestResult.FullName | ConvertFrom-Json
    Write-Host ""
    Write-Host "Summary:" -ForegroundColor Yellow
    Write-Host "  Success Rate: $($content.success_rate)%" -ForegroundColor White
    Write-Host "  Tasks: $($content.successful_tasks)/$($content.total_tasks)" -ForegroundColor White
    Write-Host "  Time: $($content.total_time)s" -ForegroundColor White
}

Write-Host ""
