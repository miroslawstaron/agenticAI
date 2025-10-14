# use the agent.py file to run the agent
import argparse
import re
from tqdm import tqdm  # Import tqdm for progress bar
from agent import AgentAI


## File name to save
strFileNameToSave = "results/conversation_viki_deepseek7b_minicp.xlsx"


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
    MAX_ITERATIONS = 20  # Set the maximum number of iterations

    # Parse command-line arguments
    parser = argparse.ArgumentParser(description="Run the AgentAI with a prompt.")
    parser.add_argument("--prompt", type=str, required=True, help="The prompt to send to the agent.")
    args = parser.parse_args()

    # Create an instance of the Agent class
    agentTeacher = AgentAI(server_address="http://lazythought.cse.chalmers.se/v1/chat/completions", 
                              model_name="gpt-oss:20b",
                              my_role="You are a teacher, you must help the student to solve their task. You respond with suggestions, not solutions.")

    agentStudent = AgentAI(server_address="http://lazythought.cse.chalmers.se/v1/chat/completions", 
                            model_name="gpt-oss:20b",
                            my_role="You are a student, you must solve the task given by the teacher. You respond with solutions, not suggestions.")
    
    # Get the response from the agent
    responseProgrammer = agentStudent.get_response(args.prompt)
    #print("Programmer Response:", responseProgrammer)

    responseDesigner = agentTeacher.get_response(f'Here is my solution to this problem {args.prompt}, how can I improve it: {responseProgrammer}?')
    #print("\n\nDesigner Response:", responseDesigner)

    for i in tqdm(range(MAX_ITERATIONS), desc="Processing iterations"):
        responseProgrammer = agentStudent.get_response(responseDesigner)
        #print("\n\n:::::::::::::::::::Programmer Response::::::::::::::::::")
        #print(responseProgrammer[:100])

        responseDesigner = agentTeacher.get_response(f'Here is my solution, how can I improve it {responseProgrammer}?')
        #print("\n\n:::::::::::::::::::Designer Response::::::::::::::::::")
        #print(responseDesigner[:100])

        agentStudent.save_to_excel(strFileNameToSave)

       

    
if __name__ == "__main__":
    main()
