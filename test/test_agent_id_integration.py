import unittest
from unittest.mock import patch, MagicMock
import sys
import os

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from agent_id_manager import AgentIDManager


class TestAgentIDIntegration(unittest.TestCase):
    """Integration tests for agent ID assignment."""

    def setUp(self):
        """Reset the counter before each test."""
        AgentIDManager.reset()
    
    def test_agent_id_manager_sequential_generation(self):
        """Test that AgentIDManager generates sequential IDs."""
        AgentIDManager.reset()
        
        id1 = AgentIDManager.get_next_id()
        id2 = AgentIDManager.get_next_id()
        id3 = AgentIDManager.get_next_id()
        
        self.assertEqual(id1, '00')
        self.assertEqual(id2, '01')
        self.assertEqual(id3, '02')

    def test_agent_id_manager_thread_safety(self):
        """Test that multiple calls produce unique sequential IDs."""
        import threading
        
        ids = []
        lock = threading.Lock()
        
        def get_id():
            agent_id = AgentIDManager.get_next_id()
            with lock:
                ids.append(agent_id)
        
        threads = [threading.Thread(target=get_id) for _ in range(10)]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join()
        
        # All IDs should be unique
        self.assertEqual(len(ids), 10)
        self.assertEqual(len(set(ids)), 10)

    def test_agent_id_manager_wraparound_and_reset(self):
        """Test wraparound behavior and reset functionality."""
        AgentIDManager._counter = 98
        
        id1 = AgentIDManager.get_next_id()
        id2 = AgentIDManager.get_next_id()
        id3 = AgentIDManager.get_next_id()
        
        self.assertEqual(id1, '98')
        self.assertEqual(id2, '99')
        self.assertEqual(id3, '00')  # Wraparound
        
        # Reset and verify
        AgentIDManager.reset()
        id4 = AgentIDManager.get_next_id()
        self.assertEqual(id4, '00')


if __name__ == '__main__':
    unittest.main()
