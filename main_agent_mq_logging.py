#!/usr/bin/env python3
"""
Event-driven main script with logging for agent interaction using MessageQueue.

This script creates Designer and Programmer agents that communicate through
a MessageQueue. Agents listen for messages and respond asynchronously instead
of using explicit loops.
"""
import argparse
import os
import threading
import time
from agent import AgentAI
from messagequeue import MessageQueue, get_message_queue, reset_message_queue
from logger import SingletonLogger

MAX_ITERATIONS = 100
FILENAME_RESULT = "results/conversation_result_mq_logging.xlsx"
API_KEY = os.getenv('OPENAI_API_KEY', '')

# Agent identifiers for message routing
DESIGNER_ID = "Designer"
PROGRAMMER_ID = "Programmer"
USER_ID = "User"

# Get singleton instances
logger = SingletonLogger(log_file="execution.log", enabled=True)
logger.enable("execution.log")


def create_agents(server_address, api_key):
    """
    Create Designer and Programmer agents.
    
    Args:
        server_address: Server URL for LLM API
        api_key: API key for authentication
        
    Returns:
        Tuple of (designer_agent, programmer_agent)
    """
    logger.log("Creating agents...")
    
    designer = AgentAI(
        server_address=server_address,
        model_name="ollama/llama3.2:1b",
        api_key=api_key,
        my_role="You are a C designer. You will be given a task and you will respond with design suggestions to solve the task."
    )
    
    programmer = AgentAI(
        server_address=server_address,
        model_name="ollama/llama3.2:1b",
        api_key=api_key,
        my_role="You are a C programmer. You respond with the code in C to solve the task. No comments or explanations."
    )
    
    logger.log("Agents created successfully")
    return designer, programmer


class AgentWorker:
    """Handles asynchronous agent message processing."""
    
    def __init__(self, agent_id, agent, message_queue, other_agent_id, output_file=None):
        """
        Initialize the agent worker.
        
        Args:
            agent_id: Identifier for this agent
            agent: The AgentAI instance
            message_queue: The MessageQueue instance
            other_agent_id: Identifier for the other agent
            output_file: Optional output file for saving results
        """
        self.agent_id = agent_id
        self.agent = agent
        self.message_queue = message_queue
        self.other_agent_id = other_agent_id
        self.output_file = output_file
        self.is_running = False
        self.iteration_count = 0
        self.thread = None
    
    def start(self):
        """Start listening for messages in a background thread."""
        self.is_running = True
        self.thread = threading.Thread(target=self._listen_and_process, daemon=True)
        self.thread.start()
        logger.log(f"{self.agent_id} agent worker started")
    
    def stop(self):
        """Stop listening for messages."""
        self.is_running = False
        if self.thread:
            self.thread.join(timeout=5)
        logger.log(f"{self.agent_id} agent worker stopped")
    
    def _listen_and_process(self):
        """Listen for messages and process them."""
        while self.is_running:
            try:
                messages = self.message_queue.get_messages(self.agent_id, consume=True)
                
                if messages:
                    for message in messages:
                        logger.log(f"{self.agent_id} received message from {message.sender}")
                        self._process_message(message)
                else:
                    # No messages, wait a bit before polling again
                    time.sleep(0.1)
            except Exception as e:
                logger.log_exception(f"Error in {self.agent_id} worker: {str(e)}")
                time.sleep(0.5)
    
    def _process_message(self, message):
        """
        Process a single message and send response.
        
        Args:
            message: The Message object to process
        """
        payload = message.payload
        message_type = payload.get("type", "unknown")
        
        try:
            if message_type == "task":
                # Initial task from user
                task_content = payload.get("content", "")
                logger.log(f"{self.agent_id} processing initial task")
                
                response = self.agent.get_response(task_content)
                logger.log(f"{self.agent_id} generated response (length: {len(response)})")
                
                # Send to other agent
                self.message_queue.publish(
                    sender=self.agent_id,
                    recipient=self.other_agent_id,
                    payload={
                        "type": "solution" if self.agent_id == PROGRAMMER_ID else "feedback",
                        "content": response,
                        "original_task": payload.get("original_task", task_content),
                        "iteration": payload.get("iteration", 0)
                    }
                )
                
            elif message_type == "solution":
                # Solution from programmer
                solution_content = payload.get("content", "")
                original_task = payload.get("original_task", "")
                iteration = payload.get("iteration", 0)
                
                logger.log(f"{self.agent_id} reviewing solution from iteration {iteration}")
                
                if iteration == 0:
                    prompt = f'Here is my solution to this problem "{original_task}", how can I improve it: {solution_content}?'
                else:
                    prompt = f'How to improve this code: {solution_content}'
                
                response = self.agent.get_response(prompt)
                logger.log(f"{self.agent_id} generated feedback (length: {len(response)})")
                
                # Send feedback back
                self.message_queue.publish(
                    sender=self.agent_id,
                    recipient=self.other_agent_id,
                    payload={
                        "type": "feedback",
                        "content": response,
                        "iteration": iteration
                    }
                )
                
                # Check if we should continue iterating
                if iteration < MAX_ITERATIONS - 1:
                    # Continue to next iteration
                    self.iteration_count = iteration + 1
                else:
                    logger.log(f"Reached maximum iterations ({MAX_ITERATIONS})")
                    # Signal completion
                    self.message_queue.publish(
                        sender=self.agent_id,
                        recipient="completion",
                        payload={"type": "done", "iteration": iteration}
                    )
                
            elif message_type == "feedback":
                # Feedback from designer
                feedback_content = payload.get("content", "")
                iteration = payload.get("iteration", 0)
                
                logger.log(f"{self.agent_id} processing feedback from iteration {iteration}")
                
                response = self.agent.get_response(feedback_content)
                logger.log(f"{self.agent_id} generated improved solution (length: {len(response)})")
                
                # Send improved solution back
                self.message_queue.publish(
                    sender=self.agent_id,
                    recipient=self.other_agent_id,
                    payload={
                        "type": "solution",
                        "content": response,
                        "iteration": iteration + 1
                    }
                )
            
            # Save progress
            if self.output_file:
                self.agent.save_to_excel(self.output_file)
                
        except Exception as e:
            logger.log_exception(f"Error processing message in {self.agent_id}: {str(e)}")


class ConversationOrchestrator:
    """Orchestrates the conversation between agents."""
    
    def __init__(self, designer, programmer, message_queue, output_file=None):
        """
        Initialize the orchestrator.
        
        Args:
            designer: Designer agent instance
            programmer: Programmer agent instance
            message_queue: MessageQueue instance
            output_file: Optional output file for saving results
        """
        self.designer = designer
        self.programmer = programmer
        self.message_queue = message_queue
        self.output_file = output_file
        
        # Create worker threads
        self.programmer_worker = AgentWorker(
            PROGRAMMER_ID, programmer, message_queue, DESIGNER_ID, output_file
        )
        self.designer_worker = AgentWorker(
            DESIGNER_ID, designer, message_queue, PROGRAMMER_ID, output_file
        )
        
        self.is_running = False
    
    def start(self, initial_prompt):
        """
        Start the conversation.
        
        Args:
            initial_prompt: The initial task prompt
        """
        logger.log("Starting conversation orchestrator")
        self.is_running = True
        
        # Start agent workers
        self.programmer_worker.start()
        self.designer_worker.start()
        
        # Send initial prompt to programmer
        logger.log("Publishing initial prompt")
        self.message_queue.publish(
            sender=USER_ID,
            recipient=PROGRAMMER_ID,
            payload={"type": "task", "content": initial_prompt, "iteration": 0}
        )
    
    def wait_for_completion(self, timeout=300):
        """
        Wait for the conversation to complete.
        
        Args:
            timeout: Maximum time to wait in seconds (default: 300)
        
        Returns:
            True if completed, False if timeout
        """
        start_time = time.time()
        
        logger.log("Waiting for conversation completion...")
        
        while self.is_running and (time.time() - start_time) < timeout:
            # Check for completion message
            messages = self.message_queue.get_messages("completion", consume=True)
            if messages:
                logger.log("Conversation completed")
                self.is_running = False
                return True
            
            # Check if workers are still active
            if not self.programmer_worker.is_running and not self.designer_worker.is_running:
                logger.log("All workers have stopped")
                self.is_running = False
                return True
            
            time.sleep(0.5)
        
        if time.time() - start_time >= timeout:
            logger.log(f"Conversation timeout after {timeout} seconds")
            return False
        
        return True
    
    def stop(self):
        """Stop the conversation and clean up resources."""
        logger.log("Stopping conversation orchestrator")
        self.is_running = False
        self.programmer_worker.stop()
        self.designer_worker.stop()
        
        # Save final results
        if self.output_file:
            logger.log(f"Saving results to {self.output_file}")
            self.programmer.save_to_excel(self.output_file)
            self.designer.save_to_excel(self.output_file.replace('.xlsx', '_designer.xlsx'))


def main():
    """Main entry point for the script."""
    # Parse command-line arguments
    parser = argparse.ArgumentParser(
        description="Run Designer-Programmer agent conversation using MessageQueue with logging."
    )
    parser.add_argument(
        "--prompt",
        type=str,
        required=True,
        help="The initial task/prompt to send to the agents."
    )
    parser.add_argument(
        "--iterations",
        type=int,
        default=MAX_ITERATIONS,
        help=f"Number of conversation iterations (default: {MAX_ITERATIONS})"
    )
    parser.add_argument(
        "--server",
        type=str,
        default="http://localhost:11434",
        help="Server address for LLM API"
    )
    parser.add_argument(
        "--output",
        type=str,
        default=FILENAME_RESULT,
        help=f"Output file for conversation results (default: {FILENAME_RESULT})"
    )
    parser.add_argument(
        "--timeout",
        type=int,
        default=300,
        help="Timeout for conversation in seconds (default: 300)"
    )
    
    args = parser.parse_args()
    
    # Update global MAX_ITERATIONS
    globals()['MAX_ITERATIONS'] = args.iterations
    
    # Determine output filename
    output_file = args.output
    
    logger.log(f"Starting conversation with prompt: {args.prompt[:50]}...")
    logger.log(f"Server: {args.server}")
    logger.log(f"Max iterations: {args.iterations}")
    logger.log(f"Timeout: {args.timeout}s")
    
    # Reset message queue singleton for fresh start
    reset_message_queue()
    message_queue = get_message_queue()
    
    try:
        # Create agents
        designer, programmer = create_agents(args.server, API_KEY)
        
        # Create orchestrator
        orchestrator = ConversationOrchestrator(
            designer,
            programmer,
            message_queue,
            output_file=output_file
        )
        
        # Start conversation
        orchestrator.start(args.prompt)
        
        # Wait for completion
        completed = orchestrator.wait_for_completion(timeout=args.timeout)
        
        if completed:
            logger.log("Conversation completed successfully")
            print(f"\n✓ Conversation completed successfully")
        else:
            logger.log("Conversation timeout")
            print(f"\n✗ Conversation timeout after {args.timeout} seconds")
        
        # Stop orchestrator
        orchestrator.stop()
        
        print(f"Conversation saved to {output_file}")
        
    except KeyboardInterrupt:
        logger.log("Conversation interrupted by user")
        print("\n✗ Conversation interrupted")
    except Exception as e:
        logger.log_exception(f"Error during conversation: {str(e)}")
        print(f"\n✗ Error: {str(e)}")
    finally:
        # Clean up message queue
        message_queue.close()
        logger.log("Cleanup complete")


if __name__ == "__main__":
    main()
