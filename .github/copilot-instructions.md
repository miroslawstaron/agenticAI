# AgenticAI Codebase Guide

## Project Overview
This is a research project that implements multi-agent AI conversations for C code generation and analysis. The system creates designer-programmer conversations between different LLM models to study iterative code improvement, compilation success rates, and conversation patterns.

## Core Architecture

### Agent System (`agent.py`, `agentC.py`, `agentCompiler.py`)
- **`AgentAI`**: Base class managing Ollama API conversations with persistent message history
- **`AgentAIC`**: Extends base with C code compilation and error fixing capabilities. It communicates with AgentCompiler for validation.
- **`AgentCompiler`**: Specialized for compilation error detection and automated fixes. It uses gcc to compile extracted C code snippets.
- All agents maintain conversation state via `self.messages` list with role-based structure
- **`AgentStaticAnalyzer`**: Analyzes C code for static issues using LLMs without compilation
- **`AgentHuman`**: Facilitates human-in-the-loop conversations for manual code review. It is essentially a wrapper for human input.

### Execution Patterns
- **Standard mode** (`main.py`): Designer-programmer conversation loop with progress tracking
- **Compiler mode** (`main_agentc.py`): Adds compilation validation to conversation cycles
- **Multiple variants** (`main2.py`, `mainT.py`, `main_human.py`): Different model combinations and server configurations

### Key Configuration Points
```python
# Server endpoints - commonly localhost:11434 or chalmers.se servers
server_address="http://deepthought.cse.chalmers.se"
model_name="deepseek-r1:70b"  # Model format: name:size
my_role="You are a C designer..."  # System prompt defining agent behavior
```

## Development Workflows

### Running Experiments
```bash
python main.py --prompt "Write a C program to sort an array"
python main_agentc.py --prompt "Create a linked list implementation"
```

### Data Analysis Pipeline
1. **Conversation Export**: Agents automatically save to Excel (`save_to_excel()`)
2. **Analysis Notebook**: `analyze.ipynb` processes conversation data
3. **Key Metrics**: BLEU/ROUGE scores, compilation rates, word counts, response patterns
4. **Visualization**: matplotlib/seaborn charts for conversation analysis

### File Naming Conventions
- **Results**: `programmer_conversation_{model1}_{model2}_complete.xlsx`
- **Compiled**: Files ending with `_cc.xlsx` include compilation results
- **HTML Reports**: Generated via `convert_to_html.py` for presentation

## Code Analysis Patterns

### C Code Extraction
```python
# Pattern used throughout codebase
pattern = r"```c(.*?)```"
match = re.search(pattern, markdown, re.DOTALL)
```

### Compilation Integration
- Uses subprocess with gcc: `gcc -w code_temp.c -o a.out -lm`
- Error detection via stderr parsing for "error" keyword
- Results categorized as: "success", "error", "no_code"

### Data Processing (analyze.ipynb)
- Excel files loaded via pandas with role-based filtering
- Assistant rows = Programmer responses, User rows = Designer responses
- Code extraction applied to all responses for compilation analysis
- Statistical analysis includes uniqueness metrics and conversation diversity

## Research-Specific Considerations
- **Temperature settings**: Typically 0.3-0.5 for reproducible experiments
- **Iteration limits**: MAX_ITERATIONS typically 1000-5000 for long-term studies
- **Progress tracking**: tqdm integration for experiment monitoring
- **Multi-model support**: Same codebase works with various Ollama models

## Common Gotchas
- Models must be pre-pulled on Ollama servers before use
- Excel files can become large (>50MB) with extensive conversations
- Compilation requires gcc and math library (`-lm` flag)
- Timeout handling essential for model server reliability (300s default)