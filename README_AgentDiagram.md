# AgentDiagram - Mermaid Diagram Generation Agent

## Overview

`AgentDiagram` is an agent that generates Mermaid diagrams from source code using Large Language Models (LLMs). It analyzes source code and produces various types of diagrams in Mermaid syntax.

## Features

- **Multiple diagram types**: class, flowchart, sequence, and entity-relationship (ER) diagrams
- **Default diagram type**: Class diagram
- **Dynamic type switching**: Change diagram types on-the-fly
- **Mermaid syntax extraction**: Automatically extracts Mermaid code from LLM responses
- **Conversation history**: Maintains conversation context like other agents

## Supported Diagram Types

1. **class** (default): Class diagrams showing classes, attributes, methods, and relationships
2. **flowchart**: Flowchart diagrams showing program flow and logic
3. **sequence**: Sequence diagrams showing interactions between components
4. **er**: Entity-Relationship diagrams showing data models

## Installation

The agent requires the same dependencies as other agents in the project:

```bash
pip install pandas requests tqdm openpyxl
```

## Usage

### Basic Usage - Class Diagram (Default)

```python
from agentDiagram import AgentDiagram

# Create the agent
agent = AgentDiagram(
    server_address="http://localhost:11434",
    model_name="deepseek-r1:70b"
)

# Source code to analyze
source_code = """
class Vehicle {
    private:
        int speed;
    public:
        void accelerate();
};
"""

# Generate diagram
response = agent.get_response(source_code)
diagram = agent.extract_mermaid_diagram(response)
print(diagram)
```

### Specifying Diagram Type

```python
# Create agent with specific diagram type
agent = AgentDiagram(
    server_address="http://localhost:11434",
    model_name="deepseek-r1:70b",
    diagram_type="flowchart"  # or "sequence", "er"
)
```

### Changing Diagram Type Dynamically

```python
# Start with class diagrams
agent = AgentDiagram(
    server_address="http://localhost:11434",
    model_name="deepseek-r1:70b",
    diagram_type="class"
)

# Change to flowchart
agent.set_diagram_type("flowchart")

# Change to sequence diagram
agent.set_diagram_type("sequence")
```

### Using API Key

```python
agent = AgentDiagram(
    server_address="http://api.openai.com/v1",
    model_name="gpt-4",
    api_key="your-api-key-here"
)
```

### Custom Max Tokens

```python
agent = AgentDiagram(
    server_address="http://localhost:11434",
    model_name="deepseek-r1:70b",
    max_tokens=8000  # Adjust based on diagram complexity
)
```

## API Reference

### Constructor

```python
AgentDiagram(server_address, model_name, diagram_type="class", max_tokens=16000, api_key="")
```

**Parameters:**
- `server_address` (str): URL of the LLM server
- `model_name` (str): Name of the model to use
- `diagram_type` (str, optional): Type of diagram ("class", "flowchart", "sequence", "er"). Default: "class"
- `max_tokens` (int, optional): Maximum tokens for response. Default: 16000
- `api_key` (str, optional): API key for authentication. Default: ""

### Methods

#### `get_response(source_code)`

Generates a Mermaid diagram from source code.

**Parameters:**
- `source_code` (str): The source code to analyze

**Returns:**
- `str`: The LLM response containing the Mermaid diagram, or `None` on error

#### `extract_mermaid_diagram(response)`

Extracts the Mermaid diagram from the LLM response.

**Parameters:**
- `response` (str): The raw response from the LLM

**Returns:**
- `str`: The extracted Mermaid diagram syntax

#### `set_diagram_type(diagram_type)`

Changes the diagram type.

**Parameters:**
- `diagram_type` (str): New diagram type ("class", "flowchart", "sequence", "er")

**Raises:**
- `ValueError`: If diagram_type is invalid

#### Inherited Methods

From `AgentAI`:
- `save_to_excel(filename)`: Save conversation to Excel file
- `save_to_csv(filename)`: Save conversation to CSV file
- `to_html(output_html, role1, role2)`: Convert conversation to HTML
- `start()`: Print agent information

## Examples

See `example_diagram.py` for complete working examples.

### Example 1: C++ Class Diagram

```python
source_code = """
class Animal {
    protected:
        string name;
    public:
        virtual void speak() = 0;
};

class Dog : public Animal {
    public:
        void speak() override;
};
"""

agent = AgentDiagram(
    server_address="http://localhost:11434",
    model_name="deepseek-r1:70b"
)

response = agent.get_response(source_code)
diagram = agent.extract_mermaid_diagram(response)
```

### Example 2: Function Flowchart

```python
source_code = """
int fibonacci(int n) {
    if (n <= 1) return n;
    return fibonacci(n-1) + fibonacci(n-2);
}
"""

agent = AgentDiagram(
    server_address="http://localhost:11434",
    model_name="deepseek-r1:70b",
    diagram_type="flowchart"
)

response = agent.get_response(source_code)
diagram = agent.extract_mermaid_diagram(response)
```

## Testing

Run the test suite:

```bash
python -m unittest test.test_agentDiagram -v
```

## Integration with Mermaid

The generated diagrams use [Mermaid](https://mermaid.js.org/) syntax and can be:
- Rendered in Markdown files (GitHub, GitLab, etc.)
- Visualized using Mermaid Live Editor
- Embedded in documentation
- Converted to images using Mermaid CLI

## Notes

- The agent uses the same server infrastructure as other agents in the project
- Temperature is set to 0.3 for consistent diagram generation
- Timeout is 300 seconds with 3 retry attempts
- The agent maintains conversation history for context

## License

Same as the parent project.
