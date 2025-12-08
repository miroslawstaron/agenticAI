import agent
import subprocess
import re
from litellm import completion
import json
import os
from agentPyInterpreter import AgentPyInterpreter
from logger import get_logger

class AgentAIPy(agent.AgentAI):
    '''This class is an agent that uses the Ollama server to generate Python code.
    It is a subclass of the AgentAI class.
    It is used to generate Python code and execute it using Python interpreter.
    It uses the requests library to communicate with the server.
    It uses the subprocess library to execute the code using Python.
    It uses the re library to extract the code from the markdown code block.
    It uses the json library to parse the response from the server.
    It uses the tqdm library to show the progress of the iterations.
    
    This class has two pipelines when talking to the model: 
    1. The first one is the main conversation between the model and the user.
    2. The second one is the conversation between the model and the user that is aimed to solve execution errors.'''

    def __init__(self, server_address, model_name, my_role, max_tokens=16000, api_key=""):
        # Call parent __init__ to initialize base agent functionality including logging
        super().__init__(server_address, model_name, my_role, max_tokens, api_key)
        
        self.__response = ""                    # response from the model
        self.__mdCode = ""                      # markdown code block, which is part of the response
        self.__code = ""                        # just the code from the markdown code block   
        self.__execution_result = ""            # result of the execution using Python 

    def get_response(self, prompt):
        '''This method gets the response from the model.
        It sends the prompt to the model and returns the response.'''
        # send a request to the ollama server
        
        # Log the action
        self.logger.log_agent_action(self.agent_id, "Sending prompt to LLM with execution", f"Model: {self.model_name}")
        
        # add the user prompt to the messages list
        self.messages.append({"role": "user", "content": prompt})

        retries = 3
        for attempt in range(retries):
            try:
                # Use LiteLLM completion API
                response = completion(
                    model=self.model_name,
                    messages=self.messages,
                    temperature=0.3,
                    max_tokens=16000,
                    api_base=self.server_address if self.server_address else None,
                    timeout=300
                )

                # Extract the content from LiteLLM response
                response_raw = response.choices[0].message.content

                # this is the difference to the parent class
                # now we need to ask the interpreter agent to execute the code
                # and return the result
                # we need to add the response to the messages list
                self.logger.log_agent_action(self.agent_id, "Creating interpreter agent for code validation")
                agentInterp = AgentPyInterpreter(server_address=self.server_address, 
                                          model_name=self.model_name, 
                                          trials=3)


                strCodeResponse = agentInterp.get_response(response_raw)

                # add the response to the messages list
                self.messages.append({"role": "assistant", "content": strCodeResponse})
                
                # Log successful response
                self.logger.log_agent_action(self.agent_id, "Received and executed code response")
                
                # contrary to the parent class, we need to return the code
                # and not the response
                return strCodeResponse
                    
            except Exception as e:
                error_msg = str(e)
                
                # Log the exception
                self.logger.log_exception(self.agent_id, e, "get_response (AgentAIPy)")
                
                if 'timeout' in error_msg.lower():
                    print(f"Timeout occurred. Retrying {attempt + 1}/{retries}...")
                else:
                    print(f"Error: {error_msg}")
                    
                if attempt == retries - 1:
                    print("Max retries reached. Exiting.")
                    self.logger.log_agent_action(self.agent_id, "Max retries reached", "Returning None")
                    return None
        
        return None

    def __extract_python_code(self, markdown: str) -> str:
        '''This function extracts the Python code from a markdown string.'''
        try: 
            pattern = r"```python(.*?)```"
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
        
        # extract only the block that is between the ```python and ``` lines
        self.code = self.__extract_python_code(code)
        
        if code != "":
            # remove the first and the last line
            self.code = self.code.split('\n')
            #mdCode = mdCode[1:-1]
            self.code = '\n'.join(self.code)
        
        return self.code
