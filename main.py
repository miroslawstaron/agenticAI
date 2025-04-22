# use the agent.py file to run the agent
import argparse
from agent import AgentAI

def main():
    # Parse command-line arguments
    parser = argparse.ArgumentParser(description="Run the AgentAI with a prompt.")
    parser.add_argument("--prompt", type=str, required=True, help="The prompt to send to the agent.")
    args = parser.parse_args()

    # Create an instance of the Agent class
    agentProgrammer = AgentAI(server_address="http://deeperthought.cse.chalmers.se", 
                              model_name="llama3.2",
                              my_role="You are a C programmer. You respond with the code in C to solve the task. No comments or explanations")
    agentDesigner = AgentAI(server_address="http://deepthought.cse.chalmers.se", 
                            model_name="llama3.2",
                            my_role="You are a C designer. You will be given a task and you will respond with design suggestions to solve or the task.")
    
    # Get the response from the agent
    responseProgrammer = agentProgrammer.get_response(args.prompt)
    print("Programmer Response:", responseProgrammer)
    
    responseDesigner = agentDesigner.get_response(responseProgrammer)
    print("Designer Response:", responseDesigner)

    for i in range(3):
        responseProgrammer = agentProgrammer.get_response(responseDesigner)
        print("Programmer Response::::::::::::::::::")
        print(responseProgrammer)
        
        responseDesigner = agentDesigner.get_response(responseProgrammer)
        print("Designer Response::::::::::::::::::")
        print(responseDesigner)

    # Save the conversation to a CSV file
    agentProgrammer.save_to_excel("programmer_conversation.xlsx")
if __name__ == "__main__":
    main()
