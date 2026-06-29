@echo off
REM SWE-bench Testing Batch Wrapper
REM Runs the PowerShell testing script with proper parameters
REM Usage: test-swe-bench.bat [tasks] [server] [model]

setlocal enabledelayedexpansion

REM Default parameters
set TASKS=10
set SERVER=http://lazythought.cse.chalmers.se:80
set MODEL=gpt-oss:20b
set OUTPUT_DIR=./swe_bench_results

REM Parse command line arguments
if "%1"=="" goto :run_default
if /i "%1"=="all" (
    set TASKS=All
    goto :check_arg2
)
if "%1"=="help" goto :show_help
if "%1"=="/?" goto :show_help

REM Check if first arg is a number
for /f "delims=0123456789" %%A in ("%1") do set "is_num=%%A"
if defined is_num (
    echo Error: Invalid tasks parameter. Use 'all' or a number.
    goto :show_help
) else (
    set TASKS=%1
)

:check_arg2
if not "%2"=="" set SERVER=%2

:check_arg3
if not "%3"=="" set MODEL=%3

:run_default
cls
echo.
echo ================================================================================
echo SWE-BENCH VERIFIED TESTING - AGENTICAI
echo ================================================================================
echo.
echo Configuration:
echo   Tasks:  %TASKS%
echo   Server: %SERVER%
echo   Model:  %MODEL%
echo.

REM Check if PowerShell is available
powershell -NoProfile -Command "exit" 2>nul
if errorlevel 1 (
    echo Error: PowerShell is not available or not in PATH
    exit /b 1
)

REM Run PowerShell script
echo Starting evaluation...
echo.

powershell -NoProfile -ExecutionPolicy Bypass -File "test-swe-bench.ps1" ^
    -Tasks "%TASKS%" ^
    -Server "%SERVER%" ^
    -Model "%MODEL%" ^
    -OutputDir "%OUTPUT_DIR%"

if errorlevel 1 (
    echo.
    echo Error: Evaluation failed. Check the output above.
    exit /b 1
)

echo.
echo ================================================================================
echo Testing completed! Results saved to: %OUTPUT_DIR%
echo ================================================================================
exit /b 0

:show_help
cls
echo.
echo ================================================================================
echo SWE-BENCH TESTING SCRIPT - USAGE GUIDE
echo ================================================================================
echo.
echo USAGE:
echo   test-swe-bench.bat [tasks] [server] [model]
echo.
echo PARAMETERS:
echo   tasks      Number of tasks to evaluate (default: 10)
echo              Use 'all' for full evaluation (300+ tasks, takes 1-4 hours)
echo.
echo   server     LLM server URL (default: http://lazythought.cse.chalmers.se:80)
echo              Example: http://localhost:8000
echo.
echo   model      Model name (default: gpt-oss:20b)
echo              Example: gpt-4, claude-opus, etc.
echo.
echo EXAMPLES:
echo   Quick test (10 tasks, default server):
echo     test-swe-bench.bat
echo.
echo   Full evaluation (all 300+ tasks):
echo     test-swe-bench.bat all
echo.
echo   Test 50 tasks:
echo     test-swe-bench.bat 50
echo.
echo   Custom server and model:
echo     test-swe-bench.bat 20 http://localhost:8000 gpt-4
echo.
echo   Full evaluation on custom server:
echo     test-swe-bench.bat all http://localhost:8000 my-model
echo.
echo OUTPUT:
echo   Results are saved to: .\swe_bench_results\
echo   - swe_bench_results_*.json (machine-readable)
echo   - swe_bench_results_*.txt  (human-readable)
echo.
echo ================================================================================
exit /b 0
