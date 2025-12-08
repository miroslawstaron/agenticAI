# AgenticAI User Guide

## Table of Contents

1. [Introduction](#introduction)
2. [Installation](#installation)
3. [Basic Concepts](#basic-concepts)
4. [Getting Started](#getting-started)
5. [Available Agents](#available-agents)
6. [Usage Examples](#usage-examples)
7. [Configuration](#configuration)
8. [Logging](#logging)
9. [Troubleshooting](#troubleshooting)

## Introduction

AgenticAI is a research project that enables multi-agent AI conversations for code generation and analysis. The framework allows different AI models to collaborate as designers, programmers, compilers, and even incorporate human feedback in the development loop.

### Key Features

- **Multi-Agent Conversations**: Create conversations between different AI agents with specific roles
- **C Code Generation**: Specialized agents for C programming with compilation support
- **Human-in-the-Loop**: Integrate human feedback into the AI conversation flow
- **Conversation Persistence**: Save all conversations to Excel/CSV for analysis
- **Logging System**: Track all agent activities for debugging and research
- **Extensible Architecture**: Easy to create custom agents for specific tasks

## Installation

### Prerequisites

- Python 3.7 or higher
- pip package manager
- (Optional) gcc compiler for C code compilation features
- (Optional) An LLM server (Ollama, OpenAI, or compatible API)

### Install Dependencies

```bash
# Clone the repository
git clone https://github.com/miroslawstaron/agenticAI.git
cd agenticAI

# Install Python dependencies
pip install -r requirements.txt
```

### Required Python Packages

- `litellm` - Unified LLM API interface
- `pandas` - Data manipulation and Excel export
- `tqdm` - Progress bars
- `openpyxl` - Excel file operations

## Basic Concepts

### Agents

An **Agent** is an AI entity with a specific role and personality. Each agent:
- Has a unique ID for tracking
- Maintains conversation history
- Communicates with an LLM (Language Model)
- Can be configured with different models and servers

### Roles

Agents are assigned **roles** that define their behavior:
- **Designer**: Provides design suggestions and improvements
- **Programmer**: Writes code to solve tasks
- **Compiler**: Validates and fixes C code compilation errors
- **Human**: Allows human interaction in the conversation loop

### Conversations

A **conversation** is an exchange between multiple agents:
1. One agent sends a prompt
2. Another agent responds
3. The response becomes the next prompt
4. This continues iteratively

### Message Structure

All conversations use a standardized message format:
```python
{
    "role": "system|user|assistant",
    "content": "The message content"
}
```

## Getting Started

### Quick Start: Basic Conversation

Here's the simplest way to start a designer-programmer conversation:

```bash
python main.py --prompt "Write a C program to calculate factorial"
```

This will:
1. Create a teacher (designer) agent
2. Create a student (programmer) agent
3. Run a conversation for 20 iterations
4. Save the results to an Excel file

### Understanding the Output

The conversation is saved to an Excel file with two columns:
- **role**: Either "user" (designer) or "assistant" (programmer)
- **content**: The message content from each agent

## Available Agents

### 1. AgentAI (Base Agent)

The foundation for all agents. Manages LLM communication and conversation history.

**Key Methods:**
- `get_response(prompt)` - Send a prompt and get a response
- `save_to_excel(filename)` - Save conversation to Excel
- `save_to_csv(filename)` - Save conversation to CSV

**Example:**
```python
from agent import AgentAI

agent = AgentAI(
    server_address="http://localhost:11434",
    model_name="deepseek-r1:70b",
    my_role="You are a helpful programming assistant"
)

response = agent.get_response("Hello, how can you help me?")
print(response)
```

### 2. AgentAIC (C Code Agent)

Extends AgentAI with automatic code compilation using gcc.

**Features:**
- Automatically compiles generated C code
- Uses AgentCompiler to fix compilation errors
- Returns validated, compilable code

**Example:**
```python
from agentC import AgentAIC

programmer = AgentAIC(
    server_address="http://localhost:11434",
    model_name="deepseek-r1:70b",
    my_role="You are a C programmer. Write code in C to solve tasks."
)

code = programmer.get_response("Write a function to reverse a string")
# Code is automatically compiled and fixed if needed
```

### 3. AgentCompiler

Specialized agent for compiling C code and fixing compilation errors.

**Features:**
- Compiles code with gcc
- Detects compilation errors
- Asks LLM to fix errors iteratively
- Returns working code or error details

**Note:** Usually used internally by AgentAIC, but can be used standalone.

### 4. AgentH (Human-in-the-Loop)

Allows human interaction in the conversation flow.

**Features:**
- Pauses execution for human input
- Displays the conversation context
- Collects human feedback
- Integrates feedback into the conversation

**Example:**
```python
from agentH import AgentH

human = AgentH(
    server_address=None,
    model_name=None,
    my_role=None
)

feedback = human.get_response("Review this code: [code here]")
# Program waits for human to type response
```

### 5. AgentStaticAnalyzer

Analyzes C code for static issues without compilation.

**Features:**
- Checks for common coding issues
- Provides improvement suggestions
- No compilation required

### 6. AgentDiagram

Generates Mermaid diagrams from source code.

**Features:**
- Creates class diagrams, flowcharts, sequence diagrams, ER diagrams
- Validates generated diagrams
- Exports to PNG format

See [README_AgentDiagram.md](README_AgentDiagram.md) for detailed documentation.

### 7. AgentAIPy (Python Code Agent)

Extends AgentAI with automatic code execution using Python interpreter.

**Features:**
- Automatically executes generated Python code
- Uses AgentPyInterpreter to fix runtime errors
- Returns validated, executable code

**Example:**
```python
from agentPy import AgentAIPy

programmer = AgentAIPy(
    server_address="http://localhost:11434",
    model_name="deepseek-r1:70b",
    my_role="You are a Python programmer. Write code in Python to solve tasks."
)

code = programmer.get_response("Write a function to calculate factorial")
# Code is automatically executed and fixed if needed
```

### 8. AgentPyInterpreter

Specialized agent for executing Python code and fixing runtime errors.

**Features:**
- Executes code with Python interpreter
- Detects runtime errors
- Asks LLM to fix errors iteratively
- Returns working code or error details

**Note:** Usually used internally by AgentAIPy, but can be used standalone.

**Example:**
```python
from agentPyInterpreter import AgentPyInterpreter

interpreter = AgentPyInterpreter(
    server_address="http://localhost:11434",
    model_name="deepseek-r1:70b",
    trials=3
)

# Validate and fix Python code
fixed_code = interpreter.get_response("print('Hello, World!')")
```

## Usage Examples

### Example 1: Simple Designer-Programmer Conversation

```python
from agent import AgentAI

# Create designer agent
designer = AgentAI(
    server_address="http://localhost:11434",
    model_name="deepseek-r1:70b",
    my_role="You are an expert software designer. Provide design suggestions."
)

# Create programmer agent
programmer = AgentAI(
    server_address="http://localhost:11434",
    model_name="deepseek-r1:70b",
    my_role="You are an expert programmer. Write code based on designs."
)

# Initial task
task = "Create a program to sort an array using quicksort"

# First response from programmer
code = programmer.get_response(task)

# Get design feedback
feedback = designer.get_response(f"Here is the code: {code}. How can it be improved?")

# Iterate for improvements
for i in range(5):
    code = programmer.get_response(feedback)
    feedback = designer.get_response(f"Review this code: {code}")

# Save conversation
programmer.save_to_excel("conversation.xlsx")
```

### Example 2: Using AgentAIC with Compiler

```python
from agentC import AgentAIC
from agent import AgentAI

# Programmer with compilation
programmer = AgentAIC(
    server_address="http://localhost:11434",
    model_name="deepseek-r1:70b",
    my_role="You are a C programmer. Write compilable C code."
)

# Designer for suggestions
designer = AgentAI(
    server_address="http://localhost:11434",
    model_name="deepseek-r1:70b",
    my_role="You are a C code designer. Suggest improvements."
)

# Get compilable code
code = programmer.get_response("Write a linked list implementation in C")
# Code is automatically compiled and fixed

# Get design feedback
suggestion = designer.get_response(f"Improve this code: {code}")

# Iterate with compilation validation
for i in range(3):
    code = programmer.get_response(suggestion)
    suggestion = designer.get_response(code)

programmer.save_to_excel("compiled_code.xlsx")
```

### Example 3: Human-in-the-Loop

```python
from agent import AgentAI
from agentH import AgentH

# Create AI agents
programmer = AgentAI(
    server_address="http://localhost:11434",
    model_name="deepseek-r1:70b",
    my_role="You are a programmer."
)

designer = AgentAI(
    server_address="http://localhost:11434",
    model_name="deepseek-r1:70b",
    my_role="You are a designer."
)

# Create human agent
human = AgentH()

# Start conversation
task = "Create a binary search tree"
code = programmer.get_response(task)
design_feedback = designer.get_response(f"Review: {code}")

# Get human input
human_feedback = human.get_response(
    f"Programmer's code: {code}\nDesigner's feedback: {design_feedback}\nYour thoughts?"
)

# Continue with human feedback
improved_code = programmer.get_response(
    f"Designer said: {design_feedback}. Human said: {human_feedback}"
)
```

## Configuration

### Server Configuration

You can use different LLM servers:

**Ollama (Local):**
```python
agent = AgentAI(
    server_address="http://localhost:11434",
    model_name="deepseek-r1:70b",
    my_role="Your role"
)
```

**Custom Server:**
```python
agent = AgentAI(
    server_address="http://your-server.com:11434",
    model_name="your-model",
    my_role="Your role"
)
```

**OpenAI:**
```python
import os
os.environ['OPENAI_API_KEY'] = "your-api-key"

agent = AgentAI(
    server_address="https://api.openai.com/v1",
    model_name="gpt-4",
    my_role="Your role",
    api_key="your-api-key"  # Optional, can use environment variable
)
```

### Model Configuration

**Temperature:** Controls randomness (default: 0.5 for AgentAI, 0.3 for AgentAIC)
- Lower (0.1-0.3): More focused and deterministic
- Higher (0.7-1.0): More creative and varied

**Max Tokens:** Maximum response length (default: 16000)

### API Key Configuration

Set the API key via environment variable:
```bash
export OPENAI_API_KEY="your-api-key-here"
```

Or pass it explicitly:
```python
agent = AgentAI(
    server_address="https://api.openai.com/v1",
    model_name="gpt-4",
    my_role="Your role",
    api_key="your-api-key"
)
```

## Logging

AgenticAI includes a comprehensive logging system for debugging and research.

### Enable Logging

Use the `--log` flag when running scripts:

```bash
python main.py --prompt "Your task" --log
python main_agentc.py --prompt "C programming task" --log
python main_human.py --prompt "Review task" --log
```

### Log Contents

Logs include:
- Agent initialization with system prompts
- All prompts sent to LLMs
- All responses received
- Compilation attempts and errors
- Exception details
- Timing information

### Log Location

Logs are written to `execution.log` in the current directory.

### Programmatic Logging

```python
from logger import get_logger

logger = get_logger()
logger.enable("execution.log")

# Now all agent activities will be logged
# Your code here...

logger.disable()
```

See [README_Logging.md](README_Logging.md) for complete logging documentation.

## Troubleshooting

### Common Issues

#### 1. Connection Refused Error

**Problem:** Cannot connect to LLM server

**Solutions:**
- Check if the server is running: `curl http://localhost:11434`
- Verify the server address is correct
- Ensure the port is not blocked by firewall

#### 2. Model Not Found

**Problem:** LLM reports model doesn't exist

**Solutions:**
- For Ollama, pull the model: `ollama pull deepseek-r1:70b`
- Verify model name is correct
- Check available models: `ollama list`

#### 3. Timeout Errors

**Problem:** Request times out after 300 seconds

**Solutions:**
- Try a smaller model
- Reduce max_tokens parameter
- Check server load
- Increase timeout (modify the code)

#### 4. Compilation Errors (AgentAIC)

**Problem:** Code doesn't compile

**Solutions:**
- Ensure gcc is installed: `gcc --version`
- Check that the model generates valid C code
- Review the generated code manually
- Increase the number of compilation trials

#### 5. Out of Memory

**Problem:** Server runs out of memory

**Solutions:**
- Use a smaller model
- Reduce max_tokens
- Close other applications
- Add more RAM or use cloud server

#### 6. Excel/CSV Save Errors

**Problem:** Cannot save conversation files

**Solutions:**
- Ensure write permissions in the directory
- Close any open Excel files with the same name
- Check disk space
- Verify openpyxl is installed: `pip install openpyxl`

### Getting Help

1. Check the logs: `execution.log`
2. Review the documentation in the repository
3. Check existing examples in the `examples/` folder
4. Open an issue on GitHub with:
   - Error message
   - Full command used
   - Log file contents
   - Environment details (OS, Python version, etc.)

## Best Practices

1. **Start Simple**: Begin with basic AgentAI before using specialized agents
2. **Use Logging**: Always enable logging for debugging: `--log`
3. **Save Frequently**: Save conversations periodically during long runs
4. **Monitor Resources**: Watch CPU, memory, and network usage
5. **Version Control**: Keep track of your prompts and configurations
6. **Test Locally**: Use local models (Ollama) before cloud APIs
7. **Set Iteration Limits**: Don't run infinite loops, set MAX_ITERATIONS
8. **Review Outputs**: Manually check generated code before using it
9. **Handle Exceptions**: Wrap agent calls in try-except blocks
10. **Use Environment Variables**: Store API keys securely

## Next Steps

- See [examples/](examples/) folder for working examples
- Read [README_CustomAgents.md](README_CustomAgents.md) to create your own agents
- Explore [README_MessageQueue.md](README_MessageQueue.md) for inter-agent communication
- Check [README_AgentDiagram.md](README_AgentDiagram.md) for diagram generation

## Additional Resources

- Main README: [README.md](README.md)
- Logging Guide: [README_Logging.md](README_Logging.md)
- Diagram Agent: [README_AgentDiagram.md](README_AgentDiagram.md)
- Message Queue: [README_MessageQueue.md](README_MessageQueue.md)
- GitHub Repository: https://github.com/miroslawstaron/agenticAI
