"""Tests for the AgentCompiler class."""
import unittest
import os
import sys
import tempfile
import json
from unittest.mock import Mock, patch, MagicMock
import subprocess

# Add parent directory to path to import modules
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from agentCompiler import AgentCompiler


class TestAgentCompiler(unittest.TestCase):
    """Test cases for the AgentCompiler class."""

    def setUp(self):
        """Set up test fixtures."""
        self.server_address = "http://localhost:11434"
        self.model_name = "test-model"
        self.trials = 3
        self.agent = AgentCompiler(
            server_address=self.server_address,
            model_name=self.model_name,
            trials=self.trials
        )

    def test_initialization(self):
        """Test agent initialization."""
        self.assertEqual(self.agent.server_address, self.server_address)
        self.assertEqual(self.agent.model_name, self.model_name)
        self.assertEqual(self.agent._AgentCompiler__trials, self.trials)

    @patch('agentCompiler.subprocess.run')
    def test_compile_code_success(self, mock_run):
        """Test successful code compilation."""
        # Create temp directory if it doesn't exist
        os.makedirs('./temp', exist_ok=True)

        # Mock successful compilation
        mock_result = Mock()
        mock_result.stderr = b''
        mock_result.stdout = b''
        mock_run.return_value = mock_result

        # NOTE: Setting __code directly is necessary because the original code at
        # agentCompiler.py:166 checks `if self.__code != ""` before attempting
        # compilation. We need to set this to ensure the code path is tested.
        # Since we cannot modify agent code per requirements, we must set this
        # private attribute.
        self.agent._AgentCompiler__code = "#include <stdio.h>\nint main() { return 0; }"
        
        code = "#include <stdio.h>\nint main() { return 0; }"
        result = self.agent._AgentCompiler__compile_code(code)

        self.assertEqual(result, "Compilation successful")

    @patch('agentCompiler.subprocess.run')
    def test_compile_code_error(self, mock_run):
        """Test code compilation with errors."""
        # Create temp directory if it doesn't exist
        os.makedirs('./temp', exist_ok=True)

        # Mock compilation error
        mock_result = Mock()
        mock_result.stderr = b'error: expected ;\n'
        mock_result.stdout = b''
        mock_run.return_value = mock_result

        # NOTE: Setting __code directly (see test_compile_code_success for explanation)
        self.agent._AgentCompiler__code = "int main() { return 0 }"  # Missing semicolon
        
        code = "int main() { return 0 }"  # Missing semicolon
        result = self.agent._AgentCompiler__compile_code(code)

        self.assertIn("Compilation error", result)
        self.assertIn("error", result)

    @patch('agentCompiler.subprocess.run')
    def test_compile_code_no_code(self, mock_run):
        """Test compilation with no code."""
        result = self.agent._AgentCompiler__compile_code("")

        self.assertEqual(result, "No code found")
        mock_run.assert_not_called()

    def test_extract_c_code(self):
        """Test C code extraction from markdown."""
        # Test with code block
        markdown = "```c\nint main() {\n    return 0;\n}\n```"
        code = self.agent._AgentCompiler__extract_c_code(markdown)
        self.assertIn('int main()', code)
        self.assertIn('return 0;', code)

        # Test without code block
        markdown = "Just plain text"
        code = self.agent._AgentCompiler__extract_c_code(markdown)
        self.assertEqual(code, "")

        # Test with invalid pattern
        markdown = "```python\nprint('hello')\n```"
        code = self.agent._AgentCompiler__extract_c_code(markdown)
        self.assertEqual(code, "")

    def test_get_code(self):
        """Test getting code from markdown block."""
        markdown = "```c\n#include <stdio.h>\nint main() {\n    return 0;\n}\n```"
        code = self.agent._AgentCompiler__get_code(markdown)
        
        self.assertIn('#include <stdio.h>', code)
        self.assertIn('int main()', code)

    @patch('agentCompiler.subprocess.run')
    def test_get_response_with_successful_compilation(self, mock_run):
        """Test get_response with code that compiles successfully."""
        # Create temp directory if it doesn't exist
        os.makedirs('./temp', exist_ok=True)

        # Mock successful compilation
        mock_result = Mock()
        mock_result.stderr = b''
        mock_run.return_value = mock_result

        code = "```c\n#include <stdio.h>\nint main() { return 0; }\n```"
        result = self.agent.get_response(code)

        self.assertIn('main', result)
        self.assertIn('return 0', result)

    @patch('agentCompiler.requests.post')
    @patch('agentCompiler.subprocess.run')
    def test_get_response_with_compilation_error_and_fix(self, mock_run, mock_post):
        """Test get_response with code that fails then gets fixed."""
        # Create temp directory if it doesn't exist
        os.makedirs('./temp', exist_ok=True)

        # First compilation fails, second succeeds
        mock_run.side_effect = [
            Mock(stderr=b'error: expected ;'),  # Initial compilation error
            Mock(stderr=b''),  # After fix: successful
        ]

        # Mock LLM response with fixed code
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.text = json.dumps({
            'choices': [{
                'message': {
                    'content': '```c\nint main() { return 0; }\n```'
                }
            }]
        })
        mock_post.return_value = mock_response

        # Code with error
        code = "```c\nint main() { return 0 }\n```"
        result = self.agent.get_response(code)

        # Should have attempted to fix
        self.assertIsNotNone(result)
        mock_post.assert_called()

    @patch('agentCompiler.requests.post')
    @patch('agentCompiler.subprocess.run')
    def test_get_response_exceeds_trials(self, mock_run, mock_post):
        """Test get_response when max trials are exceeded."""
        # Create temp directory if it doesn't exist
        os.makedirs('./temp', exist_ok=True)

        # All compilation attempts fail
        mock_run.return_value = Mock(stderr=b'error: syntax error')

        # Mock LLM responses
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.text = json.dumps({
            'choices': [{
                'message': {
                    'content': '```c\nint main() { return 0 }\n```'
                }
            }]
        })
        mock_post.return_value = mock_response

        code = "```c\nint main() { return 0 }\n```"
        result = self.agent.get_response(code)

        # Should return the last attempted code
        self.assertIsNotNone(result)
        # Should have made exactly 'trials' number of fix attempts
        self.assertEqual(mock_post.call_count, self.trials)

    @patch('agentCompiler.requests.post')
    def test_solve_problem(self, mock_post):
        """Test the problem solving mechanism."""
        # Mock LLM response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.text = json.dumps({
            'choices': [{
                'message': {
                    'content': 'Fixed code'
                }
            }]
        })
        mock_post.return_value = mock_response

        # Set up error state
        self.agent._AgentCompiler__code = "int main() { }"
        self.agent._AgentCompiler__compile_result = "error: something wrong"

        result = self.agent._AgentCompiler__solve_problem()

        self.assertEqual(result, 'Fixed code')
        mock_post.assert_called_once()

    @patch('agentCompiler.requests.post')
    def test_get_response_compilation_with_timeout(self, mock_post):
        """Test compilation response with timeout."""
        import requests
        mock_post.side_effect = requests.exceptions.Timeout()

        # Set up state
        self.agent._AgentCompiler__compile_messages = [
            {"role": "system", "content": "You are a C Programmer."}
        ]

        result = self.agent._AgentCompiler__get_response_compilation("Test prompt")

        self.assertIsNone(result)
        self.assertEqual(mock_post.call_count, 3)

    def test_get_response_plain_code(self):
        """Test get_response with plain code (no markdown)."""
        # Create temp directory if it doesn't exist
        os.makedirs('./temp', exist_ok=True)

        with patch('agentCompiler.subprocess.run') as mock_run:
            # Mock successful compilation
            mock_run.return_value = Mock(stderr=b'')

            code = "int main() { return 0; }"
            result = self.agent.get_response(code)

            self.assertIn('main', result)


if __name__ == '__main__':
    unittest.main()
