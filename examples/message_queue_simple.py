"""Simple example: Designer → Programmer → Compiler conversation via MessageQueue.

This example demonstrates inter-agent communication using the MessageQueue
for asynchronous, decoupled agent interactions.

Workflow:
    1. Designer agent sends code requirements to MessageQueue
    2. Programmer agent retrieves message and generates code
    3. Programmer sends code to Compiler agent for validation
    4. Compiler validates and sends results back to Programmer
"""

from messagequeue import MessageQueue
from agent import AgentAI
from agentC import AgentAIC
import config


def main():
    """Demonstrate inter-agent communication via MessageQueue."""
    
    # Initialize singleton message queue
    mq = MessageQueue()
    
    print("=" * 80)
    print("AgenticAI Message Queue Example")
    print("=" * 80)
    
    # Example 1: Designer → Programmer communication
    print("\n[Designer] Sending task to Programmer...")
    mq.send_message(
        sender="designer_00",
        recipient="programmer_01",
        payload={
            "task_id": 1,
            "requirement": "Write a C program to calculate factorial of a number"
        }
    )
    
    # Programmer retrieves message
    print("[Programmer] Retrieving message from queue...")
    programmer_messages = mq.get_messages(agent_id="programmer_01")
    if programmer_messages:
        msg = programmer_messages[0]
        print(f"[Programmer] Got task: {msg.payload['requirement']}")
        
        # Simulate code generation
        generated_code = """#include <stdio.h>

int factorial(int n) {
    if (n <= 1) return 1;
    return n * factorial(n - 1);
}

int main() {
    printf("5! = %d\\n", factorial(5));
    return 0;
}"""
        
        # Programmer sends code to Compiler
        print("[Programmer] Sending code to Compiler for validation...")
        mq.send_message(
            sender="programmer_01",
            recipient="compiler_02",
            payload={
                "task_id": 1,
                "code": generated_code,
                "language": "c"
            }
        )
        
        # Delete the original message after processing
        mq.delete_message(msg.message_id)
        print("[Programmer] Message marked as processed")
    
    # Compiler retrieves and validates
    print("\n[Compiler] Retrieving code from Programmer...")
    compiler_messages = mq.get_messages(agent_id="compiler_02")
    if compiler_messages:
        msg = compiler_messages[0]
        print(f"[Compiler] Got code for task {msg.payload['task_id']}")
        print(f"[Compiler] Code length: {len(msg.payload['code'])} bytes")
        
        # Simulate compilation result
        compilation_result = {
            "task_id": msg.payload['task_id'],
            "success": True,
            "output_file": "./temp/a.out",
            "errors": [],
            "warnings": []
        }
        
        # Compiler broadcasts result to all agents
        print("[Compiler] Broadcasting compilation result...")
        mq.send_message(
            sender="compiler_02",
            recipient="broadcast",
            payload=compilation_result
        )
        
        # Delete message
        mq.delete_message(msg.message_id)
        print("[Compiler] Message marked as processed")
    
    # All agents receive broadcast
    print("\n[System] Broadcast messages in queue:")
    all_messages = mq.get_all_messages()
    for msg in all_messages:
        if msg.recipient == "broadcast":
            print(f"  - From {msg.sender}: Task {msg.payload.get('task_id')} - "
                  f"Success: {msg.payload.get('success')}")
    
    print("\n" + "=" * 80)
    print("Message Queue Operations Summary:")
    print("=" * 80)
    
    # Statistics
    all_messages = mq.get_all_messages()
    print(f"Total messages in queue: {len(all_messages)}")
    print(f"Message types:")
    print(f"  - Targeted: {len([m for m in all_messages if m.recipient not in ['broadcast', 'anyone']])}")
    print(f"  - Broadcast: {len([m for m in all_messages if m.recipient == 'broadcast'])}")
    print(f"  - Anyone: {len([m for m in all_messages if m.recipient == 'anyone'])}")
    
    # Close queue when done (important!)
    mq.close()
    print("\nMessage queue closed.")


if __name__ == "__main__":
    main()
