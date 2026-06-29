"""Tests for the base AgentAI class."""
import unittest
import os
import sys
import tempfile
import json
from unittest.mock import Mock, patch, MagicMock
import pandas as pd

# Add parent directory to path to import agent module
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

from agent import AgentAI
from test_fixtures import BaseAgentTestCase


class TestAgentAI(BaseAgentTestCase):
    """Test cases for the AgentAI class."""

    def setUp(self):
        """Set up test fixtures."""
        self.server_address = "http://localhost:11434"
        self.model_name = "test-model"
        self.my_role = "You are a test assistant"
        self.agent = AgentAI(
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
        agent = AgentAI(
            server_address=self.server_address,
            model_name=self.model_name,
            my_role=self.my_role,
            api_key=api_key
        )
        self.assertEqual(agent.api_key, api_key)

    def test_initialization_with_max_tokens(self):
        """Test agent initialization with custom max_tokens."""
        max_tokens = 8000
        agent = AgentAI(
            server_address=self.server_address,
            model_name=self.model_name,
            my_role=self.my_role,
            max_tokens=max_tokens
        )
        self.assertEqual(agent.max_tokens, max_tokens)

    @patch('agent.completion')
    def test_get_response_success(self, mock_completion):
        """Test successful response from the model."""
        # Mock LiteLLM response
        mock_response = Mock()
        mock_response.choices = [Mock()]
        mock_response.choices[0].message = Mock()
        mock_response.choices[0].message.content = 'This is a test response'
        mock_completion.return_value = mock_response

        prompt = "Test prompt"
        response = self.agent.get_response(prompt)

        # Verify response
        self.assertEqual(response, 'This is a test response')
        
        # Verify messages were added
        self.assertEqual(len(self.agent.messages), 3)
        self.assertEqual(self.agent.messages[1]['role'], 'user')
        self.assertEqual(self.agent.messages[1]['content'], prompt)
        self.assertEqual(self.agent.messages[2]['role'], 'assistant')
        self.assertEqual(self.agent.messages[2]['content'], 'This is a test response')

    @patch('agent.completion')
    def test_get_response_with_api_key(self, mock_completion):
        """Test response with API key in headers."""
        api_key = "test-api-key"
        agent = AgentAI(
            server_address=self.server_address,
            model_name=self.model_name,
            my_role=self.my_role,
            api_key=api_key
        )

        mock_response = Mock()
        mock_response.choices = [Mock()]
        mock_response.choices[0].message = Mock()
        mock_response.choices[0].message.content = 'Response with API key'
        mock_completion.return_value = mock_response

        agent.get_response("Test")

        # Verify completion was called with correct parameters
        mock_completion.assert_called_once()
        call_kwargs = mock_completion.call_args[1]
        self.assertEqual(call_kwargs['model'], self.model_name)

    @patch('agent.completion')
    def test_get_response_error(self, mock_completion):
        """Test error response from the model."""
        # Mock an exception from LiteLLM
        mock_completion.side_effect = Exception("API Error")

        response = self.agent.get_response("Test prompt")

        self.assertIsNone(response)

    @patch('agent.completion')
    def test_get_response_timeout_retry(self, mock_completion):
        """Test timeout with retry mechanism."""
        # First two calls timeout, third succeeds
        mock_success_response = Mock()
        mock_success_response.choices = [Mock()]
        mock_success_response.choices[0].message = Mock()
        mock_success_response.choices[0].message.content = 'Success after retry'
        
        mock_completion.side_effect = [
            Exception("timeout error"),
            Exception("timeout error"),
            mock_success_response
        ]

        response = self.agent.get_response("Test")

        self.assertEqual(response, 'Success after retry')
        self.assertEqual(mock_completion.call_count, 3)

    @patch('agent.completion')
    def test_get_response_max_retries_exceeded(self, mock_completion):
        """Test max retries exceeded."""
        mock_completion.side_effect = Exception("timeout error")

        response = self.agent.get_response("Test")

        self.assertIsNone(response)
        self.assertEqual(mock_completion.call_count, 3)

    def test_start(self):
        """Test start method (just prints info)."""
        # Just verify it doesn't crash
        self.agent.start()

    def test_save_to_csv(self):
        """Test saving messages to CSV file."""
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.csv') as f:
            temp_file = f.name

        try:
            # Add some test messages
            self.agent.messages.append({'role': 'user', 'content': 'Test user message'})
            self.agent.messages.append({'role': 'assistant', 'content': 'Test assistant message'})

            self.agent.save_to_csv(temp_file)

            # Verify file contents
            with open(temp_file, 'r') as f:
                lines = f.readlines()
                self.assertEqual(lines[0].strip(), 'role$content')
                # Check that user and assistant messages are in the file
                content = ''.join(lines)
                self.assertIn('user$Test user message', content)
                self.assertIn('assistant$Test assistant message', content)
        finally:
            if os.path.exists(temp_file):
                os.remove(temp_file)

    def test_save_to_excel(self):
        """Test saving messages to Excel file."""
        with tempfile.NamedTemporaryFile(delete=False, suffix='.xlsx') as f:
            temp_file = f.name

        try:
            # Add some test messages
            self.agent.messages.append({'role': 'user', 'content': 'Test user'})
            self.agent.messages.append({'role': 'assistant', 'content': 'Test assistant'})

            self.agent.save_to_excel(temp_file)

            # Verify file exists and can be read
            self.assertTrue(os.path.exists(temp_file))
            df = pd.read_excel(temp_file)
            self.assertEqual(len(df), 3)  # system + user + assistant
            self.assertEqual(df.iloc[0]['role'], 'system')
            self.assertEqual(df.iloc[1]['role'], 'user')
            self.assertEqual(df.iloc[2]['role'], 'assistant')
        finally:
            if os.path.exists(temp_file):
                os.remove(temp_file)

    def test_basic_markdown_to_html(self):
        """Test markdown to HTML conversion."""
        # Test code blocks
        md = "```python\nprint('hello')\n```"
        html = self.agent.basic_markdown_to_html(md)
        self.assertIn('<pre><code class="python">', html)
        self.assertIn("print('hello')", html)

        # Test inline code
        md = "This is `inline code`"
        html = self.agent.basic_markdown_to_html(md)
        self.assertIn('<code>inline code</code>', html)

        # Test bold text
        md = "**bold text**"
        html = self.agent.basic_markdown_to_html(md)
        self.assertIn('<strong>bold text</strong>', html)

        # Test italic text
        md = "*italic text*"
        html = self.agent.basic_markdown_to_html(md)
        self.assertIn('<em>italic text</em>', html)

        # Test newlines
        md = "line1\nline2"
        html = self.agent.basic_markdown_to_html(md)
        self.assertIn('<br>', html)

    def test_to_html(self):
        """Test converting conversation to HTML."""
        with tempfile.NamedTemporaryFile(delete=False, suffix='.html') as f:
            temp_file = f.name

        try:
            # Add test conversation
            self.agent.messages.append({'role': 'user', 'content': 'Design request'})
            self.agent.messages.append({'role': 'assistant', 'content': 'Implementation'})

            self.agent.to_html(temp_file)

            # Verify HTML file was created
            self.assertTrue(os.path.exists(temp_file))
            
            with open(temp_file, 'r') as f:
                html_content = f.read()
                self.assertIn('<!DOCTYPE html>', html_content)
                self.assertIn('Designer', html_content)
                self.assertIn('Programmer', html_content)
                self.assertIn('Design request', html_content)
                self.assertIn('Implementation', html_content)
        finally:
            if os.path.exists(temp_file):
                os.remove(temp_file)


if __name__ == '__main__':
    unittest.main()
