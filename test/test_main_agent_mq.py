"""Tests for the main_agent_mq module."""
import unittest
import os
import sys
import tempfile
from unittest.mock import Mock, patch, MagicMock

# Add parent directory to path to import modules
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from main_agent_mq import create_agents, run_conversation, DESIGNER_ID, PROGRAMMER_ID
from messagequeue import MessageQueue


class TestMainAgentMQ(unittest.TestCase):
    """Test cases for main_agent_mq module."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.message_queue = MessageQueue()
    
    def tearDown(self):
        """Clean up after tests."""
        self.message_queue.close()

    @patch('main_agent_mq.AgentAI')
    def test_create_agents(self, mock_agent_class):
        """Test agent creation."""
        # Setup mock
        mock_designer = Mock()
        mock_programmer = Mock()
        mock_agent_class.side_effect = [mock_designer, mock_programmer]
        
        # Call create_agents
        designer, programmer = create_agents(
            server_address="http://localhost:11434",
            api_key="test-key"
        )
        
        # Verify agents were created
        self.assertEqual(mock_agent_class.call_count, 2)
        self.assertEqual(designer, mock_designer)
        self.assertEqual(programmer, mock_programmer)
        
        # Verify agent roles were set correctly
        calls = mock_agent_class.call_args_list
        # First call is for designer
        self.assertIn("designer", calls[0][1]['my_role'].lower())
        # Second call is for programmer
        self.assertIn("programmer", calls[1][1]['my_role'].lower())

    def test_message_queue_publish_receive(self):
        """Test basic message publishing and receiving with agent IDs."""
        # Publish a message to Programmer
        msg_id = self.message_queue.publish(
            sender="User",
            recipient=PROGRAMMER_ID,
            payload={"type": "task", "content": "Write hello world"}
        )
        
        # Verify message was published
        self.assertIsInstance(msg_id, int)
        self.assertGreater(msg_id, 0)
        
        # Retrieve message as Programmer
        messages = self.message_queue.get_messages(PROGRAMMER_ID)
        self.assertEqual(len(messages), 1)
        self.assertEqual(messages[0].sender, "User")
        self.assertEqual(messages[0].payload["type"], "task")
        self.assertEqual(messages[0].payload["content"], "Write hello world")

    def test_message_queue_agent_communication(self):
        """Test message exchange between Designer and Programmer."""
        # Programmer sends solution to Designer
        self.message_queue.publish(
            sender=PROGRAMMER_ID,
            recipient=DESIGNER_ID,
            payload={
                "type": "solution",
                "content": "#include <stdio.h>\nint main() { return 0; }"
            }
        )
        
        # Designer retrieves message
        messages = self.message_queue.get_messages(DESIGNER_ID)
        self.assertEqual(len(messages), 1)
        self.assertEqual(messages[0].sender, PROGRAMMER_ID)
        self.assertEqual(messages[0].payload["type"], "solution")
        
        # Designer sends feedback to Programmer
        self.message_queue.publish(
            sender=DESIGNER_ID,
            recipient=PROGRAMMER_ID,
            payload={"type": "feedback", "content": "Add error handling"}
        )
        
        # Programmer retrieves feedback
        messages = self.message_queue.get_messages(PROGRAMMER_ID)
        self.assertEqual(len(messages), 1)
        self.assertEqual(messages[0].sender, DESIGNER_ID)
        self.assertEqual(messages[0].payload["type"], "feedback")

    @patch('main_agent_mq.AgentAI')
    def test_run_conversation_basic(self, mock_agent_class):
        """Test basic conversation flow with mocked agents."""
        # Create mock agents
        mock_designer = Mock()
        mock_programmer = Mock()
        
        # Configure mock responses
        mock_programmer.get_response.return_value = "int main() { return 0; }"
        mock_designer.get_response.return_value = "Consider adding error handling"
        mock_programmer.save_to_excel = Mock()
        
        # Run conversation with 0 iterations (just initial exchange)
        run_conversation(
            designer=mock_designer,
            programmer=mock_programmer,
            message_queue=self.message_queue,
            initial_prompt="Write a C program",
            max_iterations=0
        )
        
        # Verify programmer received initial task and responded
        mock_programmer.get_response.assert_called()
        
        # Verify designer received solution and provided feedback
        mock_designer.get_response.assert_called()

    @patch('main_agent_mq.AgentAI')
    def test_run_conversation_with_iterations(self, mock_agent_class):
        """Test conversation with multiple iterations."""
        # Create mock agents
        mock_designer = Mock()
        mock_programmer = Mock()
        
        # Configure mock responses
        mock_programmer.get_response.return_value = "int main() { return 0; }"
        mock_designer.get_response.return_value = "Looks good"
        mock_programmer.save_to_excel = Mock()
        
        # Run conversation with 2 iterations and output file
        run_conversation(
            designer=mock_designer,
            programmer=mock_programmer,
            message_queue=self.message_queue,
            initial_prompt="Write a C program",
            max_iterations=2,
            output_file="/tmp/test_output.xlsx"
        )
        
        # Verify multiple exchanges occurred
        # Initial exchange + 2 iterations = programmer called 3 times
        self.assertEqual(mock_programmer.get_response.call_count, 3)
        # Initial response + 2 iterations = designer called 3 times
        self.assertEqual(mock_designer.get_response.call_count, 3)
        
        # Verify save was called during iterations
        self.assertEqual(mock_programmer.save_to_excel.call_count, 2)

    def test_message_queue_message_ordering(self):
        """Test that messages are retrieved in order."""
        # Send multiple messages
        for i in range(5):
            self.message_queue.publish(
                sender="Sender",
                recipient=PROGRAMMER_ID,
                payload={"sequence": i}
            )
        
        # Retrieve all messages
        messages = self.message_queue.get_messages(PROGRAMMER_ID)
        
        # Verify order
        self.assertEqual(len(messages), 5)
        for i, msg in enumerate(messages):
            self.assertEqual(msg.payload["sequence"], i)

    def test_message_queue_payload_structure(self):
        """Test complex payload structures used in agent communication."""
        # Test task payload
        task_payload = {
            "type": "task",
            "content": "Write bubble sort",
            "metadata": {
                "priority": "high",
                "tags": ["sorting", "algorithm"]
            }
        }
        
        self.message_queue.publish(
            sender="User",
            recipient=PROGRAMMER_ID,
            payload=task_payload
        )
        
        messages = self.message_queue.get_messages(PROGRAMMER_ID)
        self.assertEqual(len(messages), 1)
        self.assertEqual(messages[0].payload, task_payload)
        self.assertEqual(messages[0].payload["metadata"]["priority"], "high")

    def test_message_queue_broadcast_to_agents(self):
        """Test broadcasting messages to all agents."""
        # Broadcast announcement
        self.message_queue.publish(
            sender="System",
            recipient="broadcast",
            payload={"type": "announcement", "message": "Session starting"}
        )
        
        # Both agents should receive the broadcast
        designer_messages = self.message_queue.get_messages(DESIGNER_ID)
        programmer_messages = self.message_queue.get_messages(PROGRAMMER_ID)
        
        self.assertEqual(len(designer_messages), 1)
        self.assertEqual(len(programmer_messages), 1)
        self.assertEqual(designer_messages[0].payload["type"], "announcement")
        self.assertEqual(programmer_messages[0].payload["type"], "announcement")

    def test_message_queue_isolation(self):
        """Test that messages for one agent don't leak to another."""
        # Send message specifically to Designer
        self.message_queue.publish(
            sender=PROGRAMMER_ID,
            recipient=DESIGNER_ID,
            payload={"type": "solution", "content": "code here"}
        )
        
        # Programmer should not receive Designer's message
        programmer_messages = self.message_queue.get_messages(PROGRAMMER_ID)
        self.assertEqual(len(programmer_messages), 0)
        
        # Designer should receive the message
        designer_messages = self.message_queue.get_messages(DESIGNER_ID)
        self.assertEqual(len(designer_messages), 1)

    def test_message_queue_listener_integration(self):
        """Test listener functionality with agent communication."""
        received_messages = []
        
        def designer_listener(message):
            received_messages.append(message)
        
        # Register listener for Designer
        self.message_queue.listen(DESIGNER_ID, designer_listener)
        
        # Programmer sends message to Designer
        self.message_queue.publish(
            sender=PROGRAMMER_ID,
            recipient=DESIGNER_ID,
            payload={"type": "solution", "content": "int main() {}"}
        )
        
        # Listener should have been called
        self.assertEqual(len(received_messages), 1)
        self.assertEqual(received_messages[0].sender, PROGRAMMER_ID)


class TestMainAgentMQIntegration(unittest.TestCase):
    """Integration tests for main_agent_mq module."""
    
    @patch('main_agent_mq.AgentAI')
    def test_full_conversation_flow(self, mock_agent_class):
        """Test complete conversation flow with message queue."""
        # Create message queue
        mq = MessageQueue()
        
        try:
            # Create mock agents
            mock_designer = Mock()
            mock_programmer = Mock()
            
            # Configure mock to return different responses
            programmer_responses = [
                "int main() { return 0; }",  # Initial response
                "int main() { printf(\"Hello\"); return 0; }",  # After feedback 1
                "int main() { printf(\"Hello\\n\"); return 0; }"  # After feedback 2
            ]
            designer_responses = [
                "Add a print statement",
                "Add newline to print",
                "Looks good now"
            ]
            
            mock_programmer.get_response.side_effect = programmer_responses
            mock_designer.get_response.side_effect = designer_responses
            mock_programmer.save_to_excel = Mock()
            
            # Run conversation
            result = run_conversation(
                designer=mock_designer,
                programmer=mock_programmer,
                message_queue=mq,
                initial_prompt="Write hello world in C",
                max_iterations=2
            )
            
            # Verify the conversation progressed through all iterations
            self.assertEqual(mock_programmer.get_response.call_count, 3)
            self.assertEqual(mock_designer.get_response.call_count, 3)
            
        finally:
            mq.close()

    def test_message_queue_cleanup(self):
        """Test that message queue resources are properly cleaned up."""
        mq = MessageQueue()
        
        # Publish some messages
        mq.publish("Agent1", "Agent2", "test message")
        
        # Close the queue
        mq.close()
        
        # Verify connection is closed (will raise error if we try to use it)
        with self.assertRaises(Exception):
            mq.publish("Agent1", "Agent2", "should fail")


if __name__ == '__main__':
    unittest.main()
