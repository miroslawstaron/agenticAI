#!/usr/bin/env python3
"""
Main script demonstrating agent interaction using MessageQueue.

This script creates a Designer and Programmer agent that communicate
through a MessageQueue instead of direct function calls.
"""
import argparse
import os
from tqdm import tqdm
from agent import AgentAI
from messagequeue import MessageQueue

MAX_ITERATIONS = 2  # Set the maximum number of iterations
FILENAME_RESULT = "results/conversation_result_mq.xlsx"
API_KEY = os.getenv('OPENAI_API_KEY', '')

# Agent identifiers for message routing
DESIGNER_ID = "Designer"
PROGRAMMER_ID = "Programmer"


def create_agents(server_address, api_key):
    """
    Create Designer and Programmer agents.
    
    Args:
        server_address: Server URL for LLM API
        api_key: API key for authentication
        
    Returns:
        Tuple of (designer_agent, programmer_agent)
    """
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
    
    return designer, programmer


def run_conversation(designer, programmer, message_queue, initial_prompt, max_iterations,
                     output_file=None):
    """
    Run the designer-programmer conversation using message queue.
    
    Args:
        designer: Designer agent instance
        programmer: Programmer agent instance
        message_queue: MessageQueue instance for communication
        initial_prompt: Initial task/prompt to start the conversation
        max_iterations: Maximum number of conversation iterations
        output_file: Optional output file for saving progress
        
    Returns:
        List of all messages from the conversation
    """
    all_messages = []
    # Step 1: Send initial prompt to programmer via message queue
    message_queue.publish(
        sender="User",
        recipient=PROGRAMMER_ID,
        payload={"type": "task", "content": initial_prompt}
    )
    
    # Programmer retrieves and responds to initial task
    messages = message_queue.get_messages(PROGRAMMER_ID)
    if messages:
        task_content = messages[0].payload.get("content", "")
        programmer_response = programmer.get_response(task_content)
        
        # Programmer sends solution to Designer for review
        message_queue.publish(
            sender=PROGRAMMER_ID,
            recipient=DESIGNER_ID,
            payload={
                "type": "solution",
                "content": programmer_response,
                "original_task": initial_prompt
            }
        )
    
    # Designer retrieves and reviews the solution
    messages = message_queue.get_messages(DESIGNER_ID)
    if messages:
        solution = messages[0].payload.get("content", "")
        task = messages[0].payload.get("original_task", "")
        designer_response = designer.get_response(
            f'Here is my solution to this problem "{task}", how can I improve it: {solution}?'
        )
        
        # Designer sends feedback to Programmer
        message_queue.publish(
            sender=DESIGNER_ID,
            recipient=PROGRAMMER_ID,
            payload={"type": "feedback", "content": designer_response}
        )
    
    # Iterative improvement loop
    for i in tqdm(range(max_iterations), desc="Processing iterations"):
        # Programmer retrieves designer feedback
        messages = message_queue.get_messages(PROGRAMMER_ID)
        if messages:
            feedback = messages[0].payload.get("content", "")
            programmer_response = programmer.get_response(feedback)
            
            # Programmer sends updated solution to Designer
            message_queue.publish(
                sender=PROGRAMMER_ID,
                recipient=DESIGNER_ID,
                payload={"type": "solution", "content": programmer_response}
            )
        
        # Designer reviews updated solution
        messages = message_queue.get_messages(DESIGNER_ID)
        if messages:
            solution = messages[0].payload.get("content", "")
            if i == 0:
                designer_response = designer.get_response(
                    f'How to improve this code: {solution}'
                )
            else:
                designer_response = designer.get_response(solution)
            
            # Designer sends feedback to Programmer
            message_queue.publish(
                sender=DESIGNER_ID,
                recipient=PROGRAMMER_ID,
                payload={"type": "feedback", "content": designer_response}
            )
        
        # Save progress if output file specified
        if output_file:
            programmer.save_to_excel(output_file)
    
    # Collect all messages from agents
    if hasattr(designer, 'messages') and isinstance(designer.messages, list):
        all_messages.extend(designer.messages)
    if hasattr(programmer, 'messages') and isinstance(programmer.messages, list):
        all_messages.extend(programmer.messages)
    
    return all_messages


def main():
    """Main entry point for the script."""
    # Parse command-line arguments
    parser = argparse.ArgumentParser(
        description="Run Designer-Programmer agent conversation using MessageQueue."
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
    
    args = parser.parse_args()
    
    # Determine output filename
    output_file = args.output
    
    # Create message queue for inter-agent communication
    message_queue = MessageQueue()
    
    try:
        # Create agents
        designer, programmer = create_agents(args.server, API_KEY)
        
        # Run conversation
        all_messages = run_conversation(
            designer,
            programmer,
            message_queue,
            args.prompt,
            args.iterations,
            output_file=output_file
        )
        
        # Save final results
        programmer.save_to_excel(output_file)
        
        # Save all messages from conversation
        if all_messages:
            import pandas as pd
            df = pd.DataFrame(all_messages)
            messages_file = output_file.replace('.xlsx', '_all_messages.xlsx')
            df.to_excel(messages_file, index=False)
            print(f"All messages saved to {messages_file}")
        
        print(f"\nConversation saved to {output_file}")
        
    finally:
        # Clean up message queue
        message_queue.close()


if __name__ == "__main__":
    main()
