# use the agent.py file to run the agent
import argparse
from agentvllm import vllmAgentAI

def main():
    # Parse command-line arguments
    parser = argparse.ArgumentParser(description="Run the AgentAI with a prompt.")
    parser.add_argument("--prompt", type=str, required=True, help="The prompt to send to the agent.")
    args = parser.parse_args()

    # Create an instance of the Agent class
    agentProgrammer = vllmAgentAI(model_name="gpt-oss:20b",
                              my_role="You are a C programmer. You respond with the code in C to solve the task. No comments or explanations")
    agentDesigner = vllmAgentAI(model_name="gpt-oss:20b",
                            my_role="You are a C designer. You will be given a task and you will respond with design suggestions to solve or the task.")
    
    # Get the response from the agent
    responseProgrammer = agentProgrammer.get_response(args.prompt)
    print("Programmer Response:", responseProgrammer)
    
    responseDesigner = agentDesigner.get_response(f'Here is my program, how can I improve it {responseProgrammer}')
    print("\n\nDesigner Response:", responseDesigner)

    for i in range(5):
        responseProgrammer = agentProgrammer.get_response(responseDesigner)
        print("\n\n:::::::::::::::::::Programmer Response::::::::::::::::::")
        print(responseProgrammer)
       
        responseDesigner = agentDesigner.get_response(responseProgrammer)
        print("\n\n:::::::::::::::::::Designer Response::::::::::::::::::")
        print(responseDesigner)
    
        # once every 10 times save to excel
        if i % 10:
            agentProgrammer.save_to_excel("programmer_conversation_llama31.xlsx")
    
if __name__ == "__main__":
    main()
