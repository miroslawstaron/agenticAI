"""
SQLite-based message queue for inter-agent communication.

This module provides a simple in-memory message queue that allows agents to
communicate asynchronously through messages. Messages can be sent to specific
recipients, broadcast to all agents, or sent to anyone who retrieves them first.
"""

import sqlite3
import threading
import json
from typing import Optional, Dict, Any, List, Callable
from datetime import datetime, timezone


class Message:
    """Represents a message in the queue."""
    
    def __init__(self, sender: str, recipient: str, payload: Any, message_id: Optional[int] = None):
        """
        Initialize a message.
        
        Args:
            sender: The name/identifier of the message sender
            recipient: The recipient name, "broadcast", or "anyone"
            payload: The message payload (any JSON-serializable data)
            message_id: Optional message ID (auto-assigned by database)
        """
        self.sender = sender
        self.recipient = recipient
        self.payload = payload
        self.message_id = message_id
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert message to dictionary."""
        return {
            'id': self.message_id,
            'sender': self.sender,
            'recipient': self.recipient,
            'payload': self.payload
        }
    
    def __repr__(self):
        return f"Message(id={self.message_id}, sender='{self.sender}', recipient='{self.recipient}')"


class MessageQueue:
    """
    In-memory SQLite message queue for agent communication.
    
    This class provides a thread-safe message queue that supports:
    - Publishing messages to specific recipients, broadcast, or anyone
    - Retrieving messages for a specific recipient
    - Listening/hooking to messages for automatic callback execution
    """
    
    def __init__(self):
        """Initialize the in-memory SQLite message queue."""
        self.connection = sqlite3.connect(':memory:', check_same_thread=False)
        self.lock = threading.Lock()
        self.listeners: Dict[str, List[Callable[[Message], None]]] = {}
        self._initialize_database()
    
    def _initialize_database(self):
        """Create the messages table in the SQLite database."""
        with self.lock:
            cursor = self.connection.cursor()
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS messages (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    sender TEXT NOT NULL,
                    recipient TEXT NOT NULL,
                    payload TEXT NOT NULL,
                    timestamp TEXT NOT NULL,
                    consumed INTEGER DEFAULT 0
                )
            ''')
            cursor.execute('''
                CREATE INDEX IF NOT EXISTS idx_recipient ON messages(recipient)
            ''')
            cursor.execute('''
                CREATE INDEX IF NOT EXISTS idx_consumed ON messages(consumed)
            ''')
            self.connection.commit()
    
    def publish(self, sender: str, recipient: str, payload: Any) -> int:
        """
        Publish a message to the queue.
        
        Args:
            sender: The name/identifier of the message sender
            recipient: The recipient name, "broadcast", or "anyone"
            payload: The message payload (any JSON-serializable data)
        
        Returns:
            The ID of the published message
        
        Raises:
            ValueError: If sender or recipient is empty
            TypeError: If payload is not JSON-serializable
        """
        if not sender or not isinstance(sender, str):
            raise ValueError("Sender must be a non-empty string")
        if not recipient or not isinstance(recipient, str):
            raise ValueError("Recipient must be a non-empty string")
        
        # Serialize payload to JSON
        try:
            payload_json = json.dumps(payload)
        except (TypeError, ValueError) as e:
            raise TypeError(f"Payload must be JSON-serializable: {e}")
        
        timestamp = datetime.now(timezone.utc).isoformat()
        
        with self.lock:
            cursor = self.connection.cursor()
            cursor.execute('''
                INSERT INTO messages (sender, recipient, payload, timestamp, consumed)
                VALUES (?, ?, ?, ?, 0)
            ''', (sender, recipient, payload_json, timestamp))
            message_id = cursor.lastrowid
            self.connection.commit()
        
        # Create message object for listeners
        message = Message(sender, recipient, payload, message_id)
        
        # Trigger listeners for this recipient
        self._trigger_listeners(recipient, message)
        
        # Also trigger broadcast listeners
        if recipient != "broadcast":
            self._trigger_listeners("broadcast", message)
        
        return message_id
    
    def get_messages(self, recipient: str, consume: bool = True) -> List[Message]:
        """
        Retrieve messages for a specific recipient.
        
        This method retrieves messages that match:
        - Exact recipient name match
        - "broadcast" messages
        - "anyone" messages (if consume=True, marks them as consumed)
        
        Args:
            recipient: The recipient name to retrieve messages for
            consume: If True, marks "anyone" messages as consumed (default: True)
        
        Returns:
            List of Message objects
        
        Raises:
            ValueError: If recipient is empty
        """
        if not recipient or not isinstance(recipient, str):
            raise ValueError("Recipient must be a non-empty string")
        
        messages = []
        
        with self.lock:
            cursor = self.connection.cursor()
            
            # Get messages for specific recipient and broadcast messages
            cursor.execute('''
                SELECT id, sender, recipient, payload, timestamp
                FROM messages
                WHERE (recipient = ? OR recipient = 'broadcast')
                AND consumed = 0
                ORDER BY id ASC
            ''', (recipient,))
            
            rows = cursor.fetchall()
            for row in rows:
                msg_id, sender, recipient_name, payload_json, timestamp = row
                payload = json.loads(payload_json)
                messages.append(Message(sender, recipient_name, payload, msg_id))
            
            # Get "anyone" messages (first come, first served)
            cursor.execute('''
                SELECT id, sender, recipient, payload, timestamp
                FROM messages
                WHERE recipient = 'anyone'
                AND consumed = 0
                ORDER BY id ASC
            ''')
            
            anyone_rows = cursor.fetchall()
            for row in anyone_rows:
                msg_id, sender, recipient_name, payload_json, timestamp = row
                payload = json.loads(payload_json)
                messages.append(Message(sender, recipient_name, payload, msg_id))
                
                # Mark "anyone" messages as consumed if requested
                if consume:
                    cursor.execute('''
                        UPDATE messages SET consumed = 1 WHERE id = ?
                    ''', (msg_id,))
            
            # Mark broadcast messages as consumed for this retrieval
            # (to avoid re-delivery, we'd need a separate consumed_by table,
            # but for simplicity, we don't mark broadcast as consumed)
            
            self.connection.commit()
        
        return messages
    
    def listen(self, recipient: str, callback: Callable[[Message], None]):
        """
        Register a callback function to be invoked when messages arrive.
        
        The callback will be invoked for:
        - Messages sent directly to the recipient
        - Broadcast messages (if recipient is not "broadcast")
        
        Args:
            recipient: The recipient name to listen for
            callback: Function to call with Message object when a message arrives
        
        Raises:
            ValueError: If recipient is empty or callback is not callable
        """
        if not recipient or not isinstance(recipient, str):
            raise ValueError("Recipient must be a non-empty string")
        if not callable(callback):
            raise ValueError("Callback must be a callable function")
        
        with self.lock:
            if recipient not in self.listeners:
                self.listeners[recipient] = []
            self.listeners[recipient].append(callback)
    
    def unlisten(self, recipient: str, callback: Optional[Callable[[Message], None]] = None):
        """
        Unregister a callback function or all callbacks for a recipient.
        
        Args:
            recipient: The recipient name to stop listening for
            callback: Specific callback to remove, or None to remove all callbacks
        """
        with self.lock:
            if recipient in self.listeners:
                if callback is None:
                    # Remove all listeners for this recipient
                    del self.listeners[recipient]
                else:
                    # Remove specific listener
                    if callback in self.listeners[recipient]:
                        self.listeners[recipient].remove(callback)
                    # Clean up empty list
                    if not self.listeners[recipient]:
                        del self.listeners[recipient]
    
    def _trigger_listeners(self, recipient: str, message: Message):
        """
        Trigger all registered listeners for a recipient.
        
        Args:
            recipient: The recipient name
            message: The message to pass to listeners
        """
        # Note: We don't lock here since this is called from locked methods
        if recipient in self.listeners:
            for callback in self.listeners[recipient]:
                try:
                    callback(message)
                except Exception as e:
                    # Log error but don't crash
                    print(f"Error in listener callback for {recipient}: {e}")
    
    def clear_messages(self, recipient: Optional[str] = None):
        """
        Clear messages from the queue.
        
        Args:
            recipient: If provided, only clear messages for this recipient.
                      If None, clear all messages.
        """
        with self.lock:
            cursor = self.connection.cursor()
            if recipient:
                cursor.execute('''
                    DELETE FROM messages WHERE recipient = ?
                ''', (recipient,))
            else:
                cursor.execute('DELETE FROM messages')
            self.connection.commit()
    
    def get_message_count(self, recipient: Optional[str] = None, include_consumed: bool = False) -> int:
        """
        Get the count of messages in the queue.
        
        Args:
            recipient: If provided, count only messages for this recipient.
                      If None, count all messages.
            include_consumed: If True, include consumed messages in count
        
        Returns:
            Number of messages
        """
        with self.lock:
            cursor = self.connection.cursor()
            if recipient:
                if include_consumed:
                    cursor.execute('SELECT COUNT(*) FROM messages WHERE recipient = ?', (recipient,))
                else:
                    cursor.execute('SELECT COUNT(*) FROM messages WHERE recipient = ? AND consumed = 0', (recipient,))
            else:
                if include_consumed:
                    cursor.execute('SELECT COUNT(*) FROM messages')
                else:
                    cursor.execute('SELECT COUNT(*) FROM messages WHERE consumed = 0')
            count = cursor.fetchone()[0]
        return count
    
    def close(self):
        """Close the database connection."""
        with self.lock:
            self.connection.close()
    
    def __del__(self):
        """Cleanup: close the database connection."""
        try:
            self.connection.close()
        except:
            pass
