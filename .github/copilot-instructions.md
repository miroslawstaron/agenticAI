# AgenticAI Codebase Guide

## Project Overview
Research framework enabling multi-agent AI conversations for software engineering tasks: C/Python code generation, diagram generation, requirement specification, and source code analysis. Agents collaborate as designers, programmers, compilers, and humans to study iterative code improvement and conversation patterns.

## Core Architecture

### Agent Hierarchy
- **AgentAI** (`agent.py`): Base class managing LiteLLM API conversations with persistent message history, response serialization (CSV/Excel/HTML)
- **AgentAIC** (`agentC.py`): C code agent with compilation support via integrated `AgentCompiler`
- **AgentAIPy** (`agentPy.py`): Python code agent with execution support via integrated `AgentPyInterpreter`
- **AgentCompiler** (`agentCompiler.py`): GCC-based compilation, error detection, and automated fixes (up to 3 retry trials)
- **AgentStaticAnalyzer** (`agentStaticAnalyzer.py`): Static C code analysis without compilation, uses cppcheck
- **AgentDiagram** (`agentDiagram.py`): Mermaid diagram generation (class, flowchart, sequence, ER) with validation
- **AgentH** (`agentH.py`): Human-in-the-loop interface for interactive conversations
- **AgentReqs** (`requirements/agent_reqs.py`): 3GPP requirement specification analysis
- **Agent3GPP** (`requirements/agent_3gpp.py`): 3GPP document parsing and analysis using PyPDF2

### Cross-Agent Infrastructure
- **SingletonLogger** (`logger.py`): Thread-safe logging with agent ID tracking, timestamps, and hierarchical action logging
- **AgentIDManager** (`agent_id_manager.py`): Sequential 2-digit agent IDs (00-99) for identification
- **MessageQueue** (`messagequeue.py`): SQLite-backed inter-agent async communication with broadcast/targeted/anyone patterns
- **SingletonMeta**: Base metaclass for singleton implementations (Logger, MessageQueue, AgentIDManager)

### Message Format
All agents use consistent conversation structure: `{"role": "system|user|assistant", "content": "..."}`
- System: Initial role/context definition
- User: Input prompts (designer → programmer)
- Assistant: Model responses (programmer → designer)

## Key Patterns

### Code Handling
- **C Code Extraction**: `r"```c(.*?)```"` regex for markdown → code
- **Python Code Extraction**: `r"```python(.*?)```"` regex
- **Diagram Extraction**: `r"```mermaid(.*?)```"` for Mermaid syntax
- **Generic Extraction**: `def extract_c_code(markdown)` function in entry points

### Compilation Pipeline (AgentAIC)
1. Model generates C code in markdown block
2. Extract code from markdown
3. Write to `./temp/code_temp.c`
4. Execute: `gcc -w code_temp.c -o a.out -lm` (suppress warnings, link math)
5. Parse stderr for "error" keyword → retry with fix prompt
6. Max 3 trials before failure

### API & LLM Configuration
- **Primary Library**: `litellm.completion()` for unified API abstraction
- **Model Names**: Format `{provider}/{model}` (e.g., `ollama/qwen3:4b`, `deepseek-r1:70b`)
- **Temperature**: 0.3-0.5 for reproducibility (AgentCompiler uses 0.3, general agents use 0.5)
- **Timeouts**: 300 seconds default for all API calls
- **Retry Logic**: 3 attempts with exception handling per `get_response()`
- **Server Config**: api_base set via LiteLLM env vars or parameter

### Error Handling & Retries
```python
retries = 3
for attempt in range(retries):
    try:
        response = completion(...)
    except Exception as e:
        if attempt == retries - 1:
            return None
```

### Agent Initialization Pattern
```python
super().__init__(server_address, model_name, my_role, max_tokens, api_key)
self.agent_id = AgentIDManager.get_next_id()
self.logger = get_logger()
self.logger.log_agent_init(self.agent_id, self.__class__.__name__, my_role)
```

### Logging Integration
- All agents get unique 2-digit IDs automatically
- Log agent init with role definition
- Log all actions: `self.logger.log_agent_action(agent_id, action, details)`
- Log exceptions: `self.logger.log_exception(agent_id, exception, context)`
- Enable file logging: `logger.enable("execution.log")`

## Development Workflows

### Running Experiments
```bash
# Basic multi-agent conversation (designer ↔ programmer)
python3 main.py --prompt "Write a C program to sort an array" --log

# With compilation validation and error fixing
python3 main_agentc.py --prompt "Create a linked list implementation" --log

# Human-in-the-loop interactive mode
python3 main_human.py --prompt "Code review task"

# Python code generation and execution
python3 examples/fibonacci_python_with_interpreter.py

# Diagram generation
python3 examples/example_diagram.py
```

### Testing
```bash
# Run all tests with verbose output
python3 -m unittest discover -s test -p "test_*.py" -v

# Run specific test class
python3 -m unittest test.test_agentC.TestAgentAIC -v

# Run specific test method
python3 -m unittest test.test_agent.TestAgentAI.test_initialization -v
```
- All tests use `unittest` framework with extensive mocking
- Mock LiteLLM completion calls to avoid live API requests
- Temporary files created in `./temp/` directory
- Use `unittest.mock.patch` for subprocess, file I/O, API calls
- Clean up resources: explicitly close MessageQueue/reset AgentIDManager after tests

### Data Export & Analysis
- **Formats**: `.xlsx` (Excel), `.csv`, `.html` via `save_to_excel()`, `save_to_csv()`, `to_html()`
- **DataFrame**: All messages converted to pandas DataFrame for analysis
- **Role Mapping**: Optionally rename roles (e.g., 'user'→'Designer', 'assistant'→'Programmer')
- **Analysis**: Use `analyze.ipynb` for metrics: BLEU/ROUGE scores, compilation rates, word counts, diversity
- **File Naming**: Follow pattern `programmer_conversation_{model1}_{model2}_complete.xlsx`

## Project-Specific Conventions

### Environment Setup
- **API Keys**: `OPENAI_API_KEY` env var (command-line args take precedence)
- **Server Defaults**: `localhost:11434` (Ollama), `deepestthought.cse.chalmers.se:11434` (Chalmers)
- **Requirements**: `pip install -r requirements.txt`
- **Python Version**: Tested with Python 3.8+

### Naming & File Organization
- **Agent Classes**: Follow pattern `Agent{Type}` (AgentAI, AgentAIC, AgentH, AgentDiagram)
- **Entry Points**: `main*.py` scripts for different experiment types
- **Results**: Stored in `./results/` directory as Excel files
- **Temp Files**: `./temp/code_temp.c` for compilation, auto-cleaned
- **Logs**: `execution.log` (opt-in via `--log` flag or `logger.enable()`)

### Iteration & Conversation Limits
- **MAX_ITERATIONS**: 2-5000 depending on experiment scope (basic: 2-20, long-term: 1000-5000)
- **Compiler Trials**: 3 retry attempts for compilation error fixing
- **Agent ID Limit**: 99 sequential IDs (00-99), wraps around if exceeded

### Message Queue (Optional Multi-Agent Orchestration)
- **Singleton Pattern**: Only one MessageQueue instance per application
- **Message Types**: Targeted (recipient), broadcast (all), anonymous (anyone)
- **Async Communication**: Enable inter-agent communication without tight coupling
- **Thread-Safe**: Uses sqlite3 with threading locks

## Dependencies
- **Core**: `litellm`, `pandas`, `openpyxl` (API, data, Excel)
- **Execution**: `tqdm` (progress bars), `PyPDF2` (3GPP parsing)
- **Optional**: `vllm` (vLLM backend), `mermaid-cli` (diagram validation via subprocess)

## Common Gotchas
- **Model Availability**: Models must be pre-pulled on Ollama servers before use
- **File Cleanup**: Compilation creates `./temp/code_temp.c` — ensure cleanup or reuse
- **Excel Size**: Files can exceed 50MB with 1000+ iterations of lengthy conversations
- **Math Functions**: C compilation requires `-lm` flag for `<math.h>` functions
- **Agent IDs**: Reset `AgentIDManager.reset()` between test runs to avoid ID collision
- **Message Queue**: Close queue with `.close()` in cleanup to release sqlite resources
- **GCC Availability**: Compilation tests skip if gcc not available; check `which gcc`
- **API Timeouts**: Default 300s; adjust via completion() `timeout` parameter if needed