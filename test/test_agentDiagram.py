"""Tests for the AgentDiagram class."""
import unittest
import os
import sys
import tempfile
import json
from unittest.mock import Mock, patch, MagicMock
import pandas as pd
import requests

# Add parent directory to path to import agent module
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from agentDiagram import AgentDiagram


class TestAgentDiagram(unittest.TestCase):
    """Test cases for the AgentDiagram class."""

    def setUp(self):
        """Set up test fixtures."""
        self.server_address = "http://localhost:11434"
        self.model_name = "qwen2.5-coder:latest"
        self.agent = AgentDiagram(
            server_address=self.server_address,
            model_name=self.model_name
        )

    def test_initialization_default(self):
        """Test agent initialization with default diagram type."""
        self.assertEqual(self.agent.server_address, self.server_address)
        self.assertEqual(self.agent.model_name, self.model_name)
        self.assertEqual(self.agent.diagram_type, "class")
        self.assertEqual(len(self.agent.messages), 1)
        self.assertEqual(self.agent.messages[0]['role'], 'system')
        self.assertIn('class diagram', self.agent.messages[0]['content'])

    def test_initialization_with_diagram_type(self):
        """Test agent initialization with specific diagram type."""
        agent = AgentDiagram(
            server_address=self.server_address,
            model_name=self.model_name,
            diagram_type="flowchart"
        )
        self.assertEqual(agent.diagram_type, "flowchart")
        self.assertIn('flowchart', agent.messages[0]['content'])

    def test_initialization_with_api_key(self):
        """Test agent initialization with API key."""
        api_key = "test-api-key-123"
        agent = AgentDiagram(
            server_address=self.server_address,
            model_name=self.model_name,
            api_key=api_key
        )
        self.assertEqual(agent.api_key, api_key)

    def test_initialization_with_max_tokens(self):
        """Test agent initialization with custom max_tokens."""
        max_tokens = 8000
        agent = AgentDiagram(
            server_address=self.server_address,
            model_name=self.model_name,
            max_tokens=max_tokens
        )
        self.assertEqual(agent.max_tokens, max_tokens)

    def test_initialization_sequence_diagram(self):
        """Test initialization with sequence diagram type."""
        agent = AgentDiagram(
            server_address=self.server_address,
            model_name=self.model_name,
            diagram_type="sequence"
        )
        self.assertEqual(agent.diagram_type, "sequence")
        self.assertIn('sequence diagram', agent.messages[0]['content'])

    def test_initialization_er_diagram(self):
        """Test initialization with entity-relationship diagram type."""
        agent = AgentDiagram(
            server_address=self.server_address,
            model_name=self.model_name,
            diagram_type="er"
        )
        self.assertEqual(agent.diagram_type, "er")
        self.assertIn('entity-relationship diagram', agent.messages[0]['content'])

    @patch('agentDiagram.completion')
    def test_get_response_class_diagram(self, mock_completion):
        """Test generating a class diagram."""
        # Mock LiteLLM response with Mermaid diagram
        mermaid_diagram = """```mermaid
classDiagram
    class MyClass {
        +int attribute
        +method()
    }
```"""
        mock_response = Mock()
        mock_response.choices = [Mock()]
        mock_response.choices[0].message = Mock()
        mock_response.choices[0].message.content = mermaid_diagram
        mock_completion.return_value = mock_response

        source_code = """
class MyClass {
    int attribute;
    void method() {}
};
"""
        response = self.agent.get_response(source_code)

        # Verify response
        self.assertEqual(response, mermaid_diagram)
        self.assertEqual(len(self.agent.messages), 3)  # system, user, assistant
        self.assertIn('class diagram', self.agent.messages[1]['content'])

    @patch('agentDiagram.completion')
    def test_get_response_flowchart(self, mock_completion):
        """Test generating a flowchart diagram."""
        agent = AgentDiagram(
            server_address=self.server_address,
            model_name=self.model_name,
            diagram_type="flowchart"
        )
        
        # Mock LiteLLM response
        mermaid_diagram = """```mermaid
flowchart TD
    Start --> Process
    Process --> End
```"""
        mock_response = Mock()
        mock_response.choices = [Mock()]
        mock_response.choices[0].message = Mock()
        mock_response.choices[0].message.content = mermaid_diagram
        mock_completion.return_value = mock_response

        source_code = "int main() { return 0; }"
        response = agent.get_response(source_code)

        # Verify response
        self.assertEqual(response, mermaid_diagram)
        self.assertIn('flowchart', agent.messages[1]['content'])

    @patch('agentDiagram.completion')
    def test_get_response_error(self, mock_completion):
        """Test error response from the model."""
        # Mock error from LiteLLM
        mock_completion.side_effect = Exception("API Error")

        source_code = "int main() { return 0; }"
        response = self.agent.get_response(source_code)

        # Verify error handling
        self.assertIsNone(response)

    @patch('agentDiagram.completion')
    def test_get_response_timeout_retry(self, mock_completion):
        """Test timeout with retry mechanism."""
        # Mock timeout on first two attempts, success on third
        mock_response = Mock()
        mock_response.choices = [Mock()]
        mock_response.choices[0].message = Mock()
        mock_response.choices[0].message.content = '```mermaid\nclassDiagram\n```'
        
        mock_completion.side_effect = [
            Exception("timeout error"),
            Exception("timeout error"),
            mock_response
        ]

        source_code = "int main() { return 0; }"
        response = self.agent.get_response(source_code)

        # Verify retry worked
        self.assertIsNotNone(response)
        self.assertEqual(mock_completion.call_count, 3)

    @patch('agentDiagram.completion')
    def test_get_response_max_retries_exceeded(self, mock_completion):
        """Test max retries exceeded."""
        # Mock timeout on all attempts
        mock_completion.side_effect = Exception("timeout error")

        source_code = "int main() { return 0; }"
        response = self.agent.get_response(source_code)

        # Verify max retries reached
        self.assertIsNone(response)
        self.assertEqual(mock_completion.call_count, 3)

    @patch('agentDiagram.completion')
    def test_get_response_with_api_key(self, mock_completion):
        """Test response with API key in headers."""
        api_key = "test-key-123"
        agent = AgentDiagram(
            server_address=self.server_address,
            model_name=self.model_name,
            api_key=api_key
        )
        
        mock_response = Mock()
        mock_response.choices = [Mock()]
        mock_response.choices[0].message = Mock()
        mock_response.choices[0].message.content = '```mermaid\nclassDiagram\n```'
        mock_completion.return_value = mock_response

        agent.get_response("int main() { return 0; }")

        # Verify completion was called
        mock_completion.assert_called_once()

    def test_extract_mermaid_diagram_with_code_block(self):
        """Test extracting Mermaid diagram from code block."""
        response = """```mermaid
classDiagram
    class MyClass
```"""
        extracted = self.agent.extract_mermaid_diagram(response)
        self.assertEqual(extracted, "classDiagram\n    class MyClass")

    def test_extract_mermaid_diagram_without_code_block(self):
        """Test extracting when no code block present."""
        response = "classDiagram\n    class MyClass"
        extracted = self.agent.extract_mermaid_diagram(response)
        self.assertEqual(extracted, response)

    def test_extract_mermaid_diagram_empty(self):
        """Test extracting from empty response."""
        extracted = self.agent.extract_mermaid_diagram("")
        self.assertEqual(extracted, "")

    def test_extract_mermaid_diagram_none(self):
        """Test extracting from None response."""
        extracted = self.agent.extract_mermaid_diagram(None)
        self.assertEqual(extracted, "")

    def test_set_diagram_type_valid(self):
        """Test changing diagram type to valid type."""
        self.agent.set_diagram_type("flowchart")
        self.assertEqual(self.agent.diagram_type, "flowchart")
        self.assertIn('flowchart', self.agent.messages[0]['content'])

    def test_set_diagram_type_sequence(self):
        """Test changing diagram type to sequence."""
        self.agent.set_diagram_type("sequence")
        self.assertEqual(self.agent.diagram_type, "sequence")
        self.assertIn('sequence diagram', self.agent.messages[0]['content'])

    def test_set_diagram_type_er(self):
        """Test changing diagram type to entity-relationship."""
        self.agent.set_diagram_type("er")
        self.assertEqual(self.agent.diagram_type, "er")
        self.assertIn('entity-relationship diagram', self.agent.messages[0]['content'])

    def test_set_diagram_type_invalid(self):
        """Test changing diagram type to invalid type."""
        with self.assertRaises(ValueError) as context:
            self.agent.set_diagram_type("invalid")
        self.assertIn("Invalid diagram type", str(context.exception))

    def test_save_to_excel(self):
        """Test saving messages to Excel file."""
        # Add some messages to the agent
        self.agent.messages.append({"role": "user", "content": "Test code"})
        self.agent.messages.append({"role": "assistant", "content": "Test diagram"})

        # Save to a temporary file
        with tempfile.NamedTemporaryFile(suffix='.xlsx', delete=False) as tmp_file:
            tmp_filename = tmp_file.name

        try:
            self.agent.save_to_excel(tmp_filename)
            
            # Verify file was created and contains data
            self.assertTrue(os.path.exists(tmp_filename))
            df = pd.read_excel(tmp_filename)
            self.assertEqual(len(df), 3)  # system + user + assistant
            self.assertEqual(df.iloc[1]['role'], 'user')
            self.assertEqual(df.iloc[2]['role'], 'assistant')
        finally:
            # Clean up
            if os.path.exists(tmp_filename):
                os.remove(tmp_filename)

    def test_save_to_csv(self):
        """Test saving messages to CSV file."""
        # Add some messages to the agent
        self.agent.messages.append({"role": "user", "content": "Test code"})
        self.agent.messages.append({"role": "assistant", "content": "Test diagram"})

        # Save to a temporary file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False) as tmp_file:
            tmp_filename = tmp_file.name

        try:
            self.agent.save_to_csv(tmp_filename)
            
            # Verify file was created and contains data
            self.assertTrue(os.path.exists(tmp_filename))
            with open(tmp_filename, 'r') as f:
                content = f.read()
                self.assertIn('role$content', content)
                self.assertIn('system$', content)
                self.assertIn('user$', content)
                self.assertIn('assistant$', content)
        finally:
            # Clean up
            if os.path.exists(tmp_filename):
                os.remove(tmp_filename)


    @patch('subprocess.run')
    def test_validate_mermaid_diagram_valid(self, mock_run):
        """Test validation of a valid mermaid diagram."""
        # Mock successful validation
        mock_run.return_value = MagicMock(returncode=0, stderr='', stdout='')
        
        mermaid_content = """
        classDiagram
            class Animal {
                +String name
                +makeSound()
            }
        """
        
        is_valid, error_msg = self.agent.validate_mermaid_diagram(mermaid_content)
        
        self.assertTrue(is_valid)
        self.assertIsNone(error_msg)
        self.assertTrue(mock_run.called)

    @patch('subprocess.run')
    def test_validate_mermaid_diagram_invalid(self, mock_run):
        """Test validation of an invalid mermaid diagram."""
        # Mock failed validation
        mock_run.return_value = MagicMock(
            returncode=1, 
            stderr='Error: Parse error on line 2',
            stdout=''
        )
        
        mermaid_content = """
        classDiagram
            invalid syntax here
        """
        
        is_valid, error_msg = self.agent.validate_mermaid_diagram(mermaid_content)
        
        self.assertFalse(is_valid)
        self.assertIsNotNone(error_msg)
        self.assertIn('Error', error_msg)

    @patch('subprocess.run')
    def test_validate_mermaid_diagram_tool_not_found(self, mock_run):
        """Test validation when mmdc tool is not installed."""
        # Mock FileNotFoundError
        mock_run.side_effect = FileNotFoundError()
        
        mermaid_content = "classDiagram\n    class Test"
        
        is_valid, error_msg = self.agent.validate_mermaid_diagram(mermaid_content)
        
        # Should return valid when tool is not available
        self.assertTrue(is_valid)
        self.assertIsNone(error_msg)

    @patch('agentDiagram.AgentDiagram.validate_mermaid_diagram')
    @patch('agentDiagram.completion')
    def test_get_response_with_validation_success(self, mock_completion, mock_validate):
        """Test get_response with validation enabled and valid diagram."""
        # Mock LiteLLM response
        mock_response = Mock()
        mock_response.choices = [Mock()]
        mock_response.choices[0].message = Mock()
        mock_response.choices[0].message.content = "```mermaid\nclassDiagram\n    class Test\n```"
        mock_completion.return_value = mock_response
        
        # Mock successful validation
        mock_validate.return_value = (True, None)
        
        response = self.agent.get_response("class Test {}", validate=True)
        
        self.assertIsNotNone(response)
        self.assertIn('classDiagram', response)
        mock_validate.assert_called_once()

    @patch('agentDiagram.AgentDiagram.validate_mermaid_diagram')
    @patch('agentDiagram.completion')
    def test_get_response_with_validation_and_fix(self, mock_completion, mock_validate):
        """Test get_response with validation that requires fixes."""
        # First response - invalid diagram
        first_response = Mock()
        first_response.choices = [Mock()]
        first_response.choices[0].message = Mock()
        first_response.choices[0].message.content = "```mermaid\nclassDiagram\n    invalid syntax\n```"
        
        # Second response - valid diagram after fix
        second_response = Mock()
        second_response.choices = [Mock()]
        second_response.choices[0].message = Mock()
        second_response.choices[0].message.content = "```mermaid\nclassDiagram\n    class Test\n```"
        
        mock_completion.side_effect = [first_response, second_response]
        
        # First validation fails, second succeeds
        mock_validate.side_effect = [
            (False, "Parse error on line 2"),
            (True, None)
        ]
        
        response = self.agent.get_response("class Test {}", validate=True, max_fix_attempts=5)
        
        self.assertIsNotNone(response)
        self.assertEqual(mock_validate.call_count, 2)
        self.assertEqual(mock_completion.call_count, 2)

    @patch('agentDiagram.AgentDiagram.validate_mermaid_diagram')
    @patch('agentDiagram.completion')
    def test_get_response_with_validation_max_attempts(self, mock_completion, mock_validate):
        """Test get_response when max fix attempts is reached."""
        # Mock response with invalid diagram
        mock_response = Mock()
        mock_response.choices = [Mock()]
        mock_response.choices[0].message = Mock()
        mock_response.choices[0].message.content = "```mermaid\\nclassDiagram\\n    invalid syntax\\n```"
        mock_completion.return_value = mock_response
        
        # All validations fail
        mock_validate.return_value = (False, "Parse error")
        
        max_attempts = 2
        response = self.agent.get_response("class Test {}", validate=True, max_fix_attempts=max_attempts)
        
        self.assertIsNotNone(response)
        # Should validate initial + max_attempts (2) = 3 total
        self.assertEqual(mock_validate.call_count, max_attempts + 1)


if __name__ == '__main__':
    unittest.main()
