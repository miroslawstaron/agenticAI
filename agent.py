"""Base Agent class for LLM-powered conversations.

AgentAI manages conversations with Language Models using LiteLLM, maintaining
message history, handling retries, and supporting multiple export formats.
"""

import json
from typing import Optional, List, Dict, Any
from litellm import completion
import pandas as pd
import re
import os
from agent_id_manager import AgentIDManager
from logger import get_logger
import config


class AgentAI:
    """Base agent for managing LLM conversations.
    
    Attributes:
        server_address: URL to LLM API server (e.g., localhost:11434 for Ollama)
        model_name: Name of the model in format "provider/model" (e.g., "ollama/qwen3:4b")
        max_tokens: Maximum tokens per response
        api_key: Optional API key for authentication
        agent_id: Unique 2-digit identifier (00-99)
        logger: Singleton logger for tracking agent activities
        messages: Conversation history with role-based structure
    """
    
    # attribute to store the list of conversations
    messages: List[Dict[str, str]] = [
            ]

    def __init__(self, 
                 server_address: str, 
                 model_name: str, 
                 my_role: str, 
                 max_tokens: int = config.LLM_MAX_TOKENS,
                 api_key: str = "") -> None:
        """Initialize the base agent.
        
        Args:
            server_address: LLM API endpoint (e.g., 'http://localhost:11434')
            model_name: Model identifier in format 'provider/model' (e.g., 'ollama/qwen3:4b')
            my_role: System prompt defining the agent's role and behavior
            max_tokens: Maximum tokens per LLM response (default from config)
            api_key: Optional API key; falls back to OPENAI_API_KEY env var
            
        Side Effects:
            - Generates unique 2-digit agent ID (00-99)
            - Sets OPENAI_API_KEY and OPENAI_API_BASE environment variables
            - Initializes logger and logs agent initialization
            - Creates initial message with system role
        """
        self.server_address = server_address
        self.model_name = model_name
        self.max_tokens = max_tokens
        # Prefer explicit api_key; else fall back to env var OPENAI_API_KEY
        self.api_key = api_key
        
        # Generate unique agent ID (simple sequential 2-digit)
        self.agent_id = AgentIDManager.get_next_id()
        
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

    def get_response(self, prompt: str) -> Optional[str]:
        """Send a prompt to the LLM and get a response.
        
        Manages the full LLM interaction including message history, retries,
        and error handling. Uses LiteLLM for unified API abstraction.
        
        Args:
            prompt: The user/designer prompt to send to the LLM
            
        Returns:
            Full model response string (may contain markdown code blocks),
            or None if max retries exceeded
            
        Message Format:
            Appends {"role": "user", "content": prompt} before requesting,
            then appends {"role": "assistant", "content": response} after.
            
        Retry Logic:
            - Retries up to config.LLM_RETRY_ATTEMPTS times
            - Handles TimeoutError specially
            - Logs all exceptions via logger.log_exception()
            
        Example:
            >>> agent = AgentAI("http://localhost:11434", "ollama/qwen3:4b", "You are a C programmer")
            >>> response = agent.get_response("Write a hello world program in C")
            >>> # response contains full markdown with ```c ... ``` block
        """
        # send a request to the LLM via LiteLLM
        
        # Log the action
        self.logger.log_agent_action(self.agent_id, "Sending prompt to LLM", f"Model - {self.model_name}, Prompt - {prompt.replace(chr(10), '$$$$')}")
        
        # add the user prompt to the messages list
        self.messages.append({"role": "user", "content": prompt})

        retries = config.LLM_RETRY_ATTEMPTS
        for attempt in range(retries):
            try:
                # Use LiteLLM completion API
                response = completion(
                    model=self.model_name,
                    messages=self.messages,
                    temperature=config.LLM_TEMPERATURE_GENERATION,
                    max_tokens=self.max_tokens,
                    api_base=self.server_address if self.server_address else None,
                    timeout=config.LLM_TIMEOUT_SECONDS
                )

                # Extract the content from LiteLLM response
                response_raw = response.choices[0].message.content

                # add the response to the messages list
                self.messages.append({"role": "assistant", "content": response_raw})
                
                # Log successful response
                self.logger.log_agent_action(self.agent_id, "Received response from LLM", f"Response length: {len(response_raw)} chars")
                
                return response_raw
                
            except Exception as e:
                error_msg = str(e)
                error_type = type(e).__name__
                is_retryable = isinstance(e, (TimeoutError, ConnectionError))
                
                # Log the exception with context for AI understanding
                self.logger.log_exception(self.agent_id, e, "get_response")
                
                if 'timeout' in error_msg.lower():
                    print(f"Timeout occurred. Retrying {attempt + 1}/{retries}...")
                else:
                    print(f"Error ({error_type}): {error_msg}")
                
                if attempt == retries - 1:
                    print(f"Max retries ({retries}) reached. Exiting.")
                    self.logger.log_agent_action(self.agent_id, "Max retries reached", f"Error type: {error_type}")
                    return None
                    
        return None
        

    def start(self) -> None:
        """Start the agent and log initialization.
        
        Primarily for tracking and debugging agent lifecycle.
        """
        self.logger.log_agent_action(self.agent_id, "Agent started", f"Model - {self.model_name}, Server - {self.server_address}")
        print(f"Starting agent with model {self.model_name} at {self.server_address}")

    def save_to_csv(self, filename: str) -> None:
        """Save conversation history to CSV file.
        
        Args:
            filename: Output CSV file path
            
        Format:
            Pipe-delimited format with $ separator between fields
            Columns: role, content
            Roles: "system", "user" (designer), "assistant" (programmer)
            
        Example:
            role$content
            system$You are a C programmer
            user$Write a hello world
            assistant$#include <stdio.h>...
        """
        self.logger.log_agent_action(self.agent_id, "Saving messages to CSV", f"File - {filename}")
        # open the file in write mode
        with open(filename, 'w') as f:
            # write the header with $ as separator
            f.write('role$content\n')
            # write the messages with $ as separator
            for message in self.messages:
                f.write(f"{message['role']}${message['content']}\n")

    def save_to_excel(self, filename: str) -> None:
        """Save conversation history to Excel file.
        
        Args:
            filename: Output XLSX file path
            
        Format:
            Columns: role, content
            Rows: One message per row
            First row: System prompt with role="system"
            
        Returns:
            None (creates/overwrites file at filename)
        """
        self.logger.log_agent_action(self.agent_id, "Saving messages to Excel", f"File - {filename}")
        
        # convert the messages list to a DataFrame and rename columns if necessary
        df = pd.DataFrame(self.messages)
        # save the DataFrame to an Excel file without an index column
        df.to_excel(filename, index=False)

    def basic_markdown_to_html(self, text: str) -> str:
        """Convert basic Markdown to HTML.
        
        Supported Markdown:
            - Code blocks: ```language ... ``` → <pre><code class="language">...
            - Inline code: `text` → <code>text</code>
            - Bold: **text** → <strong>text</strong>
            - Italic: *text* → <em>text</em>
            - Line breaks: \\n → <br>
            
        Args:
            text: Markdown text
            
        Returns:
            HTML string
        """
        text = re.sub(r'```([a-z]*)\n(.*?)```', r'<pre><code class="\1">\2</code></pre>', text, flags=re.DOTALL)
        text = re.sub(r'`([^`]*)`', r'<code>\1</code>', text)
        text = re.sub(r'\*\*(.+?)\*\*', r'<strong>\1</strong>', text)
        text = re.sub(r'\*(.+?)\*', r'<em>\1</em>', text)
        text = text.replace('\n', '<br>')
        return text

    def to_html(self, output_html: str, role1: str = "Designer", role2: str = "Programmer") -> None:
        """Export conversation to interactive HTML table.
        
        Creates a side-by-side comparison of designer and programmer contributions
        with markdown-to-HTML conversion and syntax highlighting.
        
        Args:
            output_html: Output HTML file path
            role1: Display name for user/designer (default: "Designer")
            role2: Display name for assistant/programmer (default: "Programmer")
            
        Format:
            Two-column HTML table with:
            - Designer prompts (left column, white background)
            - Programmer responses (right column, gray background)
            - Code blocks with syntax highlighting
            - Markdown formatting preserved
            
        Side Effects:
            Creates/overwrites file at output_html
        """
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