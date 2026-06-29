"""Tests for the Agent3GPP class."""
import unittest
import os
import sys
import tempfile
from unittest.mock import Mock, patch, MagicMock

# Add parent directory to path to import modules
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

from requirements.agent_3gpp import Agent3GPP
from test_fixtures import BaseAgentTestCase


class TestAgent3GPP(BaseAgentTestCase):
    """Test cases for the Agent3GPP class."""

    def setUp(self):
        """Set up test fixtures."""
        self.server_address = "http://localhost:11434"
        self.model_name = "test-model"
        self.my_role = "You are a 3GPP specialist"
        self.agent = Agent3GPP(
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
        agent = Agent3GPP()
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

    def test_parse_sections_by_heading_simple(self):
        """Test parsing sections with simple headings."""
        text = """1. Introduction
This is the introduction section.

2. Overview
This is the overview section.

3. Details
This is the details section."""
        
        sections = self.agent._parse_sections_by_heading(text, "test.pdf")
        
        self.assertEqual(len(sections), 3)
        self.assertIn('[test.pdf]', sections[0])
        self.assertIn('Introduction', sections[0])
        self.assertIn('Overview', sections[1])
        self.assertIn('Details', sections[2])

    def test_parse_sections_by_heading_nested(self):
        """Test parsing sections with nested headings."""
        text = """1. Introduction
Overview text.

1.1 Subsection
Subsection content.

2. Main Section
Main content."""
        
        sections = self.agent._parse_sections_by_heading(text, "test.pdf")
        
        self.assertGreater(len(sections), 0)
        # Should have found multiple sections
        self.assertIn('[test.pdf]', sections[0])

    def test_parse_sections_by_heading_empty_text(self):
        """Test parsing sections with empty text."""
        text = ""
        
        sections = self.agent._parse_sections_by_heading(text, "test.pdf")
        
        self.assertEqual(len(sections), 0)

    def test_parse_sections_by_heading_no_headings(self):
        """Test parsing sections with no headings."""
        text = """Just some random text
without any headings
at all."""
        
        sections = self.agent._parse_sections_by_heading(text, "test.pdf")
        
        self.assertEqual(len(sections), 0)

    @patch('requirements.agent_3gpp.os.listdir')
    def test_get_sections_directory_not_found(self, mock_listdir):
        """Test get_sections when directory not found."""
        mock_listdir.side_effect = FileNotFoundError()

        result = self.agent.get_sections("Test prompt")

        self.assertEqual(result, "")

    @patch('requirements.agent_3gpp.PyPDF2.PdfReader')
    @patch('builtins.open', new_callable=unittest.mock.mock_open)
    @patch('requirements.agent_3gpp.os.listdir')
    def test_get_sections_success(self, mock_listdir, mock_open, mock_pdf_reader):
        """Test successful section retrieval from PDFs."""
        # Mock directory listing
        mock_listdir.return_value = ['test1.pdf', 'test2.pdf']

        # Mock PDF reader
        mock_page1 = Mock()
        mock_page1.extract_text.return_value = """1. Security
The system shall provide security.

2. Authentication
User authentication is required."""

        mock_page2 = Mock()
        mock_page2.extract_text.return_value = """1. Privacy
Privacy protection mechanisms."""

        mock_pdf = Mock()
        mock_pdf.pages = [mock_page1]
        mock_pdf_reader.return_value = mock_pdf

        result = self.agent.get_sections("security authentication")

        # Should return concatenated sections
        self.assertIsInstance(result, str)

    @patch('requirements.agent_3gpp.os.listdir')
    def test_get_sections_no_pdf_files(self, mock_listdir):
        """Test get_sections when no PDF files exist."""
        mock_listdir.return_value = ['readme.txt', 'data.csv']

        result = self.agent.get_sections("Test prompt")

        # Should return empty string or minimal result
        self.assertIsInstance(result, str)

    @patch('requirements.agent_3gpp.PyPDF2.PdfReader')
    @patch('builtins.open', new_callable=unittest.mock.mock_open)
    @patch('requirements.agent_3gpp.os.listdir')
    def test_get_sections_pdf_read_error(self, mock_listdir, mock_open, mock_pdf_reader):
        """Test get_sections when PDF reading fails."""
        mock_listdir.return_value = ['corrupt.pdf']
        mock_pdf_reader.side_effect = Exception("PDF read error")

        result = self.agent.get_sections("Test prompt")

        # Should handle error gracefully
        self.assertEqual(result, "")

    @patch('requirements.agent_3gpp.PyPDF2.PdfReader')
    @patch('builtins.open', new_callable=unittest.mock.mock_open)
    @patch('requirements.agent_3gpp.os.listdir')
    def test_get_sections_empty_pdf(self, mock_listdir, mock_open, mock_pdf_reader):
        """Test get_sections with empty PDF."""
        mock_listdir.return_value = ['empty.pdf']

        mock_page = Mock()
        mock_page.extract_text.return_value = ""

        mock_pdf = Mock()
        mock_pdf.pages = [mock_page]
        mock_pdf_reader.return_value = mock_pdf

        result = self.agent.get_sections("Test prompt")

        # Should handle empty PDF
        self.assertIsInstance(result, str)

    @patch('requirements.agent_3gpp.PyPDF2.PdfReader')
    @patch('builtins.open', new_callable=unittest.mock.mock_open)
    @patch('requirements.agent_3gpp.os.listdir')
    def test_get_sections_returns_top_five(self, mock_listdir, mock_open, mock_pdf_reader):
        """Test that get_sections returns top 5 sections."""
        mock_listdir.return_value = ['test.pdf']

        # Create text with many sections
        text_sections = "\n\n".join([
            f"{i}. Section {i}\nContent for section {i}." 
            for i in range(1, 11)
        ])

        mock_page = Mock()
        mock_page.extract_text.return_value = text_sections

        mock_pdf = Mock()
        mock_pdf.pages = [mock_page]
        mock_pdf_reader.return_value = mock_pdf

        result = self.agent.get_sections("section")

        # Should contain sections separated by **
        if result:
            sections = result.split('**')
            self.assertLessEqual(len(sections), 5)


if __name__ == '__main__':
    unittest.main()
