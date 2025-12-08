#!/usr/bin/env python3
"""
Simple Fibonacci Example - Designer and Programmer Agents

This example demonstrates a basic conversation between two AI agents:
- Designer: Provides design suggestions and improvements
- Programmer: Writes code to solve the Fibonacci problem

No compilation is involved in this example.
"""

import sys
import os

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from agent import AgentAI

def main():
    print("=" * 80)
    print("Simple Fibonacci Example - Designer & Programmer Conversation")
    print("=" * 80)
    print()
    
    # Configuration
    MAX_ITERATIONS = 5
    SERVER = "http://localhost:11434"
    MODEL = "deepseek-r1:70b"
    OUTPUT_FILE = "fibonacci_simple_conversation.xlsx"
    
    print(f"Configuration:")
    print(f"  Server: {SERVER}")
    print(f"  Model: {MODEL}")
    print(f"  Iterations: {MAX_ITERATIONS}")
    print(f"  Output: {OUTPUT_FILE}")
    print()
    
    # Create Designer Agent
    print("Creating Designer Agent...")
    designer = AgentAI(
        server_address=SERVER,
        model_name=MODEL,
        my_role=(
            "You are an experienced software designer. "
            "You provide design suggestions, code reviews, and improvements. "
            "You focus on code quality, efficiency, and best practices."
        )
    )
    
    # Create Programmer Agent
    print("Creating Programmer Agent...")
    programmer = AgentAI(
        server_address=SERVER,
        model_name=MODEL,
        my_role=(
            "You are an experienced programmer. "
            "You write code to solve tasks following design guidelines. "
            "You respond with complete, working solutions."
        )
    )
    
    print()
    print("Starting conversation...")
    print()
    
    # Initial task - ask programmer to solve Fibonacci
    task = (
        "Write a C program that calculates the Fibonacci sequence. "
        "The program should:\n"
        "1. Accept a number n from the user\n"
        "2. Calculate and print the first n Fibonacci numbers\n"
        "3. Use an efficient algorithm\n"
        "Please provide the complete C code."
    )
    
    print("Initial Task:")
    print("-" * 80)
    print(task)
    print("-" * 80)
    print()
    
    # Get first response from programmer
    print("[Iteration 0] Programmer is working on the initial solution...")
    programmer_response = programmer.get_response(task)
    print(f"[Iteration 0] Programmer responded ({len(programmer_response)} chars)")
    print()
    
    # Get first feedback from designer
    designer_prompt = (
        f"Here is the programmer's solution to the Fibonacci problem:\n\n"
        f"{programmer_response}\n\n"
        f"Please review this code and provide constructive feedback on:\n"
        f"1. Code quality and readability\n"
        f"2. Algorithm efficiency\n"
        f"3. Potential improvements or issues\n"
        f"4. Best practices"
    )
    
    print("[Iteration 0] Designer is reviewing the code...")
    designer_response = designer.get_response(designer_prompt)
    print(f"[Iteration 0] Designer responded ({len(designer_response)} chars)")
    print()
    
    # Iterative improvement loop
    for i in range(1, MAX_ITERATIONS + 1):
        print(f"[Iteration {i}] Starting improvement cycle...")
        
        # Programmer improves based on designer feedback
        programmer_prompt = (
            f"The designer provided this feedback on your code:\n\n"
            f"{designer_response}\n\n"
            f"Please update your Fibonacci program to address this feedback. "
            f"Provide the improved complete C code."
        )
        
        print(f"[Iteration {i}] Programmer is improving the code...")
        programmer_response = programmer.get_response(programmer_prompt)
        print(f"[Iteration {i}] Programmer responded ({len(programmer_response)} chars)")
        
        # Designer reviews the improved code
        designer_prompt = (
            f"Here is the programmer's improved Fibonacci code:\n\n"
            f"{programmer_response}\n\n"
            f"Please review the improvements and provide additional feedback if needed."
        )
        
        print(f"[Iteration {i}] Designer is reviewing the improvements...")
        designer_response = designer.get_response(designer_prompt)
        print(f"[Iteration {i}] Designer responded ({len(designer_response)} chars)")
        print()
        
        # Save progress after each iteration
        programmer.save_to_excel(OUTPUT_FILE)
    
    # Save final conversation
    print("=" * 80)
    print("Conversation Complete!")
    print("=" * 80)
    print()
    programmer.save_to_excel(OUTPUT_FILE)
    print(f"✓ Conversation saved to: {OUTPUT_FILE}")
    print()
    print("Summary:")
    print(f"  Total messages: {len(programmer.messages)}")
    print(f"  Iterations completed: {MAX_ITERATIONS}")
    print()
    print("You can now:")
    print(f"  1. Open {OUTPUT_FILE} to view the full conversation")
    print(f"  2. Analyze the improvement progression over iterations")
    print(f"  3. Extract the final C code from the conversation")
    print()

if __name__ == "__main__":
    main()
