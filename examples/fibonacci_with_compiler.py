#!/usr/bin/env python3
"""
Fibonacci Example with Compiler Agent

This example demonstrates a conversation between:
- Designer: Provides design suggestions and improvements
- Programmer: Writes C code (with automatic compilation validation via AgentAIC)

The AgentAIC automatically compiles the code and fixes any compilation errors.
"""

from agent import AgentAI
from agentC import AgentAIC
import sys
import os

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def main():
    print("=" * 80)
    print("Fibonacci Example with Compiler Agent")
    print("=" * 80)
    print()
    
    # Configuration
    MAX_ITERATIONS = 5
    SERVER = "http://localhost:11434"
    MODEL = "deepseek-r1:70b"
    OUTPUT_FILE = "fibonacci_compiled_conversation.xlsx"
    
    print(f"Configuration:")
    print(f"  Server: {SERVER}")
    print(f"  Model: {MODEL}")
    print(f"  Iterations: {MAX_ITERATIONS}")
    print(f"  Output: {OUTPUT_FILE}")
    print()
    
    print("NOTE: This example requires gcc to be installed for C compilation.")
    print("      The AgentCompiler will automatically compile and fix code.")
    print()
    
    # Create Designer Agent (without compilation)
    print("Creating Designer Agent...")
    designer = AgentAI(
        server_address=SERVER,
        model_name=MODEL,
        my_role=(
            "You are an expert C software designer. "
            "You provide design suggestions, code reviews, and improvements. "
            "You focus on code quality, efficiency, correctness, and best practices for C programming."
        )
    )
    
    # Create Programmer Agent with Compilation (AgentAIC)
    print("Creating Programmer Agent with Compiler...")
    programmer = AgentAIC(
        server_address=SERVER,
        model_name=MODEL,
        my_role=(
            "You are an expert C programmer. "
            "You write compilable C code to solve tasks. "
            "You respond only with complete, working C programs. "
            "No comments or explanations outside the code."
        )
    )
    
    print()
    print("Starting conversation...")
    print()
    
    # Initial task - ask programmer to solve Fibonacci
    task = (
        "Write a complete C program that calculates the Fibonacci sequence. "
        "Requirements:\n"
        "1. Accept a number n from the user (use scanf)\n"
        "2. Calculate and print the first n Fibonacci numbers\n"
        "3. Use an efficient iterative algorithm\n"
        "4. Include all necessary headers\n"
        "5. Include proper main function\n"
        "6. Handle edge cases (n <= 0)\n"
        "Provide only the complete compilable C code."
    )
    
    print("Initial Task:")
    print("-" * 80)
    print(task)
    print("-" * 80)
    print()
    
    # Get first response from programmer (with automatic compilation)
    print("[Iteration 0] Programmer is writing and compiling the code...")
    print("              (This may take a moment as the code is compiled and fixed)")
    programmer_response = programmer.get_response(task)
    
    if programmer_response:
        print(f"[Iteration 0] ✓ Programmer provided compiled code ({len(programmer_response)} chars)")
    else:
        print(f"[Iteration 0] ✗ Programmer failed to generate valid code")
        print("              Please check your server and model configuration")
        return
    print()
    
    # Get first feedback from designer
    designer_prompt = (
        f"Here is the programmer's compiled Fibonacci C program:\n\n"
        f"{programmer_response}\n\n"
        f"Please review this code and provide constructive feedback on:\n"
        f"1. Code quality and readability\n"
        f"2. Algorithm efficiency\n"
        f"3. Potential bugs or edge cases\n"
        f"4. Memory management (if applicable)\n"
        f"5. Best practices for C programming\n"
        f"6. Any improvements or optimizations"
    )
    
    print("[Iteration 0] Designer is reviewing the compiled code...")
    designer_response = designer.get_response(designer_prompt)
    print(f"[Iteration 0] Designer responded ({len(designer_response)} chars)")
    print()
    
    # Iterative improvement loop
    for i in range(1, MAX_ITERATIONS + 1):
        print(f"[Iteration {i}] Starting improvement cycle...")
        
        # Programmer improves based on designer feedback (with compilation)
        programmer_prompt = (
            f"The designer provided this feedback on your Fibonacci C program:\n\n"
            f"{designer_response}\n\n"
            f"Please update your program to address this feedback. "
            f"Provide the complete, improved, compilable C code."
        )
        
        print(f"[Iteration {i}] Programmer is improving and compiling the code...")
        programmer_response = programmer.get_response(programmer_prompt)
        
        if programmer_response:
            print(f"[Iteration {i}] ✓ Programmer provided improved compiled code ({len(programmer_response)} chars)")
        else:
            print(f"[Iteration {i}] ✗ Programmer failed to improve the code")
            break
        
        # Designer reviews the improved code
        designer_prompt = (
            f"Here is the programmer's improved Fibonacci C program:\n\n"
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
    print(f"  All code was compiled and validated with gcc")
    print()
    print("You can now:")
    print(f"  1. Open {OUTPUT_FILE} to view the full conversation")
    print(f"  2. Extract the final compiled C code")
    print(f"  3. Compile and run the code yourself: gcc -o fibonacci code.c && ./fibonacci")
    print(f"  4. Analyze how the code improved through iterations")
    print()

if __name__ == "__main__":
    main()
