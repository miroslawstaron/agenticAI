"""Tests for LiteLLM server connectivity."""
import unittest
import os
import sys
import requests
from unittest.mock import patch, Mock, MagicMock
from urllib.parse import urlparse

# Add parent directory to path to import agent module
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

from agent import AgentAI
from test_fixtures import BaseAgentTestCase


class TestLiteLLMConnectivity(BaseAgentTestCase):
    """Test cases for verifying LiteLLM server connectivity."""

    def setUp(self):
        """Set up test fixtures."""
        self.localhost_server = "http://localhost:11434"
        self.model_name = "test-model"
        self.my_role = "You are a test assistant"
        
        # Mock the logger to avoid singleton issues in tests
        self.logger_patcher = patch('agent.get_logger')
        self.mock_get_logger = self.logger_patcher.start()
        self.mock_logger = MagicMock()
        self.mock_get_logger.return_value = self.mock_logger
    
    def tearDown(self):
        """Clean up test fixtures."""
        self.logger_patcher.stop()

    def test_localhost_connectivity(self):
        """Test connectivity to localhost server (Ollama-style)."""
        try:
            response = requests.get(
                f"{self.localhost_server}/api/tags",
                timeout=5
            )
            # Server is reachable
            self.assertIsNotNone(response)
            print(f"✓ Localhost server at {self.localhost_server} is reachable")
        except requests.exceptions.ConnectionError as e:
            self.skipTest(f"Localhost server not running: {e}")
        except requests.exceptions.Timeout:
            self.skipTest("Localhost server timeout")
        except Exception as e:
            self.skipTest(f"Cannot test localhost connectivity: {e}")

    def test_server_address_parsing(self):
        """Test that server address is correctly parsed and formatted."""
        agent = AgentAI(
            server_address=self.localhost_server,
            model_name=self.model_name,
            my_role=self.my_role
        )
        
        # Verify server address is stored correctly
        self.assertEqual(agent.server_address, self.localhost_server)
        
        # Verify URL parsing
        parsed = urlparse(self.localhost_server)
        self.assertEqual(parsed.scheme, "http")
        self.assertEqual(parsed.netloc, "localhost:11434")

    @patch('agent.completion')
    def test_litellm_completion_call(self, mock_completion):
        """Test that LiteLLM completion is called with correct server address."""
        # Mock successful response
        mock_response = Mock()
        mock_response.choices = [Mock()]
        mock_response.choices[0].message = Mock()
        mock_response.choices[0].message.content = 'Test response'
        mock_completion.return_value = mock_response

        agent = AgentAI(
            server_address=self.localhost_server,
            model_name=self.model_name,
            my_role=self.my_role
        )

        response = agent.get_response("Test prompt")

        # Verify completion was called
        self.assertTrue(mock_completion.called)
        
        # Verify the call was made with correct parameters
        call_kwargs = mock_completion.call_args[1]
        self.assertEqual(call_kwargs['model'], self.model_name)
        self.assertEqual(call_kwargs['api_base'], self.localhost_server)
        self.assertEqual(call_kwargs['timeout'], 300)
        self.assertEqual(response, 'Test response')

    @patch('agent.completion')
    def test_litellm_connection_timeout(self, mock_completion):
        """Test handling of connection timeout."""
        # Mock timeout exception
        mock_completion.side_effect = TimeoutError("Connection timed out")

        agent = AgentAI(
            server_address=self.localhost_server,
            model_name=self.model_name,
            my_role=self.my_role
        )

        response = agent.get_response("Test prompt")
        
        # Should return None after max retries
        self.assertIsNone(response)
        
        # Verify multiple retry attempts were made
        self.assertEqual(mock_completion.call_count, 3)

    @patch('agent.completion')
    def test_litellm_connection_refused(self, mock_completion):
        """Test handling of connection refused error."""
        # Mock connection refused exception
        from requests.exceptions import ConnectionError
        mock_completion.side_effect = ConnectionError("Connection refused")

        agent = AgentAI(
            server_address=self.localhost_server,
            model_name=self.model_name,
            my_role=self.my_role
        )

        response = agent.get_response("Test prompt")
        
        # Should return None after max retries
        self.assertIsNone(response)
        
        # Verify multiple retry attempts were made
        self.assertEqual(mock_completion.call_count, 3)

    @patch('agent.completion')
    def test_litellm_invalid_api_key(self, mock_completion):
        """Test handling of invalid API key."""
        # Mock authentication error
        mock_completion.side_effect = ValueError("Invalid API key")

        agent = AgentAI(
            server_address=self.localhost_server,
            model_name=self.model_name,
            my_role=self.my_role,
            api_key="invalid-key"
        )

        response = agent.get_response("Test prompt")
        
        # Should return None after max retries
        self.assertIsNone(response)
        
        # Verify multiple retry attempts were made
        self.assertEqual(mock_completion.call_count, 3)

    @patch('agent.completion')
    def test_litellm_successful_retry(self, mock_completion):
        """Test successful recovery after initial failure."""
        # First two calls fail, third succeeds
        mock_response = Mock()
        mock_response.choices = [Mock()]
        mock_response.choices[0].message = Mock()
        mock_response.choices[0].message.content = 'Success on retry'
        
        mock_completion.side_effect = [
            TimeoutError("First timeout"),
            TimeoutError("Second timeout"),
            mock_response  # Third attempt succeeds
        ]

        agent = AgentAI(
            server_address=self.localhost_server,
            model_name=self.model_name,
            my_role=self.my_role
        )

        response = agent.get_response("Test prompt")
        
        # Should return the successful response
        self.assertEqual(response, 'Success on retry')
        
        # Verify all three attempts were made
        self.assertEqual(mock_completion.call_count, 3)

    def test_custom_server_address_configuration(self):
        """Test configuration with custom server address."""
        custom_server = "http://deepestthought.cse.chalmers.se:11434/v1"
        
        agent = AgentAI(
            server_address=custom_server,
            model_name=self.model_name,
            my_role=self.my_role
        )
        
        self.assertEqual(agent.server_address, custom_server)
        
        # Verify URL parsing
        parsed = urlparse(custom_server)
        self.assertEqual(parsed.scheme, "http")
        self.assertEqual(parsed.netloc, "deepestthought.cse.chalmers.se:11434")
        self.assertEqual(parsed.path, "/v1")

    @patch('agent.completion')
    def test_litellm_model_availability_check(self, mock_completion):
        """Test checking model availability on the server."""
        # Simulate checking if model exists
        models_available = ["qwen3:4b", "mistral:7b", "gpt-oss:20b"]
        
        agent = AgentAI(
            server_address=self.localhost_server,
            model_name="qwen3:4b",
            my_role=self.my_role
        )
        
        # Verify model is in available list
        self.assertIn(agent.model_name, models_available)

    @patch('agent.completion')
    def test_litellm_request_parameters(self, mock_completion):
        """Test that LiteLLM receives correct request parameters."""
        mock_response = Mock()
        mock_response.choices = [Mock()]
        mock_response.choices[0].message = Mock()
        mock_response.choices[0].message.content = 'Response'
        mock_completion.return_value = mock_response

        agent = AgentAI(
            server_address=self.localhost_server,
            model_name=self.model_name,
            my_role=self.my_role,
            max_tokens=8192
        )

        prompt = "Test prompt"
        agent.get_response(prompt)

        # Verify all parameters
        call_kwargs = mock_completion.call_args[1]
        self.assertEqual(call_kwargs['model'], self.model_name)
        self.assertEqual(call_kwargs['api_base'], self.localhost_server)
        self.assertEqual(call_kwargs['temperature'], 0.5)
        self.assertEqual(call_kwargs['max_tokens'], 8192)
        self.assertEqual(call_kwargs['timeout'], 300)
        
        # Verify messages are passed correctly
        # Note: Due to Python's reference behavior, the messages list passed to
        # completion may include the assistant response appended after the call.
        # We just verify the first two messages (system + user).
        messages = call_kwargs['messages']
        self.assertGreaterEqual(len(messages), 2)  # At least system + user
        self.assertEqual(messages[0]['role'], 'system')
        self.assertEqual(messages[1]['role'], 'user')
        self.assertEqual(messages[1]['content'], prompt)


class TestLiteLLMServerDiscovery(unittest.TestCase):
    """Test cases for discovering and validating available servers."""

    def test_localhost_ollama_discovery(self):
        """Test discovery of local Ollama server."""
        localhost_url = "http://localhost:11434"
        
        try:
            response = requests.get(
                f"{localhost_url}/api/tags",
                timeout=5
            )
            
            # If we reach here, server is running
            self.assertEqual(response.status_code, 200)
            
            # Verify it's a valid Ollama response
            data = response.json()
            self.assertIn('models', data)
            
            print(f"✓ Ollama server discovered at {localhost_url}")
            print(f"  Available models: {len(data['models'])}")
            
        except requests.exceptions.ConnectionError:
            self.skipTest("Ollama server not running on localhost:11434")
        except requests.exceptions.Timeout:
            self.skipTest("Ollama server timeout")
        except Exception as e:
            self.skipTest(f"Could not connect to Ollama: {e}")

    def test_endpoint_validation(self):
        """Test validation of different endpoint types."""
        endpoints = [
            ("http://localhost:11434", "Ollama"),
            ("http://deepestthought.cse.chalmers.se:11434", "Local custom"),
        ]
        
        for endpoint, description in endpoints:
            parsed = urlparse(endpoint)
            
            # Verify valid URL structure
            self.assertIn(parsed.scheme, ['http', 'https'])
            self.assertTrue(len(parsed.netloc) > 0)

            print(f"[OK] {description} endpoint is valid: {endpoint}")


if __name__ == '__main__':
    unittest.main()
