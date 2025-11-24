# AgenticAI Codebase Guide

## Project Overview
This is a research project that implements multi-agent AI conversations for C code generation and analysis. The system creates designer-programmer conversations between different LLM models to study iterative code improvement, compilation success rates, and conversation patterns.

## Development Setup

### Prerequisites
- Python 3.8 or higher
- gcc compiler (for C code compilation features)
- Git

### Installation
1. Clone the repository:
   ```bash
   git clone https://github.com/miroslawstaron/agenticAI.git
   cd agenticAI
   ```

2. Install Python dependencies:
   ```bash
   pip install -r requirements.txt
   ```

### Required Dependencies
- **pandas**: Data manipulation and Excel file handling
- **requests**: HTTP client for API calls to LLM servers
- **tqdm**: Progress bars for long-running experiments
- **openpyxl**: Excel file operations
- **PyPDF2**: PDF parsing for 3GPP document analysis (used in `requirements/` directory)

### Optional Dependencies
- **vllm**: For vLLM-based agent (large dependency, only needed for specific use cases)

### Environment Variables
Set the `OPENAI_API_KEY` environment variable when using OpenAI or compatible APIs:
```bash
export OPENAI_API_KEY="your_api_key_here"
```

## Testing

### Running Tests
Use Python's built-in unittest framework:

```bash
# Run all tests
python -m unittest discover -s test -p "test_*.py" -v

# Run specific test file
python -m unittest test.test_agent -v

# Run specific test case
python -m unittest test.test_agent.TestAgentAI.test_initialization -v
```

### Test Structure
- All tests are in the `/test` directory
- Test files follow the naming pattern `test_*.py`
- Tests use extensive mocking to avoid live API dependencies
- Temporary files are created in `./temp` directory and cleaned up after tests

### Writing Tests
- Use Python's `unittest` framework
- Mock external dependencies (API calls, file I/O, subprocess calls)
- Follow existing test patterns in `test/test_agent.py` as reference
- Each test should be independent and clean up after itself

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

## Code Style and Conventions

### Python Style
- Follow PEP 8 style guidelines
- Use 4 spaces for indentation (no tabs)
- Maximum line length: 100 characters (flexible for readability)
- Use descriptive variable names

### Naming Conventions
- **Classes**: PascalCase (e.g., `AgentAI`, `AgentCompiler`)
- **Functions/Methods**: snake_case (e.g., `get_response`, `save_to_excel`)
- **Constants**: UPPER_SNAKE_CASE (e.g., `MAX_ITERATIONS`)
- **Private attributes**: Prefix with underscore (e.g., `_internal_state`)

### Agent Design Patterns
- All agent classes should inherit from `AgentAI` base class
- Maintain conversation history in `self.messages` list
- Use role-based message structure: `{"role": "system|user|assistant", "content": "..."}`
- Implement `get_response(prompt)` method for conversation interaction

### API Integration
- Use `requests` library for HTTP API calls to LLM servers
- API keys can be passed explicitly or via `OPENAI_API_KEY` environment variable
- Explicit API keys take precedence over environment variables
- Server URLs should point to the base API endpoint (e.g., `http://deepthought.cse.chalmers.se`)

### Error Handling
- Use try-except blocks for API calls with retry logic
- Default timeout: 300 seconds for API requests
- Implement exponential backoff for retries (typically 3 retries)
- Log errors appropriately for debugging

### File Operations
- Use pandas for Excel file operations (`.xlsx` format)
- Support both CSV and Excel export formats
- Clean up temporary files (especially in `/temp` directory)
- Use descriptive filenames with model names and timestamps

## Common Commands

### Running Experiments
```bash
# Basic designer-programmer conversation
python main.py --prompt "Your task description"

# With compilation validation
python main_agentc.py --prompt "Generate C code for sorting"

# Human-in-the-loop mode
python main_human.py --prompt "Code review task"
```

### Data Analysis
```bash
# Convert conversation to HTML
python convert_to_html.py input.xlsx output.html

# Analyze conversations (Jupyter notebook)
jupyter notebook analyze.ipynb
```

### Development
```bash
# Install dependencies
pip install -r requirements.txt

# Run tests
python -m unittest discover -s test -p "test_*.py" -v

# Check for import errors
python -c "import agent; import agentC; import agentCompiler"
```

## Troubleshooting

### Common Issues

**Import errors**: Ensure all dependencies are installed
```bash
pip install pandas requests tqdm openpyxl PyPDF2
```

**API connection failures**: 
- Verify server URL is accessible
- Check API key is set correctly
- Ensure model is available on the server (for Ollama, use `ollama list`)

**Compilation errors**:
- Ensure gcc is installed and accessible
- Math library (`-lm`) is required for mathematical functions
- Check that `/temp` directory exists and is writable

**Excel file corruption**:
- Large conversation files may cause memory issues
- Consider saving intermediate results more frequently
- Use CSV format for very large datasets

## Best Practices

### When Adding New Agents
1. Inherit from `AgentAI` base class
2. Implement required methods: `__init__`, `get_response`
3. Add corresponding test file in `/test` directory
4. Update this documentation with agent description
5. Follow existing patterns for message handling and API integration

### When Modifying Existing Code
1. Run tests before and after changes
2. Maintain backward compatibility for conversation exports
3. Update documentation if changing public APIs
4. Use mocking in tests to avoid external dependencies

### When Running Experiments
1. Use descriptive prompts and task descriptions
2. Set appropriate `MAX_ITERATIONS` based on experiment scope
3. Monitor Excel file sizes for long-running experiments
4. Save intermediate results to prevent data loss
5. Use version control for experimental scripts