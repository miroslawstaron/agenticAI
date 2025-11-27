#!/usr/bin/env python3
"""
Example usage of the AgentDiagram class.

This script demonstrates how to use the AgentDiagram agent to generate
Mermaid diagrams from source code.
"""

from agentDiagram import AgentDiagram

def example_class_diagram():
    """Example: Generate a class diagram from C code."""
    print("=" * 60)
    print("Example 1: Generating a class diagram from C code")
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
        model_name="deepseek-r1:70b",
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
    # response = agent.get_response(source_code)
    # diagram = agent.extract_mermaid_diagram(response)
    # print("\nGenerated Mermaid Diagram:")
    # print(diagram)

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
        model_name="deepseek-r1:70b",
        diagram_type="flowchart"
    )
    
    print("\nSource Code:")
    print(source_code)
    
    print("\nAgent configured to generate flowchart")
    print(f"Diagram type: {agent.diagram_type}")

def example_changing_diagram_type():
    """Example: Changing diagram type dynamically."""
    print("\n" + "=" * 60)
    print("Example 3: Changing diagram type dynamically")
    print("=" * 60)
    
    # Create agent with default class diagram
    agent = AgentDiagram(
        server_address="http://localhost:11434",
        model_name="deepseek-r1:70b"
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

def main():
    """Run all examples."""
    print("AgentDiagram Usage Examples")
    print("===========================\n")
    
    example_class_diagram()
    example_flowchart()
    example_changing_diagram_type()
    
    print("\n" + "=" * 60)
    print("Examples complete!")
    print("=" * 60)
    print("\nNote: To actually generate diagrams, you need:")
    print("  1. A running LLM server (e.g., Ollama)")
    print("  2. Call agent.get_response(source_code)")
    print("  3. Extract diagram with agent.extract_mermaid_diagram(response)")

if __name__ == "__main__":
    main()
