"""Tests for the AgentReqs class."""
import unittest
import os
import sys
import tempfile
from unittest.mock import Mock, patch, MagicMock
import pandas as pd

# Add parent directory to path to import modules
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from requirements.agent_reqs import AgentReqs


class TestAgentReqs(unittest.TestCase):
    """Test cases for the AgentReqs class."""

    def setUp(self):
        """Set up test fixtures."""
        self.server_address = "http://localhost:11434"
        self.model_name = "test-model"
        self.my_role = "You are a requirements assistant"
        self.agent = AgentReqs(
            server_address=self.server_address,
            model_name=self.model_name,
            my_role=self.my_role
        )

    def test_initialization(self):
        """Test agent initialization."""
        self.assertEqual(self.agent.server_address, self.server_address)
        self.assertEqual(self.agent.model_name, self.model_name)
        # Verify parent class initialization
        self.assertEqual(len(self.agent.messages), 1)
        self.assertEqual(self.agent.messages[0]['role'], 'system')

    def test_initialization_with_defaults(self):
        """Test agent initialization with default values."""
        agent = AgentReqs()
        self.assertEqual(agent.server_address, "localhost")
        self.assertEqual(agent.model_name, "llama32")
        self.assertEqual(agent.messages[0]['content'], "User")

    def test_similarity_identical_strings(self):
        """Test similarity calculation with identical strings."""
        result = self.agent.similarity("test string", "test string")
        self.assertEqual(result, 1.0)

    def test_similarity_different_strings(self):
        """Test similarity calculation with different strings."""
        result = self.agent.similarity("hello world", "goodbye world")
        self.assertGreater(result, 0)
        self.assertLess(result, 1.0)

    def test_similarity_case_insensitive(self):
        """Test similarity is case insensitive."""
        result1 = self.agent.similarity("Test", "test")
        result2 = self.agent.similarity("TEST", "test")
        self.assertEqual(result1, result2)

    def test_similarity_empty_strings(self):
        """Test similarity with empty strings."""
        result = self.agent.similarity("", "")
        self.assertEqual(result, 1.0)

    @patch('requirements.agent_reqs.pd.read_excel')
    def test_get_requirements_success(self, mock_read_excel):
        """Test successful requirements retrieval."""
        # Mock Excel data
        mock_df = pd.DataFrame({
            'slogan': [
                'The system shall authenticate users',
                'The system shall encrypt data',
                'The system shall log all transactions',
                'The system shall backup data daily',
                'The system shall validate input'
            ]
        })
        mock_read_excel.return_value = mock_df

        prompt = "The system shall authenticate users securely"
        result = self.agent.get_requirements(prompt)

        # Should return top 5 most similar requirements
        self.assertEqual(len(result), 5)
        self.assertIn('The system shall authenticate users', result)

    @patch('requirements.agent_reqs.pd.read_excel')
    def test_get_requirements_file_not_found(self, mock_read_excel):
        """Test requirements retrieval when file not found."""
        mock_read_excel.side_effect = FileNotFoundError()

        result = self.agent.get_requirements("Test prompt")

        self.assertEqual(result, [])

    @patch('requirements.agent_reqs.pd.read_excel')
    def test_get_requirements_missing_column(self, mock_read_excel):
        """Test requirements retrieval with missing column."""
        # Mock Excel data without 'slogan' column
        mock_df = pd.DataFrame({
            'description': ['req1', 'req2']
        })
        mock_read_excel.return_value = mock_df

        result = self.agent.get_requirements("Test prompt")

        self.assertEqual(result, [])

    @patch('requirements.agent_reqs.pd.read_excel')
    def test_get_requirements_with_nan_values(self, mock_read_excel):
        """Test requirements retrieval with NaN values."""
        # Mock Excel data with NaN values
        mock_df = pd.DataFrame({
            'slogan': [
                'Valid requirement 1',
                None,
                'Valid requirement 2',
                float('nan'),
                'Valid requirement 3'
            ]
        })
        mock_read_excel.return_value = mock_df

        result = self.agent.get_requirements("Test prompt")

        # Should only include non-NaN values
        self.assertLessEqual(len(result), 5)
        for req in result:
            self.assertIsNotNone(req)

    @patch('requirements.agent_reqs.pd.read_excel')
    def test_get_requirements_fewer_than_five(self, mock_read_excel):
        """Test requirements retrieval with fewer than 5 requirements."""
        # Mock Excel data with only 3 requirements
        mock_df = pd.DataFrame({
            'slogan': [
                'Requirement 1',
                'Requirement 2',
                'Requirement 3'
            ]
        })
        mock_read_excel.return_value = mock_df

        result = self.agent.get_requirements("Test prompt")

        # Should return all 3 requirements
        self.assertEqual(len(result), 3)

    @patch('requirements.agent_reqs.pd.read_excel')
    def test_get_requirements_ordering(self, mock_read_excel):
        """Test requirements are ordered by similarity."""
        # Mock Excel data
        mock_df = pd.DataFrame({
            'slogan': [
                'Completely different requirement',
                'System authentication and security',
                'Random unrelated text',
                'User authentication system',
                'Another random requirement'
            ]
        })
        mock_read_excel.return_value = mock_df

        prompt = "User authentication"
        result = self.agent.get_requirements(prompt)

        # First result should be most similar
        # "User authentication system" should rank higher than "Completely different requirement"
        self.assertIn('User authentication system', result)


if __name__ == '__main__':
    unittest.main()
