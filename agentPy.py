"""Python Code Agent with Execution Support.

AgentAIPy extends AgentAI with automatic Python code execution validation.
It extracts Python code from markdown blocks, executes with subprocess,
and automatically attempts to fix runtime errors through iterative LLM prompts.
"""

import agent
import subprocess
import re
from typing import Optional
from litellm import completion
import json
import os
from agentPyInterpreter import AgentPyInterpreter
from logger import get_logger
import config


class AgentAIPy(agent.AgentAI):
    """Python code generation agent with execution validation.
    
    Extends AgentAI with Python-specific capabilities:
    - Automatic code extraction from markdown ```python...``` blocks
    - Python interpreter execution with error detection
    - Automated error fixing through iterative LLM prompts (max 3 trials)
    - Composition with AgentPyInterpreter for specialized execution handling
    
    Attributes:
        __response: Full model response including markdown
        __mdCode: Markdown code block (```python ... ```)
        __code: Extracted pure Python code
        __execution_result: Execution output (stderr/stdout)
    """

    def __init__(self, server_address: str, model_name: str, my_role: str, 
                 max_tokens: int = config.LLM_MAX_TOKENS, api_key: str = "") -> None:
        """Initialize Python code agent with execution support.
        
        Args:
            server_address: LLM API endpoint
            model_name: Model identifier
            my_role: System prompt (e.g., "You are a Python programmer")
            max_tokens: Max tokens per response
            api_key: Optional API authentication
        """
        # Call parent __init__ to initialize base agent functionality including logging
        super().__init__(server_address, model_name, my_role, max_tokens, api_key)
        
        self.__response = ""                    # response from the model
        self.__mdCode = ""                      # markdown code block, which is part of the response
        self.__code = ""                        # just the code from the markdown code block   
        self.__execution_result = ""            # result of the execution using Python 

    def get_response(self, prompt: str) -> Optional[str]:
        """Generate Python code and execute it with automatic error fixing.
        
        Full pipeline:
        1. Send prompt to LLM with temperature=0.3 (deterministic)
        2. Extract Python code from ```python ... ``` markdown block
        3. Execute code with: python3 <script>
        4. If execution fails:
           - Capture stderr for error message
           - Generate fix prompt with error message
           - Retry (max config.LLM_RETRY_ATTEMPTS times)
        5. Return final response or None
        
        Args:
            prompt: User/designer prompt requesting Python code
            
        Returns:
            Full response string with code and explanation, or None if failed
            
        Error Handling:
            - Runtime errors trigger automatic retry with fix prompts
            - Max 3 execution attempts
            - Logs all attempts via logger
        """
        # send a request to the ollama server
        
        # Log the action
        self.logger.log_agent_action(self.agent_id, "Sending prompt to LLM with execution", f"Model - {self.model_name}")
        
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
                    max_tokens=self.max_tokens,
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
                self.logger.log_agent_action(self.agent_id, f"Received and executed code response - {strCodeResponse.replace('\n', '$$$$')}")
                
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
        extracted_code = self.__extract_python_code(code)
        
        if code != "":
            # remove the first and the last line
            extracted_code = extracted_code.split('\n')
            #mdCode = mdCode[1:-1]
            extracted_code = '\n'.join(extracted_code)
        
        return extracted_code
