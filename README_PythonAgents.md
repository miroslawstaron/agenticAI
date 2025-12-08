# Python Programming Agents - AgenticAI

This document describes the Python programming agents available in AgenticAI, which enable automatic Python code generation and validation through AI-driven conversations.

## Table of Contents

1. [Overview](#overview)
2. [Available Agents](#available-agents)
3. [AgentAIPy](#agentaipy)
4. [AgentPyInterpreter](#agentpyinterpreter)
5. [Usage Examples](#usage-examples)
6. [Comparison with C Agents](#comparison-with-c-agents)
7. [Best Practices](#best-practices)
8. [Troubleshooting](#troubleshooting)

## Overview

The Python programming agents extend AgenticAI's capabilities to work with Python code, offering similar functionality to the C programming agents (AgentAIC and AgentCompiler) but for Python development.

### Key Features

- **Automatic Code Execution**: Python code is automatically executed using the Python interpreter
- **Error Detection**: Runtime errors are automatically detected
- **Iterative Fixing**: The LLM attempts to fix errors automatically
- **Conversation Logging**: All interactions are saved for analysis

### Architecture

The Python agent system consists of two main components:

1. **AgentAIPy**: High-level agent that generates Python code and orchestrates validation
2. **AgentPyInterpreter**: Low-level agent that executes code and fixes runtime errors

## Available Agents

### AgentAIPy

The main Python programming agent that extends `AgentAI`.

**File:** `agentPy.py`

**Purpose:** Generate Python code through LLM conversations with automatic execution validation.

**Key Features:**
- Inherits all base agent functionality
- Automatically invokes AgentPyInterpreter for code validation
- Returns validated, executable Python code
- Maintains conversation history with both design and execution feedback

**Constructor:**
```python
AgentAIPy(server_address, model_name, my_role, max_tokens=16000, api_key="")
```

**Parameters:**
- `server_address` (str): LLM server URL (e.g., "http://localhost:11434")
- `model_name` (str): Model name (e.g., "deepseek-r1:70b")
- `my_role` (str): System prompt defining the agent's role
- `max_tokens` (int): Maximum tokens for responses (default: 16000)
- `api_key` (str): Optional API key for authentication

### AgentPyInterpreter

Specialized agent for executing and validating Python code.

**File:** `agentPyInterpreter.py`

**Purpose:** Execute Python code, detect errors, and iteratively fix them using the LLM.

**Key Features:**
- Executes code using Python 3 subprocess
- Parses runtime errors from stderr
- Automatically attempts to fix errors
- Configurable retry attempts

**Constructor:**
```python
AgentPyInterpreter(server_address, model_name, trials)
```

**Parameters:**
- `server_address` (str): LLM server URL
- `model_name` (str): Model name to use for fixing code
- `trials` (int): Maximum number of fix attempts (recommended: 3)

## Usage Examples

### Example 1: Basic Python Code Generation

```python
from agentPy import AgentAIPy

# Create a Python programmer agent
programmer = AgentAIPy(
    server_address="http://localhost:11434",
    model_name="deepseek-r1:70b",
    my_role="You are a Python programmer. Write clean Python code to solve tasks."
)

# Generate and validate code
code = programmer.get_response("Write a function to calculate factorial recursively")

# The code is automatically executed and fixed if there are runtime errors
print(code)
```

### Example 2: Designer-Programmer Conversation

```python
from agent import AgentAI
from agentPy import AgentAIPy

# Create designer agent (reviews code)
designer = AgentAI(
    server_address="http://localhost:11434",
    model_name="deepseek-r1:70b",
    my_role="You are a Python software designer. Provide design feedback."
)

# Create programmer agent (writes code with validation)
programmer = AgentAIPy(
    server_address="http://localhost:11434",
    model_name="deepseek-r1:70b",
    my_role="You are a Python programmer. Write executable Python code."
)

# Initial task
task = "Write a program to find prime numbers up to 100"
code = programmer.get_response(task)

# Get design feedback
feedback = designer.get_response(f"Review this code: {code}")

# Improve code based on feedback
improved_code = programmer.get_response(feedback)

# Save conversation
programmer.save_to_excel("conversation.xlsx")
```

### Example 3: Using AgentPyInterpreter Directly

```python
from agentPyInterpreter import AgentPyInterpreter

# Create interpreter agent
interpreter = AgentPyInterpreter(
    server_address="http://localhost:11434",
    model_name="deepseek-r1:70b",
    trials=3
)

# Test code with intentional error
buggy_code = """
def divide(a, b):
    return a / b

print(divide(10, 0))  # Division by zero error
"""

# Interpreter will execute, detect error, and try to fix
fixed_code = interpreter.get_response(buggy_code)
print("Fixed code:", fixed_code)
```

### Example 4: Code with Markdown

Python agents can handle code wrapped in markdown code blocks:

```python
from agentPy import AgentAIPy

programmer = AgentAIPy(
    server_address="http://localhost:11434",
    model_name="deepseek-r1:70b",
    my_role="You are a Python programmer."
)

# Code in markdown format
markdown_code = """
```python
def hello_world():
    print("Hello, World!")

if __name__ == "__main__":
    hello_world()
```
"""

# Agent extracts and executes the code
result = programmer.get_response(f"Validate this code: {markdown_code}")
```

## Comparison with C Agents

| Feature | C Agents (AgentAIC) | Python Agents (AgentAIPy) |
|---------|---------------------|---------------------------|
| Base Agent | AgentAIC | AgentAIPy |
| Validator | AgentCompiler | AgentPyInterpreter |
| Validation Type | Compilation (gcc) | Execution (python3) |
| Error Source | Compile errors | Runtime errors |
| Code Marker | ` ```c ` | ` ```python ` |
| External Dependency | gcc compiler | Python 3 interpreter |
| Timeout | No timeout | 5 second execution timeout |

## Best Practices

### 1. Choose the Right Agent

- **Use AgentAIPy** when you need guaranteed executable code
- **Use AgentAI** (base) when you only need code suggestions without validation

### 2. Define Clear Roles

```python
# Good role definition
my_role = (
    "You are a Python programmer. "
    "Write clean, efficient, PEP-8 compliant code. "
    "Include type hints and docstrings. "
    "Ensure all code is executable without user input."
)
```

### 3. Handle Long-Running Code

The interpreter has a 5-second timeout for safety. Avoid:
- Infinite loops
- User input (input(), raw_input())
- Network operations without timeouts
- Large file operations

Instead, generate code that:
- Completes quickly
- Uses hardcoded values instead of user input
- Prints results to stdout

### 4. Configure Appropriate Trials

```python
# For simple code
interpreter = AgentPyInterpreter(server, model, trials=3)

# For complex code that might need more fixes
interpreter = AgentPyInterpreter(server, model, trials=5)
```

### 5. Monitor Conversation History

```python
# Check how many messages exchanged
print(f"Messages: {len(programmer.messages)}")

# Save regularly during long conversations
programmer.save_to_excel("checkpoint.xlsx")
```

## Troubleshooting

### Issue: "Execution error: Timeout"

**Cause:** Code took longer than 5 seconds to execute.

**Solution:**
- Simplify the code
- Remove user input requirements
- Reduce computational complexity
- Modify timeout in agentPyInterpreter.py if necessary (line with `timeout=5`)

### Issue: Code keeps failing after max trials

**Cause:** The LLM cannot fix the error, or the error is environmental.

**Solution:**
1. Check the error message in the conversation history
2. Verify Python environment has necessary packages
3. Simplify the requirements
4. Try a different LLM model
5. Increase trials parameter

### Issue: "No code found"

**Cause:** The response doesn't contain Python code in expected format.

**Solution:**
- Ensure role prompt instructs to return code in ` ```python ` blocks
- Check LLM response format
- Verify model is appropriate for code generation

### Issue: Code executes but has logic errors

**Cause:** The interpreter only catches runtime errors, not logic errors.

**Solution:**
- Use a designer agent to review logic
- Add test cases in the prompt
- Request specific output validation
- Implement a separate testing agent

### Issue: Import errors

**Cause:** Required Python packages not installed.

**Solution:**
```python
# Install required packages
pip install numpy pandas matplotlib

# Or specify in requirements
my_role = "Write code using only standard library. No external packages."
```

## Advanced Usage

### Custom System Prompts

```python
# Prompt for data science tasks
data_scientist_role = """
You are an expert Python data scientist.
Write code using pandas and numpy.
Include data validation and error handling.
Add comments explaining complex operations.
Ensure code is executable without user input.
"""

programmer = AgentAIPy(server, model, data_scientist_role)
```

### Error Analysis

```python
# Analyze what errors were encountered
interpreter = AgentPyInterpreter(server, model, trials=3)
code = interpreter.get_response(buggy_code)

# Check execution messages (logged internally)
# Review conversation to see what errors were fixed
```

### Integration with Testing

```python
# Generate code with tests
task = """
Write a function to reverse a string.
Include test cases that verify:
1. Basic string reversal
2. Empty string handling
3. Single character handling
Run the tests in the main block.
"""

code = programmer.get_response(task)
# Code will include tests and be validated by execution
```

## Files and Locations

- **agentPy.py**: Main Python programming agent
- **agentPyInterpreter.py**: Python code interpreter and fixer
- **test/test_agentPy.py**: Unit tests for AgentAIPy
- **test/test_agentPyInterpreter.py**: Unit tests for AgentPyInterpreter
- **examples/fibonacci_python_simple.py**: Basic Python example
- **examples/fibonacci_python_with_interpreter.py**: Example with execution validation
- **temp/code_temp.py**: Temporary file used for code execution

## See Also

- [README_UserGuide.md](README_UserGuide.md) - General user guide
- [README_CustomAgents.md](README_CustomAgents.md) - Creating custom agents
- [examples/README.md](examples/README.md) - Example usage
- [README_Logging.md](README_Logging.md) - Logging and debugging

## Contributing

When extending Python agents:

1. Follow the existing pattern from AgentCompiler/AgentAIC
2. Add comprehensive unit tests
3. Update documentation
4. Add example usage
5. Test with multiple LLM models

## License

Same as the main AgenticAI project.
