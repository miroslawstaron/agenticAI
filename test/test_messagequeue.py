"""Tests for the MessageQueue class."""
import unittest
import os
import sys
import threading
import time
from unittest.mock import Mock

# Add parent directory to path to import messagequeue module
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from messagequeue import MessageQueue, Message
from test_fixtures import BaseAgentTestCase, MessageQueueTestCase


class TestMessage(BaseAgentTestCase):
    """Test cases for the Message class."""
    
    def test_message_initialization(self):
        """Test message object creation."""
        msg = Message(sender="agent1", recipient="agent2", payload={"data": "test"})
        self.assertEqual(msg.sender, "agent1")
        self.assertEqual(msg.recipient, "agent2")
        self.assertEqual(msg.payload, {"data": "test"})
        self.assertIsNone(msg.message_id)
    
    def test_message_with_id(self):
        """Test message with ID."""
        msg = Message(sender="agent1", recipient="agent2", payload="test", message_id=123)
        self.assertEqual(msg.message_id, 123)
    
    def test_message_to_dict(self):
        """Test message to dictionary conversion."""
        msg = Message(sender="agent1", recipient="agent2", payload={"key": "value"}, message_id=1)
        msg_dict = msg.to_dict()
        self.assertEqual(msg_dict['id'], 1)
        self.assertEqual(msg_dict['sender'], "agent1")
        self.assertEqual(msg_dict['recipient'], "agent2")
        self.assertEqual(msg_dict['payload'], {"key": "value"})
    
    def test_message_repr(self):
        """Test message string representation."""
        msg = Message(sender="agent1", recipient="agent2", payload="test", message_id=5)
        repr_str = repr(msg)
        self.assertIn("Message", repr_str)
        self.assertIn("id=5", repr_str)
        self.assertIn("agent1", repr_str)
        self.assertIn("agent2", repr_str)


class TestMessageQueue(MessageQueueTestCase):
    """Test cases for the MessageQueue class."""

    def setUp(self):
        """Set up test fixtures."""
        super().setUp()
        self.queue = MessageQueue()

    def tearDown(self):
        """Clean up after tests."""
        super().tearDown()
        self.queue.close()
    
    def test_initialization(self):
        """Test message queue initialization."""
        self.assertIsNotNone(self.queue.connection)
        self.assertIsNotNone(self.queue.lock)
        self.assertIsInstance(self.queue.listeners, dict)
        self.assertEqual(len(self.queue.listeners), 0)
    
    def test_publish_simple_message(self):
        """Test publishing a simple message."""
        msg_id = self.queue.publish("agent1", "agent2", "Hello")
        self.assertIsInstance(msg_id, int)
        self.assertGreater(msg_id, 0)
    
    def test_publish_with_dict_payload(self):
        """Test publishing a message with dictionary payload."""
        payload = {"type": "request", "data": [1, 2, 3]}
        msg_id = self.queue.publish("agent1", "agent2", payload)
        self.assertIsInstance(msg_id, int)
    
    def test_publish_with_list_payload(self):
        """Test publishing a message with list payload."""
        payload = [1, 2, 3, "test"]
        msg_id = self.queue.publish("agent1", "agent2", payload)
        self.assertIsInstance(msg_id, int)
    
    def test_publish_invalid_sender(self):
        """Test publishing with invalid sender."""
        with self.assertRaises(ValueError):
            self.queue.publish("", "agent2", "test")
        
        with self.assertRaises(ValueError):
            self.queue.publish(None, "agent2", "test")
    
    def test_publish_invalid_recipient(self):
        """Test publishing with invalid recipient."""
        with self.assertRaises(ValueError):
            self.queue.publish("agent1", "", "test")
        
        with self.assertRaises(ValueError):
            self.queue.publish("agent1", None, "test")
    
    def test_publish_non_serializable_payload(self):
        """Test publishing with non-JSON-serializable payload."""
        # Functions are not JSON-serializable
        with self.assertRaises(TypeError):
            self.queue.publish("agent1", "agent2", lambda x: x)
    
    def test_get_messages_for_specific_recipient(self):
        """Test retrieving messages for a specific recipient."""
        # Publish messages
        self.queue.publish("agent1", "agent2", "Message 1")
        self.queue.publish("agent1", "agent2", "Message 2")
        self.queue.publish("agent1", "agent3", "Message 3")
        
        # Get messages for agent2
        messages = self.queue.get_messages("agent2")
        self.assertEqual(len(messages), 2)
        self.assertEqual(messages[0].payload, "Message 1")
        self.assertEqual(messages[1].payload, "Message 2")
        
        # Get messages for agent3
        messages = self.queue.get_messages("agent3")
        self.assertEqual(len(messages), 1)
        self.assertEqual(messages[0].payload, "Message 3")
    
    def test_get_messages_broadcast(self):
        """Test retrieving broadcast messages."""
        # Publish broadcast and specific messages
        self.queue.publish("agent1", "broadcast", "Broadcast message")
        self.queue.publish("agent1", "agent2", "Direct message")
        
        # Agent2 should receive both broadcast and direct message
        messages = self.queue.get_messages("agent2")
        self.assertEqual(len(messages), 2)
        
        # Agent3 should only receive the broadcast message
        messages = self.queue.get_messages("agent3")
        self.assertEqual(len(messages), 1)
        self.assertEqual(messages[0].payload, "Broadcast message")
    
    def test_get_messages_anyone(self):
        """Test retrieving 'anyone' messages."""
        # Publish an "anyone" message
        self.queue.publish("agent1", "anyone", "First come, first served")
        
        # First agent to retrieve gets the message
        messages = self.queue.get_messages("agent2")
        self.assertEqual(len(messages), 1)
        self.assertEqual(messages[0].payload, "First come, first served")
        
        # Second agent should not get the consumed message
        messages = self.queue.get_messages("agent3")
        self.assertEqual(len(messages), 0)
    
    def test_get_messages_anyone_no_consume(self):
        """Test retrieving 'anyone' messages without consuming."""
        # Publish an "anyone" message
        self.queue.publish("agent1", "anyone", "Available to all")
        
        # Multiple agents can retrieve if consume=False
        messages = self.queue.get_messages("agent2", consume=False)
        self.assertEqual(len(messages), 1)
        
        messages = self.queue.get_messages("agent3", consume=False)
        self.assertEqual(len(messages), 1)
    
    def test_get_messages_invalid_recipient(self):
        """Test getting messages with invalid recipient."""
        with self.assertRaises(ValueError):
            self.queue.get_messages("")
        
        with self.assertRaises(ValueError):
            self.queue.get_messages(None)
    
    def test_get_messages_empty_queue(self):
        """Test getting messages from empty queue."""
        messages = self.queue.get_messages("agent1")
        self.assertEqual(len(messages), 0)
    
    def test_listen_callback(self):
        """Test listening with callback."""
        received_messages = []
        
        def callback(message):
            received_messages.append(message)
        
        # Register listener
        self.queue.listen("agent1", callback)
        
        # Publish a message
        self.queue.publish("agent2", "agent1", "Test message")
        
        # Callback should have been invoked
        self.assertEqual(len(received_messages), 1)
        self.assertEqual(received_messages[0].payload, "Test message")
        self.assertEqual(received_messages[0].sender, "agent2")
    
    def test_listen_broadcast(self):
        """Test listening to broadcast messages via broadcast listener."""
        received_messages = []
        
        def callback(message):
            received_messages.append(message)
        
        # Register listener for broadcast
        self.queue.listen("broadcast", callback)
        
        # Publish a broadcast message
        self.queue.publish("agent2", "broadcast", "Broadcast test")
        
        # Callback should receive broadcast message
        self.assertEqual(len(received_messages), 1)
        self.assertEqual(received_messages[0].payload, "Broadcast test")
    
    def test_listen_multiple_callbacks(self):
        """Test multiple callbacks for same recipient."""
        received1 = []
        received2 = []
        
        def callback1(message):
            received1.append(message)
        
        def callback2(message):
            received2.append(message)
        
        # Register multiple listeners
        self.queue.listen("agent1", callback1)
        self.queue.listen("agent1", callback2)
        
        # Publish a message
        self.queue.publish("agent2", "agent1", "Test")
        
        # Both callbacks should be invoked
        self.assertEqual(len(received1), 1)
        self.assertEqual(len(received2), 1)
    
    def test_listen_invalid_recipient(self):
        """Test listening with invalid recipient."""
        def callback(msg):
            pass
        
        with self.assertRaises(ValueError):
            self.queue.listen("", callback)
        
        with self.assertRaises(ValueError):
            self.queue.listen(None, callback)
    
    def test_listen_invalid_callback(self):
        """Test listening with invalid callback."""
        with self.assertRaises(ValueError):
            self.queue.listen("agent1", "not a function")
        
        with self.assertRaises(ValueError):
            self.queue.listen("agent1", None)
    
    def test_unlisten_specific_callback(self):
        """Test unregistering a specific callback."""
        received = []
        
        def callback(message):
            received.append(message)
        
        # Register and then unregister
        self.queue.listen("agent1", callback)
        self.queue.unlisten("agent1", callback)
        
        # Publish a message
        self.queue.publish("agent2", "agent1", "Test")
        
        # Callback should not be invoked
        self.assertEqual(len(received), 0)
    
    def test_unlisten_all_callbacks(self):
        """Test unregistering all callbacks for a recipient."""
        received1 = []
        received2 = []
        
        def callback1(message):
            received1.append(message)
        
        def callback2(message):
            received2.append(message)
        
        # Register multiple listeners
        self.queue.listen("agent1", callback1)
        self.queue.listen("agent1", callback2)
        
        # Unregister all
        self.queue.unlisten("agent1")
        
        # Publish a message
        self.queue.publish("agent2", "agent1", "Test")
        
        # No callbacks should be invoked
        self.assertEqual(len(received1), 0)
        self.assertEqual(len(received2), 0)
    
    def test_clear_messages_for_recipient(self):
        """Test clearing messages for a specific recipient."""
        # Publish messages
        self.queue.publish("agent1", "agent2", "Message 1")
        self.queue.publish("agent1", "agent2", "Message 2")
        self.queue.publish("agent1", "agent3", "Message 3")
        
        # Clear messages for agent2
        self.queue.clear_messages("agent2")
        
        # Agent2 should have no messages
        messages = self.queue.get_messages("agent2")
        self.assertEqual(len(messages), 0)
        
        # Agent3 should still have messages
        messages = self.queue.get_messages("agent3")
        self.assertEqual(len(messages), 1)
    
    def test_clear_all_messages(self):
        """Test clearing all messages."""
        # Publish messages
        self.queue.publish("agent1", "agent2", "Message 1")
        self.queue.publish("agent1", "agent3", "Message 2")
        
        # Clear all messages
        self.queue.clear_messages()
        
        # No agent should have messages
        self.assertEqual(len(self.queue.get_messages("agent2")), 0)
        self.assertEqual(len(self.queue.get_messages("agent3")), 0)
    
    def test_get_message_count(self):
        """Test getting message count."""
        # Initially empty
        self.assertEqual(self.queue.get_message_count(), 0)
        
        # Publish some messages
        self.queue.publish("agent1", "agent2", "Message 1")
        self.queue.publish("agent1", "agent2", "Message 2")
        self.queue.publish("agent1", "agent3", "Message 3")
        
        # Total count
        self.assertEqual(self.queue.get_message_count(), 3)
        
        # Count for specific recipient
        self.assertEqual(self.queue.get_message_count("agent2"), 2)
        self.assertEqual(self.queue.get_message_count("agent3"), 1)
    
    def test_get_message_count_with_consumed(self):
        """Test message count including consumed messages."""
        # Publish "anyone" message
        self.queue.publish("agent1", "anyone", "Test")
        
        # Get message (consumes it)
        self.queue.get_messages("agent2", consume=True)
        
        # Count without consumed
        self.assertEqual(self.queue.get_message_count("anyone", include_consumed=False), 0)
        
        # Count with consumed
        self.assertEqual(self.queue.get_message_count("anyone", include_consumed=True), 1)
    
    def test_thread_safety_publish(self):
        """Test thread-safe publishing."""
        def publish_messages():
            for i in range(10):
                self.queue.publish(f"agent{threading.current_thread().ident}", "test", i)
        
        threads = [threading.Thread(target=publish_messages) for _ in range(5)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        
        # Should have 50 messages total
        self.assertEqual(self.queue.get_message_count(), 50)
    
    def test_thread_safety_get_messages(self):
        """Test thread-safe message retrieval."""
        # Publish 10 "anyone" messages
        for i in range(10):
            self.queue.publish("agent1", "anyone", f"Message {i}")
        
        retrieved_messages = []
        lock = threading.Lock()
        
        def get_messages():
            messages = self.queue.get_messages(f"agent{threading.current_thread().ident}")
            with lock:
                retrieved_messages.extend(messages)
        
        threads = [threading.Thread(target=get_messages) for _ in range(5)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        
        # Each thread should get some messages, total should be 10
        self.assertEqual(len(retrieved_messages), 10)
    
    def test_listener_error_handling(self):
        """Test that listener errors don't crash the system."""
        successful_calls = []
        
        def bad_callback(message):
            raise Exception("Intentional error")
        
        def good_callback(message):
            successful_calls.append(message)
        
        # Register both callbacks
        self.queue.listen("agent1", bad_callback)
        self.queue.listen("agent1", good_callback)
        
        # Publish a message (should not crash despite bad_callback error)
        self.queue.publish("agent2", "agent1", "Test")
        
        # Good callback should still be invoked
        self.assertEqual(len(successful_calls), 1)
    
    def test_message_ordering(self):
        """Test that messages are retrieved in order."""
        # Publish messages in order
        for i in range(5):
            self.queue.publish("agent1", "agent2", f"Message {i}")
        
        # Retrieve and check order
        messages = self.queue.get_messages("agent2")
        self.assertEqual(len(messages), 5)
        for i, msg in enumerate(messages):
            self.assertEqual(msg.payload, f"Message {i}")
    
    def test_complex_payload(self):
        """Test complex nested payload."""
        complex_payload = {
            "type": "task",
            "data": {
                "nested": {
                    "values": [1, 2, 3],
                    "flags": {"active": True, "pending": False}
                }
            },
            "metadata": ["tag1", "tag2"]
        }
        
        msg_id = self.queue.publish("agent1", "agent2", complex_payload)
        messages = self.queue.get_messages("agent2")
        
        self.assertEqual(len(messages), 1)
        self.assertEqual(messages[0].payload, complex_payload)


if __name__ == '__main__':
    unittest.main()
