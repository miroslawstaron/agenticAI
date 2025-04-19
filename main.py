# use the agent.py file to run the agent
import argparse
from agent import AgentAI

def main():
    # Parse command-line arguments
    parser = argparse.ArgumentParser(description="Run the AgentAI with a prompt.")
    parser.add_argument("--prompt", type=str, required=True, help="The prompt to send to the agent.")
    args = parser.parse_args()

    # Create an instance of the Agent class
    agent = AgentAI(server_address="http://deeperthought.cse.chalmers.se", model_name="llama3.2")

    # Get the response from the agent
    response = agent.get_response(args.prompt)
    
    print("Agent Response:", response)

if __name__ == "__main__":
    main()
