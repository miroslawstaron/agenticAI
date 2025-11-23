"""Tests for the AgentAIC class."""
import unittest
import os
import sys
import tempfile
import json
from unittest.mock import Mock, patch, MagicMock

# Add parent directory to path to import modules
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from agentC import AgentAIC


class TestAgentAIC(unittest.TestCase):
    """Test cases for the AgentAIC class."""

    def setUp(self):
        """Set up test fixtures."""
        self.server_address = "http://localhost:11434"
        self.model_name = "test-model"
        self.my_role = "You are a C programmer"
        self.agent = AgentAIC(
            server_address=self.server_address,
            model_name=self.model_name,
            my_role=self.my_role
        )

    def test_initialization(self):
        """Test agent initialization."""
        self.assertEqual(self.agent.server_address, self.server_address)
        self.assertEqual(self.agent.model_name, self.model_name)
        self.assertEqual(self.agent.url, f'{self.server_address}')
        self.assertEqual(len(self.agent.messages), 1)
        self.assertEqual(self.agent.messages[0]['role'], 'system')
        self.assertEqual(self.agent.messages[0]['content'], self.my_role)

    def test_initialization_with_api_key(self):
        """Test agent initialization with API key."""
        api_key = "test-api-key-123"
        agent = AgentAIC(
            server_address=self.server_address,
            model_name=self.model_name,
            my_role=self.my_role,
            api_key=api_key
        )
        self.assertEqual(agent.api_key, api_key)

    def test_initialization_with_max_tokens(self):
        """Test agent initialization with custom max_tokens."""
        max_tokens = 8000
        agent = AgentAIC(
            server_address=self.server_address,
            model_name=self.model_name,
            my_role=self.my_role,
            max_tokens=max_tokens
        )
        self.assertEqual(agent.max_tokens, max_tokens)

    @patch('agentC.AgentCompiler')
    @patch('agentC.requests.post')
    def test_get_response_success(self, mock_post, mock_compiler_class):
        """Test successful response with code compilation."""
        # Mock compiler
        mock_compiler = Mock()
        mock_compiler.get_response.return_value = '#include <stdio.h>\nint main() { return 0; }'
        mock_compiler_class.return_value = mock_compiler

        # Mock successful API response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.text = json.dumps({
            'choices': [{
                'message': {
                    'content': '```c\n#include <stdio.h>\nint main() { return 0; }\n```'
                }
            }]
        })
        mock_post.return_value = mock_response

        prompt = "Write a simple C program"
        response = self.agent.get_response(prompt)

        # Verify response
        self.assertIsNotNone(response)
        self.assertIn('main', response)
        
        # Verify compiler was called
        mock_compiler.get_response.assert_called_once()

        # Verify messages were added
        self.assertEqual(len(self.agent.messages), 3)
        self.assertEqual(self.agent.messages[1]['role'], 'user')
        self.assertEqual(self.agent.messages[2]['role'], 'assistant')

    @patch('agentC.AgentCompiler')
    @patch('agentC.requests.post')
    def test_get_response_with_api_key(self, mock_post, mock_compiler_class):
        """Test response with API key in headers."""
        api_key = "test-api-key"
        agent = AgentAIC(
            server_address=self.server_address,
            model_name=self.model_name,
            my_role=self.my_role,
            api_key=api_key
        )

        # Mock compiler
        mock_compiler = Mock()
        mock_compiler.get_response.return_value = 'int main() { return 0; }'
        mock_compiler_class.return_value = mock_compiler

        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.text = json.dumps({
            'choices': [{
                'message': {
                    'content': 'int main() { return 0; }'
                }
            }]
        })
        mock_post.return_value = mock_response

        agent.get_response("Test")

        # Verify Authorization header was set
        call_kwargs = mock_post.call_args[1]
        self.assertIn('headers', call_kwargs)
        self.assertEqual(call_kwargs['headers']['Authorization'], f'Bearer {api_key}')

    @patch('agentC.AgentCompiler')
    @patch('agentC.requests.post')
    def test_get_response_error(self, mock_post, mock_compiler_class):
        """Test error response from the model."""
        mock_response = Mock()
        mock_response.status_code = 500
        mock_response.text = "Internal Server Error"
        mock_post.return_value = mock_response

        response = self.agent.get_response("Test prompt")

        self.assertIsNone(response)

    @patch('agentC.AgentCompiler')
    @patch('agentC.requests.post')
    def test_get_response_timeout_retry(self, mock_post, mock_compiler_class):
        """Test timeout with retry mechanism."""
        import requests

        # Mock compiler
        mock_compiler = Mock()
        mock_compiler.get_response.return_value = 'int main() { return 0; }'
        mock_compiler_class.return_value = mock_compiler

        # First two calls timeout, third succeeds
        mock_post.side_effect = [
            requests.exceptions.Timeout(),
            requests.exceptions.Timeout(),
            Mock(status_code=200, text=json.dumps({
                'choices': [{'message': {'content': 'Success after retry'}}]
            }))
        ]

        response = self.agent.get_response("Test")

        self.assertIsNotNone(response)
        self.assertEqual(mock_post.call_count, 3)

    @patch('agentC.AgentCompiler')
    @patch('agentC.requests.post')
    def test_get_response_max_retries_exceeded(self, mock_post, mock_compiler_class):
        """Test max retries exceeded."""
        import requests
        mock_post.side_effect = requests.exceptions.Timeout()

        response = self.agent.get_response("Test")

        self.assertIsNone(response)
        self.assertEqual(mock_post.call_count, 3)

    def test_extract_c_code(self):
        """Test C code extraction from markdown."""
        # Test with code block
        markdown = "```c\nint main() {\n    return 0;\n}\n```"
        code = self.agent._AgentAIC__extract_c_code(markdown)
        self.assertIn('int main()', code)
        self.assertIn('return 0;', code)

        # Test without code block
        markdown = "Just plain text"
        code = self.agent._AgentAIC__extract_c_code(markdown)
        self.assertEqual(code, "")

    def test_get_code(self):
        """Test getting code from markdown block."""
        markdown = "```c\n#include <stdio.h>\nint main() {\n    printf(\"Hello\");\n    return 0;\n}\n```"
        code = self.agent._AgentAIC__get_code(markdown)
        
        self.assertIn('#include <stdio.h>', code)
        self.assertIn('int main()', code)
        self.assertIn('printf', code)


if __name__ == '__main__':
    unittest.main()
