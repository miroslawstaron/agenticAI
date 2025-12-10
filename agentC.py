"""C Code Agent with Compilation Support.

AgentAIC extends AgentAI with automatic C code compilation validation.
It extracts C code from markdown blocks, compiles with gcc, and automatically
attempts to fix compilation errors through iterative LLM prompts.
"""

import agent
import subprocess
import re
from typing import Optional
from litellm import completion
import json
import os
from agentCompiler import AgentCompiler
from agentStaticAnalyzer import AgentStaticAnalyzer
from logger import get_logger
import config


class AgentAIC(agent.AgentAI):
    """C code generation agent with compilation validation.
    
    Extends AgentAI with C-specific capabilities:
    - Automatic code extraction from markdown ```c...``` blocks
    - GCC compilation with error detection
    - Automated error fixing through iterative LLM prompts (max 3 trials)
    - Composition with AgentCompiler for specialized compilation handling
    
    Attributes:
        __response: Full model response including markdown
        __mdCode: Markdown code block (```c ... ```)
        __code: Extracted pure C code
        __compile_result: Compilation output (stderr/stdout)
    
    Pipelines:
        1. Main: User prompt → LLM generation → Code extraction → Compilation
        2. Error recovery: Compilation error → Fix prompt → Retry (max 3x)
    """

    def __init__(self, server_address: str, model_name: str, my_role: str, 
                 max_tokens: int = config.LLM_MAX_TOKENS, api_key: str = "") -> None:
        """Initialize C code agent with compilation support.
        
        Args:
            server_address: LLM API endpoint
            model_name: Model identifier
            my_role: System prompt (e.g., "You are a C programmer")
            max_tokens: Max tokens per response
            api_key: Optional API authentication
        """
        # Call parent __init__ to initialize base agent functionality including logging
        super().__init__(server_address, model_name, my_role, max_tokens, api_key)
        
        self.__response = ""                    # response from the model
        self.__mdCode = ""                      # markdown code block, which is part of the response
        self.__code = ""                        # just the code from the markdown code block   
        self.__compile_result = ""              # result of the compilation using gcc 
        
    def get_response(self, prompt: str) -> Optional[str]:
        """Generate C code and compile it with automatic error fixing.
        
        Full pipeline:
        1. Send prompt to LLM with temperature=0.3 (deterministic)
        2. Extract C code from ```c ... ``` markdown block
        3. Write code to ./temp/code_temp.c
        4. Compile with: gcc -w code_temp.c -o a.out -lm
        5. If compilation fails:
           - Parse stderr for "error" keyword
           - Generate fix prompt with error message
           - Retry (max config.COMPILER_MAX_TRIALS times)
        6. Return final response or None
        
        Args:
            prompt: User/designer prompt requesting C code
            
        Returns:
            Full response string with code and explanation, or None if failed
            
        Error Handling:
            - Compilation errors trigger automatic retry with fix prompts
            - Max 3 compilation attempts
            - Logs all attempts via logger
            
        Example:
            >>> agent = AgentAIC("localhost:11434", "ollama/qwen3:4b", "You are a C programmer")
            >>> response = agent.get_response("Write a program that calculates factorial")
            >>> # Returns response with working C code or None
        """
        # send a request to the ollama server
        
        # Log the action
        self.logger.log_agent_action(self.agent_id, 
                                     "Sending prompt to LLM with compilation", 
                                     f"Model - {self.model_name} , Prompt - {prompt.replace(chr(10), '$$$$')}")
        
        # add the user prompt to the messages list
        self.messages.append({"role": "user", "content": prompt})

        retries = config.LLM_RETRY_ATTEMPTS
        for attempt in range(retries):
            try:
                # Use LiteLLM completion API
                response = completion(
                    model=self.model_name,
                    messages=self.messages,
                    temperature=config.LLM_TEMPERATURE_FIXING,
                    max_tokens=config.LLM_MAX_TOKENS,
                    api_base=self.server_address if self.server_address else None,
                    timeout=config.LLM_TIMEOUT_SECONDS
                )

                # Extract the content from LiteLLM response
                response_raw = response.choices[0].message.content

                # this is the difference to the parent class
                # now we need to ask the compiler agent to compile the code
                # and return the result
                # we need to add the response to the messages list
                self.logger.log_agent_action(self.agent_id, 
                                             "Creating compiler agent for code validation", 
                                             f"Model - {self.model_name}, Server - {self.server_address}")
                agentComp = AgentCompiler(server_address=self.server_address, 
                                          model_name=self.model_name, 
                                          trials=3)


                #strCompilerResponse = agentComp.get_response(response_raw)
                strCodeResponse = agentComp.get_response(response_raw)

                # Log successful response
                self.logger.log_agent_action(self.agent_id, 
                                             "Received response", 
                                             f"Response - {response_raw.replace('\n', '$$$$')}")

                # add the response to the messages list
                self.messages.append({"role": "assistant", "content": strCodeResponse})
                
                # Log successful response
                self.logger.log_agent_action(self.agent_id, 
                                             "Received and compiled code response", 
                                             f"Response - {strCodeResponse.replace('\n', '$$$$')}")
                
                # contrary to the parent class, we need to return the code
                # and not the response
                return strCodeResponse
                    
            except Exception as e:
                error_msg = str(e)
                
                # Log the exception
                self.logger.log_exception(self.agent_id, e, "get_response (AgentAIC)")
                
                if 'timeout' in error_msg.lower():
                    print(f"Timeout occurred. Retrying {attempt + 1}/{retries}...")
                else:
                    print(f"Error: {error_msg}")
                    
                if attempt == retries - 1:
                    print("Max retries reached. Exiting.")
                    self.logger.log_agent_action(self.agent_id, 
                                                 "Max retries reached", 
                                                 "Returning None")
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
    