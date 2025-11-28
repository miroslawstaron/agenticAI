# AgenticAI Codebase Guide

## Project Overview
Research project implementing multi-agent AI conversations for C code generation and analysis. Creates designer-programmer conversations between LLM models to study iterative code improvement, compilation success rates, and conversation patterns.

## Core Architecture
- **AgentAI** (`agent.py`): Base class managing LiteLLM API conversations with persistent message history
- **AgentAIC** (`agentC.py`): Extends base with C code compilation and error fixing via AgentCompiler
- **AgentCompiler** (`agentCompiler.py`): Specialized for compilation error detection and automated fixes using gcc
- **AgentStaticAnalyzer** (`agentStaticAnalyzer.py`): Analyzes C code for static issues without compilation
- **AgentHuman** (`agentH.py`): Facilitates human-in-the-loop conversations
- All agents maintain conversation state in `self.messages` list with role-based structure: `{"role": "system|user|assistant", "content": "..."}`

## Key Patterns
- **Code Extraction**: Use regex `r"```c(.*?)```"` to extract C code from markdown responses
- **Compilation**: `gcc -w code_temp.c -o a.out -lm` with error parsing for "error" keyword
- **Message Handling**: Append user prompts, get assistant responses, maintain conversation history
- **Error Handling**: 3 retries with exponential backoff, 300s timeout for API calls
- **Data Export**: Save conversations to Excel via `pandas.DataFrame(self.messages).to_excel(filename, index=False)`

## Development Workflows
### Running Experiments
```bash
# Basic designer-programmer conversation
python3 main.py --prompt "Write a C program to sort an array"

# With compilation validation
python3 main_agentc.py --prompt "Create a linked list implementation"

# Human-in-the-loop mode
python3 main_human.py --prompt "Code review task"
```

### Testing
```bash
# Run all tests
python3 -m unittest discover -s test -p "test_*.py" -v

# Run specific test
python3 -m unittest test.test_agent.TestAgentAI.test_initialization -v
```
- Use extensive mocking for API calls, file I/O, subprocess
- Create temporary files in `./temp` directory, clean up after tests
- Mock external dependencies to avoid live API calls

### Data Analysis
- Load conversation Excel files with `pandas`
- Filter by role: Assistant = Programmer responses, User = Designer responses
- Apply code extraction to all responses for compilation analysis
- Use `analyze.ipynb` for BLEU/ROUGE scores, compilation rates, word counts, conversation diversity metrics

## Project-Specific Conventions
- **API Integration**: Use `litellm.completion()` with model names like "deepseek-r1:70b"
- **Environment Variables**: Set `OPENAI_API_KEY` for API access (explicit keys take precedence)
- **Server Endpoints**: Default to localhost:11434 or chalmers.se servers
- **Temperature Settings**: Typically 0.3-0.5 for reproducible experiments
- **Iteration Limits**: MAX_ITERATIONS 1000-5000 for long-term studies
- **Progress Tracking**: `tqdm` integration for experiment monitoring
- **File Naming**: Results as `programmer_conversation_{model1}_{model2}_complete.xlsx`

## Dependencies
- `litellm`: Unified LLM API interface
- `pandas`: Data manipulation and Excel export
- `tqdm`: Progress bars
- `openpyxl`: Excel operations
- `PyPDF2`: PDF parsing for 3GPP docs
- Optional: `vllm` for vLLM-based agents

## Common Gotchas
- Models must be pre-pulled on Ollama servers
- Excel files can exceed 50MB with extensive conversations
- Compilation requires gcc and `-lm` flag for math functions
- API timeouts default to 300s; implement retry logic
- Clean up temporary files in `/temp` directory