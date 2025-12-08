#!/usr/bin/env python3
"""
Fibonacci Example with Human-in-the-Loop

This example demonstrates a three-way conversation:
- Designer: Provides design suggestions and improvements
- Programmer: Writes code to solve the problem
- Human: Reviews and provides feedback (you!)

The human provides input at each iteration to guide the development.
"""

from agent import AgentAI
from agentH import AgentH
import sys
import os
import pandas as pd

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def main():
    print("=" * 80)
    print("Fibonacci Example with Human-in-the-Loop")
    print("=" * 80)
    print()
    
    # Configuration
    MAX_ITERATIONS = 3  # Fewer iterations since human input takes time
    SERVER = "http://localhost:11434"
    MODEL = "deepseek-r1:70b"
    OUTPUT_FILE = "fibonacci_human_conversation.xlsx"
    LOG_FILE = "fibonacci_human_conversation_log.xlsx"
    
    print(f"Configuration:")
    print(f"  Server: {SERVER}")
    print(f"  Model: {MODEL}")
    print(f"  Iterations: {MAX_ITERATIONS}")
    print(f"  Output: {OUTPUT_FILE}")
    print(f"  Log: {LOG_FILE}")
    print()
    
    print("NOTE: You will be prompted to provide feedback at each iteration.")
    print("      Please review the AI agents' conversation and guide them.")
    print()
    
    # Create Designer Agent
    print("Creating Designer Agent...")
    designer = AgentAI(
        server_address=SERVER,
        model_name=MODEL,
        my_role=(
            "You are an experienced software designer. "
            "You provide design suggestions, code reviews, and improvements. "
            "You consider both human feedback and code quality. "
            "You focus on best practices and user requirements."
        )
    )
    
    # Create Programmer Agent
    print("Creating Programmer Agent...")
    programmer = AgentAI(
        server_address=SERVER,
        model_name=MODEL,
        my_role=(
            "You are an experienced programmer. "
            "You write code to solve tasks following design guidelines and human feedback. "
            "You respond with complete, working solutions. "
            "You incorporate feedback from both the designer and human reviewers."
        )
    )
    
    # Create Human Agent
    print("Creating Human Agent...")
    human = AgentH(
        server_address=None,
        model_name=None,
        my_role="Human reviewer providing feedback and guidance"
    )
    
    # Conversation log for analysis
    conversation_log = []
    
    print()
    print("Starting conversation...")
    print()
    
    # Initial task
    task = (
        "Write a C program that calculates the Fibonacci sequence. "
        "The program should:\n"
        "1. Accept a number n from the user\n"
        "2. Calculate and print the first n Fibonacci numbers\n"
        "3. Be efficient and readable\n"
        "Please provide the complete C code."
    )
    
    print("=" * 80)
    print("INITIAL TASK")
    print("=" * 80)
    print(task)
    print()
    
    # === Iteration 0: Initial responses ===
    
    # Programmer's initial solution
    print("[Iteration 0] Programmer is working on the initial solution...")
    print("              Please wait...")
    programmer_response = programmer.get_response(task)
    print(f"[Iteration 0] ✓ Programmer responded")
    print()
    
    # Log programmer response
    conversation_log.append({
        'iteration': 0,
        'role': 'programmer',
        'prompt': task,
        'response': programmer_response[:500] + "..." if len(programmer_response) > 500 else programmer_response
    })
    
    # Designer's initial review
    designer_prompt = (
        f"Here is the programmer's solution to the Fibonacci problem:\n\n"
        f"{programmer_response}\n\n"
        f"Please review this code and provide constructive feedback."
    )
    
    print("[Iteration 0] Designer is reviewing the code...")
    print("              Please wait...")
    designer_response = designer.get_response(designer_prompt)
    print(f"[Iteration 0] ✓ Designer responded")
    print()
    
    # Log designer response
    conversation_log.append({
        'iteration': 0,
        'role': 'designer',
        'prompt': 'Review programmer code',
        'response': designer_response[:500] + "..." if len(designer_response) > 500 else designer_response
    })
    
    # Human's initial feedback
    print("=" * 80)
    print("YOUR TURN - Please provide your feedback")
    print("=" * 80)
    print()
    print("Programmer's Code Summary:")
    print("-" * 80)
    print(programmer_response[:300] + "..." if len(programmer_response) > 300 else programmer_response)
    print()
    print("Designer's Feedback Summary:")
    print("-" * 80)
    print(designer_response[:300] + "..." if len(designer_response) > 300 else designer_response)
    print()
    
    human_prompt = (
        f"Iteration 0: Here is the conversation so far:\n\n"
        f"PROGRAMMER'S CODE:\n{programmer_response}\n\n"
        f"DESIGNER'S FEEDBACK:\n{designer_response}\n\n"
        f"Please provide your feedback, suggestions, or guidance."
    )
    
    human_response = human.get_response(human_prompt)
    print()
    print(f"[Iteration 0] ✓ Human feedback received: {len(human_response)} chars")
    print()
    
    # Log human response
    conversation_log.append({
        'iteration': 0,
        'role': 'human',
        'prompt': 'Review and provide feedback',
        'response': human_response
    })
    
    # === Iterative improvement loop ===
    
    for i in range(1, MAX_ITERATIONS + 1):
        print("=" * 80)
        print(f"ITERATION {i}")
        print("=" * 80)
        print()
        
        # Programmer improves based on designer AND human feedback
        programmer_prompt = (
            f"Please improve your Fibonacci program based on this feedback:\n\n"
            f"DESIGNER FEEDBACK:\n{designer_response}\n\n"
            f"HUMAN FEEDBACK:\n{human_response}\n\n"
            f"Provide the complete improved C code."
        )
        
        print(f"[Iteration {i}] Programmer is improving the code...")
        print("              Please wait...")
        programmer_response = programmer.get_response(programmer_prompt)
        print(f"[Iteration {i}] ✓ Programmer responded")
        print()
        
        # Log programmer response
        conversation_log.append({
            'iteration': i,
            'role': 'programmer',
            'prompt': 'Improve based on feedback',
            'response': programmer_response[:500] + "..." if len(programmer_response) > 500 else programmer_response
        })
        
        # Designer reviews the improvements
        designer_prompt = (
            f"Here is the programmer's improved Fibonacci code:\n\n"
            f"{programmer_response}\n\n"
            f"The human previously said:\n{human_response}\n\n"
            f"Please review if the improvements address the concerns."
        )
        
        print(f"[Iteration {i}] Designer is reviewing the improvements...")
        print("              Please wait...")
        designer_response = designer.get_response(designer_prompt)
        print(f"[Iteration {i}] ✓ Designer responded")
        print()
        
        # Log designer response
        conversation_log.append({
            'iteration': i,
            'role': 'designer',
            'prompt': 'Review improvements',
            'response': designer_response[:500] + "..." if len(designer_response) > 500 else designer_response
        })
        
        # Human reviews again
        print("=" * 80)
        print("YOUR TURN - Review the improvements")
        print("=" * 80)
        print()
        print("Programmer's Updated Code Summary:")
        print("-" * 80)
        print(programmer_response[:300] + "..." if len(programmer_response) > 300 else programmer_response)
        print()
        print("Designer's Review Summary:")
        print("-" * 80)
        print(designer_response[:300] + "..." if len(designer_response) > 300 else designer_response)
        print()
        
        human_prompt = (
            f"Iteration {i}: Here is the updated conversation:\n\n"
            f"PROGRAMMER'S IMPROVED CODE:\n{programmer_response}\n\n"
            f"DESIGNER'S REVIEW:\n{designer_response}\n\n"
            f"Please provide your feedback on the improvements."
        )
        
        human_response = human.get_response(human_prompt)
        print()
        print(f"[Iteration {i}] ✓ Human feedback received")
        print()
        
        # Log human response
        conversation_log.append({
            'iteration': i,
            'role': 'human',
            'prompt': 'Review improvements',
            'response': human_response
        })
        
        # Save progress
        programmer.save_to_excel(OUTPUT_FILE)
        try:
            pd.DataFrame(conversation_log).to_excel(LOG_FILE, index=False)
        except Exception:
            pass  # Ignore save errors during iteration
    
    # Save final results
    print()
    print("=" * 80)
    print("Conversation Complete!")
    print("=" * 80)
    print()
    
    programmer.save_to_excel(OUTPUT_FILE)
    
    try:
        pd.DataFrame(conversation_log).to_excel(LOG_FILE, index=False)
        print(f"✓ Full conversation saved to: {OUTPUT_FILE}")
        print(f"✓ Structured log saved to: {LOG_FILE}")
    except Exception as e:
        print(f"✗ Error saving log: {e}")
        print(f"✓ Conversation saved to: {OUTPUT_FILE}")
    
    print()
    print("Summary:")
    print(f"  Total messages: {len(programmer.messages)}")
    print(f"  Iterations completed: {MAX_ITERATIONS}")
    print(f"  Human inputs provided: {MAX_ITERATIONS + 1}")
    print()
    print("You can now:")
    print(f"  1. Open {OUTPUT_FILE} to view the full conversation")
    print(f"  2. Open {LOG_FILE} to see the structured conversation log")
    print(f"  3. Extract and test the final C code")
    print(f"  4. Analyze how your feedback influenced the development")
    print()

if __name__ == "__main__":
    main()
