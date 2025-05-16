#!/usr/bin/env python3
# use the agent.py file to run the agent
import argparse
from agentC import AgentAIC
from agent import AgentAI
from tqdm import tqdm

MAX_ITERATIONS = 20  # Set the maximum number of iterations

def main():
    # Parse command-line arguments
    parser = argparse.ArgumentParser(description="Run the AgentAI with a prompt.")
    parser.add_argument("--prompt", type=str, required=True, help="The prompt to send to the agent.")
    args = parser.parse_args()

    # Create an instance of the Agent class
    agentProgrammer = AgentAIC(server_address="http://deeperthought.cse.chalmers.se", 
                              model_name="llama3.3",
                              my_role="You are a C programmer. You respond with the code in C to solve the task. No comments or explanations")
    
    agentDesigner = AgentAI(server_address="http://deeperthought.cse.chalmers.se", 
                            model_name="llama3.3",
                            my_role="You are a C designer. You will be given a task and you will respond with design suggestions to solve or the task.")
    

    for i in tqdm(range(MAX_ITERATIONS), desc="Processing iterations"):
        # if this is the first iteration, then we use the original prompt
        if i == 0:
            # Get the response from the programmer agent
            responseProgrammer = agentProgrammer.start(3, args.prompt)

            # Get the response from the designer agent
            responseDesigner = agentDesigner.get_response(f'How to improve this code: {responseProgrammer}')
        else: 
            # for all the other iterations, we only match the responses from one another
            responseProgrammer = agentProgrammer.start(3, responseDesigner)
            
            responseDesigner = agentDesigner.get_response(responseProgrammer)

        # save to excel to get the conversation saved somewhere
        agentProgrammer.save_to_excel("programmer_conversation_ll3_ll3.xlsx")
 
    
if __name__ == "__main__":
    main()
