#!/usr/bin/env python3
"""
Fibonacci Example with Python Agent (Simple)

This example demonstrates a conversation between:
- Designer: Provides design suggestions and improvements
- Programmer: Writes Python code (without automatic execution validation)

This is the simplest Python example, similar to fibonacci_simple.py but for Python code.
"""

import sys
import os

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from agent import AgentAI

def main():
    print("=" * 80)
    print("Fibonacci Example with Python Agent (Simple)")
    print("=" * 80)
    print()
    
    # Configuration
    MAX_ITERATIONS = 3
    SERVER = "http://localhost:11434"
    MODEL = "deepseek-r1:70b"
    OUTPUT_FILE = "fibonacci_python_simple_conversation.xlsx"
    
    print(f"Configuration:")
    print(f"  Server: {SERVER}")
    print(f"  Model: {MODEL}")
    print(f"  Iterations: {MAX_ITERATIONS}")
    print(f"  Output: {OUTPUT_FILE}")
    print()
    
    print("NOTE: This example does NOT validate Python code execution.")
    print("      For code validation, use fibonacci_python_with_interpreter.py")
    print()
    
    # Create Designer Agent
    print("Creating Designer Agent...")
    designer = AgentAI(
        server_address=SERVER,
        model_name=MODEL,
        my_role=(
            "You are an expert Python software designer. "
            "You provide design suggestions, code reviews, and improvements. "
            "You focus on code quality, efficiency, correctness, and best practices for Python programming."
        )
    )
    
    # Create Programmer Agent (basic, no execution)
    print("Creating Programmer Agent...")
    programmer = AgentAI(
        server_address=SERVER,
        model_name=MODEL,
        my_role=(
            "You are an expert Python programmer. "
            "You write clean, efficient Python code to solve tasks. "
            "You respond only with complete, working Python programs. "
            "No comments or explanations outside the code."
        )
    )
    
    print()
    print("Starting conversation...")
    print()
    
    # Initial task - ask programmer to solve Fibonacci
    task = (
        "Write a complete Python program that calculates the Fibonacci sequence. "
        "Requirements:\n"
        "1. Accept a number n from the user (use input())\n"
        "2. Calculate and print the first n Fibonacci numbers\n"
        "3. Use an efficient iterative algorithm\n"
        "4. Include proper main function with if __name__ == '__main__'\n"
        "5. Handle edge cases (n <= 0)\n"
        "6. Use type hints for better code quality\n"
        "Provide only the complete Python code."
    )
    
    print("Initial Task:")
    print("-" * 80)
    print(task)
    print("-" * 80)
    print()
    
    # Get first response from programmer
    print("[Iteration 0] Programmer is writing the code...")
    programmer_response = programmer.get_response(task)
    
    if programmer_response:
        print(f"[Iteration 0] ✓ Programmer provided code ({len(programmer_response)} chars)")
    else:
        print(f"[Iteration 0] ✗ Programmer failed to generate code")
        print("              Please check your server and model configuration")
        return
    print()
    
    # Get first feedback from designer
    designer_prompt = (
        f"Here is the programmer's Python Fibonacci program:\n\n"
        f"{programmer_response}\n\n"
        f"Please review this code and provide constructive feedback on:\n"
        f"1. Code quality and readability\n"
        f"2. Algorithm efficiency\n"
        f"3. Potential bugs or edge cases\n"
        f"4. Python best practices (PEP 8, type hints, etc.)\n"
        f"5. Error handling\n"
        f"6. Any improvements or optimizations"
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
            f"The designer provided this feedback on your Python Fibonacci program:\n\n"
            f"{designer_response}\n\n"
            f"Please update your program to address this feedback. "
            f"Provide the complete, improved Python code."
        )
        
        print(f"[Iteration {i}] Programmer is improving the code...")
        programmer_response = programmer.get_response(programmer_prompt)
        
        if programmer_response:
            print(f"[Iteration {i}] ✓ Programmer provided improved code ({len(programmer_response)} chars)")
        else:
            print(f"[Iteration {i}] ✗ Programmer failed to improve the code")
            break
        
        # Designer reviews the improved code
        designer_prompt = (
            f"Here is the programmer's improved Python Fibonacci program:\n\n"
            f"{programmer_response}\n\n"
            f"Please review the improvements and provide additional feedback if needed. "
            f"Focus on any remaining issues or further optimizations."
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
    print(f"  2. Extract the final Python code from the conversation")
    print(f"  3. Save the code to a .py file and run it: python fibonacci.py")
    print(f"  4. Analyze how the code improved through iterations")
    print()

if __name__ == "__main__":
    main()
