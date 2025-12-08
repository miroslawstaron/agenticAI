# AgenticAI Examples

This folder contains practical examples demonstrating how to use the AgenticAI framework.

## Overview

All examples focus on solving the **Fibonacci sequence problem** using different agent configurations. This allows you to compare approaches and understand the capabilities of each agent type.

Examples are available for both **C programming** and **Python programming** to demonstrate the versatility of the framework.

## Available Examples

### C Programming Examples

### 1. Simple Fibonacci (fibonacci_simple.py)

**Agents Used:** Designer + Programmer (without compilation)

**Description:** Basic conversation between a designer and programmer agent to develop a Fibonacci C program. No code compilation is performed - this is a pure AI-to-AI conversation focused on design and implementation.

**Key Features:**
- Simple two-agent conversation
- Design feedback loop
- No compilation requirements
- Good for understanding basic agent interactions

**Run:**
```bash
python examples/fibonacci_simple.py
```

**Requirements:**
- Python 3.7+
- Access to an LLM server (Ollama or compatible)
- No compiler needed

**Output:**
- `fibonacci_simple_conversation.xlsx` - Full conversation log

---

### 2. Fibonacci with Compiler (fibonacci_with_compiler.py)

**Agents Used:** Designer + Programmer with Compiler (AgentAIC)

**Description:** Enhanced conversation where the programmer agent automatically compiles C code using gcc. The AgentCompiler validates all generated code and iteratively fixes any compilation errors.

**Key Features:**
- Automatic code compilation with gcc
- Error detection and fixing
- Guaranteed compilable output
- Design feedback on compiled code

**Run:**
```bash
python examples/fibonacci_with_compiler.py
```

**Requirements:**
- Python 3.7+
- Access to an LLM server
- **gcc compiler must be installed**
  - Linux/Mac: Usually pre-installed
  - Windows: Install MinGW or similar

**Output:**
- `fibonacci_compiled_conversation.xlsx` - Full conversation with compiled code

**Verify gcc installation:**
```bash
gcc --version
```

---

### 3. Fibonacci with Human-in-the-Loop (fibonacci_human_in_loop.py)

**Agents Used:** Designer + Programmer + Human (you!)

**Description:** Three-way conversation involving two AI agents and a human reviewer. At each iteration, you'll be prompted to review the code and provide feedback, which both agents will incorporate into their next responses.

**Key Features:**
- Human feedback integration
- Interactive development process
- Structured conversation logging
- Demonstrates human-AI collaboration

**Run:**
```bash
python examples/fibonacci_human_in_loop.py
```

**Requirements:**
- Python 3.7+
- Access to an LLM server
- Human interaction (you!)
- Time and patience (each iteration requires your input)

**Output:**
- `fibonacci_human_conversation.xlsx` - Full conversation log
- `fibonacci_human_conversation_log.xlsx` - Structured log by iteration and role

**Interactive Process:**
1. AI programmer writes initial code
2. AI designer reviews the code
3. **You** provide your feedback
4. Agents incorporate your feedback
5. Process repeats for configured iterations

---

### Python Programming Examples

### 4. Simple Python Fibonacci (fibonacci_python_simple.py)

**Agents Used:** Designer + Programmer (Python, without execution)

**Description:** Basic conversation between a designer and programmer agent to develop a Fibonacci Python program. No code execution is performed - this is a pure AI-to-AI conversation focused on design and implementation.

**Key Features:**
- Simple two-agent conversation for Python
- Design feedback loop
- No execution requirements
- Good for understanding basic Python agent interactions

**Run:**
```bash
python examples/fibonacci_python_simple.py
```

**Requirements:**
- Python 3.7+
- Access to an LLM server (Ollama or compatible)
- No additional requirements

**Output:**
- `fibonacci_python_simple_conversation.xlsx` - Full conversation log

---

### 5. Python Fibonacci with Interpreter (fibonacci_python_with_interpreter.py)

**Agents Used:** Designer + Programmer with Interpreter (AgentAIPy)

**Description:** Enhanced conversation where the programmer agent automatically executes Python code. The AgentPyInterpreter validates all generated code and iteratively fixes any runtime errors.

**Key Features:**
- Automatic code execution with Python interpreter
- Runtime error detection and fixing
- Guaranteed executable output
- Design feedback on executed code

**Run:**
```bash
python examples/fibonacci_python_with_interpreter.py
```

**Requirements:**
- Python 3.7+
- Access to an LLM server
- Python 3 interpreter (already available if you can run the example)

**Output:**
- `fibonacci_python_interpreted_conversation.xlsx` - Full conversation with executed code

---

## Configuration

All examples use the following default configuration:

```python
SERVER = "http://localhost:11434"  # Ollama default
MODEL = "deepseek-r1:70b"          # Model name
MAX_ITERATIONS = 3-5               # Number of improvement cycles
```

### Customizing Examples

You can modify these values in each script:

**Change the server:**
```python
SERVER = "http://your-server.com:11434"
```

**Change the model:**
```python
MODEL = "gpt-4"  # or any compatible model
```

**Adjust iterations:**
```python
MAX_ITERATIONS = 10  # More iterations = more refinement
```

**Change output location:**
```python
OUTPUT_FILE = "my_custom_output.xlsx"
```

## Prerequisites

### Required for All Examples

1. **Python 3.7+**
   ```bash
   python --version
   ```

2. **Python Dependencies**
   ```bash
   pip install -r ../requirements.txt
   ```
   
   Installs:
   - litellm
   - pandas
   - openpyxl
   - tqdm

3. **LLM Server Access**
   
   Option A - Local Ollama (recommended):
   ```bash
   # Install Ollama
   curl -fsSL https://ollama.com/install.sh | sh
   
   # Pull a model
   ollama pull deepseek-r1:70b
   
   # Server runs automatically
   ```
   
   Option B - Remote Server:
   - Update SERVER variable in examples
   - Ensure network access
   
   Option C - OpenAI API:
   ```bash
   export OPENAI_API_KEY="your-key-here"
   ```
   Then update scripts:
   ```python
   SERVER = "https://api.openai.com/v1"
   MODEL = "gpt-4"
   ```

### Additional Requirements

- **fibonacci_with_compiler.py** requires gcc:
  - Ubuntu/Debian: `sudo apt-get install gcc`
  - macOS: `xcode-select --install`
  - Windows: Install MinGW

## Running the Examples

### Step 1: Navigate to Repository Root

```bash
cd /path/to/agenticAI
```

### Step 2: Ensure Dependencies Are Installed

```bash
pip install -r requirements.txt
```

### Step 3: Start Your LLM Server (if using Ollama)

```bash
ollama serve
# In another terminal:
ollama pull deepseek-r1:70b
```

### Step 4: Run an Example

```bash
# Simple version (fastest)
python examples/fibonacci_simple.py

# With compilation (requires gcc)
python examples/fibonacci_with_compiler.py

# With human interaction (interactive)
python examples/fibonacci_human_in_loop.py
```

## Understanding the Output

### Excel Files

All examples generate Excel files with the conversation history:

| role | content |
|------|---------|
| system | You are a designer... |
| user | Write a Fibonacci program... |
| assistant | Here is the code: ... |
| user | How can I improve it... |
| assistant | You can improve by... |

- **role = user**: Designer's prompts
- **role = assistant**: Programmer's responses
- **role = system**: Initial agent role definition

### Extracting Code

The C code is embedded in markdown code blocks within the conversation:

```
```c
#include <stdio.h>
int main() {
    // Your code here
}
```
```

You can:
1. Open the Excel file
2. Find the last assistant response
3. Extract the code between ` ```c ` and ` ``` `
4. Save to a .c file
5. Compile and run

## Troubleshooting

### "Connection Refused" Error

**Problem:** Cannot connect to LLM server

**Solution:**
```bash
# Check if server is running
curl http://localhost:11434

# Start Ollama if needed
ollama serve

# Verify model is available
ollama list
```

### "gcc: command not found"

**Problem:** Compiler not installed (affects fibonacci_with_compiler.py)

**Solution:**
```bash
# Ubuntu/Debian
sudo apt-get install gcc

# macOS
xcode-select --install

# Verify
gcc --version
```

### "Model not found"

**Problem:** Requested model isn't available

**Solution:**
```bash
# Pull the model
ollama pull deepseek-r1:70b

# Or use a different model in the script
MODEL = "llama2"  # or another available model
```

### Slow Execution

**Problem:** Examples take a long time to run

**Possible Causes:**
- Large model (70B parameters)
- Limited hardware
- Network latency (remote server)

**Solutions:**
- Use a smaller model: `MODEL = "deepseek-r1:7b"`
- Reduce iterations: `MAX_ITERATIONS = 2`
- Use a more powerful server
- Enable GPU acceleration for Ollama

### Import Errors

**Problem:** `ModuleNotFoundError` when running examples

**Solution:**
```bash
# Install dependencies
pip install -r requirements.txt

# Run from repository root
cd /path/to/agenticAI
python examples/fibonacci_simple.py
```

## Next Steps

After running these examples, you can:

1. **Modify the examples** to solve different problems
2. **Create your own agents** - see [README_CustomAgents.md](../README_CustomAgents.md)
3. **Combine agents in new ways** - mix and match different agent types
4. **Analyze the conversations** - use pandas to study improvement patterns
5. **Experiment with different models** - compare outputs from various LLMs

## Additional Resources

- [User Guide](../README_UserGuide.md) - Complete documentation
- [Custom Agents Guide](../README_CustomAgents.md) - Create your own agents
- [Logging Guide](../README_Logging.md) - Debug and monitor agents
- [Main README](../README.md) - Project overview

## Support

If you encounter issues:

1. Check the troubleshooting section above
2. Enable logging: Add `--log` flag to main scripts
3. Review the full documentation
4. Open an issue on GitHub with:
   - Error message
   - Your configuration (OS, Python version, model)
   - Steps to reproduce

## License

Same as the parent project - see [../LICENSE](../LICENSE)
