"""
Integration example: Using MessageQueue with AgentAI for inter-agent communication.

This example demonstrates how the MessageQueue can be integrated with existing
AgentAI instances to enable asynchronous communication between agents.
"""

from messagequeue import MessageQueue


class AgentWithMessageQueue:
    """
    Example wrapper showing how to integrate MessageQueue with agents.
    
    This is a simple example - in a real scenario, you might:
    - Add the message queue to the AgentAI base class
    - Use listeners to trigger agent responses automatically
    - Implement request-response patterns
    - Create agent orchestration workflows
    """
    
    def __init__(self, name, message_queue):
        """
        Initialize agent with message queue.
        
        Args:
            name: Agent name/identifier
            message_queue: Shared MessageQueue instance
        """
        self.name = name
        self.mq = message_queue
        
        # Register listener for this agent
        self.mq.listen(self.name, self._on_message_received)
    
    def _on_message_received(self, message):
        """
        Internal callback when a message is received.
        
        Args:
            message: Message object
        """
        print(f"[{self.name}] Received message from {message.sender}: {message.payload}")
    
    def send_message(self, recipient, payload):
        """
        Send a message to another agent.
        
        Args:
            recipient: Recipient name, "broadcast", or "anyone"
            payload: Message payload
        """
        print(f"[{self.name}] Sending message to {recipient}")
        self.mq.publish(sender=self.name, recipient=recipient, payload=payload)
    
    def get_pending_messages(self):
        """
        Retrieve all pending messages for this agent.
        
        Returns:
            List of Message objects
        """
        messages = self.mq.get_messages(self.name)
        print(f"[{self.name}] Retrieved {len(messages)} pending message(s)")
        return messages
    
    def broadcast(self, payload):
        """
        Broadcast a message to all agents.
        
        Args:
            payload: Message payload
        """
        self.send_message("broadcast", payload)


def example_agent_collaboration():
    """Demonstrate agent collaboration via message queue."""
    print("=== Agent Collaboration Example ===\n")
    
    # Create shared message queue
    mq = MessageQueue()
    
    # Create agents
    designer = AgentWithMessageQueue("Designer", mq)
    programmer = AgentWithMessageQueue("Programmer", mq)
    tester = AgentWithMessageQueue("Tester", mq)
    
    # Designer sends a task to Programmer
    designer.send_message("Programmer", {
        "task": "implement",
        "description": "Implement bubble sort in C",
        "priority": "high"
    })
    
    # Programmer responds to Designer
    programmer.send_message("Designer", {
        "status": "completed",
        "task_id": "bubble_sort",
        "code_location": "src/sort.c"
    })
    
    # Designer broadcasts to all agents
    designer.broadcast({
        "announcement": "Code review scheduled for tomorrow",
        "time": "10:00 AM"
    })
    
    # Retrieve pending messages
    print("\n--- Retrieving Pending Messages ---\n")
    programmer.get_pending_messages()
    tester.get_pending_messages()
    
    mq.close()
    print("\n" + "="*50 + "\n")


def example_task_distribution():
    """Demonstrate task distribution using 'anyone' mode."""
    print("=== Task Distribution Example ===\n")
    
    # Create shared message queue
    mq = MessageQueue()
    
    # Create manager and worker agents
    manager = AgentWithMessageQueue("Manager", mq)
    worker1 = AgentWithMessageQueue("Worker1", mq)
    worker2 = AgentWithMessageQueue("Worker2", mq)
    worker3 = AgentWithMessageQueue("Worker3", mq)
    
    # Manager publishes tasks for "anyone" to pick up
    print("Manager distributing tasks...\n")
    for i in range(5):
        manager.send_message("anyone", {
            "task_id": f"TASK-{i+1}",
            "action": "process",
            "data": f"dataset_{i+1}.csv"
        })
    
    # Workers pick up tasks on first-come-first-served basis
    print("\n--- Workers Picking Up Tasks ---\n")
    worker1.get_pending_messages()  # Gets some tasks
    worker2.get_pending_messages()  # Gets some tasks
    worker3.get_pending_messages()  # Gets remaining tasks
    
    # Check what's left
    print(f"\nRemaining tasks in queue: {mq.get_message_count('anyone')}")
    
    mq.close()
    print("\n" + "="*50 + "\n")


def example_request_response_pattern():
    """Demonstrate request-response pattern."""
    print("=== Request-Response Pattern Example ===\n")
    
    # Create shared message queue
    mq = MessageQueue()
    
    # Create agents
    client = AgentWithMessageQueue("Client", mq)
    server = AgentWithMessageQueue("Server", mq)
    
    # Client sends request to server
    client.send_message("Server", {
        "request_id": "REQ-001",
        "action": "get_user_data",
        "user_id": 12345
    })
    
    # Server processes and responds
    server.send_message("Client", {
        "request_id": "REQ-001",
        "status": "success",
        "data": {
            "user_id": 12345,
            "name": "John Doe",
            "email": "john@example.com"
        }
    })
    
    # Client retrieves response
    print("\n--- Client Retrieving Response ---\n")
    responses = client.get_pending_messages()
    if responses:
        print(f"Response data: {responses[0].payload['data']}")
    
    mq.close()
    print("\n" + "="*50 + "\n")


def example_workflow_orchestration():
    """Demonstrate complex workflow orchestration."""
    print("=== Workflow Orchestration Example ===\n")
    
    # Create shared message queue
    mq = MessageQueue()
    
    # Create agents for a CI/CD pipeline
    orchestrator = AgentWithMessageQueue("Orchestrator", mq)
    builder = AgentWithMessageQueue("Builder", mq)
    tester = AgentWithMessageQueue("Tester", mq)
    deployer = AgentWithMessageQueue("Deployer", mq)
    
    # Orchestrator initiates pipeline
    print("Starting CI/CD pipeline...\n")
    orchestrator.send_message("Builder", {
        "pipeline_id": "PIPE-123",
        "stage": "build",
        "source": "main",
        "commit": "abc123"
    })
    
    # Builder completes and notifies Tester
    builder.send_message("Tester", {
        "pipeline_id": "PIPE-123",
        "stage": "test",
        "build_artifact": "build/app-v1.0.jar"
    })
    
    # Tester completes and notifies Deployer
    tester.send_message("Deployer", {
        "pipeline_id": "PIPE-123",
        "stage": "deploy",
        "test_results": "PASSED",
        "artifact": "build/app-v1.0.jar"
    })
    
    # Deployer notifies Orchestrator of completion
    deployer.send_message("Orchestrator", {
        "pipeline_id": "PIPE-123",
        "stage": "complete",
        "deployment_url": "https://prod.example.com"
    })
    
    # Orchestrator broadcasts success
    orchestrator.broadcast({
        "pipeline_id": "PIPE-123",
        "status": "SUCCESS",
        "message": "Deployment completed successfully"
    })
    
    # All agents get the broadcast
    print("\n--- Agents Checking for Broadcasts ---\n")
    for agent in [builder, tester, deployer]:
        messages = agent.get_pending_messages()
    
    mq.close()
    print("\n" + "="*50 + "\n")


if __name__ == "__main__":
    print("\nMessageQueue Integration Examples\n")
    print("=" * 50 + "\n")
    
    example_agent_collaboration()
    example_task_distribution()
    example_request_response_pattern()
    example_workflow_orchestration()
    
    print("All integration examples completed!")
