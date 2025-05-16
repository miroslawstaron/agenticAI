import agent
import subprocess
import re
import requests
import json

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

    def __init__(self, server_address, model_name, my_role):
        self.server_address = server_address        # address of the server
        self.model_name = model_name                # name of the model 
        self.url = f'{self.server_address}/api/chat'    # chat API endpoint
        self.__response = ""                    # response from the model
        self.__mdCode = ""                      # markdown code block, which is part of the response
        self.__code = ""                        # just the code from the markdown code block   
        self.__compile_result = ""              # result of the compilation using gcc
        
        # the main conversation between the model
        self.messages = [                   
            {"role": "system",
             "content": my_role 
            }
        ] 

        # initial compile messages queue
        self.__initial_compile_messages = [
            {"role": "system",
             "content": "You are a C Programmer. You solve problems with C programs, no comments or explanations. "
            }
        ]

        # the conversation between the model and the user
        # that is aimed to solve compilation errors
        self.__compile_messages = self.__initial_compile_messages

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
            "max_tokens": 2096,             # adjust this parameter to control the length of the output
        }

        headers = {'Content-Type': 'application/json'}

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
                    response_raw = response_dict['message']['content']

                    # this is the difference to the parent class
                    # we do NOT add the response to the messages list
                    return response_raw
                else:
                    # on error, we print the error message
                    print(f"Error: {response.status_code} - {response.text}")
                    return None
            except requests.exceptions.Timeout:
                print(f"Timeout occurred. Retrying {attempt + 1}/{retries}...")
                if attempt == retries - 1:
                    print("Max retries reached. Exiting.")
                    return None

    def __get_response_compilation(self, prompt: str) -> str:
        '''This method gets the response from the model. 
        It sends the prompt to the model and returns the response.'''
        
        data = {
            "model": self.model_name,
            "messages": self.__compile_messages,
            "stream": False,
            "temperature": 0.0,
        }
        headers = {'Content-Type': 'application/json'}

        # we use three retries just in case the server is busy
        # or there is a timeout
        retries = 3     


        for attempt in range(retries):
            try:
                # communicate with the server
                response = requests.post(self.url,
                                        headers=headers,
                                        json=data,
                                        timeout=300)

                if response.status_code == 200:
                    # get the response from the server
                    response_dict = json.loads(response.text)

                    # since the response contains a lot of other things, we need to extract the content
                    response_raw = response_dict['message']['content']

                    return response_raw
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

    def __solve_problem(self) -> str:
        '''This method solves the compilation problems using the model.
        It sends the prompt to the model and returns the response.'''     

        strPrompt = f'For this program {self.__code}, I got the following compilation error: {self.__compile_result}. Please fix the code and return the fixed code in a markdown code block.'
        
        # please note that we use the __compile_messages list to store the conversation
        # between the model and the user
        self.__compile_messages.append({"role": "user", "content": strPrompt})
        
        # get the response from the model
        strResult = self.__get_response_compilation(strPrompt)
        return strResult
    
    def start(self, tries: int, prompt: str) -> str:
        '''This method starts the agent. 
        It talks to the model and tries to fix problems if there are any.
        It sends the prompt to the model and returns the response.'''
        
        attempt = 0
        __strResult = ""
        
        # get the response from the server
        self.__response = self.get_response(prompt)

        self.__mdCode = self.__get_code(self.__response)
        
        self.__code = self.__mdCode
        
        # compile the code
        self.compile_result = self.__compile_code(self.__code)
        
        __strResult = self.__code
        
        while attempt < tries and self.__compile_result != "Compilation successful":
            # solve the problem
            __strResult = self.__solve_problem()

            # compile the result
            self.__code = self.__get_code(__strResult)
            
            # checking the compilation result of the code
            self.__compile_result = self.__compile_code(self.__code)

            # if the compilation was successful, we break the loop
            # if the compilation was not successful, we try again
            if self.__compile_result == "Compilation successful":
                break
            
            attempt += 1

        # when we finish the loop,
        # we check if the compilation was successful
        # if no, then we return the code and the error message
        # if yes, then we return the code only
        if attempt == tries and self.__compile_result != "Compilation successful":
            strResult = f'Compilation failed after {attempt} attempts. Code: {self.__code}, the last error was: {self.__compile_result}'
        else:
            strResult = __strResult

        # add this to the messages in the main conversation
        self.messages.append({"role": "assistant", "content": strResult})

        # and clean up the compile messages
        # it is important because the next time we need to solve a problem
        # it is a different problem and the situation must start from scratch
        self.__compile_messages = self.__initial_compile_messages

        # return the result
        return strResult