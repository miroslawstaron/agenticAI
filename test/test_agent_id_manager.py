import unittest
from agent_id_manager import AgentIDManager


class TestAgentIDManager(unittest.TestCase):
    """Test cases for the AgentIDManager class."""

    def setUp(self):
        """Reset the counter before each test."""
        AgentIDManager.reset()

    def test_initial_id(self):
        """Test that the first ID generated is '00'."""
        agent_id = AgentIDManager.get_next_id()
        self.assertEqual(agent_id, '00')

    def test_sequential_ids(self):
        """Test that IDs are generated sequentially."""
        expected_ids = ['00', '01', '02', '03', '04']
        for expected_id in expected_ids:
            agent_id = AgentIDManager.get_next_id()
            self.assertEqual(agent_id, expected_id)

    def test_id_format(self):
        """Test that all IDs are 2-digit strings."""
        for _ in range(10):
            agent_id = AgentIDManager.get_next_id()
            self.assertEqual(len(agent_id), 2)
            self.assertTrue(agent_id.isdigit())

    def test_wraparound_at_100(self):
        """Test that counter wraps around after reaching 99."""
        # Manually set counter to 98 to test wraparound
        AgentIDManager._counter = 98
        
        agent_id_1 = AgentIDManager.get_next_id()  # Should be '98'
        self.assertEqual(agent_id_1, '98')
        
        agent_id_2 = AgentIDManager.get_next_id()  # Should be '99'
        self.assertEqual(agent_id_2, '99')
        
        agent_id_3 = AgentIDManager.get_next_id()  # Should wrap to '00'
        self.assertEqual(agent_id_3, '00')

    def test_reset(self):
        """Test that reset() resets the counter to 0."""
        # Generate some IDs
        for _ in range(5):
            AgentIDManager.get_next_id()
        
        # Reset counter
        AgentIDManager.reset()
        
        # Next ID should be '00'
        agent_id = AgentIDManager.get_next_id()
        self.assertEqual(agent_id, '00')

    def test_multiple_instances_share_counter(self):
        """Test that all instances of AgentIDManager share the same counter."""
        id1 = AgentIDManager.get_next_id()  # '00'
        id2 = AgentIDManager.get_next_id()  # '01'
        
        self.assertEqual(id1, '00')
        self.assertEqual(id2, '01')

    def test_large_sequence(self):
        """Test generating a large sequence of IDs."""
        ids = [AgentIDManager.get_next_id() for _ in range(150)]
        
        # First 100 should be 00-99
        self.assertEqual(ids[0], '00')
        self.assertEqual(ids[99], '99')
        
        # Should wrap around after 100
        self.assertEqual(ids[100], '00')
        self.assertEqual(ids[149], '49')

    def test_id_uniqueness_within_cycle(self):
        """Test that IDs are unique within a single cycle (0-99)."""
        ids = [AgentIDManager.get_next_id() for _ in range(100)]
        unique_ids = set(ids)
        
        self.assertEqual(len(unique_ids), 100)
        self.assertEqual(unique_ids, set(f'{i:02d}' for i in range(100)))


if __name__ == '__main__':
    unittest.main()
