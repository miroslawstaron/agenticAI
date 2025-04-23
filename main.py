# use the agent.py file to run the agent
import argparse
from agent import AgentAI

def main():
    # Parse command-line arguments
    parser = argparse.ArgumentParser(description="Run the AgentAI with a prompt.")
    parser.add_argument("--prompt", type=str, required=True, help="The prompt to send to the agent.")
    args = parser.parse_args()

    # Create an instance of the Agent class
    agentDesigner = AgentAI(server_address="http://deepthought.cse.chalmers.se", 
                              model_name="gemma2:2b",
                              my_role="You are a C designer. You will be given a task and you will respond with design suggestions to solve or the task.")
    agentProgrammer = AgentAI(server_address="http://deeperthought.cse.chalmers.se", 
                            model_name="gemma3:12b",
                            my_role="You are a C Programmer. You respond with the code in C to solve the task. No comments or explanations")
    
    # Get the response from the agent
    responseProgrammer = agentProgrammer.get_response(args.prompt)
    print("Programmer Response:", responseProgrammer[:100])
    
    responseDesigner = agentDesigner.get_response(f'Here is my program, how can I improve it {responseProgrammer}')
    print("\n\nDesigner Response:", responseDesigner[:100])

    for i in range(100000):
        responseProgrammer = agentProgrammer.get_response(responseDesigner)
        print("\n\n:::::::::::::::::::Programmer Response::::::::::::::::::")
        print(responseProgrammer[:100])
        
        responseDesigner = agentDesigner.get_response(responseProgrammer)
        print("\n\n:::::::::::::::::::Designer Response::::::::::::::::::")
        print(responseDesigner[:100])

        print(f'iteration {i} done')

        # once every 10 times save to excel
        if i % 10:
            agentProgrammer.save_to_excel("programmer_conversation_gemma3_gemma2.xlsx")

    
if __name__ == "__main__":
    main()
