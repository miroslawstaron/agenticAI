#!/usr/bin/env python3
"""
Example usage of the AgentDiagram class.

This script demonstrates how to use the AgentDiagram agent to generate
Mermaid diagrams from source code and save them to the results folder.
"""

import os
from datetime import datetime
from agentDiagram import AgentDiagram

def save_diagram(diagram_type, diagram_content):
    """Save a generated diagram to the results folder.
    
    Args:
        diagram_type: Type of diagram (class, flowchart, sequence, er)
        diagram_content: The mermaid diagram content
        
    Returns:
        Path to the saved file
    """
    # Ensure results folder exists
    results_folder = "results"
    if not os.path.exists(results_folder):
        os.makedirs(results_folder)
    
    # Create filename with timestamp
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"{results_folder}/diagram_{diagram_type}_{timestamp}.mmd"
    
    # Save the diagram
    with open(filename, 'w') as f:
        f.write(diagram_content)
    
    return filename

def save_diagram_as_png(agent, diagram_type, diagram_content):
    """Save a generated diagram as PNG.
    
    Args:
        agent: The AgentDiagram instance
        diagram_type: Type of diagram (class, flowchart, sequence, er)
        diagram_content: The mermaid diagram content
        
    Returns:
        Path to the saved PNG file or None on error
    """
    # Ensure results folder exists
    results_folder = "results"
    if not os.path.exists(results_folder):
        os.makedirs(results_folder)
    
    # Create filename with timestamp
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_path = f"{results_folder}/diagram_{diagram_type}_{timestamp}.png"
    
    # Convert to PNG
    png_file = agent.diagram_to_png(diagram_content, output_path)
    return png_file

def example_class_diagram():
    """Example: Generate a class diagram from C++ code."""
    print("=" * 60)
    print("Example 1: Generating a class diagram from C++ code")
    print("=" * 60)
    
    # Sample C code
    source_code = """
class Vehicle {
    private:
        int speed;
        string brand;
    public:
        void accelerate();
        void brake();
};

class Car : public Vehicle {
    private:
        int doors;
    public:
        void openTrunk();
};
"""
    
    # Create the agent (class diagram is default)
    agent = AgentDiagram(
        server_address="http://localhost:11434",
        model_name="qwen2.5-coder:latest",
        diagram_type="class"
    )
    
    print("\nSource Code:")
    print(source_code)
    
    # Note: This would make an actual API call if the server is available
    # For demonstration purposes, we're just showing the setup
    print("\nAgent configured to generate class diagram")
    print(f"Diagram type: {agent.diagram_type}")
    print(f"Server: {agent.server_address}")
    print(f"Model: {agent.model_name}")
    
    # To actually generate a diagram (requires a running LLM server):
    # Without validation:
    # response = agent.get_response(source_code)
    
    # With validation (recommended):
    response = agent.get_response(source_code, validate=True, max_fix_attempts=5)
    diagram = agent.extract_mermaid_diagram(response)
    print("\nGenerated Mermaid Diagram:")
    print(diagram)
    
    # Save the diagram
    if diagram:
        mmd_filepath = save_diagram("class", diagram)
        print(f"\nDiagram saved to: {mmd_filepath}")
        
        # Convert to PNG
        png_filepath = save_diagram_as_png(agent, "class", diagram)
        if png_filepath:
            print(f"PNG saved to: {png_filepath}")

def example_flowchart():
    """Example: Generate a flowchart from C code."""
    print("\n" + "=" * 60)
    print("Example 2: Generating a flowchart from C code")
    print("=" * 60)
    
    # Sample C code
    source_code = """
int factorial(int n) {
    if (n <= 1) {
        return 1;
    } else {
        return n * factorial(n - 1);
    }
}
"""
    
    # Create the agent with flowchart type
    agent = AgentDiagram(
        server_address="http://localhost:11434",
        model_name="qwen2.5-coder:latest",
        diagram_type="flowchart"
    )
    
    print("\nSource Code:")
    print(source_code)
    
    print("\nAgent configured to generate flowchart")
    print(f"Diagram type: {agent.diagram_type}")
    
    # Generate the flowchart
    # With validation enabled to ensure diagram is valid
    response = agent.get_response(source_code, validate=True, max_fix_attempts=5)
    diagram = agent.extract_mermaid_diagram(response)
    print("\nGenerated Mermaid Diagram:")
    print(diagram)
    
    # Save the diagram
    if diagram:
        mmd_filepath = save_diagram("flowchart", diagram)
        print(f"\nDiagram saved to: {mmd_filepath}")
        
        # Convert to PNG
        png_filepath = save_diagram_as_png(agent, "flowchart", diagram)
        if png_filepath:
            print(f"PNG saved to: {png_filepath}")

def example_changing_diagram_type():
    """Example: Changing diagram type dynamically."""
    print("\n" + "=" * 60)
    print("Example 3: Changing diagram type dynamically")
    print("=" * 60)
    
    # Create agent with default class diagram
    agent = AgentDiagram(
        server_address="http://localhost:11434",
        model_name="qwen2.5-coder:latest"
    )
    
    print(f"Initial diagram type: {agent.diagram_type}")
    
    # Change to sequence diagram
    agent.set_diagram_type("sequence")
    print(f"Changed to: {agent.diagram_type}")
    
    # Change to flowchart
    agent.set_diagram_type("flowchart")
    print(f"Changed to: {agent.diagram_type}")
    
    # Change to entity-relationship
    agent.set_diagram_type("er")
    print(f"Changed to: {agent.diagram_type}")
    
    print("\nSupported diagram types:")
    print("  - class: Class diagrams (default)")
    print("  - flowchart: Flowchart diagrams")
    print("  - sequence: Sequence diagrams")
    print("  - er: Entity-Relationship diagrams")

def example_validation():
    """Example: Using diagram validation."""
    print("\n" + "=" * 60)
    print("Example 4: Generating diagrams with validation")
    print("=" * 60)
    
    source_code = """
class Database {
    private:
        Connection conn;
    public:
        void connect();
        void disconnect();
};
"""
    
    agent = AgentDiagram(
        server_address="http://localhost:11434",
        model_name="qwen2.5-coder:latest",
        diagram_type="class"
    )
    
    print("\nSource Code:")
    print(source_code)
    
    print("\nGenerating diagram with validation enabled...")
    print("The agent will:")
    print("  1. Generate a mermaid diagram")
    print("  2. Validate it using the mermaid compiler (mmdc)")
    print("  3. If errors are found, ask the model to fix them")
    print("  4. Repeat up to 5 times until valid or max attempts reached")
    
    # Generate with validation
    response = agent.get_response(source_code, validate=True, max_fix_attempts=5)
    
    if response:
        diagram = agent.extract_mermaid_diagram(response)
        print("\nFinal validated diagram:")
        print(diagram)
        
        # Save the diagram
        mmd_filepath = save_diagram("class_validated", diagram)
        print(f"\nValidated diagram saved to: {mmd_filepath}")
    else:
        print("\nFailed to generate diagram")

def main():
    """Run all examples."""
    print("AgentDiagram Usage Examples")
    print("===========================\n")
    
    example_class_diagram()
    example_flowchart()
    example_changing_diagram_type()
    example_validation()
    
    print("\n" + "=" * 60)
    print("Examples complete!")
    print("=" * 60)
    print("\nNote: To actually generate diagrams, you need:")
    print("  1. A running LLM server (e.g., Ollama)")
    print("  2. Call agent.get_response(source_code, validate=True) for validation")
    print("  3. Extract diagram with agent.extract_mermaid_diagram(response)")
    print("  4. Convert to PNG with agent.diagram_to_png(diagram, output_path)")
    print("\nFor validation to work, install mermaid-cli:")
    print("  npm install -g @mermaid-js/mermaid-cli")

if __name__ == "__main__":
    main()
