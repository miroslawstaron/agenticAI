"""Tests for the AgentPyInterpreter class."""
import unittest
import os
import sys
import tempfile
import json
from unittest.mock import Mock, patch, MagicMock
import subprocess

# Add parent directory to path to import modules
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

from agentPyInterpreter import AgentPyInterpreter
from test_fixtures import BaseAgentTestCase


class TestAgentPyInterpreter(BaseAgentTestCase):
    """Test cases for the AgentPyInterpreter class."""

    def setUp(self):
        """Set up test fixtures."""
        self.server_address = "http://localhost:11434"
        self.model_name = "test-model"
        self.trials = 3
        self.agent = AgentPyInterpreter(
            server_address=self.server_address,
            model_name=self.model_name,
            trials=self.trials
        )

    def test_initialization(self):
        """Test agent initialization."""
        self.assertEqual(self.agent.server_address, self.server_address)
        self.assertEqual(self.agent.model_name, self.model_name)
        self.assertEqual(self.agent._AgentPyInterpreter__trials, self.trials)

    @patch('agentPyInterpreter.subprocess.run')
    def test_execute_code_success(self, mock_run):
        """Test successful code execution."""
        # Create temp directory if it doesn't exist
        os.makedirs('./temp', exist_ok=True)

        # Mock successful execution
        mock_result = Mock()
        mock_result.stderr = b''
        mock_result.stdout = b'Hello, World!'
        mock_result.returncode = 0
        mock_run.return_value = mock_result

        # NOTE: Setting __code directly is necessary because the original code
        # checks `if self.__code != ""` before attempting execution
        self.agent._AgentPyInterpreter__code = "print('Hello, World!')"
        
        code = "print('Hello, World!')"
        result = self.agent._AgentPyInterpreter__execute_code(code)

        self.assertEqual(result, "Execution successful")

    @patch('agentPyInterpreter.subprocess.run')
    def test_execute_code_error(self, mock_run):
        """Test code execution with errors."""
        # Create temp directory if it doesn't exist
        os.makedirs('./temp', exist_ok=True)

        # Mock execution error
        mock_result = Mock()
        mock_result.stderr = b'NameError: name \'x\' is not defined\n'
        mock_result.stdout = b''
        mock_result.returncode = 1
        mock_run.return_value = mock_result

        # NOTE: Setting __code directly (see test_execute_code_success for explanation)
        self.agent._AgentPyInterpreter__code = "print(x)"  # Undefined variable
        
        code = "print(x)"  # Undefined variable
        result = self.agent._AgentPyInterpreter__execute_code(code)

        self.assertIn("Execution error", result)
        self.assertIn("NameError", result)

    @patch('agentPyInterpreter.subprocess.run')
    def test_execute_code_no_code(self, mock_run):
        """Test execution with no code."""
        result = self.agent._AgentPyInterpreter__execute_code("")

        self.assertEqual(result, "No code found")
        mock_run.assert_not_called()

    def test_extract_python_code(self):
        """Test Python code extraction from markdown."""
        # Test with code block
        markdown = "```python\nprint('Hello')\nx = 5\n```"
        code = self.agent._AgentPyInterpreter__extract_python_code(markdown)
        self.assertIn('print(', code)
        self.assertIn('x = 5', code)

        # Test without code block
        markdown = "Just plain text"
        code = self.agent._AgentPyInterpreter__extract_python_code(markdown)
        self.assertEqual(code, "")

    def test_get_code(self):
        """Test getting code from markdown block."""
        markdown = "```python\nimport sys\nprint('Hello, World!')\nx = 42\n```"
        code = self.agent._AgentPyInterpreter__get_code(markdown)
        
        self.assertIn('import sys', code)
        self.assertIn('print(', code)
        self.assertIn('x = 42', code)

    @patch('agentPyInterpreter.subprocess.run')
    @patch('agentPyInterpreter.completion')
    def test_get_response_success_first_try(self, mock_completion, mock_run):
        """Test successful code execution on first try."""
        # Mock successful execution
        mock_result = Mock()
        mock_result.stderr = b''
        mock_result.stdout = b'Output'
        mock_result.returncode = 0
        mock_run.return_value = mock_result

        code = "```python\nprint('Hello')\n```"
        result = self.agent.get_response(code)

        self.assertIn('print', result)
        # Should not call LLM for fixes since it succeeds first time
        mock_completion.assert_not_called()

    @patch('agentPyInterpreter.subprocess.run')
    @patch('agentPyInterpreter.completion')
    def test_get_response_with_fix(self, mock_completion, mock_run):
        """Test code execution with error and subsequent fix."""
        # First execution fails, second succeeds
        mock_result_fail = Mock()
        mock_result_fail.stderr = b'SyntaxError: invalid syntax'
        mock_result_fail.stdout = b''
        mock_result_fail.returncode = 1
        
        mock_result_success = Mock()
        mock_result_success.stderr = b''
        mock_result_success.stdout = b'Fixed output'
        mock_result_success.returncode = 0
        
        mock_run.side_effect = [mock_result_fail, mock_result_success]

        # Mock LLM response with fixed code
        mock_response = Mock()
        mock_response.choices = [Mock()]
        mock_response.choices[0].message = Mock()
        mock_response.choices[0].message.content = "```python\nprint('Fixed')\n```"
        mock_completion.return_value = mock_response

        code = "```python\nprint('Broken'\n```"  # Invalid syntax
        result = self.agent.get_response(code)

        # Should have attempted to fix
        mock_completion.assert_called_once()
        self.assertIn('print', result)

    @patch('agentPyInterpreter.subprocess.run')
    def test_get_response_plain_code(self, mock_run):
        """Test code without markdown wrapper."""
        # Mock successful execution
        mock_result = Mock()
        mock_result.stderr = b''
        mock_result.stdout = b'Success'
        mock_result.returncode = 0
        mock_run.return_value = mock_result

        code = "print('No markdown')"
        result = self.agent.get_response(code)

        self.assertEqual(result, code)

    @patch('agentPyInterpreter.subprocess.run')
    @patch('agentPyInterpreter.completion')
    def test_get_response_max_retries(self, mock_completion, mock_run):
        """Test that fixing stops after max trials."""
        # Always fail execution
        mock_result = Mock()
        mock_result.stderr = b'Error'
        mock_result.stdout = b''
        mock_result.returncode = 1
        mock_run.return_value = mock_result

        # Mock LLM response
        mock_response = Mock()
        mock_response.choices = [Mock()]
        mock_response.choices[0].message = Mock()
        mock_response.choices[0].message.content = "```python\nstill_broken\n```"
        mock_completion.return_value = mock_response

        code = "```python\nbroken_code\n```"
        result = self.agent.get_response(code)

        # Should have tried exactly 'trials' times
        self.assertEqual(mock_completion.call_count, self.trials)

    @patch('agentPyInterpreter.completion')
    def test_get_response_execution_timeout(self, mock_completion):
        """Test timeout in LLM API call during fixing."""
        mock_completion.side_effect = Exception("timeout")

        # This will fail to execute, then fail to fix (timeout)
        code = "```python\ninvalid syntax\n```"
        
        # We need to mock subprocess to fail first
        with patch('agentPyInterpreter.subprocess.run') as mock_run:
            mock_result = Mock()
            mock_result.stderr = b'SyntaxError'
            mock_result.returncode = 1
            mock_run.return_value = mock_result
            
            result = self.agent.get_response(code)

        # Should still return the original code even if fixing fails
        self.assertIsNotNone(result)


if __name__ == '__main__':
    unittest.main()
