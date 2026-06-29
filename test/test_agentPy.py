"""Tests for the AgentAIPy class."""
import unittest
import os
import sys
import tempfile
import json
from unittest.mock import Mock, patch, MagicMock

# Add parent directory to path to import modules
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

from agentPy import AgentAIPy
from test_fixtures import BaseAgentTestCase


class TestAgentAIPy(BaseAgentTestCase):
    """Test cases for the AgentAIPy class."""

    def setUp(self):
        """Set up test fixtures."""
        self.server_address = "http://localhost:11434"
        self.model_name = "test-model"
        self.my_role = "You are a Python programmer"
        self.agent = AgentAIPy(
            server_address=self.server_address,
            model_name=self.model_name,
            my_role=self.my_role
        )

    def test_initialization(self):
        """Test agent initialization."""
        self.assertEqual(self.agent.server_address, self.server_address)
        self.assertEqual(self.agent.model_name, self.model_name)
        self.assertEqual(len(self.agent.messages), 1)
        self.assertEqual(self.agent.messages[0]['role'], 'system')
        self.assertEqual(self.agent.messages[0]['content'], self.my_role)

    def test_initialization_with_api_key(self):
        """Test agent initialization with API key."""
        api_key = "test-api-key-123"
        agent = AgentAIPy(
            server_address=self.server_address,
            model_name=self.model_name,
            my_role=self.my_role,
            api_key=api_key
        )
        self.assertEqual(agent.api_key, api_key)

    def test_initialization_with_max_tokens(self):
        """Test agent initialization with custom max_tokens."""
        max_tokens = 8000
        agent = AgentAIPy(
            server_address=self.server_address,
            model_name=self.model_name,
            my_role=self.my_role,
            max_tokens=max_tokens
        )
        self.assertEqual(agent.max_tokens, max_tokens)

    @patch('agentPy.AgentPyInterpreter')
    @patch('agentPy.completion')
    def test_get_response_success(self, mock_completion, mock_interpreter_class):
        """Test successful response with code execution."""
        # Mock interpreter
        mock_interpreter = Mock()
        mock_interpreter.get_response.return_value = 'print("Hello, World!")'
        mock_interpreter_class.return_value = mock_interpreter

        # Mock successful LiteLLM response
        mock_response = Mock()
        mock_response.choices = [Mock()]
        mock_response.choices[0].message = Mock()
        mock_response.choices[0].message.content = '```python\nprint("Hello, World!")\n```'
        mock_completion.return_value = mock_response

        prompt = "Write a simple Python program"
        response = self.agent.get_response(prompt)

        # Verify response
        self.assertIsNotNone(response)
        self.assertIn('print', response)
        
        # Verify interpreter was called
        mock_interpreter.get_response.assert_called_once()

        # Verify messages were added
        self.assertEqual(len(self.agent.messages), 3)
        self.assertEqual(self.agent.messages[1]['role'], 'user')
        self.assertEqual(self.agent.messages[2]['role'], 'assistant')

    @patch('agentPy.AgentPyInterpreter')
    @patch('agentPy.completion')
    def test_get_response_with_api_key(self, mock_completion, mock_interpreter_class):
        """Test response with API key in headers."""
        api_key = "test-api-key"
        agent = AgentAIPy(
            server_address=self.server_address,
            model_name=self.model_name,
            my_role=self.my_role,
            api_key=api_key
        )

        # Mock interpreter
        mock_interpreter = Mock()
        mock_interpreter.get_response.return_value = 'x = 5'
        mock_interpreter_class.return_value = mock_interpreter

        mock_response = Mock()
        mock_response.choices = [Mock()]
        mock_response.choices[0].message = Mock()
        mock_response.choices[0].message.content = 'x = 5'
        mock_completion.return_value = mock_response

        agent.get_response("Test")

        # Verify completion was called with correct parameters
        mock_completion.assert_called_once()
        call_kwargs = mock_completion.call_args[1]
        self.assertEqual(call_kwargs['model'], self.model_name)

    @patch('agentPy.AgentPyInterpreter')
    @patch('agentPy.completion')
    def test_get_response_error(self, mock_completion, mock_interpreter_class):
        """Test error response from the model."""
        # Mock an exception from LiteLLM
        mock_completion.side_effect = Exception("API Error")

        response = self.agent.get_response("Test prompt")

        self.assertIsNone(response)

    @patch('agentPy.AgentPyInterpreter')
    @patch('agentPy.completion')
    def test_get_response_timeout_retry(self, mock_completion, mock_interpreter_class):
        """Test timeout with retry mechanism."""
        # Mock interpreter
        mock_interpreter = Mock()
        mock_interpreter.get_response.return_value = 'x = 10'
        mock_interpreter_class.return_value = mock_interpreter

        # First two calls timeout, third succeeds
        mock_success = Mock()
        mock_success.choices = [Mock()]
        mock_success.choices[0].message = Mock()
        mock_success.choices[0].message.content = 'Success after retry'
        
        mock_completion.side_effect = [
            Exception("timeout"),
            Exception("timeout"),
            mock_success
        ]

        response = self.agent.get_response("Test")

        self.assertIsNotNone(response)
        self.assertEqual(mock_completion.call_count, 3)

    @patch('agentPy.AgentPyInterpreter')
    @patch('agentPy.completion')
    def test_get_response_max_retries_exceeded(self, mock_completion, mock_interpreter_class):
        """Test max retries exceeded."""
        mock_completion.side_effect = Exception("timeout")

        response = self.agent.get_response("Test")

        self.assertIsNone(response)
        self.assertEqual(mock_completion.call_count, 3)

    def test_extract_python_code(self):
        """Test Python code extraction from markdown."""
        # Test with code block
        markdown = "```python\ndef hello():\n    print('Hello')\n```"
        code = self.agent._AgentAIPy__extract_python_code(markdown)
        self.assertIn('def hello()', code)
        self.assertIn("print('Hello')", code)

        # Test without code block
        markdown = "Just plain text"
        code = self.agent._AgentAIPy__extract_python_code(markdown)
        self.assertEqual(code, "")

    def test_get_code(self):
        """Test getting code from markdown block."""
        markdown = "```python\nimport os\ndef main():\n    print('Test')\n    return 0\n```"
        code = self.agent._AgentAIPy__get_code(markdown)
        
        self.assertIn('import os', code)
        self.assertIn('def main()', code)
        self.assertIn('print', code)


if __name__ == '__main__':
    unittest.main()
