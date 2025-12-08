import agent
import subprocess
import re
from litellm import completion
import json
import os
import uuid
from logger import get_logger

class AgentPyInterpreter(agent.AgentAI):
    '''This class uses the LLM model together with a Python interpreter to execute
        and to fix potential runtime errors.'''

    def __init__(self, server_address, model_name, trials):
        self.server_address = server_address        # address of the server
        self.model_name = model_name                # name of the model 
        self.__response = ""                    # response from the model
        self.__mdCode = ""                      # markdown code block, which is part of the response
        self.__code = ""                        # just the code from the markdown code block   
        self.__execution_result = ""            # result of the execution using Python 
        self.__trials = trials                   # number of trials to fix the execution errors

        # Generate unique agent ID
        self.agent_id = str(uuid.uuid4())
        
        # Get logger instance
        self.logger = get_logger()

        # initial execution messages queue
        self.__initial_execution_messages = [
            {"role": "system",
             "content": "You are a Python Programmer. You solve problems with Python programs, no comments or explanations. "
            }
        ]

        # the conversation between the model and the user
        # that is aimed to solve execution errors
        self.__execution_messages = self.__initial_execution_messages
        
        # Log agent initialization
        self.logger.log_agent_init(self.agent_id, self.__class__.__name__, 
                                   "You are a Python Programmer. You solve problems with Python programs, no comments or explanations.")

    def get_response(self, code: str) -> str:
        '''This method executes the code using Python and tries to fix the execution errors. 
        It returns the result of the execution.'''

        self.logger.log_agent_action(self.agent_id, "Starting code execution process")
        
        # check if the code is in the markdown code block
        # if it is, we extract the code from the markdown code block
        # if it is not, we just use the code as it is
        if code.__contains__("```python"):
            self.__mdCode = code
            self.__code = self.__get_code(code)
        else:
            self.__code = code

        # execute the code using Python
        self.__execution_result = self.__execute_code(self.__code)

        # if the execution was successful, we return the result
        if self.__execution_result == "Execution successful":
            self.logger.log_agent_action(self.agent_id, "Execution successful on first attempt")
            return self.__code
        else:
            # if the execution was not successful, we try to fix it
            self.logger.log_agent_action(self.agent_id, "Execution failed, attempting to fix", 
                                        f"Error: {self.__execution_result[:100]}")
            attempts = 0
            while attempts < self.__trials and self.__execution_result != "Execution successful":
                print(f'Attempt {attempts + 1} to fix the execution error...')
                self.logger.log_agent_action(self.agent_id, f"Fixing attempt {attempts + 1}/{self.__trials}")
                
                code = self.__solve_problem()
                if code.__contains__("```python"):
                    self.__mdCode = code
                    self.__code = self.__get_code(code)
                else:
                    self.__code = code

                self.__execution_result = self.__execute_code(self.__code)

                attempts += 1
            
            if self.__execution_result == "Execution successful":
                self.logger.log_agent_action(self.agent_id, "Execution successful after fixing", 
                                           f"Fixed in {attempts} attempt(s)")
            else:
                self.logger.log_agent_action(self.agent_id, "Execution failed after all attempts", 
                                           f"Final error: {self.__execution_result[:100]}")
            
            return self.__code

    def __solve_problem(self) -> str:
        '''This method solves the execution problems using the model.
        It sends the prompt to the model and returns the response.'''

        # get the response from the model
        strPrompt = f'For this program {self.__code}, I got the following execution error: {self.__execution_result}. Please fix the code and return the fixed code in a markdown code block.'
        
        # please note that we use the __execution_messages list to store the conversation
        # between the model and the user
        self.__execution_messages.append({"role": "user", "content": strPrompt})
        
        # get the response from the model
        strResult = self.__get_response_execution(strPrompt)
        # If we get None, return the original code to avoid AttributeError
        return strResult if strResult is not None else self.__code

    def __get_response_execution(self, prompt: str) -> str:
        '''This method gets the response from the model. 
        It sends the prompt to the model and returns the response.'''
        
        # we use three retries just in case the server is busy
        # or there is a timeout
        retries = 3     

        for attempt in range(retries):
            try:
                # Use LiteLLM completion API
                response = completion(
                    model=self.model_name,
                    messages=self.__execution_messages,
                    temperature=0.0,
                    api_base=self.server_address if self.server_address else None,
                    timeout=300
                )

                # Extract the content from LiteLLM response
                response_raw = response.choices[0].message.content
                return response_raw
                    
            except Exception as e:
                error_msg = str(e)
                
                # Log the exception
                self.logger.log_exception(self.agent_id, e, "__get_response_execution")
                
                if 'timeout' in error_msg.lower():
                    print(f"Timeout occurred. Retrying {attempt + 1}/{retries}...")
                else:
                    print(f"Error: {error_msg}")
                    
                if attempt == retries - 1:
                    print("Max retries reached. Exiting.")
                    self.logger.log_agent_action(self.agent_id, "Max retries reached in execution", "Returning None")
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
    
    # execute the code using Python
    def __execute_code(self, code: str) -> str:
        '''This method executes the code using Python.
        It returns the result of the execution.'''

        if self.__code != "":
            os.makedirs('./temp', exist_ok=True)
            with open(f'./temp/code_temp.py', 'w+') as f:
                f.write(self.__code)
            # execute the code using Python
            result = subprocess.run(['python3', f'./temp/code_temp.py'], 
                                  stdout=subprocess.PIPE, 
                                  stderr=subprocess.PIPE,
                                  timeout=5)  # 5 second timeout for safety

            # check if the output of the execution contains any errors
            if result.returncode != 0:
                self.__execution_result = f"Execution error: {result.stderr.decode()}"
            else:
                self.__execution_result = "Execution successful"
        else:
            self.__execution_result = "No code found"   

        return self.__execution_result
