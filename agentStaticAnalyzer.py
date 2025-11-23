import agent
import subprocess
import re
import json
import pandas as pd
import os
from litellm import completion
from agentCompiler import AgentCompiler


class AgentStaticAnalyzer(agent.AgentAI):
    '''This class uses the LLM model together with a gcc compiler to compile
        and to fix potential compilation errors.'''

    def __init__(self, server_address, model_name, trials):
        self.server_address = server_address        # address of the server
        self.model_name = model_name                # name of the model 
        self.__response = ""                    # response from the model
        self.__mdCode = ""                      # markdown code block, which is part of the response
        self.__code = ""                        # just the code from the markdown code block   
        self.__analyzer_result = ""              # result of the compilation using gcc 
        self.__trials = trials
        self.logs = []                   # number of trials to fix the compilation errors
        self.api_key = os.getenv('OPENAI_API_KEY', '')
        
        # Set litellm configuration for custom base URLs
        if server_address:
            os.environ["OPENAI_API_BASE"] = server_address
        if self.api_key:
            os.environ["OPENAI_API_KEY"] = self.api_key
        

        # initial compile messages queue
        self.__initial_analyzer_messages = [
            {"role": "system",
             "content": "You are a C Programmer. You solve problems with C programs, no comments or explanations. "
            }
        ]

        # the conversation between the model and the user
        # that is aimed to solve compilation errors
        self.__analyzer_messages = self.__initial_analyzer_messages

    def get_response(self, code: str) -> str:
        '''This method analyzes the code using CPP and tries to fix the errors. 
        It returns the result of the compilation.'''
        
        # check if the code is in the markdown code block
        # if it is, we extract the code from the markdown code block
        # if it is not, we just use the code as it is
        if code.__contains__("```c"):
            self.__mdCode = code
            self.__code = self.__get_code(code)
        else:
            self.__code = code

        # analyze the code using static analyzer
        self.__analyzer_result = self.__analyze_code(code)

        # print(f'Analyzing the code: {self.__code}')

        # if the compilation was successful, we return the result
        if self.__analyzer_result == "Static Analysis successful":
            return self.__code
        else:
            # if the compilation was not successful, we try to fix it
            attempts = 0
            while attempts < self.__trials and self.__analyzer_result != "Static Analysis successful":
                self.__solve_problem()
                attempts = attempts + 1
            return self.__analyzer_result

    def __solve_problem(self) -> str:
        '''This method solves the compilation problems using the model.
        It sends the prompt to the model and returns the response.'''

        # get the response from the model
        strPrompt = f'For this program {self.__code}, I got the following compilation error: {self.__analyzer_result}. Please fix the code and return the fixed code in a markdown code block.'
        
        # please note that we use the __compile_messages list to store the conversation
        # between the model and the user
        self.__analyzer_messages.append({"role": "user", "content": strPrompt})
        
        # get the response from the model
        strResult = self.__get_response_analyzer(strPrompt)
        return strResult
    
    def __get_response_analyzer(self, prompt: str) -> str:
        '''This method gets the response from the model. 
        It sends the prompt to the model and returns the response.'''
        
        # we use three retries just in case the server is busy
        # or there is a timeout
        retries = 3     

        for attempt in range(retries):
            try:
                # Use litellm's completion function
                response = completion(
                    model=self.model_name,
                    messages=self.__analyzer_messages,
                    temperature=0.0,
                    api_base=self.server_address if self.server_address else None,
                    api_key=self.api_key if self.api_key else None,
                    timeout=300
                )

                # Extract the content from the response
                response_raw = response.choices[0].message.content
                return response_raw
                
            except Exception as e:
                print(f"Error occurred: {str(e)}. Retrying {attempt + 1}/{retries}...")
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
    
    # Run Static Analyzer
    def __analyze_code(self,code: str) -> str:
        #with open("debug_log.txt", "a") as f:
                #f.write("Test")
        '''Run cppcheck static analysis on the code.'''
        agentComp = AgentCompiler(server_address=self.server_address, 
                                              model_name=self.model_name, 
                                              trials=3)
        
        compile_result = agentComp.get_response(code)
        #if compile_result == "Compilation successful":
        if self.__code != "": #Just for the sake of testing.. The above if condition should be used in real
            with open(f'./temp/code_temp.c', 'w+') as f:
                f.write(self.__code)

             # analyze the code using cppcheck
            result = subprocess.run(
            ['cppcheck', '--enable=all', '--std=c11', '--quiet', '--suppress=missingIncludeSystem', f'./temp/code_temp.c'], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            analysis_output = result.stderr.decode()
            with open("debug_log.txt", "a") as f:
                f.write(f"Analyzer result: {analysis_output}\n")
            
           
            meaningful_issues = [
            line for line in analysis_output.splitlines()
            if line.strip() != "" and not line.startswith("nofile:") 
        ]
            if meaningful_issues:
                self.__analyzer_result = f"Static Analyzer Issue: {result.stderr.decode()}"
                msg = "Static Analyzer Issue"
                with open("SA1.txt", "a") as f:
                    f.write(f"Analyzer result: {self.__analyzer_result}\n") 
                

            else:
                self.__analyzer_result = "Static Analysis successful"
                msg = "Static Analysis successful"
                with open("SA2.txt", "a") as f:
                    f.write(f"Analyzer result: {self.__analyzer_result}\n")        
        self.logs.append({
           "code": self.__code,
           "Issue": self.__analyzer_result,
           "result": msg
})
        return self.__analyzer_result

    #def save_to_excel(self, filename):
        #text = str(self.logs)
        #with open("SA3.txt", "a") as f:
            #f.write(text)
        #df = pd.DataFrame(self.logs)
        #df = pd.DataFrame(self.logs)
        #df.to_excel(filename, index=False)

    def save_to_excel(self, filename):
        text = str(self.logs)
        with open("SA3.txt", "a") as f:
            f.write(text)
    

        self.logs = list(self.logs)
        # print(" LOGS:", self.logs)

        if not self.logs:
             print("No logs to save.")
             return

    # Check that each item is a dict
        if not all(isinstance(entry, dict) for entry in self.logs):
             print("ERROR: self.logs is not a list of dictionaries.")
             return
        new_df = pd.DataFrame(self.logs)
        if os.path.exists(filename):
        # Read existing file
            existing_df = pd.read_excel(filename)
        # Concatenate and remove duplicates (optional)
            combined_df = pd.concat([existing_df, new_df], ignore_index=True)
        else:
            combined_df = new_df

    # Write back the full combined DataFrame
        combined_df.to_excel(filename, index=False)
        print(f" Logs saved to {filename}")
        #df = pd.DataFrame(self.logs)
        #df.to_excel(filename, index=False)
       # print(f" Saved to {filename}")