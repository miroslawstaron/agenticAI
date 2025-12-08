import json
from litellm import completion
import pandas as pd
import re
import os
import uuid
from logger import get_logger

class AgentAI:
    
    # attribute to store the list of conversations
    messages = [
            ]

    def __init__(self, 
                 server_address, 
                 model_name, 
                 my_role, 
                 max_tokens=16000,
                 api_key=""):
        self.server_address = server_address
        self.model_name = model_name
        self.max_tokens = max_tokens
        # Prefer explicit api_key; else fall back to env var OPENAI_API_KEY
        self.api_key = api_key
        
        # Generate unique agent ID
        self.agent_id = str(uuid.uuid4())
        
        # Get logger instance
        self.logger = get_logger()
        
        # Set API key in environment for LiteLLM if provided
        if self.api_key:
            os.environ['OPENAI_API_KEY'] = self.api_key
        
        # Configure base URL for LiteLLM if using custom server
        if server_address and 'localhost' not in server_address:
            os.environ['OPENAI_API_BASE'] = server_address
        
        self.messages = [
            {"role": "system",
             "content": my_role 
            }
        ]
        
        # Log agent initialization with system prompt
        self.logger.log_agent_init(self.agent_id, self.__class__.__name__, my_role) 

    def get_response(self, prompt):
        # send a request to the LLM via LiteLLM
        
        # Log the action
        self.logger.log_agent_action(self.agent_id, "Sending prompt to LLM", f"Model: {self.model_name}")
        
        # add the user prompt to the messages list
        self.messages.append({"role": "user", "content": prompt})

        retries = 3
        for attempt in range(retries):
            try:
                # Use LiteLLM completion API
                response = completion(
                    model=self.model_name,
                    messages=self.messages,
                    temperature=0.5,
                    max_tokens=self.max_tokens,
                    api_base=self.server_address if self.server_address else None,
                    timeout=300
                )

                # Extract the content from LiteLLM response
                response_raw = response.choices[0].message.content

                # add the response to the messages list
                self.messages.append({"role": "assistant", "content": response_raw})
                
                # Log successful response
                self.logger.log_agent_action(self.agent_id, "Received response from LLM")
                
                return response_raw
                
            except Exception as e:
                error_msg = str(e)
                
                # Log the exception
                self.logger.log_exception(self.agent_id, e, "get_response")
                
                if 'timeout' in error_msg.lower():
                    print(f"Timeout occurred. Retrying {attempt + 1}/{retries}...")
                else:
                    print(f"Error: {error_msg}")
                
                if attempt == retries - 1:
                    print("Max retries reached. Exiting.")
                    self.logger.log_agent_action(self.agent_id, "Max retries reached", "Returning None")
                    return None
                    
        return None
        

    def start(self):
        self.logger.log_agent_action(self.agent_id, "Agent started", f"Model: {self.model_name}, Server: {self.server_address}")
        print(f"Starting agent with model {self.model_name} at {self.server_address}")

    # this function saves the messages to a file
    def save_to_csv(self,filename):
        self.logger.log_agent_action(self.agent_id, "Saving messages to CSV", f"File: {filename}")
        # open the file in write mode
        with open(filename, 'w') as f:
            # write the header with $ as separator
            f.write('role$content\n')
            # write the messages with $ as separator
            for message in self.messages:
                f.write(f"{message['role']}${message['content']}\n")

    # this function saves the messages to an Excel file
    def save_to_excel(self, filename):
        self.logger.log_agent_action(self.agent_id, "Saving messages to Excel", f"File: {filename}")
        
        # convert the messages list to a DataFrame and rename columns if necessary
        df = pd.DataFrame(self.messages)
        # save the DataFrame to an Excel file without an index column
        df.to_excel(filename, index=False)

    # Markdown conversion function
    def basic_markdown_to_html(self, text):
        '''Convert basic Markdown to HTML.'''
        text = re.sub(r'```([a-z]*)\n(.*?)```', r'<pre><code class="\1">\2</code></pre>', text, flags=re.DOTALL)
        text = re.sub(r'`([^`]*)`', r'<code>\1</code>', text)
        text = re.sub(r'\*\*(.+?)\*\*', r'<strong>\1</strong>', text)
        text = re.sub(r'\*(.+?)\*', r'<em>\1</em>', text)
        text = text.replace('\n', '<br>')
        return text

    # Main conversion function
    def to_html(self, output_html, role1="Designer", role2="Programmer"):
        '''Convert a pandas DataFrame to an HTML table format.'''
        # Make a copy to avoid modifying the original dataframe
        df = pd.DataFrame(self.messages)

        # Update roles
        df['role'] = df['role'].replace({'user': role1, 'assistant': role2})

        # Remove the first row and keep up to 209 rows
        df = df.iloc[1:]

        # Separate Designer and Programmer contents
        designer_content = df[df['role'] == role1]['content'].reset_index(drop=True)
        programmer_content = df[df['role'] == role2]['content'].reset_index(drop=True)

        max_len = max(len(designer_content), len(programmer_content))
        designer_content = designer_content.reindex(range(max_len), fill_value='')
        programmer_content = programmer_content.reindex(range(max_len), fill_value='')

        # Convert Markdown to HTML
        designer_html = designer_content.apply(self.basic_markdown_to_html)
        programmer_html = programmer_content.apply(self.basic_markdown_to_html)

        # HTML content
        html_content = f"""
        <!DOCTYPE html>
        <html lang="en">
        <head>
            <meta charset="UTF-8">
            <title>Designer and Programmer Conversation</title>
            <style>
                body {{ font-family: Arial, sans-serif; margin: 0; padding: 0; }}
                table {{ width: 100%; border-collapse: collapse; table-layout: fixed; }}
                th, td {{ border: 1px solid #ddd; padding: 12px; vertical-align: top; width: 50%; word-wrap: break-word; }}
                th {{ background-color: #f4f4f4; }}
                .programmer {{ background-color: #f0f0f0; }}
                pre {{ background-color: #eaeaea; padding: 10px; overflow-x: auto; }}
                code {{ font-family: monospace; background-color: #ddd; padding: 2px 4px; }}
            </style>
        </head>
        <body>
            <table>
                <tr>
                    <th>Designer</th>
                    <th>Programmer</th>
                </tr>
        """

        # Populate HTML table
        for d_html, p_html in zip(designer_html, programmer_html):
            html_content += f"""
                <tr>
                    <td>{d_html}</td>
                    <td class="programmer">{p_html}</td>
                </tr>
            """

        html_content += """
            </table>
        </body>
        </html>
        """

        with open(output_html, 'w', encoding='utf-8') as file:
            file.write(html_content)