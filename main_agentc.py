#!/usr/bin/env python3
# use the agent.py file to run the agent
import argparse
from agentC import AgentAIC
from agent import AgentAI
from tqdm import tqdm
import os
from logger import get_logger

MAX_ITERATIONS = 2  # Set the maximum number of iterations
FILENAME_RESULT = "results/conversation_result_test.xlsx"
API_KEY = os.getenv('OPENAI_API_KEY', '')

def main():
    # Parse command-line arguments
    parser = argparse.ArgumentParser(description="Run the AgentAI with a prompt.")
    
    parser.add_argument("--prompt", 
                        type=str, 
                        required=True, 
                        help="The prompt to send to the agent.")
    
    parser.add_argument("--log", 
                        action="store_true", 
                        help="Enable logging to execution.log file.")
    
    args = parser.parse_args()
    
    # Initialize logger if --log flag is set
    if args.log:
        logger = get_logger()
        logger.enable("execution.log")
        logger.info("="*80)
        logger.info("Starting new execution session (main_agentc)")
        logger.info("="*80)

    # Create an instance of the Agent class
    agentProgrammer = AgentAIC(server_address="http://localhost:11434", 
                              model_name="ollama/qwen2.5-coder:latest",
                              api_key=API_KEY,
                              my_role="You are a C programmer. You respond with the code in C to solve the task. No comments or explanations")
    
    agentDesigner = AgentAI(server_address="http://localhost:11434", 
                            model_name="ollama/phi4-mini-reasoning:latest",
                            api_key=API_KEY,
                            my_role="You are a C designer. You will be given a task and you will respond with design suggestions to solve or the task.")
    
    # Get the response from the agent
    responseProgrammer = agentProgrammer.get_response(args.prompt)
    # print("Programmer Response:", responseProgrammer)
    
    # Get the response from the designer
    responseDesigner = agentDesigner.get_response(f'Here is my program, how can I improve it {responseProgrammer}?')
    # print("Designer Response:", responseDesigner)
    
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
        agentProgrammer.save_to_excel(FILENAME_RESULT)

    agentProgrammer.save_to_excel(FILENAME_RESULT)

    # Initialize logger if --log flag is set
    if args.log:
        logger.info("="*80)
        logger.info("Finished execution session (main_agentc)")
        logger.info("="*80)
if __name__ == "__main__":
    main()
