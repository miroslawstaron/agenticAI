import agent
import subprocess
import re
import requests
import json
import os
from agentCompiler import AgentCompiler
from agentStaticAnalyzer import AgentStaticAnalyzer

class AgentAIC(agent.AgentAI):
    '''This class is an agent that uses the Ollama server to generate C code.
    It is a subclass of the AgentAI class.
    It is used to generate C code and compile it using gcc.
    It uses the requests library to communicate with the server.
    It uses the subprocess library to compile the code using gcc.
    It uses the re library to extract the code from the markdown code block.
    It uses the json library to parse the response from the server.
    It uses the tqdm library to show the progress of the iterations.
    
    This class has two pipelines when talking to the model: 
    1. The first one is the main conversation between the model and the user.
    2. The second one is the conversation between the model and the user that is aimed to solve compilation errors.'''

    def __init__(self, server_address, model_name, my_role, max_tokens=16000, api_key=""):
        self.server_address = server_address        # address of the server
        self.model_name = model_name                # name of the model 
        self.url = f'{self.server_address}'    # chat API endpoint
        self.__response = ""                    # response from the model
        self.__mdCode = ""                      # markdown code block, which is part of the response
        self.__code = ""                        # just the code from the markdown code block   
        self.__compile_result = ""              # result of the compilation using gcc
        self.max_tokens = max_tokens              # maximum tokens for the response
        self.api_key = api_key                    # API key for authentication

        # the main conversation between the model
        self.messages = [                   
            {"role": "system",
             "content": my_role 
            }
        ] 

    def get_response(self, prompt):
        '''This method gets the response from the model.
        It sends the prompt to the model and returns the response.'''
        # send a request to the ollama server
        
        # add the user prompt to the messages list
        self.messages.append({"role": "user", "content": prompt})

        data = {
            "model": self.model_name,
            "messages": self.messages,
            "stream": False,
            "temperature": 0.3,             # adjust this parameter to control the randomness of the output
            "max_tokens": 16000,             # adjust this parameter to control the length of the output
        }

        headers = {'Content-Type': 'application/json'}
        
        if self.api_key:
            headers['Authorization'] = f'Bearer {self.api_key}'

        retries = 3
        for attempt in range(retries):
            try:
                response = requests.post(self.url,
                                        headers=headers,
                                        json=data,
                                        timeout=300)

                if response.status_code == 200:
                    # get the response from the server
                    response_dict = json.loads(response.text)

                    # since the response contains a lot of other things, we need to extract the content
                    response_raw = response_dict['choices'][0]['message']['content']

                    # this is the difference to the parent class
                    # now we need to ask the compiler agent to compile the code
                    # and return the result
                    # we need to add the response to the messages list
                    agentComp = AgentCompiler(server_address=self.server_address, 
                                              model_name=self.model_name, 
                                              trials=3)


                    #strCompilerResponse = agentComp.get_response(response_raw)
                    strCodeResponse = agentComp.get_response(response_raw)

                    # add the response to the messages list
                    self.messages.append({"role": "assistant", "content": strCodeResponse})
                    
                    # contrary to the parent class, we need to return the code
                    # and not the response
                    return strCodeResponse
                else:
                    # on error, we print the error message
                    print(f"Error: {response.status_code} - {response.text}")
                    return None
            except requests.exceptions.Timeout:
                print(f"Timeout occurred. Retrying {attempt + 1}/{retries}...")
                if attempt == retries - 1:
                    print("Max retries reached. Exiting.")
                    return None

    def __extract_c_code(self, markdown: str) -> str:
        '''This function extracts the C code from a markdown string.'''
        try: 
            pattern = r"```c(.*?)```"
            match = re.search(pattern, markdown, re.DOTALL)
            if match:
                return match.group(1).strip()
        except:
            pass
        return ""
    
    def __get_code(self, code: str) -> str:
        '''This method gets the program code generated by the prompt. 
        The generation often results in a markdown code block. 
        This method extracts the code from the markdown block and returns it as a string.
        Line by line, with line breaks.'''
        
        # extract only the block that is between the ```c and ``` lines
        self.code = self.__extract_c_code(code)
        
        if code != "":
            # remove the first and the last line
            self.code = self.code.split('\n')
            #mdCode = mdCode[1:-1]
            self.code = '\n'.join(self.code)
        
        return self.code
    