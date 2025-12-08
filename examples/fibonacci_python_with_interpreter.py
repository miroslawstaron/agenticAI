#!/usr/bin/env python3
"""
Fibonacci Example with Python Interpreter Agent

This example demonstrates a conversation between:
- Designer: Provides design suggestions and improvements
- Programmer: Writes Python code (with automatic execution validation via AgentAIPy)

The AgentAIPy automatically executes the code and fixes any runtime errors.
"""

import sys
import os

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from agent import AgentAI
from agentPy import AgentAIPy

def main():
    print("=" * 80)
    print("Fibonacci Example with Python Interpreter Agent")
    print("=" * 80)
    print()
    
    # Configuration
    MAX_ITERATIONS = 3
    SERVER = "http://localhost:11434"
    MODEL = "deepseek-r1:70b"
    OUTPUT_FILE = "fibonacci_python_interpreted_conversation.xlsx"
    
    print(f"Configuration:")
    print(f"  Server: {SERVER}")
    print(f"  Model: {MODEL}")
    print(f"  Iterations: {MAX_ITERATIONS}")
    print(f"  Output: {OUTPUT_FILE}")
    print()
    
    print("NOTE: This example validates Python code execution automatically.")
    print("      The AgentPyInterpreter will execute and fix code with runtime errors.")
    print()
    
    # Create Designer Agent (without execution)
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
    
    # Create Programmer Agent with Interpreter (AgentAIPy)
    print("Creating Programmer Agent with Interpreter...")
    programmer = AgentAIPy(
        server_address=SERVER,
        model_name=MODEL,
        my_role=(
            "You are an expert Python programmer. "
            "You write clean, efficient, executable Python code to solve tasks. "
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
        "1. Calculate and print the first 10 Fibonacci numbers (hardcoded, no user input)\n"
        "2. Use an efficient iterative algorithm\n"
        "3. Include proper main function with if __name__ == '__main__'\n"
        "4. Use type hints for better code quality\n"
        "5. Make sure the program runs without errors\n"
        "Provide only the complete executable Python code."
    )
    
    print("Initial Task:")
    print("-" * 80)
    print(task)
    print("-" * 80)
    print()
    
    # Get first response from programmer (with automatic execution)
    print("[Iteration 0] Programmer is writing and executing the code...")
    print("              (This may take a moment as the code is executed and fixed)")
    programmer_response = programmer.get_response(task)
    
    if programmer_response:
        print(f"[Iteration 0] ✓ Programmer provided executable code ({len(programmer_response)} chars)")
    else:
        print(f"[Iteration 0] ✗ Programmer failed to generate valid code")
        print("              Please check your server and model configuration")
        return
    print()
    
    # Get first feedback from designer
    designer_prompt = (
        f"Here is the programmer's executable Python Fibonacci program:\n\n"
        f"{programmer_response}\n\n"
        f"Please review this code and provide constructive feedback on:\n"
        f"1. Code quality and readability\n"
        f"2. Algorithm efficiency\n"
        f"3. Potential bugs or edge cases\n"
        f"4. Python best practices (PEP 8, type hints, etc.)\n"
        f"5. Error handling\n"
        f"6. Any improvements or optimizations"
    )
    
    print("[Iteration 0] Designer is reviewing the executable code...")
    designer_response = designer.get_response(designer_prompt)
    print(f"[Iteration 0] Designer responded ({len(designer_response)} chars)")
    print()
    
    # Iterative improvement loop
    for i in range(1, MAX_ITERATIONS + 1):
        print(f"[Iteration {i}] Starting improvement cycle...")
        
        # Programmer improves based on designer feedback (with execution)
        programmer_prompt = (
            f"The designer provided this feedback on your Python Fibonacci program:\n\n"
            f"{designer_response}\n\n"
            f"Please update your program to address this feedback. "
            f"Provide the complete, improved, executable Python code."
        )
        
        print(f"[Iteration {i}] Programmer is improving and executing the code...")
        programmer_response = programmer.get_response(programmer_prompt)
        
        if programmer_response:
            print(f"[Iteration {i}] ✓ Programmer provided improved executable code ({len(programmer_response)} chars)")
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
    print(f"  All code was executed and validated with Python interpreter")
    print()
    print("You can now:")
    print(f"  1. Open {OUTPUT_FILE} to view the full conversation")
    print(f"  2. Extract the final executable Python code")
    print(f"  3. Save and run the code yourself: python fibonacci.py")
    print(f"  4. Analyze how the code improved through iterations")
    print()

if __name__ == "__main__":
    main()
