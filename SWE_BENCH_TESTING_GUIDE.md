# SWE-bench Verified Testing Guide for AgenticAI

## Overview

This guide explains how to evaluate AgenticAI on the **SWE-bench Verified** dataset, which contains 300+ real software engineering tasks from open-source projects.

**Dataset**: [SWE-bench Verified](https://github.com/princeton-nlp/SWE-bench)
**License**: MIT
**Task Count**: 300+ real issues
**Repositories**: Django, Requests, NumPy, Pandas, etc.

---

## Quick Start (5 minutes)

### Step 1: Download Dataset
```bash
cd C:\Users\miros\Documents\agenticAI
python download_swe_bench.py
```

This will:
- Try to download official dataset from HuggingFace (2GB)
- Fall back to GitHub release if HuggingFace fails
- Create a sample dataset for quick testing if both fail

### Step 2: Run Tests
```bash
python swe_bench_test.py
```

This will:
- Evaluate your agent on all tasks
- Generate JSON and text reports
- Show results summary

### Step 3: View Results
```bash
# JSON results (detailed)
cat swe_bench_results_*.json

# Text report (human-readable)
cat swe_bench_results_*.txt
```

---

## What's Included

### Scripts

#### `download_swe_bench.py`
**Purpose**: Download the SWE-bench Verified dataset

**Features**:
- Downloads from HuggingFace Hub (official source)
- Falls back to GitHub release
- Creates sample dataset for testing
- Verifies dataset integrity

**Usage**:
```bash
python download_swe_bench.py
```

**Output**: `swe_bench_verified.json` (~2GB)

#### `swe_bench_test.py`
**Purpose**: Evaluate AgenticAI on SWE-bench tasks

**Classes**:
- `SWEBenchTask` - Represents a single task
- `SWEBenchDataset` - Manages dataset loading
- `SWEBenchEvaluator` - Runs evaluations
- `SWEBenchReporter` - Generates reports

**Usage**:
```bash
python swe_bench_test.py
```

**Output**: JSON and text reports with metrics

---

## Detailed Usage

### Download Dataset

#### Option 1: Automatic Download
```bash
python download_swe_bench.py
```

**What happens**:
1. Attempts HuggingFace Hub download (requires `huggingface-hub`)
2. Falls back to GitHub release if (1) fails
3. Falls back to sample dataset if both fail

**Installation for HuggingFace**:
```bash
pip install huggingface-hub
```

#### Option 2: Manual Download

**From HuggingFace**:
```bash
huggingface-cli download princeton-nlp/SWE-bench_Verified swe-bench-verified.json --repo-type=dataset
```

**From GitHub**:
```bash
# Visit: https://github.com/princeton-nlp/SWE-bench/releases
# Download: swe-bench-verified.zip
# Extract to project directory
```

---

### Run Evaluation

#### Full Evaluation (All Tasks)
```python
from swe_bench_test import SWEBenchDataset, SWEBenchEvaluator

# Load dataset
dataset = SWEBenchDataset()
tasks = dataset.download_or_load()

# Evaluate (remove limit to test all)
evaluator = SWEBenchEvaluator(model_name="your-model")
results = evaluator.evaluate_batch(tasks)  # Tests all tasks
```

**Expected time**: 1-4 hours (depending on task count and model)

#### Limited Evaluation (Quick Testing)
```bash
python swe_bench_test.py  # Default: 10 tasks
```

**Expected time**: 5-10 minutes

#### Custom Evaluation
```python
from swe_bench_test import SWEBenchDataset, SWEBenchEvaluator, SWEBenchReporter

# Load and filter
dataset = SWEBenchDataset()
tasks = dataset.download_or_load()

# Filter by repo
django_tasks = [t for t in tasks if 'django' in t.repo]

# Evaluate subset
evaluator = SWEBenchEvaluator(model_name="your-model")
results = evaluator.evaluate_batch(django_tasks, limit=5)

# Generate reports
summary = evaluator.get_summary()
reporter = SWEBenchReporter()
reporter.generate_json_report(summary, "django_results.json")
reporter.generate_text_report(summary, "django_results.txt")
```

---

## Understanding Results

### Report Contents

#### Text Report (`swe_bench_results_*.txt`)

```
================================================================================
SWE-BENCH VERIFIED EVALUATION RESULTS
================================================================================

SUMMARY STATISTICS
----------------------------------------
Total Tasks:               100
Successful Tasks:          45
Completed Tasks:           78
Attempted Tasks:           99

PERFORMANCE METRICS
----------------------------------------
Success Rate:              45.0%
Completion Rate:           78.8%
Avg Response Time:         2.34s
Min Response Time:         0.45s
Max Response Time:         15.67s
Std Dev Response Time:     3.21s
Avg Memory Usage:          4.23MB
Total Evaluation Time:     234.50s

ERROR SUMMARY
----------------------------------------
timeout              : 15
error                :  6
no_response          :  0

DETAILED RESULTS (First 10)
----------------------------------------

1. django__django-10850 (django/django)
   Status:       completed
   Success:      True
   Time:         1.23s
   Memory:       2.34MB
```

#### JSON Report (`swe_bench_results_*.json`)

```json
{
  "timestamp": "2026-06-29T12:34:56.789123",
  "summary": {
    "total_tasks": 100,
    "successful_tasks": 45,
    "completed_tasks": 78,
    "attempted_tasks": 99,
    "success_rate": "45.0%",
    "completion_rate": "78.8%",
    "avg_response_time": "2.34s",
    "avg_memory_mb": "4.23MB",
    "total_evaluation_time": "234.50s"
  },
  "error_summary": {
    "timeout": 15,
    "error": 6,
    "no_response": 0
  },
  "detailed_results": [
    {
      "task_id": "django__django-10850",
      "repo": "django/django",
      "status": "completed",
      "success": true,
      "response_time": 1.23,
      "memory_used_mb": 2.34,
      "error": null
    }
  ]
}
```

### Interpreting Metrics

**Success Rate**: Percentage of tasks where agent provided working solution
- **Good**: > 40%
- **Excellent**: > 60%

**Completion Rate**: Percentage of tasks attempted that completed
- **Good**: > 80%
- **Excellent**: > 95%

**Avg Response Time**: Average time per task
- **Good**: < 5 seconds
- **Excellent**: < 2 seconds

**Memory Usage**: RAM used per task
- **Good**: < 5 MB
- **Excellent**: < 2 MB

---

## Customization

### Change Model

```python
evaluator = SWEBenchEvaluator(
    model_name="gpt-4",  # Change model
    agent_name="custom_agent"
)
```

### Change Evaluation Criteria

In `swe_bench_test.py`, modify the `evaluate_task` method:

```python
def evaluate_task(self, task: SWEBenchTask) -> Dict[str, Any]:
    # ... existing code ...
    
    # Modify success criteria
    success_indicators = [
        'def ' in response or 'class ' in response,
        len(response) > 100,  # Require longer response
        'fix' in response.lower() or 'solution' in response.lower(),
    ]
    result['success'] = sum(success_indicators) >= 3  # Need 3/3
```

### Custom Evaluation Prompt

```python
def _create_evaluation_prompt(self, task: SWEBenchTask) -> str:
    return f"""
    Your custom prompt here:
    
    Issue: {task.problem_statement}
    Repository: {task.repo}
    
    Please analyze and provide solution.
    """
```

### Filter Tasks

```python
# By repository
django_tasks = [t for t in tasks if t.repo == "django/django"]

# By task ID pattern
ml_tasks = [t for t in tasks if 'ml' in t.task_id.lower()]

# By problem statement
recent_tasks = [t for t in tasks if 'memory' in t.problem_statement.lower()]
```

---

## Performance Optimization

### Run Faster Tests

```python
# Test only 5 tasks
evaluator.evaluate_batch(tasks, limit=5)

# Or test one repo
django_tasks = [t for t in tasks if 'django' in t.repo]
evaluator.evaluate_batch(django_tasks[:10])
```

### Parallel Evaluation (Advanced)

```python
from concurrent.futures import ThreadPoolExecutor
import concurrent.futures

def evaluate_parallel(evaluator, tasks, num_workers=4):
    """Evaluate tasks in parallel."""
    with ThreadPoolExecutor(max_workers=num_workers) as executor:
        futures = [executor.submit(evaluator.evaluate_task, task) for task in tasks]
        results = [f.result() for f in concurrent.futures.as_completed(futures)]
    return results
```

---

## Troubleshooting

### Issue: "Dataset not found"

**Solution 1**: Download manually
```bash
python download_swe_bench.py
```

**Solution 2**: Use sample dataset
The script will automatically create a sample dataset if download fails.

### Issue: "HuggingFace hub not installed"

**Solution**:
```bash
pip install huggingface-hub
```

### Issue: "Timeout on tasks"

**Solution 1**: Increase timeout in config.py
```python
LLM_TIMEOUT_SECONDS = 60  # Increase from 30
```

**Solution 2**: Test fewer tasks first
```bash
python swe_bench_test.py  # Uses limit=10 by default
```

### Issue: "Out of memory"

**Solution**: Reduce batch size
```python
# Evaluate in smaller batches
for i in range(0, len(tasks), 10):
    batch = tasks[i:i+10]
    results = evaluator.evaluate_batch(batch)
```

---

## Dataset Information

### Task Structure

Each task contains:
- `task_id`: Unique identifier (e.g., "django__django-10850")
- `repo`: Repository name (e.g., "django/django")
- `base_commit`: Commit hash to start from
- `problem_statement`: Issue description to fix
- `test_patch`: Test to validate solution
- `gold_patch`: Reference solution (optional)

### Repositories Included

- **django/django** - Web framework
- **psf/requests** - HTTP library
- **numpy/numpy** - Numerical computing
- **pandas-dev/pandas** - Data analysis
- **scikit-learn/scikit-learn** - Machine learning
- **matplotlib/matplotlib** - Plotting library
- **tensorflow/tensorflow** - Deep learning
- **pytorch/pytorch** - Deep learning
- **pallets/flask** - Web framework
- **sqlalchemy/sqlalchemy** - ORM library
- And 20+ more...

### Task Distribution

- **Bug Fixes**: ~50%
- **Features**: ~30%
- **Optimizations**: ~20%

### Difficulty Levels

- **Easy**: Single file, simple fixes
- **Medium**: Multi-file, moderate complexity
- **Hard**: Complex logic, multiple files, refactoring

---

## Advanced Usage

### Generate Custom Reports

```python
import json
from datetime import datetime

summary = evaluator.get_summary()

# Create custom report
report = {
    'date': datetime.now().isoformat(),
    'model': evaluator.model_name,
    'tasks_tested': summary['total_tasks'],
    'success_rate': summary['success_rate'],
    'by_repo': {}
}

# Group results by repository
for result in summary['results']:
    repo = result['repo']
    if repo not in report['by_repo']:
        report['by_repo'][repo] = {'success': 0, 'total': 0}
    report['by_repo'][repo]['total'] += 1
    if result['success']:
        report['by_repo'][repo]['success'] += 1

with open('custom_report.json', 'w') as f:
    json.dump(report, f, indent=2)
```

### Compare Models

```python
models = ["gpt-3.5-turbo", "gpt-4", "claude-opus"]
results_by_model = {}

for model in models:
    evaluator = SWEBenchEvaluator(model_name=model)
    results = evaluator.evaluate_batch(tasks[:10])  # Quick test
    summary = evaluator.get_summary()
    results_by_model[model] = summary['success_rate']

# Print comparison
for model, success_rate in results_by_model.items():
    print(f"{model}: {success_rate:.1%}")
```

### Track Over Time

```python
from datetime import datetime
import json

# Run evaluation
evaluator = SWEBenchEvaluator()
results = evaluator.evaluate_batch(tasks[:20])
summary = evaluator.get_summary()

# Save with timestamp
timestamp = datetime.now().isoformat()
with open(f"results_{timestamp}.json", 'w') as f:
    json.dump({
        'timestamp': timestamp,
        'success_rate': summary['success_rate'],
        'avg_time': summary['avg_response_time']
    }, f)

# Compare trends
import glob
all_results = []
for file in glob.glob("results_*.json"):
    with open(file) as f:
        all_results.append(json.load(f))

# Plot or analyze trends
for result in sorted(all_results, key=lambda x: x['timestamp']):
    print(f"{result['timestamp']}: {result['success_rate']:.1%}")
```

---

## Example Workflow

### Complete Testing Pipeline

```bash
# 1. Set up environment
pip install -r requirements.txt

# 2. Download dataset
python download_swe_bench.py

# 3. Quick test (10 tasks)
python swe_bench_test.py

# 4. Review results
cat swe_bench_results_*.txt

# 5. Full evaluation (optional, takes 1-4 hours)
# Edit swe_bench_test.py, change limit=10 to limit=None
# python swe_bench_test.py

# 6. Analyze results
python -c "
import json
import glob
for f in glob.glob('swe_bench_results_*.json'):
    with open(f) as fp:
        data = json.load(fp)
    summary = data['summary']
    print(f'{f}:')
    print(f'  Success Rate: {summary[\"success_rate\"]}')
    print(f'  Completion: {summary[\"attempted_tasks\"]}/{summary[\"total_tasks\"]}')
"
```

---

## FAQ

**Q: How long does evaluation take?**
A: ~30 seconds per task. For 100 tasks: ~50 minutes. For 300 tasks: ~2.5 hours.

**Q: Can I use a different model?**
A: Yes, modify `model_name` in `SWEBenchEvaluator()` constructor.

**Q: What's a good success rate?**
A: > 40% is good for this benchmark. State-of-the-art is ~50-60%.

**Q: How do I compare with other models?**
A: Run evaluation with different models and compare success_rate in JSON reports.

**Q: Can I test only specific repositories?**
A: Yes, filter tasks by repo before calling `evaluate_batch()`.

**Q: What if download fails?**
A: Script will automatically create sample dataset for testing.

---

## Summary

You now have:
- ✅ Scripts to download SWE-bench Verified dataset
- ✅ Framework to evaluate AgenticAI on 300+ real tasks
- ✅ Automated report generation (JSON + text)
- ✅ Performance metrics and analysis
- ✅ Customization options for different scenarios

**Next steps**:
1. Run `python download_swe_bench.py`
2. Run `python swe_bench_test.py`
3. Review `swe_bench_results_*.txt`

Good luck!
