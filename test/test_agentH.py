"""Tests for the AgentH class."""
import unittest
import os
import sys
from unittest.mock import Mock, patch, MagicMock

# Add parent directory to path to import modules
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

from agentH import AgentH
from test_fixtures import BaseAgentTestCase


class TestAgentH(BaseAgentTestCase):
    """Test cases for the AgentH class."""

    def setUp(self):
        """Set up test fixtures."""
        self.server_address = "http://localhost:11434"
        self.model_name = "test-model"
        self.my_role = "You are a human assistant"
        self.agent = AgentH(
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

    def test_initialization_with_none_values(self):
        """Test agent initialization with None values."""
        agent = AgentH(
            server_address=None,
            model_name=None,
            my_role=None
        )
        self.assertIsNone(agent.server_address)
        self.assertIsNone(agent.model_name)
        self.assertEqual(agent.messages[0]['content'], None)

    @patch('builtins.input', return_value='Human response text')
    @patch('builtins.open', new_callable=unittest.mock.mock_open)
    def test_get_response(self, mock_open, mock_input):
        """Test getting response from human."""
        prompt = "What is your suggestion?"
        
        response = self.agent.get_response(prompt)

        # Verify response
        self.assertEqual(response, 'Human response text')
        
        # Verify messages were added
        self.assertEqual(len(self.agent.messages), 3)
        self.assertEqual(self.agent.messages[1]['role'], 'user')
        self.assertEqual(self.agent.messages[1]['content'], prompt)
        self.assertEqual(self.agent.messages[2]['role'], 'assistant')
        self.assertEqual(self.agent.messages[2]['content'], 'Human response text')

        # Verify file was written
        mock_open.assert_called_once_with('human_prompt.txt', 'w')
        mock_open().write.assert_called_once_with(prompt)

    @patch('builtins.input', return_value='')
    @patch('builtins.open', new_callable=unittest.mock.mock_open)
    def test_get_response_empty_input(self, mock_open, mock_input):
        """Test getting empty response from human."""
        prompt = "Test prompt"
        
        response = self.agent.get_response(prompt)

        self.assertEqual(response, '')
        self.assertEqual(len(self.agent.messages), 3)

    @patch('builtins.input', return_value='Multi\nline\nresponse')
    @patch('builtins.open', new_callable=unittest.mock.mock_open)
    def test_get_response_multiline(self, mock_open, mock_input):
        """Test getting multi-line response from human."""
        prompt = "Provide detailed explanation"
        
        response = self.agent.get_response(prompt)

        self.assertIn('Multi', response)
        self.assertIn('line', response)
        self.assertIn('response', response)

    @patch('builtins.input', return_value='Response with special chars: !@#$%^&*()')
    @patch('builtins.open', new_callable=unittest.mock.mock_open)
    def test_get_response_special_characters(self, mock_open, mock_input):
        """Test getting response with special characters."""
        prompt = "Test special chars"
        
        response = self.agent.get_response(prompt)

        self.assertEqual(response, 'Response with special chars: !@#$%^&*()')


if __name__ == '__main__':
    unittest.main()
