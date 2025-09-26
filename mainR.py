# use the agent.py file to run the agent
import argparse
import re
from tqdm import tqdm  # Import tqdm for progress bar
from requirements.agent_reqs import AgentReqs
from requirements.agent_3gpp import Agent3GPP
from agent import AgentAI


def main():
    MAX_ITERATIONS = 5  # Set the maximum number of iterations


    # Parse command-line arguments
    parser = argparse.ArgumentParser(description="Run the AgentAI with a prompt.")
    parser.add_argument("--prompt", type=str, required=True, help="The prompt to send to the agent.")
    args = parser.parse_args()

    # Create instances of the Agent classes
    agent3GPP = Agent3GPP(server_address="http://lazythought.cse.chalmers.se", 
                              model_name="gpt-oss:20b",
                              my_role="You are a 3GPP expert. You respond with a list of relevant 3GPP sections.")
    
    agentReqs = AgentReqs(server_address="http://lazythought.cse.chalmers.se", 
                              model_name="gpt-oss:20b",
                              my_role="You are a requirements engineer. You respond with a list of requirements in bullet points. No comments or explanations")
    
    agentGenerator = AgentAI(server_address="http://lazythought.cse.chalmers.se", 
                            model_name="gpt-oss:20b",
                            my_role="You are a Requirements Engineer.You generate new requirements based on the set of given ones and the new text from the document.")
    
    # get the list of relevant 3GPP sections
    response3GPP = agent3GPP.get_sections(args.prompt)

    # Get the list of relevant requirements from the database
    responseReqs = agentReqs.get_requirements(args.prompt)
    
    responseReqsOriginal = responseReqs

    # now, generate the new requirements based on the original ones and the new text
    responseGenerator = agentGenerator.get_response(f'Here is a list of my requirements: #{responseReqs}#. Given my prompt "{args.prompt}" and the text of the standard #{response3GPP}#, which new requirement should I add?')

    for i in tqdm(range(MAX_ITERATIONS), desc="Processing iterations"):
        responseReqs = agentReqs.get_response(f'''This is the feedback I got from the requirements generator: {responseGenerator}. 
                                              How should I improve my requirements?''')
        #print("\n\n:::::::::::::::::::Programmer Response::::::::::::::::::")
        #print(responseProgrammer[:100])
        
        responseGenerator = agentGenerator.get_response(f'Here is a list of my requirements: {responseReqs}. Given these new requirements {responseGenerator}, how should I improve my requirements?')
        #print("\n\n:::::::::::::::::::Designer Response::::::::::::::::::")
        #print(responseDesigner[:100])

        agentGenerator.save_to_excel("generator_conversation_oss20b.xlsx")
        
        agentGenerator.to_html("generator_conversation_oss20b.html", role1="Miner", role2="Generator")

       

    
if __name__ == "__main__":
    main()
