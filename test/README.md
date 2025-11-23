# Test Suite for AgenticAI

This directory contains comprehensive tests for all agent classes in the AgenticAI project.

## Test Coverage

The test suite includes tests for:

1. **AgentAI** (`test_agent.py`) - Base agent class
   - Initialization with various parameters
   - API response handling with retries and timeouts
   - Message management
   - CSV and Excel export functionality
   - Markdown to HTML conversion

2. **AgentAIC** (`test_agentC.py`) - C code generation agent
   - C code generation with compilation
   - Code extraction from markdown
   - Integration with AgentCompiler

3. **AgentCompiler** (`test_agentCompiler.py`) - Compilation agent
   - Code compilation using gcc
   - Compilation error detection
   - Automatic error fixing with retries
   - Code extraction from markdown

4. **AgentStaticAnalyzer** (`test_agentStaticAnalyzer.py`) - Static analysis agent
   - Static code analysis using cppcheck
   - Issue detection and reporting
   - Log management and Excel export

5. **AgentH** (`test_agentH.py`) - Human-in-the-loop agent
   - Human input handling
   - Message persistence

6. **vllmAgentAI** (`test_agentvllm.py`) - vLLM-based agent
   - vLLM integration (skipped if vllm not installed)
   - Response generation
   - Message export

7. **AgentReqs** (`test_agentReqs.py`) - Requirements retrieval agent
   - Similarity-based requirement matching
   - Excel database integration
   - Error handling for missing files

8. **Agent3GPP** (`test_agent3GPP.py`) - 3GPP document parsing agent
   - PDF document parsing
   - Section extraction by headings
   - Similarity-based section retrieval

## Running the Tests

### Prerequisites

Install required dependencies:

```bash
pip install pandas requests tqdm openpyxl PyPDF2
```

Note: The `vllm` library is optional. Tests for `vllmAgentAI` will be skipped if it's not installed.

### Run All Tests

```bash
# From the repository root
python -m unittest discover -s test -p "test_*.py" -v
```

### Run Specific Test File

```bash
python -m unittest test.test_agent -v
python -m unittest test.test_agentC -v
python -m unittest test.test_agentCompiler -v
# ... etc
```

### Run Specific Test Case

```bash
python -m unittest test.test_agent.TestAgentAI.test_initialization -v
```

## Test Design

All tests are designed to:

- **Not modify agent code**: Tests use mocking extensively to avoid needing live API servers
- **Be independent**: Each test can run in isolation
- **Clean up**: Temporary files are properly cleaned up after tests
- **Be comprehensive**: Cover happy paths, error cases, edge cases, and retries
- **Use standard libraries**: Built with Python's `unittest` framework

## Mocking Strategy

Tests extensively use mocking to:
- Avoid requiring live LLM API servers
- Simulate network timeouts and errors
- Mock file I/O operations
- Mock subprocess calls (gcc, cppcheck)
- Test retry logic without waiting

## Notes

- Tests create temporary directories (`./temp`) for compilation artifacts
- Some tests create temporary files (`.xlsx`, `.csv`, `.html`) which are cleaned up
- Tests for AgentStaticAnalyzer and AgentCompiler require the `./temp` directory
- The vLLM tests are skipped if the `vllm` library is not installed (it's a large dependency)
