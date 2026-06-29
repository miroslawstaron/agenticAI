<#
.SYNOPSIS
    SWE-bench detailed test script with comprehensive results
    Tests AgenticAI on real SWE-bench tasks with prompt, expected output, and agent response logging

.DESCRIPTION
    Runs the detailed SWE-bench test suite against a specified Ollama server.
    Captures and logs:
    - The problem statement and full prompt sent to the agent
    - Expected output from SWE-bench
    - Complete agent response with analysis and solutions
    - Performance metrics (time, success rate)

.PARAMETER Tasks
    Number of tasks to evaluate. Default: 3
    Examples: 1, 5, 10, 20

.PARAMETER Model
    Ollama model to use. Default: qwen2.5:14b
    Examples: qwen2.5:14b, laguna-xs.2:latest, minicpm-v:8b

.PARAMETER Server
    Ollama server address. Default: http://lazythought.cse.chalmers.se
    Examples: http://localhost:11434, http://server.com:8000

.PARAMETER OutputDir
    Directory to save results. Default: ./swe_bench_results

.EXAMPLE
    # Quick test with 3 tasks
    .\test-swe-bench.ps1

    # Test 10 tasks
    .\test-swe-bench.ps1 -Tasks 10

    # Custom server and model
    .\test-swe-bench.ps1 -Tasks 5 -Model "laguna-xs.2:latest" -Server "http://localhost:11434"

.NOTES
    Author: Claude Code
    Version: 1.0
#>

param(
    [Parameter(Mandatory=$false)]
    [int]$Tasks = 3,

    [Parameter(Mandatory=$false)]
    [string]$Model = "qwen2.5:14b",

    [Parameter(Mandatory=$false)]
    [string]$Server = "http://lazythought.cse.chalmers.se",

    [Parameter(Mandatory=$false)]
    [string]$OutputDir = "./swe_bench_results"
)

# ============================================================================
# HEADER & CONFIGURATION
# ============================================================================

Write-Host "`n" + ("="*80) -ForegroundColor Magenta
Write-Host "SWE-BENCH DETAILED TEST" -ForegroundColor Magenta
Write-Host ("="*80) -ForegroundColor Magenta + "`n"

Write-Host "Configuration:" -ForegroundColor Cyan
Write-Host "  Tasks:  $Tasks" -ForegroundColor White
Write-Host "  Model:  $Model" -ForegroundColor White
Write-Host "  Server: $Server" -ForegroundColor White
Write-Host "  Output: $OutputDir" -ForegroundColor White
Write-Host ""

# ============================================================================
# VALIDATION
# ============================================================================

# Check Python is available
try {
    $pythonVersion = python --version 2>&1
    Write-Host "[OK] Python found: $pythonVersion" -ForegroundColor Green
} catch {
    Write-Host "[ERROR] Python not found. Please install Python 3.7+" -ForegroundColor Red
    exit 1
}

# Check Python script exists
if (-not (Test-Path "run_swe_bench_detailed.py")) {
    Write-Host "[ERROR] run_swe_bench_detailed.py not found" -ForegroundColor Red
    exit 1
}

Write-Host "[OK] Test script found" -ForegroundColor Green
Write-Host ""

# ============================================================================
# RUN TEST
# ============================================================================

Write-Host "Starting evaluation..." -ForegroundColor Yellow
Write-Host ""

$startTime = Get-Date

try {
    python run_swe_bench_detailed.py $Tasks $Model $Server 2>&1 | ForEach-Object {
        $line = $_

        # Color-code output
        if ($line -match "^\[OK\]") {
            Write-Host $line -ForegroundColor Green
        } elseif ($line -match "^\[ERROR\]|FAIL") {
            Write-Host $line -ForegroundColor Red
        } elseif ($line -match "^=+$") {
            Write-Host $line -ForegroundColor Cyan
        } elseif ($line -match "^\[" -or $line -match "Calling agent|Testing|Successful|Success Rate|Total Time|SUMMARY") {
            Write-Host $line -ForegroundColor Yellow
        } else {
            Write-Host $line
        }
    }

    if ($LASTEXITCODE -ne 0) {
        Write-Host ""
        Write-Host "[ERROR] Test failed with exit code $LASTEXITCODE" -ForegroundColor Red
        exit $LASTEXITCODE
    }

} catch {
    Write-Host "[ERROR] Test execution failed: $_" -ForegroundColor Red
    exit 1
}

# ============================================================================
# SUMMARY
# ============================================================================

$duration = $(Get-Date) - $startTime

Write-Host ""
Write-Host ("="*80) -ForegroundColor Magenta
Write-Host "TEST COMPLETE" -ForegroundColor Magenta
Write-Host ("="*80) -ForegroundColor Magenta
Write-Host ""

Write-Host "Execution time: $($duration.TotalSeconds.ToString('F1'))s" -ForegroundColor Cyan
Write-Host ""

# Find and display latest results
$latestJson = Get-ChildItem -Path $OutputDir -Filter "swe_bench_detailed_*.json" -ErrorAction SilentlyContinue |
    Sort-Object LastWriteTime -Descending |
    Select-Object -First 1

if ($latestJson) {
    Write-Host "Results saved to:" -ForegroundColor Green
    Write-Host "  JSON:  $($latestJson.FullName)" -ForegroundColor White

    $latestTxt = $latestJson.FullName -replace '.json$', '.txt'
    if (Test-Path $latestTxt) {
        Write-Host "  Text:  $latestTxt" -ForegroundColor White
    }

    # Parse and display summary from JSON
    try {
        $results = Get-Content $latestJson.FullName | ConvertFrom-Json
        Write-Host ""
        Write-Host "Summary:" -ForegroundColor Yellow
        Write-Host "  Success Rate: $($results.summary.success_rate)%" -ForegroundColor $(if ($results.summary.success_rate -eq 100) { "Green" } else { "Yellow" })
        Write-Host "  Tasks: $($results.summary.successful_tasks)/$($results.summary.total_tasks)" -ForegroundColor White
        Write-Host "  Time: $($results.summary.total_time.ToString('F2'))s" -ForegroundColor White
        Write-Host "  Avg/Task: $($results.summary.avg_time_per_task.ToString('F2'))s" -ForegroundColor White
    } catch {
        # Silently ignore JSON parse errors
    }
}

Write-Host ""
Write-Host "Next steps:" -ForegroundColor Cyan
Write-Host "  View detailed results: cat $($latestJson.FullName -replace '\\', '/')" -ForegroundColor Gray
Write-Host "  Run more tasks: .\test-swe-bench.ps1 -Tasks 10" -ForegroundColor Gray
Write-Host "  Change model: .\test-swe-bench.ps1 -Model ""laguna-xs.2:latest""" -ForegroundColor Gray
Write-Host ""
