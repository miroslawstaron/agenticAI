"""
Unit tests for main_agent_mq_logging.py

Tests the event-driven agent communication with logging.
"""

import unittest
from unittest.mock import Mock, MagicMock, patch, call
import threading
import time
from io import StringIO

from main_agent_mq_logging import (
    create_agents,
    AgentWorker,
    ConversationOrchestrator,
    DESIGNER_ID,
    PROGRAMMER_ID,
    USER_ID,
)
from messagequeue import MessageQueue, reset_message_queue
from logger import SingletonLogger


class TestCreateAgents(unittest.TestCase):
    """Test agent creation."""
    
    def test_create_agents_success(self):
        """Test successful agent creation."""
        designer, programmer = create_agents(
            server_address="http://localhost:11434",
            api_key="test_key"
        )
        
        self.assertIsNotNone(designer)
        self.assertIsNotNone(programmer)
        self.assertEqual(designer.server_address, "http://localhost:11434")
        self.assertEqual(programmer.server_address, "http://localhost:11434")
    
    def test_create_agents_with_empty_api_key(self):
        """Test agent creation with empty API key."""
        designer, programmer = create_agents(
            server_address="http://localhost:11434",
            api_key=""
        )
        
        self.assertIsNotNone(designer)
        self.assertIsNotNone(programmer)
    
    @patch('main_agent_mq_logging.AgentAI')
    def test_create_agents_logging(self, mock_agent_ai):
        """Test that agent creation logs appropriately."""
        create_agents("http://localhost:11434", "test_key")
        
        # Verify AgentAI was called twice (for designer and programmer)
        self.assertEqual(mock_agent_ai.call_count, 2)


class TestAgentWorker(unittest.TestCase):
    """Test AgentWorker class."""
    
    def setUp(self):
        """Set up test fixtures."""
        reset_message_queue()
        self.message_queue = MessageQueue()
        self.mock_agent = Mock()
        self.mock_agent.get_response.return_value = "Test response"
        self.mock_agent.messages = []
    
    def tearDown(self):
        """Clean up after tests."""
        reset_message_queue()
    
    def test_agent_worker_initialization(self):
        """Test AgentWorker initialization."""
        worker = AgentWorker(
            agent_id=PROGRAMMER_ID,
            agent=self.mock_agent,
            message_queue=self.message_queue,
            other_agent_id=DESIGNER_ID
        )
        
        self.assertEqual(worker.agent_id, PROGRAMMER_ID)
        self.assertEqual(worker.other_agent_id, DESIGNER_ID)
        self.assertFalse(worker.is_running)
        self.assertEqual(worker.iteration_count, 0)
    
    def test_agent_worker_start_and_stop(self):
        """Test starting and stopping an agent worker."""
        worker = AgentWorker(
            agent_id=PROGRAMMER_ID,
            agent=self.mock_agent,
            message_queue=self.message_queue,
            other_agent_id=DESIGNER_ID
        )
        
        worker.start()
        self.assertTrue(worker.is_running)
        self.assertIsNotNone(worker.thread)
        
        worker.stop()
        self.assertFalse(worker.is_running)
    
    def test_agent_worker_process_task_message(self):
        """Test processing an initial task message."""
        worker = AgentWorker(
            agent_id=PROGRAMMER_ID,
            agent=self.mock_agent,
            message_queue=self.message_queue,
            other_agent_id=DESIGNER_ID
        )
        
        # Create a task message
        self.message_queue.publish(
            sender=USER_ID,
            recipient=PROGRAMMER_ID,
            payload={
                "type": "task",
                "content": "Write a hello world program",
                "iteration": 0
            }
        )
        
        # Get the message and process it
        messages = self.message_queue.get_messages(PROGRAMMER_ID, consume=True)
        self.assertEqual(len(messages), 1)
        
        worker._process_message(messages[0])
        
        # Verify agent was called
        self.mock_agent.get_response.assert_called_once()
        
        # Verify response was sent to designer
        designer_messages = self.message_queue.get_messages(DESIGNER_ID)
        self.assertEqual(len(designer_messages), 1)
        self.assertEqual(designer_messages[0].payload["type"], "solution")
    
    def test_agent_worker_process_solution_message(self):
        """Test processing a solution message."""
        worker = AgentWorker(
            agent_id=DESIGNER_ID,
            agent=self.mock_agent,
            message_queue=self.message_queue,
            other_agent_id=PROGRAMMER_ID
        )
        
        # Create a solution message
        self.message_queue.publish(
            sender=PROGRAMMER_ID,
            recipient=DESIGNER_ID,
            payload={
                "type": "solution",
                "content": "Code solution here",
                "original_task": "Write a program",
                "iteration": 0
            }
        )
        
        # Get the message and process it
        messages = self.message_queue.get_messages(DESIGNER_ID, consume=True)
        self.assertEqual(len(messages), 1)
        
        worker._process_message(messages[0])
        
        # Verify agent was called with appropriate prompt
        self.mock_agent.get_response.assert_called_once()
        call_args = self.mock_agent.get_response.call_args[0][0]
        self.assertIn("how can I improve", call_args)
    
    def test_agent_worker_process_feedback_message(self):
        """Test processing a feedback message."""
        worker = AgentWorker(
            agent_id=PROGRAMMER_ID,
            agent=self.mock_agent,
            message_queue=self.message_queue,
            other_agent_id=DESIGNER_ID
        )
        
        # Create a feedback message
        self.message_queue.publish(
            sender=DESIGNER_ID,
            recipient=PROGRAMMER_ID,
            payload={
                "type": "feedback",
                "content": "Please improve variable naming",
                "iteration": 0
            }
        )
        
        # Get the message and process it
        messages = self.message_queue.get_messages(PROGRAMMER_ID, consume=True)
        self.assertEqual(len(messages), 1)
        
        worker._process_message(messages[0])
        
        # Verify agent was called
        self.mock_agent.get_response.assert_called_once()
        
        # Verify solution was sent back
        designer_messages = self.message_queue.get_messages(DESIGNER_ID)
        self.assertEqual(len(designer_messages), 1)
        self.assertEqual(designer_messages[0].payload["type"], "solution")
    
    def test_agent_worker_max_iterations(self):
        """Test that max iterations are respected."""
        worker = AgentWorker(
            agent_id=DESIGNER_ID,
            agent=self.mock_agent,
            message_queue=self.message_queue,
            other_agent_id=PROGRAMMER_ID
        )
        
        # Set MAX_ITERATIONS to 2 for testing
        import main_agent_mq_logging
        original_max = main_agent_mq_logging.MAX_ITERATIONS
        main_agent_mq_logging.MAX_ITERATIONS = 2
        
        try:
            # Simulate final iteration
            self.message_queue.publish(
                sender=PROGRAMMER_ID,
                recipient=DESIGNER_ID,
                payload={
                    "type": "solution",
                    "content": "Final solution",
                    "iteration": 1  # This is the last iteration
                }
            )
            
            messages = self.message_queue.get_messages(DESIGNER_ID, consume=True)
            worker._process_message(messages[0])
            
            # Check for completion message
            completion_messages = self.message_queue.get_messages("completion")
            self.assertEqual(len(completion_messages), 1)
            self.assertEqual(completion_messages[0].payload["type"], "done")
        finally:
            main_agent_mq_logging.MAX_ITERATIONS = original_max


class TestConversationOrchestrator(unittest.TestCase):
    """Test ConversationOrchestrator class."""
    
    def setUp(self):
        """Set up test fixtures."""
        reset_message_queue()
        self.message_queue = MessageQueue()
        
        self.mock_designer = Mock()
        self.mock_designer.get_response.return_value = "Design feedback"
        self.mock_designer.messages = []
        self.mock_designer.save_to_excel = Mock()
        
        self.mock_programmer = Mock()
        self.mock_programmer.get_response.return_value = "Code solution"
        self.mock_programmer.messages = []
        self.mock_programmer.save_to_excel = Mock()
    
    def tearDown(self):
        """Clean up after tests."""
        reset_message_queue()
    
    def test_orchestrator_initialization(self):
        """Test orchestrator initialization."""
        orchestrator = ConversationOrchestrator(
            self.mock_designer,
            self.mock_programmer,
            self.message_queue
        )
        
        self.assertIsNotNone(orchestrator.programmer_worker)
        self.assertIsNotNone(orchestrator.designer_worker)
        self.assertFalse(orchestrator.is_running)
    
    def test_orchestrator_start(self):
        """Test starting the orchestrator."""
        orchestrator = ConversationOrchestrator(
            self.mock_designer,
            self.mock_programmer,
            self.message_queue
        )
        
        orchestrator.start("Write a program")
        self.assertTrue(orchestrator.is_running)
        
        # Verify initial prompt was published
        messages = self.message_queue.get_messages(PROGRAMMER_ID, consume=True)
        self.assertEqual(len(messages), 1)
        self.assertEqual(messages[0].payload["type"], "task")
        self.assertEqual(messages[0].payload["content"], "Write a program")
        
        orchestrator.stop()
    
    def test_orchestrator_wait_for_completion_timeout(self):
        """Test wait_for_completion with timeout."""
        orchestrator = ConversationOrchestrator(
            self.mock_designer,
            self.mock_programmer,
            self.message_queue
        )
        
        orchestrator.start("Quick test")
        
        # Wait with very short timeout
        completed = orchestrator.wait_for_completion(timeout=0.5)
        
        # Should timeout since no completion message is published
        self.assertFalse(completed)
        
        orchestrator.stop()
    
    def test_orchestrator_wait_for_completion_success(self):
        """Test wait_for_completion with successful completion."""
        orchestrator = ConversationOrchestrator(
            self.mock_designer,
            self.mock_programmer,
            self.message_queue
        )
        
        orchestrator.start("Test")
        
        # Publish completion message in a separate thread
        def publish_completion():
            time.sleep(0.5)
            self.message_queue.publish(
                sender=DESIGNER_ID,
                recipient="completion",
                payload={"type": "done", "iteration": 1}
            )
        
        thread = threading.Thread(target=publish_completion, daemon=True)
        thread.start()
        
        # Wait for completion
        completed = orchestrator.wait_for_completion(timeout=5)
        
        self.assertTrue(completed)
        
        orchestrator.stop()
        thread.join(timeout=2)
    
    def test_orchestrator_stop(self):
        """Test stopping the orchestrator."""
        orchestrator = ConversationOrchestrator(
            self.mock_designer,
            self.mock_programmer,
            self.message_queue,
            output_file="test_output.xlsx"
        )
        
        orchestrator.start("Test")
        orchestrator.stop()
        
        self.assertFalse(orchestrator.is_running)
        # Verify save was called
        self.mock_programmer.save_to_excel.assert_called()


class TestAgentCommunicationFlow(unittest.TestCase):
    """Test complete communication flow between agents."""
    
    def setUp(self):
        """Set up test fixtures."""
        reset_message_queue()
        self.message_queue = MessageQueue()
        
        self.mock_designer = Mock()
        self.mock_designer.get_response.side_effect = ["Design feedback"]
        self.mock_designer.messages = []
        self.mock_designer.save_to_excel = Mock()
        
        self.mock_programmer = Mock()
        self.mock_programmer.get_response.side_effect = ["Initial solution"]
        self.mock_programmer.messages = []
        self.mock_programmer.save_to_excel = Mock()
    
    def tearDown(self):
        """Clean up after tests."""
        reset_message_queue()
    
    def test_single_message_exchange(self):
        """Test a single message exchange between agents."""
        # Create workers
        programmer_worker = AgentWorker(
            PROGRAMMER_ID,
            self.mock_programmer,
            self.message_queue,
            DESIGNER_ID
        )
        
        designer_worker = AgentWorker(
            DESIGNER_ID,
            self.mock_designer,
            self.message_queue,
            PROGRAMMER_ID
        )
        
        # Send initial task to programmer
        self.message_queue.publish(
            sender=USER_ID,
            recipient=PROGRAMMER_ID,
            payload={"type": "task", "content": "Write a program", "iteration": 0}
        )
        
        # Process by programmer
        messages = self.message_queue.get_messages(PROGRAMMER_ID, consume=True)
        programmer_worker._process_message(messages[0])
        
        # Verify designer received the solution
        designer_messages = self.message_queue.get_messages(DESIGNER_ID, consume=True)
        self.assertGreaterEqual(len(designer_messages), 1)
        # Find the solution message (not broadcast)
        solution_messages = [m for m in designer_messages if m.payload["type"] == "solution"]
        self.assertEqual(len(solution_messages), 1)
        
        # Process by designer
        designer_worker._process_message(solution_messages[0])
        
        # Verify programmer received feedback
        programmer_messages = self.message_queue.get_messages(PROGRAMMER_ID, consume=True)
        feedback_messages = [m for m in programmer_messages if m.payload["type"] == "feedback"]
        self.assertEqual(len(feedback_messages), 1)


class TestConversationIntegration(unittest.TestCase):
    """Integration tests for the full conversation system."""
    
    def setUp(self):
        """Set up test fixtures."""
        reset_message_queue()
    
    def tearDown(self):
        """Clean up after tests."""
        reset_message_queue()
    
    @patch('main_agent_mq_logging.AgentAI')
    def test_full_conversation_initialization(self, mock_agent_ai):
        """Test full conversation system initialization."""
        mock_agent_ai.return_value.get_response.return_value = "Test response"
        mock_agent_ai.return_value.messages = []
        mock_agent_ai.return_value.save_to_excel = Mock()
        
        designer, programmer = create_agents("http://localhost:11434", "test_key")
        message_queue = MessageQueue()
        
        orchestrator = ConversationOrchestrator(
            designer,
            programmer,
            message_queue
        )
        
        self.assertIsNotNone(orchestrator)
        self.assertTrue(len([orchestrator.programmer_worker, orchestrator.designer_worker]) == 2)
    
    def test_message_queue_persistence(self):
        """Test that messages persist in the queue."""
        message_queue = MessageQueue()
        
        # Send multiple messages
        for i in range(3):
            message_queue.publish(
                sender="Sender",
                recipient=PROGRAMMER_ID,
                payload={"type": "test", "content": f"Message {i}"}
            )
        
        # Retrieve messages
        messages = message_queue.get_messages(PROGRAMMER_ID, consume=False)
        self.assertEqual(len(messages), 3)
        
        # Retrieve again without consuming
        messages2 = message_queue.get_messages(PROGRAMMER_ID, consume=False)
        self.assertEqual(len(messages2), 3)


if __name__ == '__main__':
    unittest.main()
