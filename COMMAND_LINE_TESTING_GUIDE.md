# SWE-bench Command Line Testing Guide

## Quick Start

### Windows Command Prompt or PowerShell

```batch
REM Quick test (10 tasks)
test-swe-bench.bat

REM Full evaluation (300+ tasks)
test-swe-bench.bat all

REM Custom number of tasks
test-swe-bench.bat 50

REM Custom server and model
test-swe-bench.bat 10 http://localhost:8000 gpt-4
```

---

## Files Provided

### 1. **test-swe-bench.bat** (Windows Batch)
**Easy-to-use batch wrapper for command line**

- Simple syntax
- Automatic PowerShell execution
- Built-in help
- Works in Command Prompt or PowerShell

### 2. **test-swe-bench.ps1** (PowerShell)
**Full-featured PowerShell script**

- Advanced parameters
- Detailed logging
- Progress tracking
- Report generation
- Color-coded output

---

## Command Line Usage

### Batch File (Recommended for Windows)

#### Syntax
```batch
test-swe-bench.bat [tasks] [server] [model]
```

#### Parameters

| Parameter | Default | Example |
|-----------|---------|---------|
| **tasks** | 10 | 50, all |
| **server** | http://lazythought.cse.chalmers.se:80 | http://localhost:8000 |
| **model** | gpt-oss:20b | gpt-4, claude-opus |

#### Examples

**Quick Test (Default)**
```batch
test-swe-bench.bat
```
- Uses default server: http://lazythought.cse.chalmers.se:80
- Uses default model: gpt-oss:20b
- Evaluates 10 tasks
- Estimated time: 5-10 minutes

**Full Evaluation**
```batch
test-swe-bench.bat all
```
- Evaluates all 300+ tasks
- Estimated time: 1-4 hours
- Comprehensive results

**Custom Task Count**
```batch
test-swe-bench.bat 50
```
- Evaluates 50 tasks
- Uses default server and model
- Estimated time: 20-30 minutes

**Custom Server**
```batch
test-swe-bench.bat 20 http://localhost:8000
```
- Evaluates 20 tasks
- Uses custom server: http://localhost:8000
- Uses default model: gpt-oss:20b

**Custom Model**
```batch
test-swe-bench.bat 30 http://lazythought.cse.chalmers.se:80 gpt-4
```
- Evaluates 30 tasks
- Uses specified server
- Uses GPT-4 model

**Help**
```batch
test-swe-bench.bat help
test-swe-bench.bat /?
```
- Shows usage guide

---

### PowerShell Script (Advanced)

#### Syntax
```powershell
.\test-swe-bench.ps1 -Tasks <value> -Server <url> -Model <name> [options]
```

#### Parameters

```powershell
-Tasks         # Number of tasks or "All". Default: 10
-Server        # Server URL. Default: http://lazythought.cse.chalmers.se:80
-Model         # Model name. Default: gpt-oss:20b
-OutputDir     # Output directory. Default: ./swe_bench_results
-SkipDownload  # Skip dataset download
-ShowLogs      # Show detailed logs
-ParallelWorkers # Number of parallel workers (experimental)
```

#### Examples

**Default (PowerShell)**
```powershell
.\test-swe-bench.ps1
```

**Full Evaluation (PowerShell)**
```powershell
.\test-swe-bench.ps1 -Tasks All
```

**Custom Configuration (PowerShell)**
```powershell
.\test-swe-bench.ps1 -Tasks 50 -Server "http://localhost:8000" -Model "gpt-4" -ShowLogs
```

**Skip Download (PowerShell)**
```powershell
.\test-swe-bench.ps1 -Tasks 20 -SkipDownload
```

---

## Output

### Console Output

```
================================================================================
SWE-BENCH VERIFIED TESTING - AGENTICAI
================================================================================

[INFO] Checking environment...
[OK] Python found: Python 3.9.0
[INFO] Creating test configuration...
[OK] Configuration created

STEP 1: DOWNLOADING DATASET
[INFO] Downloading SWE-bench Verified dataset...
[OK] Dataset ready

STEP 2: PREPARING EVALUATION
[INFO] Creating custom test runner...
[OK] Test runner created

STEP 3: RUNNING EVALUATION
[INFO] Starting evaluation on server: http://lazythought.cse.chalmers.se:80
[INFO] Model: gpt-oss:20b
[INFO] Tasks: 10

================================================================================
SWE-BENCH VERIFIED EVALUATION
================================================================================

Configuration:
  Server:  http://lazythought.cse.chalmers.se:80
  Model:   gpt-oss:20b
  Tasks:   10

Starting evaluation on 10 tasks...

[  1/10] Evaluating django-1... [OK] (1.23s)
[  2/10] Evaluating requests-1... [PARTIAL] (0.92s)
[  3/10] Evaluating numpy-1... [FAIL] timeout (30.00s)
...

================================================================================
EVALUATION COMPLETE
================================================================================

Success Rate:          40.0%
Completion Rate:       80.0%
Completed:             8/10
Avg Response Time:     2.34s
Min Response Time:     0.45s
Max Response Time:     30.00s
Avg Memory:            1.23MB
Total Evaluation Time: 23.40s

[OK] JSON report: ./swe_bench_results/swe_bench_results_20260629_105743.json
[OK] Text report: ./swe_bench_results/swe_bench_results_20260629_105743.txt
```

### Generated Reports

#### Text Report (Human-Readable)
```
./swe_bench_results/swe_bench_results_YYYYMMDD_HHMMSS.txt
```

Shows:
- Summary statistics
- Performance metrics
- Error breakdown
- Detailed per-task results

#### JSON Report (Machine-Readable)
```
./swe_bench_results/swe_bench_results_YYYYMMDD_HHMMSS.json
```

Contains:
- Summary data
- Detailed results
- Error information
- Performance metrics

#### Summary JSON
```
./swe_bench_results/summary_YYYYMMDD_HHMMSS.json
```

Contains:
- Key metrics
- Success rate
- Completion rate
- Average times

---

## Common Scenarios

### Scenario 1: Quick Baseline
**Get a quick performance baseline**

```batch
test-swe-bench.bat 10
```

- Time: 5-10 minutes
- Output: Quick metrics for comparison
- Use: Initial performance measurement

### Scenario 2: Model Comparison
**Compare different models**

```batch
REM Test model 1
test-swe-bench.bat 20 http://lazythought.cse.chalmers.se:80 gpt-oss:20b

REM Test model 2
test-swe-bench.bat 20 http://localhost:8000 gpt-4

REM Compare results
fc swe_bench_results\*.json
```

### Scenario 3: Server Testing
**Test different server configurations**

```batch
REM Test primary server
test-swe-bench.bat 30 http://lazythought.cse.chalmers.se:80 gpt-oss:20b

REM Test backup server
test-swe-bench.bat 30 http://backup-server:8000 gpt-oss:20b
```

### Scenario 4: Full Evaluation
**Complete benchmark on all tasks**

```batch
test-swe-bench.bat all
```

- Time: 1-4 hours
- Output: Comprehensive results
- Use: Final performance assessment

### Scenario 5: Monitor Improvements
**Track improvements over time**

```batch
REM Run at different times
test-swe-bench.bat 50

REM Results are timestamped automatically
REM Compare historical results:
REM - swe_bench_results/summary_20260629_100000.json
REM - swe_bench_results/summary_20260629_110000.json
```

---

## Expected Output

### Quick Test (10 tasks)
- Time: 5-10 minutes
- Success rate: 30-60%
- Completion rate: 70-90%

### Medium Test (50 tasks)
- Time: 20-30 minutes
- Success rate: 30-60%
- Completion rate: 70-90%

### Full Evaluation (300+ tasks)
- Time: 1-4 hours
- Success rate: 30-60%
- Completion rate: 70-90%

---

## Troubleshooting

### Issue: "PowerShell is not recognized"
**Solution**: Install PowerShell or run from PowerShell directly:
```powershell
.\test-swe-bench.ps1
```

### Issue: "File cannot be loaded because running scripts is disabled"
**Solution**: Bypass execution policy:
```powershell
powershell -ExecutionPolicy Bypass -File test-swe-bench.ps1
```

### Issue: "Python not found"
**Solution**: Ensure Python is installed and in PATH:
```batch
python --version
```

### Issue: "Dataset not found"
**Solution**: Run without `-SkipDownload` flag:
```batch
test-swe-bench.bat 10
```

### Issue: "Timeout errors"
**Solution**: 
- Use fewer tasks for quick test
- Check server connectivity
- Increase timeout in Python config

### Issue: "Connection refused"
**Solution**:
- Verify server is running: `http://lazythought.cse.chalmers.se:80`
- Check firewall settings
- Try different server address

---

## Advanced Usage

### Logging

**Enable detailed logging:**
```powershell
.\test-swe-bench.ps1 -ShowLogs
```

### Custom Output Directory

**Save results elsewhere:**
```powershell
.\test-swe-bench.ps1 -Tasks 30 -OutputDir "C:\Results\SWE-Bench"
```

### Skip Dataset Download

**Use existing dataset:**
```powershell
.\test-swe-bench.ps1 -Tasks 50 -SkipDownload
```

### Experimental Parallel Execution

**Run with multiple workers (experimental):**
```powershell
.\test-swe-bench.ps1 -Tasks 50 -ParallelWorkers 4
```

---

## Performance Expectations

### By Model Strength

**Weak (GPT-3.5-like)**
- Success Rate: 25-35%
- Avg Time: 2-5s per task

**Medium (GPT-4-like)**
- Success Rate: 40-50%
- Avg Time: 1-3s per task

**Strong (GPT-4 Turbo+)**
- Success Rate: 50-60%+
- Avg Time: <2s per task

---

## Integration Examples

### GitHub Actions
```yaml
- name: Test AgenticAI on SWE-bench
  run: |
    test-swe-bench.bat 20
```

### Jenkins
```groovy
stage('SWE-bench Test') {
    steps {
        bat 'test-swe-bench.bat all'
    }
}
```

### Manual CI/CD
```bash
#!/bin/bash
cd agenticai
test-swe-bench.bat 50 || exit 1
```

---

## Summary

You can now easily test AgenticAI on SWE-bench from command line:

**Quick Test:**
```batch
test-swe-bench.bat
```

**Full Test:**
```batch
test-swe-bench.bat all
```

**Custom:**
```batch
test-swe-bench.bat 50 http://your-server:port your-model
```

All results are automatically saved to `swe_bench_results/` with detailed reports!
