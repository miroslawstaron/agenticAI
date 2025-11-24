"""Tests for the AgentDiagram class."""
import unittest
import os
import sys
import tempfile
import json
from unittest.mock import Mock, patch, MagicMock
import pandas as pd

# Add parent directory to path to import agent module
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from agentDiagram import AgentDiagram


class TestAgentDiagram(unittest.TestCase):
    """Test cases for the AgentDiagram class."""

    def setUp(self):
        """Set up test fixtures."""
        self.server_address = "http://localhost:11434"
        self.model_name = "test-model"
        self.agent = AgentDiagram(
            server_address=self.server_address,
            model_name=self.model_name
        )

    def test_initialization_default(self):
        """Test agent initialization with default diagram type."""
        self.assertEqual(self.agent.server_address, self.server_address)
        self.assertEqual(self.agent.model_name, self.model_name)
        self.assertEqual(self.agent.diagram_type, "class")
        self.assertEqual(self.agent.url, f'{self.server_address}')
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

    @patch('agentDiagram.requests.post')
    def test_get_response_class_diagram(self, mock_post):
        """Test generating a class diagram."""
        # Mock successful API response with Mermaid diagram
        mermaid_diagram = """```mermaid
classDiagram
    class MyClass {
        +int attribute
        +method()
    }
```"""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.text = json.dumps({
            'choices': [{
                'message': {
                    'content': mermaid_diagram
                }
            }]
        })
        mock_post.return_value = mock_response

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

    @patch('agentDiagram.requests.post')
    def test_get_response_flowchart(self, mock_post):
        """Test generating a flowchart diagram."""
        agent = AgentDiagram(
            server_address=self.server_address,
            model_name=self.model_name,
            diagram_type="flowchart"
        )
        
        # Mock successful API response
        mermaid_diagram = """```mermaid
flowchart TD
    Start --> Process
    Process --> End
```"""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.text = json.dumps({
            'choices': [{
                'message': {
                    'content': mermaid_diagram
                }
            }]
        })
        mock_post.return_value = mock_response

        source_code = "int main() { return 0; }"
        response = agent.get_response(source_code)

        # Verify response
        self.assertEqual(response, mermaid_diagram)
        self.assertIn('flowchart', agent.messages[1]['content'])

    @patch('agentDiagram.requests.post')
    def test_get_response_error(self, mock_post):
        """Test error response from the model."""
        # Mock error response
        mock_response = Mock()
        mock_response.status_code = 500
        mock_response.text = "Internal Server Error"
        mock_post.return_value = mock_response

        source_code = "int main() { return 0; }"
        response = self.agent.get_response(source_code)

        # Verify error handling
        self.assertIsNone(response)

    @patch('agentDiagram.requests.post')
    def test_get_response_timeout_retry(self, mock_post):
        """Test timeout with retry mechanism."""
        # Mock timeout on first two attempts, success on third
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.text = json.dumps({
            'choices': [{
                'message': {
                    'content': '```mermaid\nclassDiagram\n```'
                }
            }]
        })
        
        mock_post.side_effect = [
            requests.exceptions.Timeout(),
            requests.exceptions.Timeout(),
            mock_response
        ]

        source_code = "int main() { return 0; }"
        response = self.agent.get_response(source_code)

        # Verify retry worked
        self.assertIsNotNone(response)
        self.assertEqual(mock_post.call_count, 3)

    @patch('agentDiagram.requests.post')
    def test_get_response_max_retries_exceeded(self, mock_post):
        """Test max retries exceeded."""
        # Mock timeout on all attempts
        mock_post.side_effect = requests.exceptions.Timeout()

        source_code = "int main() { return 0; }"
        response = self.agent.get_response(source_code)

        # Verify max retries reached
        self.assertIsNone(response)
        self.assertEqual(mock_post.call_count, 3)

    @patch('agentDiagram.requests.post')
    def test_get_response_with_api_key(self, mock_post):
        """Test response with API key in headers."""
        api_key = "test-key-123"
        agent = AgentDiagram(
            server_address=self.server_address,
            model_name=self.model_name,
            api_key=api_key
        )
        
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.text = json.dumps({
            'choices': [{
                'message': {
                    'content': '```mermaid\nclassDiagram\n```'
                }
            }]
        })
        mock_post.return_value = mock_response

        agent.get_response("int main() { return 0; }")

        # Verify Authorization header was included
        call_args = mock_post.call_args
        headers = call_args[1]['headers']
        self.assertIn('Authorization', headers)
        self.assertEqual(headers['Authorization'], f'Bearer {api_key}')

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


# Required to avoid import errors with requests
import requests


if __name__ == '__main__':
    unittest.main()
