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

from agent import AgentAI


class TestAgentAI(unittest.TestCase):
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
        self.assertEqual(self.agent.url, f'{self.server_address}')
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

    @patch('agent.requests.post')
    def test_get_response_success(self, mock_post):
        """Test successful response from the model."""
        # Mock successful API response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.text = json.dumps({
            'choices': [{
                'message': {
                    'content': 'This is a test response'
                }
            }]
        })
        mock_post.return_value = mock_response

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

    @patch('agent.requests.post')
    def test_get_response_with_api_key(self, mock_post):
        """Test response with API key in headers."""
        api_key = "test-api-key"
        agent = AgentAI(
            server_address=self.server_address,
            model_name=self.model_name,
            my_role=self.my_role,
            api_key=api_key
        )

        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.text = json.dumps({
            'choices': [{
                'message': {
                    'content': 'Response with API key'
                }
            }]
        })
        mock_post.return_value = mock_response

        agent.get_response("Test")

        # Verify Authorization header was set
        call_kwargs = mock_post.call_args[1]
        self.assertIn('headers', call_kwargs)
        self.assertEqual(call_kwargs['headers']['Authorization'], f'Bearer {api_key}')

    @patch('agent.requests.post')
    def test_get_response_error(self, mock_post):
        """Test error response from the model."""
        mock_response = Mock()
        mock_response.status_code = 500
        mock_response.text = "Internal Server Error"
        mock_post.return_value = mock_response

        response = self.agent.get_response("Test prompt")

        self.assertIsNone(response)

    @patch('agent.requests.post')
    def test_get_response_timeout_retry(self, mock_post):
        """Test timeout with retry mechanism."""
        import requests
        # First two calls timeout, third succeeds
        mock_post.side_effect = [
            requests.exceptions.Timeout(),
            requests.exceptions.Timeout(),
            Mock(status_code=200, text=json.dumps({
                'choices': [{'message': {'content': 'Success after retry'}}]
            }))
        ]

        response = self.agent.get_response("Test")

        self.assertEqual(response, 'Success after retry')
        self.assertEqual(mock_post.call_count, 3)

    @patch('agent.requests.post')
    def test_get_response_max_retries_exceeded(self, mock_post):
        """Test max retries exceeded."""
        import requests
        mock_post.side_effect = requests.exceptions.Timeout()

        response = self.agent.get_response("Test")

        self.assertIsNone(response)
        self.assertEqual(mock_post.call_count, 3)

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
