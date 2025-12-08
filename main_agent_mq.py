#!/usr/bin/env python3
"""
Main script demonstrating agent interaction using MessageQueue.

This script creates a Designer and Programmer agent that communicate
through a MessageQueue instead of direct function calls.
"""
# Import argparse to parse command-line arguments
import argparse
# Import os to access environment variables like API keys
import os
# Import tqdm for progress bar visualization during iterations
from tqdm import tqdm
# Import the base AgentAI class for creating agent instances
from agent import AgentAI
# Import MessageQueue for asynchronous inter-agent communication
from messagequeue import MessageQueue
# Import SingletonLogger for thread-safe logging throughout execution
from logger import SingletonLogger

# Maximum number of iterative improvement cycles between designer and programmer (default: 2)
MAX_ITERATIONS = 2
# Default output filename for storing conversation results in Excel format
FILENAME_RESULT = "results/conversation_result_mq.xlsx"
# Retrieve OpenAI API key from environment variable, empty string if not set
API_KEY = os.getenv('OPENAI_API_KEY', '')

# Unique identifier for the Designer agent used in message routing
DESIGNER_ID = "Designer"
# Unique identifier for the Programmer agent used in message routing
PROGRAMMER_ID = "Programmer"

# Initialize singleton logger instance with logging disabled by default (can be enabled via --log flag)
logger = SingletonLogger(log_file="execution.log", enabled=False)


# Function to instantiate both agents with specified configurations
def create_agents(server_address, api_key, model_name="ollama/llama3.2:1b"):
    """
    Create Designer and Programmer agents.
    
    Args:
        server_address: Server URL for LLM API
        api_key: API key for authentication
        model_name: Model name to use for agents (default: ollama/llama3.2:1b)
        
    Returns:
        Tuple of (designer_agent, programmer_agent)
    """
    # Log that agent creation process is starting with the specified model
    logger.log(f"[Coordinator] Creating agents with model: {model_name}")
    
    # Instantiate Designer agent with C design role for solving problems through design suggestions
    designer = AgentAI(
        server_address=server_address,
        model_name=model_name,
        api_key=api_key,
        my_role="You are a C designer. You will be given a task and you will respond with design suggestions to solve the task."
    )
    
    # Instantiate Programmer agent with C coding role for implementing solutions
    programmer = AgentAI(
        server_address=server_address,
        model_name=model_name,
        api_key=api_key,
        my_role="You are a C programmer. You respond with the code in C to solve the task. No comments or explanations."
    )
    
    # Log successful agent creation to track initialization progress
    logger.log("[Coordinator] Agents created successfully")
    # Return both agents as a tuple for use in the main conversation loop
    return designer, programmer


# Main conversation orchestration function that manages the designer-programmer interaction loop
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
    # Initialize list to collect all messages from both agents for later analysis
    all_messages = []
    # Log conversation start for debugging and tracking execution flow
    logger.log("[Coordinator] Starting conversation...")
    
    # Step 1: Send initial prompt to programmer via message queue
    # Log the initial prompt being published (sanitize newlines for readability)
    logger.log(f"[Coordinator] Publishing initial prompt: {initial_prompt.replace('\n', '$$$$')[:50]}...")
    # Publish initial task to the Programmer agent through the message queue
    message_queue.publish(
        sender="User",  # Sender is the user initiating the conversation
        recipient=PROGRAMMER_ID,  # Target is the Programmer agent
        payload={"type": "task", "content": initial_prompt}  # Payload contains task type and content
    )
    
    # Programmer retrieves and responds to initial task
    # Get the latest message for the Programmer using the new get_latest_message() method
    message = message_queue.get_latest_message(PROGRAMMER_ID)
    # Check if a message was retrieved (defensive programming)
    if message:
        # Extract task content from the message payload
        task_content = message.payload.get("content", "")
        # Log that programmer is processing the initial task
        logger.log("[Coordinator] Programmer processing initial task")
        # Request programmer agent to generate response/code for the task
        programmer_response = programmer.get_response(task_content)
        # Log the response length for debugging and tracking output size
        logger.log(f"[Coordinator] Programmer generated response (length: {programmer_response.replace('\n', '$$$$')[:100]})")
        
        # Programmer sends solution to Designer for review
        # Publish the programmer's solution to the Designer agent
        message_queue.publish(
            sender=PROGRAMMER_ID,  # Sender is the Programmer agent
            recipient=DESIGNER_ID,  # Target is the Designer agent
            payload={
                "type": "solution",  # Message type indicates this is a solution
                "content": programmer_response,  # Actual code/solution generated
                "original_task": initial_prompt  # Include original task for context
            }
        )
    
    # Designer retrieves and reviews the solution
    # Get the latest message for the Designer using the new get_latest_message() method
    message = message_queue.get_latest_message(DESIGNER_ID)
    # Check if a message was retrieved (defensive programming)
    if message:
        # Extract solution content from the message payload
        solution = message.payload.get("content", "")
        # Extract original task from message metadata for review context
        task = message.payload.get("original_task", "")
        # Log that designer is reviewing the initial solution
        logger.log("[Coordinator] Designer reviewing initial solution")
        # Request designer agent to provide feedback and improvement suggestions
        designer_response = designer.get_response(
            f'Here is my solution to this problem "{task}", how can I improve it: {solution}?'
        )
        # Log the feedback length for debugging and tracking output size
        logger.log(f"[Coordinator] Designer generated feedback (length: {designer_response.replace('\n', '$$$$')[:100]})")
        
        # Designer sends feedback to Programmer
        # Publish the designer's feedback back to the Programmer for improvements
        message_queue.publish(
            sender=DESIGNER_ID,  # Sender is the Designer agent
            recipient=PROGRAMMER_ID,  # Target is the Programmer agent
            payload={"type": "feedback", "content": designer_response}  # Payload contains improvement suggestions
        )
    
    # Iterative improvement loop
    # Create progress bar for visual feedback on iteration count
    for i in tqdm(range(max_iterations), desc="Processing iterations"):
        # Programmer retrieves designer feedback
        # Get the latest message for the Programmer using the new get_latest_message() method
        message = message_queue.get_latest_message(PROGRAMMER_ID)
        # Check if a message was retrieved (defensive programming)
        if message:
            # Extract feedback content from the message payload
            feedback = message.payload.get("content", "")
            # Log the feedback being processed in current iteration
            logger.log(f"[Coordinator] Programmer processing feedback (iteration {i+1}) - Feedback - {feedback.replace('\n', '$$$$')[:100]}")
            # Request programmer to generate improved code based on designer feedback
            programmer_response = programmer.get_response(feedback)
            # Log the improved code length for debugging and tracking output size
            logger.log(f"[Coordinator] Programmer generated response (iteration {i+1}, response: {programmer_response.replace('\n', '$$$$')[:100]})")
            
            # Programmer sends updated solution to Designer
            # Publish the improved solution back to the Designer for review
            message_queue.publish(
                sender=PROGRAMMER_ID,  # Sender is the Programmer agent
                recipient=DESIGNER_ID,  # Target is the Designer agent
                payload={"type": "solution", "content": programmer_response}  # Payload contains updated code
            )
        
        # Designer reviews updated solution
        # Get the latest message for the Designer using the new get_latest_message() method
        message = message_queue.get_latest_message(DESIGNER_ID)
        # Check if a message was retrieved (defensive programming)
        if message:
            # Extract solution content from the message payload
            solution = message.payload.get("content", "")
            # Log the solution being reviewed in current iteration
            logger.log(f"[Coordinator] Designer reviewing solution (iteration {i+1} - Solution - {solution.replace('\n', '$$$$')[:100]})")
            # Check if this is the first iteration (iteration 0) to use different prompt
            if i == 0:
                # First iteration: use specific improvement prompt
                designer_response = designer.get_response(
                    f'How to improve this code: {solution}'
                )
            else:
                # Subsequent iterations: provide solution directly for continued refinement
                designer_response = designer.get_response(solution)
            # Log the feedback length for debugging and tracking output size
            logger.log(f"[Coordinator] Designer generated feedback (iteration {i+1}, length: {designer_response.replace('\n', '$$$$')[:100]})")
            
            # Designer sends feedback to Programmer
            # Publish the designer's feedback to drive next iteration of improvements
            message_queue.publish(
                sender=DESIGNER_ID,  # Sender is the Designer agent
                recipient=PROGRAMMER_ID,  # Target is the Programmer agent
                payload={"type": "feedback", "content": designer_response}  # Payload contains feedback
            )
        
        # Save progress if output file specified
        # Check if an output file path was provided for progress saving
        if output_file:
            # Log that progress is being saved to track file I/O operations
            logger.log(f"[Coordinator] Saving progress to {output_file}")
            # Save current programmer messages to Excel for intermediate results
            programmer.save_to_excel(output_file)
    
    # Collect all messages from agents
    # Check if designer agent has a messages list attribute (defensive programming)
    if hasattr(designer, 'messages') and isinstance(designer.messages, list):
        # Extend the all_messages list with designer's conversation history
        all_messages.extend(designer.messages)
        # Log number of messages collected from designer for tracking
        logger.log(f"[Coordinator] Collected {len(designer.messages)} messages from Designer")
    # Check if programmer agent has a messages list attribute (defensive programming)
    if hasattr(programmer, 'messages') and isinstance(programmer.messages, list):
        # Extend the all_messages list with programmer's conversation history
        all_messages.extend(programmer.messages)
        # Log number of messages collected from programmer for tracking
        logger.log(f"[Coordinator] Collected {len(programmer.messages)} messages from Programmer")
    
    # Log conversation completion for execution tracking
    logger.log("[Coordinator] Conversation completed")
    # Return all collected messages for analysis and storage
    return all_messages


# Main entry point function that orchestrates the entire application flow
def main():
    """Main entry point for the script."""
    # Create argument parser for command-line interface with description
    # Parse command-line arguments
    parser = argparse.ArgumentParser(
        description="Run Designer-Programmer agent conversation using MessageQueue."
    )
    # Required argument: initial task prompt for the conversation
    parser.add_argument(
        "--prompt",
        type=str,
        required=True,
        help="The initial task/prompt to send to the agents."
    )
    # Optional argument: number of iterations (default from MAX_ITERATIONS constant)
    parser.add_argument(
        "--iterations",
        type=int,
        default=MAX_ITERATIONS,
        help=f"Number of conversation iterations (default: {MAX_ITERATIONS})"
    )
    # Optional argument: server address for LLM API (default is localhost)
    parser.add_argument(
        "--server",
        type=str,
        default="http://localhost:11434",
        help="Server address for LLM API"
    )
    # Optional argument: output file path for results (default from FILENAME_RESULT constant)
    parser.add_argument(
        "--output",
        type=str,
        default=FILENAME_RESULT,
        help=f"Output file for conversation results (default: {FILENAME_RESULT})"
    )
    # Optional flag: enables logging to execution.log file (boolean flag)
    parser.add_argument(
        "--log",
        action="store_true",
        help="Enable logging to execution.log file"
    )
    # Optional argument: model name to use for both agents (default is ollama/llama3.2:1b)
    parser.add_argument(
        "--model",
        type=str,
        default="ollama/llama3.2:1b",
        help="Model name to use for agents (default: ollama/llama3.2:1b)"
    )
    
    # Parse all command-line arguments from sys.argv
    args = parser.parse_args()
    
    # Configure logging if enabled
    # Check if user provided --log flag to enable logging
    if args.log:
        # Enable logging to the execution.log file
        logger.enable("execution.log")
        # Log separator line for visual organization in log file
        logger.log("=" * 80)
        # Log conversation start marker for tracking execution
        logger.log("CONVERSATION STARTED")
        # Log separator line for visual organization in log file
        logger.log("=" * 80)
    
    # Determine output filename
    # Store the output file path from arguments for use throughout execution
    output_file = args.output
    
    # Log all configuration parameters from command-line arguments with [Coordinator] prefix
    logger.log(f"[Coordinator] Server: {args.server}")
    # Log max iterations setting from arguments
    logger.log(f"[Coordinator] Max iterations: {args.iterations}")
    # Log output file path from arguments
    logger.log(f"[Coordinator] Output file: {output_file}")
    # Log model selection from arguments
    logger.log(f"[Coordinator] Model: {args.model}")
    # Log prompt preview (first 100 characters) to verify input
    logger.log(f"[Coordinator] Prompt: {args.prompt[:100]}...")
    
    # Create message queue for inter-agent communication
    # Instantiate MessageQueue singleton for managing agent-to-agent message passing
    message_queue = MessageQueue()
    
    # Try-except-finally block for robust error handling and resource cleanup
    try:
        # Create agents
        # Call factory function to instantiate both designer and programmer agents
        designer, programmer = create_agents(args.server, API_KEY, args.model)
        
        # Run conversation
        # Execute the conversation orchestration function with all parameters
        all_messages = run_conversation(
            designer,  # Pass designer agent instance
            programmer,  # Pass programmer agent instance
            message_queue,  # Pass message queue for inter-agent communication
            args.prompt,  # Pass user's initial prompt/task
            args.iterations,  # Pass maximum iterations from arguments
            output_file=output_file  # Pass output file path for progress saving
        )
        
        # Save final results
        # Log that results are being saved to output file
        logger.log(f"[Coordinator] Saving results to {output_file}")
        # Save programmer's conversation messages to Excel file
        programmer.save_to_excel(output_file)
        
        # Save all messages from conversation
        # Check if any messages were collected during conversation
        if all_messages:
            # Import pandas for Excel file operations (done here to avoid unnecessary imports)
            import pandas as pd
            # Convert messages list to pandas DataFrame for Excel export
            df = pd.DataFrame(all_messages)
            # Construct output file name for all messages (replace .xlsx with _all_messages.xlsx)
            messages_file = output_file.replace('.xlsx', '_all_messages.xlsx')
            # Save DataFrame to Excel file without row indices
            df.to_excel(messages_file, index=False)
            # Log successful save of all messages to file
            logger.log(f"[Coordinator] All messages saved to {messages_file}")
            # Print success message to console output
            print(f"All messages saved to {messages_file}")
        
        # Log successful completion and file save to console
        logger.log(f"[Coordinator] Conversation successfully saved to {output_file}")
        # Print success message to console for user feedback
        print(f"\nConversation saved to {output_file}")
        
    # Catch keyboard interrupt for graceful shutdown
    except KeyboardInterrupt:
        # Log user interrupt for debugging and tracking
        logger.log("[Coordinator] Conversation interrupted by user")
        # Print interrupt message to console
        print("\n✗ Conversation interrupted")
    # Catch all other exceptions for error reporting
    except Exception as e:
        # Log exception details for debugging and error tracking
        logger.log(f"[Coordinator] Error during conversation: {str(e)}")
        # Print error message to console for user notification
        print(f"\n✗ Error: {str(e)}")
        # Re-raise exception to propagate it to Python runtime (prevents silent failures)
        raise
    # Always execute cleanup code regardless of success or exception
    finally:
        # Close and cleanup message queue resources
        # Call close method on message queue to release resources
        message_queue.close()
        # Log separator line for visual organization in log file
        logger.log("=" * 80)
        # Log cleanup completion marker for tracking execution flow
        logger.log("Cleanup complete")
        # Log separator line for visual organization in log file
        logger.log("=" * 80)


# Python entry point guard - ensures main() only runs if script is executed directly
if __name__ == "__main__":
    # Call main function to start application execution
    main()
