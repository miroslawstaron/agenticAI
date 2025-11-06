import agent
import subprocess
import re
import requests
import json

class AgentH(agent.AgentAI):
    '''This class extends the AgentAI class, but mainly for an interface. 
    
    In fact, it is a class that encapsulates the interaction with a human. 
    It is supposed to bring the human into the loop. '''

    def __init__(self, server_address=None, model_name=None, my_role=None):
        self.server_address = server_address        # address of the server
        self.model_name = model_name                # name of the model 
        self.url = f'{self.server_address}'    # chat API endpoint
        self.__response = ""                    # response from the model
        self.__mdCode = ""                      # markdown code block, which is part of the response
        self.__code = ""                        # just the code from the markdown code block   
        self.__compile_result = ""              # result of the compilation using gcc
        
        # the main conversation between the agent and the human. 
        # we do not use it at the moment, but it could be useful in the future
        # TODO: implement the conversation log
        self.messages = [                   
            {"role": "system",
             "content": my_role 
            }
        ] 

    def get_response(self, prompt):
        '''This method gets the response from the human being.
        It saves the prompt to a file.
        Then it prints the prompt for the human to see.
        Then it waits for the human to write the response.
        It saves the response and returns it.'''
        
        # add the user prompt to the messages list
        self.messages.append({"role": "user", "content": prompt})

        # save the prompt to a file
        with open("human_prompt.txt", "w") as f:
            f.write(prompt)

        print("\n\n==================== HUMAN IN THE LOOP ====================")
        print(prompt)
        print("Please read the text above and write your response.")
        print("Then press Enter to continue...")
        self.__response = input("Response: ")  # wait for the human to press Enter

        print("\n\n==================== HUMAN RESPONSE send forward ====================")
        
        # save the response to the conversation log
        self.messages.append({"role": "assistant", "content": self.__response})

        return self.__response
    