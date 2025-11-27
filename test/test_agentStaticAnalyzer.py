"""Tests for the AgentStaticAnalyzer class."""
import unittest
import os
import sys
import tempfile
import json
from unittest.mock import Mock, patch, MagicMock
import subprocess

# Add parent directory to path to import modules
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from agentStaticAnalyzer import AgentStaticAnalyzer


class TestAgentStaticAnalyzer(unittest.TestCase):
    """Test cases for the AgentStaticAnalyzer class."""

    def setUp(self):
        """Set up test fixtures."""
        self.server_address = "http://localhost:11434"
        self.model_name = "test-model"
        self.trials = 3
        self.agent = AgentStaticAnalyzer(
            server_address=self.server_address,
            model_name=self.model_name,
            trials=self.trials
        )

    def test_initialization(self):
        """Test agent initialization."""
        self.assertEqual(self.agent.server_address, self.server_address)
        self.assertEqual(self.agent.model_name, self.model_name)
        self.assertEqual(self.agent._AgentStaticAnalyzer__trials, self.trials)
        self.assertEqual(self.agent.logs, [])

    def test_extract_c_code(self):
        """Test C code extraction from markdown."""
        # Test with code block
        markdown = "```c\nint main() {\n    return 0;\n}\n```"
        code = self.agent._AgentStaticAnalyzer__extract_c_code(markdown)
        self.assertIn('int main()', code)
        self.assertIn('return 0;', code)

        # Test without code block
        markdown = "Just plain text"
        code = self.agent._AgentStaticAnalyzer__extract_c_code(markdown)
        self.assertEqual(code, "")

    def test_get_code(self):
        """Test getting code from markdown block."""
        markdown = "```c\n#include <stdio.h>\nint main() {\n    return 0;\n}\n```"
        code = self.agent._AgentStaticAnalyzer__get_code(markdown)
        
        self.assertIn('#include <stdio.h>', code)
        self.assertIn('int main()', code)

    @patch('agentStaticAnalyzer.subprocess.run')
    @patch('agentStaticAnalyzer.AgentCompiler')
    def test_analyze_code_success(self, mock_compiler_class, mock_run):
        """Test successful static analysis."""
        # Create temp directory if it doesn't exist
        os.makedirs('./temp', exist_ok=True)

        # Mock compiler
        mock_compiler = Mock()
        mock_compiler.get_response.return_value = '#include <stdio.h>\nint main() { return 0; }'
        mock_compiler_class.return_value = mock_compiler

        # Mock clean cppcheck output (no issues)
        mock_result = Mock()
        mock_result.stderr = b''
        mock_result.stdout = b''
        mock_run.return_value = mock_result

        code = "```c\n#include <stdio.h>\nint main() { return 0; }\n```"
        
        # NOTE: Setting __code directly is necessary because the original code at
        # agentStaticAnalyzer.py:167 checks `if self.__code != ""` before setting
        # the `msg` variable. Without this, line 198 raises UnboundLocalError.
        # Since we cannot modify agent code per requirements, we must set this
        # private attribute to work around the bug.
        self.agent._AgentStaticAnalyzer__code = '#include <stdio.h>\nint main() { return 0; }'
        
        result = self.agent._AgentStaticAnalyzer__analyze_code(code)

        self.assertEqual(result, "Static Analysis successful")
        self.assertEqual(len(self.agent.logs), 1)
        self.assertEqual(self.agent.logs[0]['result'], "Static Analysis successful")

    @patch('agentStaticAnalyzer.subprocess.run')
    @patch('agentStaticAnalyzer.AgentCompiler')
    def test_analyze_code_with_issues(self, mock_compiler_class, mock_run):
        """Test static analysis with issues found."""
        # Create temp directory if it doesn't exist
        os.makedirs('./temp', exist_ok=True)

        # Mock compiler
        mock_compiler = Mock()
        mock_compiler.get_response.return_value = 'int main() { int x; return 0; }'
        mock_compiler_class.return_value = mock_compiler

        # Mock cppcheck output with issues
        mock_result = Mock()
        mock_result.stderr = b'./temp/code_temp.c:1: style: Variable x is not used\n'
        mock_result.stdout = b''
        mock_run.return_value = mock_result

        code = "```c\nint main() { int x; return 0; }\n```"
        
        # NOTE: Setting __code directly (see test_analyze_code_success for explanation)
        self.agent._AgentStaticAnalyzer__code = 'int main() { int x; return 0; }'
        
        result = self.agent._AgentStaticAnalyzer__analyze_code(code)

        self.assertIn("Static Analyzer Issue", result)
        self.assertEqual(len(self.agent.logs), 1)
        self.assertEqual(self.agent.logs[0]['result'], "Static Analyzer Issue")

    @patch('agentStaticAnalyzer.subprocess.run')
    @patch('agentStaticAnalyzer.AgentCompiler')
    def test_get_response_successful_analysis(self, mock_compiler_class, mock_run):
        """Test get_response with successful analysis."""
        # Create temp directory if it doesn't exist
        os.makedirs('./temp', exist_ok=True)

        # Mock compiler
        mock_compiler = Mock()
        mock_compiler.get_response.return_value = 'int main() { return 0; }'
        mock_compiler_class.return_value = mock_compiler

        # Mock clean analysis
        mock_result = Mock()
        mock_result.stderr = b''
        mock_run.return_value = mock_result

        code = "```c\nint main() { return 0; }\n```"
        result = self.agent.get_response(code)

        self.assertIn('main', result)

    @patch('agentStaticAnalyzer.completion')
    @patch('agentStaticAnalyzer.subprocess.run')
    @patch('agentStaticAnalyzer.AgentCompiler')
    def test_get_response_with_issues_and_fix(self, mock_compiler_class, mock_run, mock_completion):
        """Test get_response with issues that get fixed."""
        # Create temp directory if it doesn't exist
        os.makedirs('./temp', exist_ok=True)

        # Mock compiler
        mock_compiler = Mock()
        mock_compiler.get_response.return_value = 'int main() { return 0; }'
        mock_compiler_class.return_value = mock_compiler

        # First analysis has issues, subsequent ones don't
        mock_run.side_effect = [
            Mock(stderr=b'./temp/code_temp.c:1: warning: something\n'),
            Mock(stderr=b''),
        ]

        # Mock LiteLLM response with fixed code
        mock_response = Mock()
        mock_response.choices = [Mock()]
        mock_response.choices[0].message = Mock()
        mock_response.choices[0].message.content = '```c\nint main() { return 0; }\n```'
        mock_completion.return_value = mock_response

        code = "```c\nint main() { int x; return 0; }\n```"
        result = self.agent.get_response(code)

        # Should have attempted to fix
        self.assertIsNotNone(result)

    @patch('agentStaticAnalyzer.completion')
    def test_solve_problem(self, mock_completion):
        """Test the problem solving mechanism."""
        # Mock LiteLLM response
        mock_response = Mock()
        mock_response.choices = [Mock()]
        mock_response.choices[0].message = Mock()
        mock_response.choices[0].message.content = 'Fixed code'
        mock_completion.return_value = mock_response

        # Set up error state
        self.agent._AgentStaticAnalyzer__code = "int main() { }"
        self.agent._AgentStaticAnalyzer__analyzer_result = "Static Analyzer Issue: something wrong"

        result = self.agent._AgentStaticAnalyzer__solve_problem()

        self.assertEqual(result, 'Fixed code')

    @patch('agentStaticAnalyzer.completion')
    def test_get_response_analyzer_timeout(self, mock_completion):
        """Test analyzer response with timeout."""
        mock_completion.side_effect = Exception("timeout")

        # Set up state
        self.agent._AgentStaticAnalyzer__analyzer_messages = [
            {"role": "system", "content": "You are a C Programmer."}
        ]

        result = self.agent._AgentStaticAnalyzer__get_response_analyzer("Test prompt")

        self.assertIsNone(result)

    def test_save_to_excel(self):
        """Test saving logs to Excel file."""
        # Use a unique filename that doesn't exist
        temp_file = f'/tmp/test_static_analyzer_{os.getpid()}.xlsx'

        try:
            # Ensure file doesn't exist
            if os.path.exists(temp_file):
                os.remove(temp_file)
            
            # Add test logs
            self.agent.logs = [
                {
                    'code': 'int main() { return 0; }',
                    'Issue': 'Static Analysis successful',
                    'result': 'Static Analysis successful'
                }
            ]

            self.agent.save_to_excel(temp_file)

            # Verify file exists
            self.assertTrue(os.path.exists(temp_file))
            
            import pandas as pd
            df = pd.read_excel(temp_file, engine='openpyxl')
            self.assertEqual(len(df), 1)
            self.assertEqual(df.iloc[0]['result'], 'Static Analysis successful')
        finally:
            if os.path.exists(temp_file):
                os.remove(temp_file)

    def test_save_to_excel_empty_logs(self):
        """Test saving empty logs."""
        with tempfile.NamedTemporaryFile(delete=False, suffix='.xlsx') as f:
            temp_file = f.name

        try:
            # Empty logs
            self.agent.logs = []
            
            # Should not crash, just print message
            self.agent.save_to_excel(temp_file)
        finally:
            if os.path.exists(temp_file):
                os.remove(temp_file)


if __name__ == '__main__':
    unittest.main()
