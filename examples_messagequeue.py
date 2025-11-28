#!/usr/bin/env python3
"""
Example usage of the MessageQueue for inter-agent communication.

This script demonstrates the key features of the MessageQueue:
1. Publishing messages to specific recipients
2. Broadcasting messages to all agents
3. Using "anyone" for first-come-first-served messages
4. Listening/hooking to messages with callbacks
"""

from messagequeue import MessageQueue


def example_basic_messaging():
    """Demonstrate basic message publishing and retrieval."""
    print("=== Example 1: Basic Messaging ===")
    
    # Create a message queue
    mq = MessageQueue()
    
    # Agent1 sends a message to Agent2
    msg_id = mq.publish(sender="Agent1", recipient="Agent2", payload="Hello, Agent2!")
    print(f"Agent1 sent message {msg_id} to Agent2")
    
    # Agent2 retrieves messages
    messages = mq.get_messages("Agent2")
    print(f"Agent2 received {len(messages)} message(s):")
    for msg in messages:
        print(f"  - From {msg.sender}: {msg.payload}")
    
    mq.close()
    print()


def example_broadcast():
    """Demonstrate broadcast messaging."""
    print("=== Example 2: Broadcast Messaging ===")
    
    mq = MessageQueue()
    
    # Agent1 broadcasts a message to all agents
    mq.publish(sender="Agent1", recipient="broadcast", 
               payload={"type": "announcement", "message": "System maintenance at 3 PM"})
    print("Agent1 broadcast a message to all agents")
    
    # Multiple agents can retrieve the broadcast
    for agent_name in ["Agent2", "Agent3", "Agent4"]:
        messages = mq.get_messages(agent_name)
        print(f"{agent_name} received {len(messages)} broadcast message(s):")
        for msg in messages:
            print(f"  - {msg.payload}")
    
    mq.close()
    print()


def example_anyone():
    """Demonstrate 'anyone' messaging (first-come-first-served)."""
    print("=== Example 3: 'Anyone' Messaging ===")
    
    mq = MessageQueue()
    
    # Agent1 publishes a task for anyone to pick up
    mq.publish(sender="Agent1", recipient="anyone", 
               payload={"task": "process_data", "data": [1, 2, 3, 4, 5]})
    print("Agent1 published a task for 'anyone'")
    
    # Agent2 picks up the task first
    messages = mq.get_messages("Agent2")
    if messages:
        print(f"Agent2 picked up task: {messages[0].payload}")
    
    # Agent3 tries to get the task but it's already consumed
    messages = mq.get_messages("Agent3")
    if not messages:
        print("Agent3 found no available tasks (already consumed)")
    
    mq.close()
    print()


def example_listeners():
    """Demonstrate listener/hook functionality."""
    print("=== Example 4: Listeners/Hooks ===")
    
    mq = MessageQueue()
    
    # Define a callback function for Agent2
    def agent2_handler(message):
        print(f"[Agent2 Listener] Received message from {message.sender}: {message.payload}")
    
    # Register the listener
    mq.listen("Agent2", agent2_handler)
    print("Agent2 registered a listener")
    
    # Agent1 sends messages to Agent2
    mq.publish(sender="Agent1", recipient="Agent2", payload="First message")
    mq.publish(sender="Agent1", recipient="Agent2", payload="Second message")
    
    # The listener was automatically invoked (messages printed above)
    print("Messages were automatically handled by the listener")
    
    # Agent2 can also retrieve messages normally
    messages = mq.get_messages("Agent2")
    print(f"Agent2 can still retrieve {len(messages)} message(s) from queue")
    
    mq.close()
    print()


def example_complex_workflow():
    """Demonstrate a complex multi-agent workflow."""
    print("=== Example 5: Complex Multi-Agent Workflow ===")
    
    mq = MessageQueue()
    
    # Track processed messages
    processed_tasks = []
    
    # Worker agents register listeners
    def worker_handler(agent_name):
        def handler(message):
            if message.payload.get("type") == "task":
                processed_tasks.append({
                    "worker": agent_name,
                    "task": message.payload.get("task_id")
                })
                print(f"[{agent_name}] Processing task {message.payload.get('task_id')}")
        return handler
    
    mq.listen("Worker1", worker_handler("Worker1"))
    mq.listen("Worker2", worker_handler("Worker2"))
    mq.listen("Worker3", worker_handler("Worker3"))
    print("Three workers registered listeners")
    
    # Manager sends tasks to specific workers
    mq.publish("Manager", "Worker1", {"type": "task", "task_id": "T1", "action": "compile"})
    mq.publish("Manager", "Worker2", {"type": "task", "task_id": "T2", "action": "test"})
    mq.publish("Manager", "Worker3", {"type": "task", "task_id": "T3", "action": "deploy"})
    print("Manager assigned tasks to workers")
    
    # Broadcast a status update
    mq.publish("Manager", "broadcast", {"type": "status", "message": "All tasks dispatched"})
    print("Manager broadcast status update")
    
    # All workers get the broadcast
    for worker in ["Worker1", "Worker2", "Worker3"]:
        messages = mq.get_messages(worker)
        status_messages = [m for m in messages if m.payload.get("type") == "status"]
        if status_messages:
            print(f"[{worker}] Received status: {status_messages[0].payload.get('message')}")
    
    print(f"\nProcessed tasks: {processed_tasks}")
    
    mq.close()
    print()


def example_message_count_and_clear():
    """Demonstrate message count and clearing."""
    print("=== Example 6: Message Count and Clearing ===")
    
    mq = MessageQueue()
    
    # Send some messages
    mq.publish("Agent1", "Agent2", "Message 1")
    mq.publish("Agent1", "Agent2", "Message 2")
    mq.publish("Agent1", "Agent3", "Message 3")
    
    print(f"Total messages in queue: {mq.get_message_count()}")
    print(f"Messages for Agent2: {mq.get_message_count('Agent2')}")
    print(f"Messages for Agent3: {mq.get_message_count('Agent3')}")
    
    # Clear messages for Agent2
    mq.clear_messages("Agent2")
    print(f"\nAfter clearing Agent2's messages:")
    print(f"Total messages in queue: {mq.get_message_count()}")
    print(f"Messages for Agent2: {mq.get_message_count('Agent2')}")
    
    # Clear all messages
    mq.clear_messages()
    print(f"\nAfter clearing all messages:")
    print(f"Total messages in queue: {mq.get_message_count()}")
    
    mq.close()
    print()


if __name__ == "__main__":
    print("MessageQueue Examples\n")
    
    example_basic_messaging()
    example_broadcast()
    example_anyone()
    example_listeners()
    example_complex_workflow()
    example_message_count_and_clear()
    
    print("All examples completed!")
