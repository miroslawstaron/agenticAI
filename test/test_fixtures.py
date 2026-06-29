"""Test fixtures and utilities for resetting singleton state between tests.

This module provides utilities for properly cleaning up singleton state
(AgentIDManager, MessageQueue, Logger) between test runs to prevent
test isolation issues.
"""

import unittest
import os
import shutil
from agent_id_manager import AgentIDManager
from messagequeue import MessageQueue, SingletonMeta
from logger import SingletonLogger


class TestEnvironment:
    """Utilities for setting up and tearing down test environment."""

    # Directories to clean up after tests
    CLEANUP_DIRS = ['./temp/', './results/']

    @staticmethod
    def reset_singletons():
        """Reset all singleton instances to their initial state.

        This must be called before each test to ensure clean state.
        """
        # Reset AgentIDManager
        AgentIDManager.reset()

        # Reset MessageQueue and all SingletonMeta instances
        try:
            MessageQueue.reset()
        except Exception:
            pass

        # Reset SingletonMeta instances dictionary
        try:
            SingletonMeta.reset_all()
        except Exception:
            pass

        # Reset Logger
        try:
            SingletonLogger.reset()
        except Exception:
            pass

    @staticmethod
    def create_directories():
        """Create required directories for testing."""
        for directory in TestEnvironment.CLEANUP_DIRS:
            os.makedirs(directory, exist_ok=True)

    @staticmethod
    def cleanup_directories():
        """Remove temporary test directories and files."""
        import time
        import glob

        for directory in TestEnvironment.CLEANUP_DIRS:
            if os.path.exists(directory):
                try:
                    shutil.rmtree(directory, ignore_errors=True)
                except Exception:
                    pass

        # Clean up any log files created during testing
        log_files = ['execution.log', 'test_execution.log']
        for log_file in log_files:
            if os.path.exists(log_file):
                # Retry file removal in case it's locked
                for _ in range(3):
                    try:
                        os.remove(log_file)
                        break
                    except (PermissionError, OSError):
                        time.sleep(0.1)  # Brief wait before retry

        # Clean up temp log files from /tmp directories
        try:
            import tempfile
            tmpdir = tempfile.gettempdir()
            for log_glob in glob.glob(os.path.join(tmpdir, '**/test_execution.log'), recursive=True):
                try:
                    os.remove(log_glob)
                except:
                    pass
        except:
            pass

    @staticmethod
    def setup_test_environment():
        """Perform full test environment setup.

        This should be called once before all tests in a class.
        """
        TestEnvironment.reset_singletons()
        TestEnvironment.create_directories()

    @staticmethod
    def cleanup_test_environment():
        """Perform full test environment cleanup.

        This should be called once after all tests in a class.
        """
        TestEnvironment.cleanup_directories()
        TestEnvironment.reset_singletons()


class BaseAgentTestCase(unittest.TestCase):
    """Base test case class for agent tests.

    This class provides automatic setup and teardown to ensure
    singleton state is clean for each test.

    Usage:
        class TestMyAgent(BaseAgentTestCase):
            def test_something(self):
                # Test code here
                pass
    """

    @classmethod
    def setUpClass(cls):
        """Set up test environment before all tests in the class."""
        TestEnvironment.setup_test_environment()

    def setUp(self):
        """Reset environment before each test method.

        This ensures each test starts with a clean slate.
        """
        TestEnvironment.reset_singletons()

    def tearDown(self):
        """Clean up after each test method."""
        TestEnvironment.reset_singletons()
        TestEnvironment.cleanup_directories()

    @classmethod
    def tearDownClass(cls):
        """Clean up after all tests in the class."""
        TestEnvironment.cleanup_test_environment()


class MessageQueueTestCase(BaseAgentTestCase):
    """Specialized test case for MessageQueue tests.

    Provides extra cleanup for message queue tests which are sensitive
    to state pollution.
    """

    def setUp(self):
        """Extra setup for MessageQueue tests."""
        super().setUp()
        # Explicitly recreate MessageQueue with fresh state
        try:
            MessageQueue.reset()
        except Exception:
            pass

    def tearDown(self):
        """Extra cleanup for MessageQueue tests."""
        # Explicitly close and reset MessageQueue
        try:
            MessageQueue.reset()
        except Exception:
            pass
        super().tearDown()


if __name__ == '__main__':
    unittest.main()
