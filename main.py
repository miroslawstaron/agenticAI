# use the agent.py file to run the agent
import os
import sys
import time

from agent import AgentAI

def main():
    # Create an instance of the Agent class
    agent = AgentAI(server_address="http://deeperthought.cse.chalmers.se", model_name="llama3.2")

    # Start the agent
    strResponse = agent.get_response("Hello, how are you?")

if __name__ == "__main__":
    main()
