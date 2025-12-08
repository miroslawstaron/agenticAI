# Creating Custom Agents - Developer Guide

## Table of Contents

1. [Introduction](#introduction)
2. [Agent Architecture](#agent-architecture)
3. [Quick Start](#quick-start)
4. [Step-by-Step Guide](#step-by-step-guide)
5. [Complete Example](#complete-example)
6. [Advanced Patterns](#advanced-patterns)
7. [Best Practices](#best-practices)
8. [Testing Your Agent](#testing-your-agent)
9. [Integration Guide](#integration-guide)

## Introduction

This guide teaches you how to create custom agents by subclassing the base `AgentAI` class. Custom agents allow you to:

- Add specialized behaviors and capabilities
- Integrate external tools and services
- Create domain-specific agents (e.g., for Python, Java, SQL)
- Implement custom validation and error handling
- Build multi-step workflows

## Agent Architecture

### Class Hierarchy

```
AgentAI (base class)
├── AgentAIC (C code with compilation)
│   └── Uses AgentCompiler internally
├── AgentCompiler (compilation error fixing)
├── AgentStaticAnalyzer (static code analysis)
├── AgentH (human-in-the-loop)
├── AgentDiagram (Mermaid diagram generation)
└── YourCustomAgent (your implementation)
```

### Base Class: AgentAI

The `AgentAI` class provides:

**Core Functionality:**
- LLM communication via LiteLLM
- Message history management
- Retry logic with exponential backoff
- Conversation persistence (Excel/CSV/HTML)
- Logging integration

**Key Attributes:**
- `self.messages` - List of conversation messages
- `self.agent_id` - Unique identifier (sequential 2-digit: 00-99)
- `self.logger` - Logger instance
- `self.server_address` - LLM server URL
- `self.model_name` - Model identifier
- `self.max_tokens` - Maximum response length
- `self.api_key` - API authentication key

**Key Methods:**
- `get_response(prompt)` - Send prompt, get response
- `save_to_excel(filename)` - Save conversation to Excel
- `save_to_csv(filename)` - Save conversation to CSV
- `to_html(output_html)` - Convert to HTML
- `start()` - Print startup information

## Quick Start

Here's the minimal custom agent:

```python
from agent import AgentAI

class MyCustomAgent(AgentAI):
    """A simple custom agent that adds a greeting."""
    
    def __init__(self, server_address, model_name, my_role, max_tokens=16000, api_key=""):
        # ALWAYS call parent constructor first
        super().__init__(server_address, model_name, my_role, max_tokens, api_key)
        
        # Add your custom initialization here
        self.custom_attribute = "Hello from custom agent!"
    
    def get_response(self, prompt):
        """Override to add custom behavior."""
        # Add prefix to prompt
        modified_prompt = f"[CUSTOM PREFIX] {prompt}"
        
        # Call parent method
        response = super().get_response(modified_prompt)
        
        # Post-process response
        return f"Custom Agent Says: {response}"

# Usage
agent = MyCustomAgent(
    server_address="http://localhost:11434",
    model_name="deepseek-r1:70b",
    my_role="You are a helpful assistant"
)

response = agent.get_response("Hello!")
print(response)
```

## Step-by-Step Guide

### Step 1: Create the File

Create a new file `agentYourName.py` in the repository root:

```bash
touch agentYourName.py
```

### Step 2: Import Dependencies

```python
import agent  # Base class
from logger import get_logger  # Logging
from agent_id_manager import AgentIDManager  # For agent IDs if custom ID management needed
# Add other dependencies as needed
```

### Step 3: Define Your Class

```python
class AgentYourName(agent.AgentAI):
    """Your agent description.
    
    This agent does X, Y, and Z.
    It extends AgentAI with functionality for [your purpose].
    """
    
    pass  # We'll add methods next
```

### Step 4: Implement `__init__`

**CRITICAL:** Always call `super().__init__()` first!

```python
def __init__(self, server_address, model_name, my_role, max_tokens=16000, api_key=""):
    """Initialize your custom agent.
    
    Args:
        server_address: LLM server URL
        model_name: Model identifier
        my_role: System prompt defining agent behavior
        max_tokens: Maximum response length (default: 16000)
        api_key: API key for authentication (default: "")
    """
    # STEP 1: Call parent constructor - THIS IS MANDATORY
    super().__init__(server_address, model_name, my_role, max_tokens, api_key)
    
    # STEP 2: Initialize your custom attributes
    self.custom_config = {}
    self.processing_count = 0
    
    # STEP 3: Log initialization if needed (parent already logs basic init)
    self.logger.log_agent_action(self.agent_id, "Custom agent initialized", "Ready to process")
```

### Step 5: Override `get_response` (Optional)

Override this method to add custom behavior:

```python
def get_response(self, prompt):
    """Get response with custom processing.
    
    Args:
        prompt: User prompt to send to LLM
        
    Returns:
        str: Processed response or None on error
    """
    # Log the action
    self.logger.log_agent_action(self.agent_id, "Processing custom prompt")
    
    # PRE-PROCESSING: Modify prompt before sending
    processed_prompt = self._preprocess_prompt(prompt)
    
    # CALL PARENT: Get response from LLM
    response = super().get_response(processed_prompt)
    
    if response is None:
        return None
    
    # POST-PROCESSING: Modify response after receiving
    final_response = self._postprocess_response(response)
    
    # Update counter
    self.processing_count += 1
    
    return final_response
```

### Step 6: Add Helper Methods

```python
def _preprocess_prompt(self, prompt):
    """Private method for prompt preprocessing."""
    # Add your logic here
    return prompt.strip().upper()

def _postprocess_response(self, response):
    """Private method for response postprocessing."""
    # Add your logic here
    return response

def custom_method(self, param):
    """Public method for specific functionality."""
    # Your custom functionality
    return "result"
```

## Complete Example

Here's a complete custom agent that validates Python code:

```python
# agentPython.py
import agent
import subprocess
import re
from logger import get_logger

class AgentPython(agent.AgentAI):
    """Python code agent with syntax validation.
    
    This agent generates Python code and validates it using the Python compiler.
    It can detect syntax errors and ask the LLM to fix them.
    """
    
    def __init__(self, server_address, model_name, my_role, max_tokens=16000, api_key="", max_retries=3):
        """Initialize Python code agent.
        
        Args:
            server_address: LLM server URL
            model_name: Model identifier  
            my_role: System prompt
            max_tokens: Maximum response length
            api_key: API key for authentication
            max_retries: Maximum syntax error fix attempts
        """
        # Call parent constructor
        super().__init__(server_address, model_name, my_role, max_tokens, api_key)
        
        # Custom attributes
        self.max_retries = max_retries
        self.syntax_check_count = 0
        self.error_fix_count = 0
        
        # Log initialization
        self.logger.log_agent_action(
            self.agent_id, 
            "AgentPython initialized", 
            f"Max retries: {max_retries}"
        )
    
    def get_response(self, prompt):
        """Get response and validate Python code.
        
        Args:
            prompt: User prompt requesting Python code
            
        Returns:
            str: Valid Python code or error message
        """
        self.logger.log_agent_action(self.agent_id, "Generating Python code")
        
        # Get initial response
        response = super().get_response(prompt)
        
        if response is None:
            return None
        
        # Extract Python code
        code = self._extract_python_code(response)
        
        if not code:
            self.logger.log_agent_action(
                self.agent_id, 
                "No Python code found in response"
            )
            return response
        
        # Validate syntax
        for attempt in range(self.max_retries):
            syntax_error = self._check_syntax(code)
            
            if syntax_error is None:
                # Code is valid!
                self.logger.log_agent_action(
                    self.agent_id, 
                    "Python code validated successfully"
                )
                return response
            
            # Code has errors, ask LLM to fix
            self.logger.log_agent_action(
                self.agent_id,
                f"Syntax error detected (attempt {attempt + 1}/{self.max_retries})",
                syntax_error
            )
            
            self.error_fix_count += 1
            
            # Create fix prompt
            fix_prompt = (
                f"The following Python code has a syntax error:\n\n"
                f"```python\n{code}\n```\n\n"
                f"Error: {syntax_error}\n\n"
                f"Please fix the syntax error and provide the corrected code."
            )
            
            # Get fixed code
            response = super().get_response(fix_prompt)
            
            if response is None:
                return None
            
            code = self._extract_python_code(response)
            
            if not code:
                break
        
        # Return final response (valid or not)
        return response
    
    def _extract_python_code(self, text):
        """Extract Python code from markdown code block.
        
        Args:
            text: Response text that may contain code
            
        Returns:
            str: Extracted Python code or empty string
        """
        pattern = r"```python\n(.*?)```"
        match = re.search(pattern, text, re.DOTALL)
        
        if match:
            return match.group(1).strip()
        
        # Try without language specifier
        pattern = r"```\n(.*?)```"
        match = re.search(pattern, text, re.DOTALL)
        
        if match:
            code = match.group(1).strip()
            # Check if it looks like Python
            if 'def ' in code or 'import ' in code or 'print(' in code:
                return code
        
        return ""
    
    def _check_syntax(self, code):
        """Check Python code syntax.
        
        Args:
            code: Python code to validate
            
        Returns:
            str: Error message if invalid, None if valid
        """
        self.syntax_check_count += 1
        
        try:
            # Write code to temporary file
            with open('/tmp/temp_python_check.py', 'w') as f:
                f.write(code)
            
            # Run Python syntax check
            result = subprocess.run(
                ['python3', '-m', 'py_compile', '/tmp/temp_python_check.py'],
                capture_output=True,
                text=True,
                timeout=10
            )
            
            if result.returncode != 0:
                # Syntax error found
                return result.stderr.strip()
            
            # Code is valid
            return None
            
        except subprocess.TimeoutExpired:
            return "Syntax check timeout"
        except Exception as e:
            return f"Syntax check error: {str(e)}"
    
    def get_stats(self):
        """Get agent statistics.
        
        Returns:
            dict: Statistics about agent operations
        """
        return {
            'syntax_checks': self.syntax_check_count,
            'error_fixes': self.error_fix_count,
            'total_messages': len(self.messages)
        }


# Example usage
if __name__ == "__main__":
    # Create the agent
    agent = AgentPython(
        server_address="http://localhost:11434",
        model_name="deepseek-r1:70b",
        my_role="You are a Python programmer. Write clean, syntactically correct Python code.",
        max_retries=3
    )
    
    # Get Python code
    prompt = "Write a Python function to calculate factorial using recursion"
    response = agent.get_response(prompt)
    
    print("Response:")
    print(response)
    print("\nStats:")
    print(agent.get_stats())
    
    # Save conversation
    agent.save_to_excel("python_agent_conversation.xlsx")
```

## Advanced Patterns

### Pattern 1: Multi-Step Processing

```python
class AgentMultiStep(agent.AgentAI):
    """Agent with multi-step processing pipeline."""
    
    def get_response(self, prompt):
        # Step 1: Analyze
        analysis = super().get_response(f"Analyze this task: {prompt}")
        
        # Step 2: Design
        design = super().get_response(f"Based on this analysis: {analysis}, create a design")
        
        # Step 3: Implement
        implementation = super().get_response(f"Implement this design: {design}")
        
        return implementation
```

### Pattern 2: External Tool Integration

```python
class AgentWithTool(agent.AgentAI):
    """Agent that integrates external tools."""
    
    def get_response(self, prompt):
        # Get code from LLM
        response = super().get_response(prompt)
        
        # Extract code
        code = self._extract_code(response)
        
        # Run external tool (linter, formatter, etc.)
        tool_result = self._run_external_tool(code)
        
        # Return combined result
        return f"{response}\n\nTool Output:\n{tool_result}"
    
    def _run_external_tool(self, code):
        # Your tool integration logic
        return "Tool result"
```

### Pattern 3: State Management

```python
class AgentStateful(agent.AgentAI):
    """Agent with persistent state across interactions."""
    
    def __init__(self, server_address, model_name, my_role, max_tokens=16000, api_key=""):
        super().__init__(server_address, model_name, my_role, max_tokens, api_key)
        
        # State management
        self.state = {
            'mode': 'design',
            'context': {},
            'history': []
        }
    
    def get_response(self, prompt):
        # Use state in prompt
        contextualized_prompt = f"[Mode: {self.state['mode']}] {prompt}"
        
        # Get response
        response = super().get_response(contextualized_prompt)
        
        # Update state
        self.state['history'].append({
            'prompt': prompt,
            'response': response
        })
        
        return response
    
    def set_mode(self, mode):
        """Change agent mode."""
        self.state['mode'] = mode
        self.logger.log_agent_action(self.agent_id, f"Mode changed to: {mode}")
```

### Pattern 4: Delegating to Sub-Agents

```python
class AgentDelegator(agent.AgentAI):
    """Agent that delegates work to specialized sub-agents."""
    
    def __init__(self, server_address, model_name, my_role, max_tokens=16000, api_key=""):
        super().__init__(server_address, model_name, my_role, max_tokens, api_key)
        
        # Create sub-agents
        from agentCompiler import AgentCompiler
        self.compiler = AgentCompiler(server_address, model_name, trials=3)
    
    def get_response(self, prompt):
        # Get code from main LLM
        response = super().get_response(prompt)
        
        # Delegate compilation to sub-agent
        compiled_code = self.compiler.get_response(response)
        
        return compiled_code
```

## Best Practices

### 1. Always Call Parent Constructor

```python
# ✓ CORRECT
def __init__(self, server_address, model_name, my_role, max_tokens=16000, api_key=""):
    super().__init__(server_address, model_name, my_role, max_tokens, api_key)
    # Your code...

# ✗ WRONG - Missing super().__init__()
def __init__(self, server_address, model_name, my_role):
    self.my_attribute = "value"  # Parent not initialized!
```

### 2. Use Logging

```python
# Log important actions
self.logger.log_agent_action(self.agent_id, "Action description", "Details")

# Log exceptions
try:
    # Your code
    pass
except Exception as e:
    self.logger.log_exception(self.agent_id, e, "Context")
    raise
```

### 3. Handle Errors Gracefully

```python
def get_response(self, prompt):
    try:
        response = super().get_response(prompt)
        
        if response is None:
            self.logger.log_agent_action(self.agent_id, "Got None response")
            return None
        
        # Process response
        return self._process(response)
        
    except Exception as e:
        self.logger.log_exception(self.agent_id, e, "get_response")
        return None
```

### 4. Keep Methods Focused

```python
# ✓ GOOD - Single responsibility
def _extract_code(self, text):
    """Extract code from markdown."""
    return self._apply_regex(text, r"```.*?```")

def _validate_code(self, code):
    """Validate extracted code."""
    return len(code) > 0

# ✗ BAD - Doing too much
def _process(self, text):
    """Extract and validate and format code."""
    # Too many responsibilities!
```

### 5. Document Your Code

```python
class AgentExample(agent.AgentAI):
    """One-line description.
    
    Detailed description of what this agent does,
    its use cases, and any important notes.
    """
    
    def custom_method(self, param1, param2):
        """Short description.
        
        Args:
            param1: Description of param1
            param2: Description of param2
            
        Returns:
            Description of return value
            
        Raises:
            ExceptionType: When this exception occurs
        """
        pass
```

### 6. Use Private Methods for Internal Logic

```python
class AgentExample(agent.AgentAI):
    # Public interface
    def get_response(self, prompt):
        """Public method."""
        return self._internal_process(prompt)
    
    # Private implementation
    def _internal_process(self, prompt):
        """Private method - starts with underscore."""
        return prompt
    
    def _another_helper(self):
        """Another private helper."""
        pass
```

## Testing Your Agent

### Unit Test Example

```python
# test/test_agentYourName.py
import unittest
from unittest.mock import Mock, patch, MagicMock
from agentYourName import AgentYourName

class TestAgentYourName(unittest.TestCase):
    
    def setUp(self):
        """Set up test fixtures."""
        self.server = "http://localhost:11434"
        self.model = "test-model"
        self.role = "You are a test agent"
    
    @patch('agent.completion')
    def test_initialization(self, mock_completion):
        """Test agent initializes correctly."""
        agent = AgentYourName(
            server_address=self.server,
            model_name=self.model,
            my_role=self.role
        )
        
        self.assertEqual(agent.server_address, self.server)
        self.assertEqual(agent.model_name, self.model)
        self.assertIsNotNone(agent.agent_id)
    
    @patch('agent.completion')
    def test_get_response(self, mock_completion):
        """Test get_response method."""
        # Setup mock
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = "Test response"
        mock_completion.return_value = mock_response
        
        # Create agent
        agent = AgentYourName(
            server_address=self.server,
            model_name=self.model,
            my_role=self.role
        )
        
        # Test
        response = agent.get_response("Test prompt")
        
        self.assertIsNotNone(response)
        self.assertIn("Test response", response)
    
    @patch('agent.completion')
    def test_custom_method(self, mock_completion):
        """Test custom method."""
        agent = AgentYourName(
            server_address=self.server,
            model_name=self.model,
            my_role=self.role
        )
        
        result = agent.custom_method("test")
        
        self.assertEqual(result, "expected_value")

if __name__ == "__main__":
    unittest.main()
```

### Run Tests

```bash
python -m unittest test.test_agentYourName -v
```

## Integration Guide

### Using Your Custom Agent in Scripts

```python
# my_script.py
from agentYourName import AgentYourName
from agent import AgentAI

# Create your custom agent
my_agent = AgentYourName(
    server_address="http://localhost:11434",
    model_name="deepseek-r1:70b",
    my_role="Your role description"
)

# Create a regular agent
other_agent = AgentAI(
    server_address="http://localhost:11434",
    model_name="deepseek-r1:70b",
    my_role="Another role"
)

# Have them talk
response1 = my_agent.get_response("Hello!")
response2 = other_agent.get_response(f"Someone said: {response1}")

# Save conversation
my_agent.save_to_excel("conversation.xlsx")
```

### Command-Line Interface

```python
# main_your_agent.py
#!/usr/bin/env python3
import argparse
from agentYourName import AgentYourName
from logger import get_logger

def main():
    parser = argparse.ArgumentParser(description="Run your custom agent")
    parser.add_argument("--prompt", type=str, required=True)
    parser.add_argument("--log", action="store_true")
    args = parser.parse_args()
    
    if args.log:
        logger = get_logger()
        logger.enable("execution.log")
    
    agent = AgentYourName(
        server_address="http://localhost:11434",
        model_name="deepseek-r1:70b",
        my_role="Your role"
    )
    
    response = agent.get_response(args.prompt)
    print(response)
    
    agent.save_to_excel("output.xlsx")

if __name__ == "__main__":
    main()
```

Usage:
```bash
python main_your_agent.py --prompt "Your task" --log
```

## Summary

Creating custom agents involves:

1. **Subclass AgentAI** - Inherit base functionality
2. **Call super().__init__()** - Initialize parent class first
3. **Override methods** - Add custom behavior (especially `get_response`)
4. **Add new methods** - Extend functionality
5. **Use logging** - Track agent behavior
6. **Handle errors** - Graceful degradation
7. **Test thoroughly** - Unit tests with mocks
8. **Document well** - Docstrings and comments

## Additional Resources

- [AgentAI source code](../agent.py) - Base class implementation
- [AgentAIC source code](../agentC.py) - Example of subclassing
- [AgentCompiler source code](../agentCompiler.py) - Advanced example
- [User Guide](../README_UserGuide.md) - Using existing agents
- [Examples](../examples/) - Working examples
- [Test examples](../test/) - Test patterns

## Need Help?

- Review existing agent implementations in the repository
- Check the test files for usage examples
- Open an issue on GitHub
- Refer to the User Guide for general concepts

Happy agent building! 🤖
