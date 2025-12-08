"""Tests for the Singleton Logger class."""
import unittest
import os
import sys
import tempfile
import threading
import time
import re
from pathlib import Path

# Add parent directory to path to import logger module
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from logger import SingletonLogger, get_logger


class TestSingletonLogger(unittest.TestCase):
    """Test cases for the SingletonLogger class."""

    def setUp(self):
        """Set up test fixtures."""
        # Reset singleton instance before each test
        SingletonLogger._instance = None
        SingletonLogger._initialized = False
        
        # Create a temporary log file for testing
        self.temp_dir = tempfile.mkdtemp()
        self.test_log_file = os.path.join(self.temp_dir, "test_execution.log")

    def tearDown(self):
        """Clean up after tests."""
        # Reset singleton instance
        SingletonLogger._instance = None
        SingletonLogger._initialized = False
        
        # Clean up temporary log file
        if os.path.exists(self.test_log_file):
            os.remove(self.test_log_file)
        if os.path.exists(self.temp_dir):
            os.rmdir(self.temp_dir)

    def test_singleton_pattern(self):
        """Test that only one instance is created."""
        logger1 = SingletonLogger()
        logger2 = SingletonLogger()
        
        # Both references should point to the same instance
        self.assertIs(logger1, logger2)

    def test_singleton_with_get_logger(self):
        """Test singleton pattern with get_logger function."""
        logger1 = get_logger()
        logger2 = get_logger()
        logger3 = SingletonLogger()
        
        # All references should point to the same instance
        self.assertIs(logger1, logger2)
        self.assertIs(logger2, logger3)

    def test_initialization_once(self):
        """Test that initialization only happens once."""
        logger1 = SingletonLogger(log_file=self.test_log_file, enabled=True)
        original_enabled = logger1.enabled
        original_log_file = logger1.log_file
        
        # Try to initialize again with different parameters
        logger2 = SingletonLogger(log_file="different.log", enabled=False)
        
        # Should still have original configuration
        self.assertEqual(logger2.enabled, original_enabled)
        self.assertEqual(logger2.log_file, original_log_file)

    def test_enable_logging(self):
        """Test enabling logging."""
        logger = SingletonLogger()
        self.assertFalse(logger.enabled)
        
        logger.enable(self.test_log_file)
        self.assertTrue(logger.enabled)
        self.assertEqual(logger.log_file, self.test_log_file)

    def test_disable_logging(self):
        """Test disabling logging."""
        logger = SingletonLogger(log_file=self.test_log_file, enabled=True)
        self.assertTrue(logger.enabled)
        
        logger.disable()
        self.assertFalse(logger.enabled)

    def test_log_when_disabled(self):
        """Test that logging does nothing when disabled."""
        logger = SingletonLogger(log_file=self.test_log_file, enabled=False)
        
        logger.info("This should not be logged")
        
        # Log file should not exist
        self.assertFalse(os.path.exists(self.test_log_file))

    def test_log_when_enabled(self):
        """Test that logging works when enabled."""
        logger = SingletonLogger(log_file=self.test_log_file, enabled=True)
        
        logger.info("Test info message")
        logger.error("Test error message")
        
        # Log file should exist and contain the messages
        self.assertTrue(os.path.exists(self.test_log_file))
        
        with open(self.test_log_file, 'r') as f:
            content = f.read()
            self.assertIn("Test info message", content)
            self.assertIn("Test error message", content)

    def test_log_levels(self):
        """Test different log levels."""
        logger = SingletonLogger(log_file=self.test_log_file, enabled=True)
        
        logger.debug("Debug message")
        logger.info("Info message")
        logger.warning("Warning message")
        logger.error("Error message")
        logger.critical("Critical message")
        
        # Check that all messages are in the log file
        self.assertTrue(os.path.exists(self.test_log_file))
        
        with open(self.test_log_file, 'r') as f:
            content = f.read()
            self.assertIn("DEBUG", content)
            self.assertIn("INFO", content)
            self.assertIn("WARNING", content)
            self.assertIn("ERROR", content)
            self.assertIn("CRITICAL", content)

    def test_log_agent_init(self):
        """Test agent initialization logging."""
        logger = SingletonLogger(log_file=self.test_log_file, enabled=True)
        
        agent_id = "test-agent-123"
        agent_class = "TestAgent"
        system_prompt = "You are a test assistant"
        
        logger.log_agent_init(agent_id, agent_class, system_prompt)
        
        # Check log file content
        with open(self.test_log_file, 'r') as f:
            content = f.read()
            self.assertIn(f"[Agent:{agent_id}]", content)
            self.assertIn("Initialized", content)
            self.assertIn(agent_class, content)
            self.assertIn("System Prompt:", content)
            self.assertIn(system_prompt, content)

    def test_log_agent_action(self):
        """Test agent action logging."""
        logger = SingletonLogger(log_file=self.test_log_file, enabled=True)
        
        agent_id = "test-agent-456"
        action = "Sending request"
        details = "To model GPT-4"
        
        logger.log_agent_action(agent_id, action, details)
        
        # Check log file content
        with open(self.test_log_file, 'r') as f:
            content = f.read()
            self.assertIn(f"[Agent:{agent_id}]", content)
            self.assertIn(action, content)
            self.assertIn(details, content)

    def test_log_exception(self):
        """Test exception logging."""
        logger = SingletonLogger(log_file=self.test_log_file, enabled=True)
        
        agent_id = "test-agent-789"
        exception = ValueError("Test error")
        context = "test_function"
        
        logger.log_exception(agent_id, exception, context)
        
        # Check log file content
        with open(self.test_log_file, 'r') as f:
            content = f.read()
            self.assertIn(f"[Agent:{agent_id}]", content)
            self.assertIn("Exception", content)
            self.assertIn("ValueError", content)
            self.assertIn("Test error", content)
            self.assertIn(context, content)

    def test_log_timestamp(self):
        """Test that timestamps are included in log entries."""
        logger = SingletonLogger(log_file=self.test_log_file, enabled=True)
        
        logger.info("Test message with timestamp")
        
        # Check log file content includes timestamp
        with open(self.test_log_file, 'r') as f:
            content = f.read()
            # Check for timestamp format (YYYY-MM-DD HH:MM:SS)
            timestamp_pattern = r'\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}'
            self.assertIsNotNone(re.search(timestamp_pattern, content))

    def test_thread_safety(self):
        """Test that the singleton is thread-safe."""
        instances = []
        
        def create_instance():
            instance = SingletonLogger()
            instances.append(instance)
        
        # Create multiple threads
        threads = []
        for _ in range(10):
            thread = threading.Thread(target=create_instance)
            threads.append(thread)
            thread.start()
        
        # Wait for all threads to complete
        for thread in threads:
            thread.join()
        
        # All instances should be the same
        first_instance = instances[0]
        for instance in instances[1:]:
            self.assertIs(instance, first_instance)

    def test_concurrent_logging(self):
        """Test concurrent logging from multiple threads."""
        logger = SingletonLogger(log_file=self.test_log_file, enabled=True)
        
        def log_messages(thread_id):
            for i in range(5):
                logger.info(f"Thread {thread_id} - Message {i}")
                time.sleep(0.01)
        
        # Create multiple threads
        threads = []
        for i in range(5):
            thread = threading.Thread(target=log_messages, args=(i,))
            threads.append(thread)
            thread.start()
        
        # Wait for all threads to complete
        for thread in threads:
            thread.join()
        
        # Check that all messages were logged
        with open(self.test_log_file, 'r') as f:
            content = f.read()
            for i in range(5):
                for j in range(5):
                    self.assertIn(f"Thread {i} - Message {j}", content)

    def test_log_method_with_custom_level(self):
        """Test generic log method with custom level."""
        logger = SingletonLogger(log_file=self.test_log_file, enabled=True)
        
        logger.log("Custom info message", "INFO")
        logger.log("Custom error message", "ERROR")
        logger.log("Custom debug message", "DEBUG")
        
        # Check log file content
        with open(self.test_log_file, 'r') as f:
            content = f.read()
            self.assertIn("Custom info message", content)
            self.assertIn("Custom error message", content)
            self.assertIn("Custom debug message", content)


if __name__ == '__main__':
    unittest.main()
