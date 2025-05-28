# use the agent.py file to run the agent
import argparse
import re
from tqdm import tqdm  # Import tqdm for progress bar
from agent import AgentAI

def extract_c_code(markdown: str) -> str:
    '''This function extracts the C code from a markdown string.'''
    try: 
        pattern = r"```c(.*?)```"
        match = re.search(pattern, markdown, re.DOTALL)
        if match:
            return match.group(1).strip()
    except:
        pass
    return ""

def main():
    MAX_ITERATIONS = 5000  # Set the maximum number of iterations

    # Parse command-line arguments
    parser = argparse.ArgumentParser(description="Run the AgentAI with a prompt.")
    parser.add_argument("--prompt", type=str, required=True, help="The prompt to send to the agent.")
    args = parser.parse_args()

    # Create an instance of the Agent class
    agentDesigner = AgentAI(server_address="http://deeperthought.cse.chalmers.se", 
                              model_name="deepseek-r1:7b",
                              my_role="You are a C designer. You will be given a task and you will respond with design suggestions to solve or the task.")
    
    agentProgrammer = AgentAI(server_address="http://deepthought.cse.chalmers.se", 
                            model_name="minicpm-v:8b",
                            my_role="You are a C Programmer. You respond with the code in C to solve the task. No comments or explanations")
    
    # Get the response from the agent
    responseProgrammer = agentProgrammer.get_response(args.prompt)
    #print("Programmer Response:", responseProgrammer)
    
    responseDesigner = agentDesigner.get_response(f'Here is my program, how can I improve it {responseProgrammer}?')
    #print("\n\nDesigner Response:", responseDesigner)

    for i in tqdm(range(MAX_ITERATIONS), desc="Processing iterations"):
        responseProgrammer = agentProgrammer.get_response(responseDesigner)
        #print("\n\n:::::::::::::::::::Programmer Response::::::::::::::::::")
        #print(responseProgrammer[:100])
        
        responseDesigner = agentDesigner.get_response(f'Here is my program, how can I improve it {responseProgrammer}?')
        #print("\n\n:::::::::::::::::::Designer Response::::::::::::::::::")
        #print(responseDesigner[:100])

        agentProgrammer.save_to_excel("programmer_conversation_deepseek7b_minicp.xlsx")

       

    
if __name__ == "__main__":
    main()
