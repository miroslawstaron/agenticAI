import agent
import subprocess
import re
from litellm import completion
import json
import os
from agent_id_manager import AgentIDManager
from logger import get_logger

class AgentCompiler(agent.AgentAI):
    '''This class uses the LLM model together with a gcc compiler to compile
        and to fix potential compilation errors.'''

    def __init__(self, server_address, model_name, trials):
        self.server_address = server_address        # address of the server
        self.model_name = model_name                # name of the model 
        self.__response = ""                    # response from the model
        self.__mdCode = ""                      # markdown code block, which is part of the response
        self.__code = ""                        # just the code from the markdown code block   
        self.__compile_result = ""              # result of the compilation using gcc 
        self.__trials = trials                   # number of trials to fix the compilation errors
        
        # Generate unique agent ID (simple sequential 2-digit)
        self.agent_id = AgentIDManager.get_next_id()
        
        # Get logger instance
        self.logger = get_logger()

        # initial compile messages queue
        self.__initial_compile_messages = [
            {"role": "system",
             "content": "You are a C Programmer. You solve problems with C programs, no comments or explanations. "
            }
        ]

        # the conversation between the model and the user
        # that is aimed to solve compilation errors
        self.__compile_messages = self.__initial_compile_messages
        
        # Log agent initialization
        self.logger.log_agent_init(self.agent_id, self.__class__.__name__, 
                                   "You are a C Programmer. You solve problems with C programs, no comments or explanations.",
                                   f'Model - {self.model_name}, Server - {self.server_address}')

    def get_response(self, code: str) -> str:
        '''This method compiles the code using gcc and tries to fix the compilation errors. 
        It returns the result of the compilation.'''

        self.logger.log_agent_action(self.agent_id, "Starting code compilation process", f"Initial code - {code.replace('\n', '$$$$')[:100]}")
        
        # check if the code is in the markdown code block
        # if it is, we extract the code from the markdown code block
        # if it is not, we just use the code as it is
        if code.__contains__("```c"):
            self.__mdCode = code
            self.__code = self.__get_code(code)
        else:
            self.__code = code

        # compile the code using gcc
        self.__compile_result = self.__compile_code(self.__code)

        #print(f'Compiling the code: {self.__code}')

        # if the compilation was successful, we return the result
        if self.__compile_result == "Compilation successful":
            self.logger.log_agent_action(self.agent_id, "Compilation successful on first attempt")
            return self.__code
        else:
            # if the compilation was not successful, we try to fix it
            self.logger.log_agent_action(self.agent_id, "Compilation failed, attempting to fix", 
                                        f"Error: {self.__compile_result[:100]}")
            attempts = 0
            while attempts < self.__trials and self.__compile_result != "Compilation successful":
                print(f'Attempt {attempts + 1} to fix the compilation error...')
                self.logger.log_agent_action(self.agent_id, f"Fixing attempt {attempts + 1}/{self.__trials}", 
                                           f"Current code: {self.__code[:100]}, Current error: {self.__compile_result[:100]}")
                
                code = self.__solve_problem()
                if code.__contains__("```c"):
                    self.__mdCode = code
                    self.__code = self.__get_code(code)
                else:
                    self.__code = code

                self.__compile_result = self.__compile_code(self.__code)

                attempts += 1
            
            if self.__compile_result == "Compilation successful":
                self.logger.log_agent_action(self.agent_id, "Compilation successful after fixing", 
                                           f"Fixed in {attempts} attempt(s)")
            else:
                self.logger.log_agent_action(self.agent_id, "Compilation failed after all attempts", 
                                           f"Final error: {self.__compile_result[:100]}")
            
            return self.__code

    def __solve_problem(self) -> str:
        '''This method solves the compilation problems using the model.
        It sends the prompt to the model and returns the response.'''

        # get the response from the model
        strPrompt = f'For this program {self.__code}, I got the following compilation error: {self.__compile_result.replace('\n', '$$$$')}. Please fix the code and return the fixed code in a markdown code block.'
        
        # please note that we use the __compile_messages list to store the conversation
        # between the model and the user
        self.__compile_messages.append({"role": "user", "content": strPrompt})
        
        # get the response from the model
        strResult = self.__get_response_compilation(strPrompt)
        return strResult

    def __get_response_compilation(self, prompt: str) -> str:
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
                    messages=self.__compile_messages,
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
                context = f"__get_response_compilation (Attempt {attempt + 1} of {retries})"
                self.logger.log_exception(self.agent_id, e, context)
                
                if 'timeout' in error_msg.lower():
                    print(f"Timeout occurred. Retrying {attempt + 1}/{retries}...")
                else:
                    print(f"Error: {error_msg}")
                    
                if attempt == retries - 1:
                    print("Max retries reached. Exiting.")
                    self.logger.log_agent_action(self.agent_id, "Max retries reached in compilation", "Returning None")
                    return None
        
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
    
    # compile the code using gcc
    def __compile_code(self, code: str) -> str:
        '''This method compiles the code using gcc.
        It returns the result of the compilation.'''

        if self.__code != "":
            with open(f'./temp/code_temp.c', 'w+') as f:
                f.write(self.__code)
            # compile the code using gcc
            result = subprocess.run(['gcc', '-w', f'./temp/code_temp.c', '-o', './temp/a.out', '-lm'], stdout=subprocess.PIPE, stderr=subprocess.PIPE)

            # print the output of the compilation
            # print(result.stdout.decode())
            # print(result.stderr.decode())

            # check if the output of the compilation contains the word "error"
            if b'error' in result.stderr:
                self.__compile_result = f"Compilation error: {result.stderr.decode()}"
            else:
                self.__compile_result = "Compilation successful"
        else:
            self.__compile_result = "No code found"   

        return self.__compile_result