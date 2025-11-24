# MessageQueue

A lightweight, thread-safe, in-memory SQLite message queue for inter-agent communication in the agenticAI project.

## Features

- **In-memory SQLite database** for fast message storage and retrieval
- **Thread-safe** operations with proper locking mechanisms
- **Simple API** with just three main methods: `publish()`, `get_messages()`, and `listen()`
- **Multiple recipient modes**:
  - Specific recipient (point-to-point messaging)
  - `"broadcast"` - message sent to all agents
  - `"anyone"` - first-come-first-served message consumption
- **Listener/Hook support** for automatic message handling via callbacks
- **JSON-serializable payloads** supporting complex nested data structures

## Installation

No additional dependencies required beyond the standard library. The MessageQueue uses only built-in Python modules:
- `sqlite3`
- `threading`
- `json`
- `typing`
- `datetime`

## Quick Start

```python
from messagequeue import MessageQueue

# Create a message queue
mq = MessageQueue()

# Agent1 sends a message to Agent2
mq.publish(sender="Agent1", recipient="Agent2", payload="Hello!")

# Agent2 retrieves messages
messages = mq.get_messages("Agent2")
for msg in messages:
    print(f"From {msg.sender}: {msg.payload}")

# Clean up
mq.close()
```

## API Reference

### MessageQueue Class

#### `__init__()`
Initialize a new in-memory message queue.

```python
mq = MessageQueue()
```

#### `publish(sender, recipient, payload) -> int`
Publish a message to the queue.

**Parameters:**
- `sender` (str): Name/identifier of the message sender
- `recipient` (str): Recipient name, `"broadcast"`, or `"anyone"`
- `payload` (Any): Any JSON-serializable data

**Returns:**
- `int`: Message ID

**Example:**
```python
msg_id = mq.publish("Agent1", "Agent2", {"task": "compile", "file": "main.c"})
```

#### `get_messages(recipient, consume=True) -> List[Message]`
Retrieve messages for a specific recipient.

**Parameters:**
- `recipient` (str): The recipient name to retrieve messages for
- `consume` (bool): If True, marks "anyone" messages as consumed (default: True)

**Returns:**
- `List[Message]`: List of Message objects

**Note:** This method retrieves:
- Messages sent directly to the recipient
- All `"broadcast"` messages
- Available `"anyone"` messages (consumed if `consume=True`)

**Example:**
```python
messages = mq.get_messages("Agent2")
for msg in messages:
    print(msg.payload)
```

#### `listen(recipient, callback)`
Register a callback function to be invoked when messages arrive.

**Parameters:**
- `recipient` (str): The recipient name to listen for
- `callback` (Callable[[Message], None]): Function to call when messages arrive

**Example:**
```python
def my_handler(message):
    print(f"Received: {message.payload}")

mq.listen("Agent2", my_handler)
mq.publish("Agent1", "Agent2", "Hello!")  # my_handler is automatically called
```

#### `unlisten(recipient, callback=None)`
Unregister callback function(s).

**Parameters:**
- `recipient` (str): The recipient name
- `callback` (Callable, optional): Specific callback to remove, or None to remove all

**Example:**
```python
mq.unlisten("Agent2", my_handler)  # Remove specific handler
mq.unlisten("Agent2")              # Remove all handlers for Agent2
```

#### `clear_messages(recipient=None)`
Clear messages from the queue.

**Parameters:**
- `recipient` (str, optional): If provided, only clear messages for this recipient. If None, clear all messages.

**Example:**
```python
mq.clear_messages("Agent2")  # Clear Agent2's messages
mq.clear_messages()          # Clear all messages
```

#### `get_message_count(recipient=None, include_consumed=False) -> int`
Get the count of messages in the queue.

**Parameters:**
- `recipient` (str, optional): If provided, count only messages for this recipient
- `include_consumed` (bool): If True, include consumed messages in count

**Returns:**
- `int`: Number of messages

**Example:**
```python
total = mq.get_message_count()
agent2_count = mq.get_message_count("Agent2")
```

#### `close()`
Close the database connection. Always call this when done with the queue.

```python
mq.close()
```

### Message Class

The `Message` class represents a message in the queue.

**Attributes:**
- `sender` (str): Message sender
- `recipient` (str): Message recipient
- `payload` (Any): Message payload
- `message_id` (int): Unique message ID

**Methods:**
- `to_dict()`: Convert message to dictionary

## Usage Examples

### 1. Basic Point-to-Point Messaging

```python
mq = MessageQueue()

# Send a message
mq.publish("Designer", "Programmer", "Please implement bubble sort")

# Retrieve messages
messages = mq.get_messages("Programmer")
print(messages[0].payload)  # "Please implement bubble sort"

mq.close()
```

### 2. Broadcast Messaging

```python
mq = MessageQueue()

# Broadcast to all agents
mq.publish("Manager", "broadcast", {
    "type": "announcement",
    "message": "System maintenance at 3 PM"
})

# All agents receive the broadcast
for agent in ["Agent1", "Agent2", "Agent3"]:
    messages = mq.get_messages(agent)
    print(f"{agent} received: {messages[0].payload}")

mq.close()
```

### 3. "Anyone" Messaging (Task Queue)

```python
mq = MessageQueue()

# Publish tasks for anyone to pick up
mq.publish("Manager", "anyone", {"task_id": 1, "action": "process_data"})
mq.publish("Manager", "anyone", {"task_id": 2, "action": "generate_report"})

# Workers pick up tasks on a first-come-first-served basis
task1 = mq.get_messages("Worker1")  # Gets task_id 1
task2 = mq.get_messages("Worker2")  # Gets task_id 2
task3 = mq.get_messages("Worker3")  # Gets nothing (no more tasks)

mq.close()
```

### 4. Listener/Hook Pattern

```python
mq = MessageQueue()

# Define a handler
def compile_handler(message):
    if message.payload.get("action") == "compile":
        print(f"Compiling: {message.payload.get('file')}")

# Register listener
mq.listen("CompilerAgent", compile_handler)

# Send a message (handler is automatically invoked)
mq.publish("Designer", "CompilerAgent", {
    "action": "compile",
    "file": "program.c"
})

mq.close()
```

### 5. Complex Multi-Agent Workflow

```python
mq = MessageQueue()

# Setup listeners for workers
def worker_listener(worker_name):
    def handler(msg):
        print(f"[{worker_name}] Processing: {msg.payload.get('task')}")
    return handler

mq.listen("Worker1", worker_listener("Worker1"))
mq.listen("Worker2", worker_listener("Worker2"))

# Manager distributes work
mq.publish("Manager", "Worker1", {"task": "compile", "file": "main.c"})
mq.publish("Manager", "Worker2", {"task": "test", "suite": "unit_tests"})

# Manager broadcasts status
mq.publish("Manager", "broadcast", {"status": "All tasks dispatched"})

# Workers can retrieve messages manually too
messages = mq.get_messages("Worker1")

mq.close()
```

## Thread Safety

The MessageQueue is thread-safe and can be used safely across multiple threads:

```python
import threading

mq = MessageQueue()

def worker():
    for i in range(10):
        mq.publish(f"Thread-{threading.current_thread().name}", 
                  "collector", 
                  f"Message {i}")

threads = [threading.Thread(target=worker) for _ in range(5)]
for t in threads:
    t.start()
for t in threads:
    t.join()

# All messages safely stored
messages = mq.get_messages("collector")
print(f"Received {len(messages)} messages")  # 50 messages

mq.close()
```

## Message Structure

Messages contain three key components:

1. **sender**: The originator of the message (string)
2. **recipient**: The intended recipient (string: agent name, "broadcast", or "anyone")
3. **payload**: The message data (any JSON-serializable type)

The payload can be:
- Simple types: strings, numbers, booleans
- Collections: lists, dictionaries
- Complex nested structures

```python
# Simple payload
mq.publish("Agent1", "Agent2", "Hello")

# Dictionary payload
mq.publish("Agent1", "Agent2", {"action": "compile", "file": "main.c"})

# Complex nested payload
mq.publish("Agent1", "Agent2", {
    "type": "task",
    "metadata": {
        "priority": "high",
        "tags": ["urgent", "bug-fix"]
    },
    "data": [1, 2, 3, 4, 5]
})
```

## Best Practices

1. **Always close the queue** when done: `mq.close()`
2. **Use specific recipient names** when possible for better performance
3. **Keep payloads JSON-serializable** to avoid errors
4. **Handle listener errors** gracefully - exceptions in listeners are caught and logged
5. **Use "anyone" mode** for work distribution among multiple workers
6. **Use "broadcast" mode** for announcements to all agents
7. **Clear consumed messages** periodically if running long-lived processes

## Testing

Run the comprehensive test suite:

```bash
python -m unittest test.test_messagequeue -v
```

## Examples

See `examples_messagequeue.py` for detailed usage examples:

```bash
python examples_messagequeue.py
```

## License

This module is part of the agenticAI project and follows the same license.
