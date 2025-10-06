#!/usr/bin/env python3
# use the agent.py file to run the agent
import argparse
from agentC import AgentAIC
from agent import AgentAI
from tqdm import tqdm

MAX_ITERATIONS = 10  # Set the maximum number of iterations

def main():
    # Parse command-line arguments
    parser = argparse.ArgumentParser(description="Run the AgentAI with a prompt.")
    parser.add_argument("--prompt", type=str, required=True, help="The prompt to send to the agent.")
    args = parser.parse_args()

    # Create an instance of the Agent class
    agentProgrammer = AgentAIC(server_address="http://lazythought.cse.chalmers.se/v1/chat/completions", 
                              model_name="llama3.2:3b",
                              my_role="You are a C programmer. You respond with the code in C to solve the task. No comments or explanations")
    
    agentDesigner = AgentAI(server_address="http://lazythought.cse.chalmers.se/v1/chat/completions", 
                            model_name="gpt-oss:20b",
                            my_role="You are a C designer. You will be given a task and you will respond with design suggestions to solve or the task.")
    
    # Get the response from the agent
    responseProgrammer = agentProgrammer.get_response(args.prompt)
    #print("Programmer Response:", responseProgrammer)
    
    responseDesigner = agentDesigner.get_response(f'Here is my program, how can I improve it {responseProgrammer}?')

    for i in tqdm(range(MAX_ITERATIONS), desc="Processing iterations"):
        # if this is the first iteration, then we use the original prompt
        if i == 0:
            # Get the response from the programmer agent
            responseProgrammer = agentProgrammer.get_response(responseDesigner)

            # Get the response from the designer agent
            responseDesigner = agentDesigner.get_response(f'How to improve this code: {responseProgrammer}')
        else: 
            # for all the other iterations, we only match the responses from one another
            responseProgrammer = agentProgrammer.get_response(responseDesigner)
            
            responseDesigner = agentDesigner.get_response(responseProgrammer)

        # save to excel to get the conversation saved somewhere
        agentProgrammer.save_to_excel("./results/programmer_compiler_conversation_oss20b_llama32_3b_t.xlsx")

    agentProgrammer.save_to_excel("./results/programmer_compiler_conversation_oss20b_llama32_3b_t.xlsx")
    
if __name__ == "__main__":
    main()
