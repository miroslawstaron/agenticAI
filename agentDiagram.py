import agent
import re
from litellm import completion
import json
import os
import subprocess
import tempfile


class AgentDiagram(agent.AgentAI):
    '''This class is an agent that generates Mermaid diagrams from source code.
    It takes source code as input and generates various types of Mermaid diagrams.
    Supported diagram types: class, flowchart, sequence, er (entity-relationship).
    '''

    def __init__(self, server_address, model_name, diagram_type="class", max_tokens=16000, api_key=""):
        """Initialize the diagram agent.
        
        Args:
            server_address: The address of the LLM server
            model_name: The name of the model to use
            diagram_type: Type of diagram to generate (class, flowchart, sequence, er)
            max_tokens: Maximum tokens for the response
            api_key: API key for authentication
        """
        # Define the role based on diagram type
        role_descriptions = {
            "class": "You are an expert at analyzing source code and creating Mermaid class diagrams. Generate only the Mermaid diagram syntax in a ```mermaid code block, no explanations.",
            "flowchart": "You are an expert at analyzing source code and creating Mermaid flowcharts. Generate only the Mermaid diagram syntax in a ```mermaid code block, no explanations.",
            "sequence": "You are an expert at analyzing source code and creating Mermaid sequence diagrams. Generate only the Mermaid diagram syntax in a ```mermaid code block, no explanations.",
            "er": "You are an expert at analyzing source code and creating Mermaid entity-relationship diagrams. Generate only the Mermaid diagram syntax in a ```mermaid code block, no explanations."
        }
        
        my_role = role_descriptions.get(diagram_type, role_descriptions["class"])
        
        # Call parent constructor
        super().__init__(server_address, model_name, my_role, max_tokens, api_key)
        
        # Store diagram type for later use
        self.diagram_type = diagram_type

    def validate_mermaid_diagram(self, mermaid_content):
        """Validate a Mermaid diagram using mermaid-cli.
        
        Args:
            mermaid_content: The Mermaid diagram syntax to validate
            
        Returns:
            Tuple of (is_valid, error_message)
            - is_valid: True if diagram is valid, False otherwise
            - error_message: None if valid, error message string if invalid
        """
        try:
            # Create a temporary file for the mermaid diagram
            with tempfile.NamedTemporaryFile(mode='w', suffix='.mmd', delete=False) as tmp_file:
                tmp_file.write(mermaid_content)
                tmp_mmd_path = tmp_file.name
            
            try:
                # Use mermaid-cli to validate the diagram by attempting to compile it
                # We'll try to render to SVG as it's faster than PNG for validation
                with tempfile.NamedTemporaryFile(suffix='.svg', delete=False) as tmp_output:
                    tmp_output_path = tmp_output.name
                
                try:
                    result = subprocess.run(
                        ['mmdc', '-i', tmp_mmd_path, '-o', tmp_output_path],
                        capture_output=True,
                        text=True,
                        timeout=30
                    )
                    
                    if result.returncode == 0:
                        return True, None
                    else:
                        # Extract error message from stderr
                        error_msg = result.stderr.strip() if result.stderr else result.stdout.strip()
                        return False, error_msg
                finally:
                    # Clean up temporary output file
                    if os.path.exists(tmp_output_path):
                        os.remove(tmp_output_path)
            finally:
                # Clean up temporary mermaid file
                if os.path.exists(tmp_mmd_path):
                    os.remove(tmp_mmd_path)
                    
        except FileNotFoundError:
            print("Warning: 'mmdc' command not found. Skipping validation.")
            print("Install with: npm install -g @mermaid-js/mermaid-cli")
            return True, None  # Return valid if tool is not available
        except Exception as e:
            print(f"Warning: Error validating mermaid diagram: {e}")
            return True, None  # Return valid on unexpected errors

    def get_response(self, source_code, validate=False, max_fix_attempts=5):
        """Generate a Mermaid diagram from source code.
        
        Args:
            source_code: The source code to analyze and diagram
            validate: Whether to validate the diagram with mermaid compiler
            max_fix_attempts: Maximum number of attempts to fix compilation errors (default: 5)
            
        Returns:
            The Mermaid diagram syntax or None on error
        """
        # Construct the prompt based on diagram type
        prompts = {
            "class": f"Analyze this source code and generate a Mermaid class diagram:\n\n{source_code}",
            "flowchart": f"Analyze this source code and generate a Mermaid flowchart diagram:\n\n{source_code}",
            "sequence": f"Analyze this source code and generate a Mermaid sequence diagram:\n\n{source_code}",
            "er": f"Analyze this source code and generate a Mermaid entity-relationship diagram:\n\n{source_code}"
        }
        
        prompt = prompts.get(self.diagram_type, prompts["class"])
        
        # Add the user prompt to the messages list
        self.messages.append({"role": "user", "content": prompt})

        # Main loop for generating and validating the diagram
        fix_attempt = 0
        while fix_attempt <= max_fix_attempts:
            retries = 3
            response_raw = None
            
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

                    # Add the response to the messages list
                    self.messages.append({"role": "assistant", "content": response_raw})
                    break  # Successfully got a response
                    
                except Exception as e:
                    error_msg = str(e)
                    if 'timeout' in error_msg.lower():
                        print(f"Timeout occurred. Retrying {attempt + 1}/{retries}...")
                    else:
                        print(f"Error: {error_msg}")
                        
                    if attempt == retries - 1:
                        print("Max retries reached. Exiting.")
                        return None
            
            if response_raw is None:
                return None
            
            # If validation is not requested, return immediately
            if not validate:
                return response_raw
            
            # Extract and validate the mermaid diagram
            mermaid_content = self.extract_mermaid_diagram(response_raw)
            if not mermaid_content:
                print("Warning: Could not extract mermaid diagram from response")
                return response_raw
            
            is_valid, error_msg = self.validate_mermaid_diagram(mermaid_content)
            
            if is_valid:
                print(f"✓ Mermaid diagram validation successful!")
                return response_raw
            else:
                fix_attempt += 1
                if fix_attempt > max_fix_attempts:
                    print(f"✗ Max fix attempts ({max_fix_attempts}) reached. Returning last diagram despite errors.")
                    return response_raw
                
                print(f"✗ Mermaid diagram validation failed (attempt {fix_attempt}/{max_fix_attempts})")
                print(f"Error: {error_msg}")
                
                # Ask the model to fix the errors
                fix_prompt = f"""The previous Mermaid diagram has compilation errors:

{error_msg}

Please fix the diagram and generate a corrected version. Make sure to:
1. Fix the syntax errors mentioned above
2. Keep the same structure and information
3. Return only the corrected Mermaid diagram in a ```mermaid code block

Generate the fixed diagram now:"""
                
                self.messages.append({"role": "user", "content": fix_prompt})
                print(f"Requesting fix from model...")
        
        return None

    def extract_mermaid_diagram(self, response):
        """Extract the Mermaid diagram from the response.
        
        Args:
            response: The raw response containing the Mermaid diagram
            
        Returns:
            The extracted Mermaid diagram or the full response if extraction fails
        """
        if not response:
            return ""
            
        # Try to extract mermaid code block
        pattern = r"```mermaid(.*?)```"
        match = re.search(pattern, response, re.DOTALL)
        if match:
            return match.group(1).strip()
        
        # If no mermaid block found, return the full response
        return response

    def set_diagram_type(self, diagram_type):
        """Change the diagram type.
        
        Args:
            diagram_type: New diagram type (class, flowchart, sequence, er)
        """
        valid_types = ["class", "flowchart", "sequence", "er"]
        if diagram_type not in valid_types:
            raise ValueError(f"Invalid diagram type. Must be one of: {', '.join(valid_types)}")
        
        self.diagram_type = diagram_type
        
        # Update the system message
        role_descriptions = {
            "class": "You are an expert at analyzing source code and creating Mermaid class diagrams. Generate only the Mermaid diagram syntax in a ```mermaid code block, no explanations.",
            "flowchart": "You are an expert at analyzing source code and creating Mermaid flowcharts. Generate only the Mermaid diagram syntax in a ```mermaid code block, no explanations.",
            "sequence": "You are an expert at analyzing source code and creating Mermaid sequence diagrams. Generate only the Mermaid diagram syntax in a ```mermaid code block, no explanations.",
            "er": "You are an expert at analyzing source code and creating Mermaid entity-relationship diagrams. Generate only the Mermaid diagram syntax in a ```mermaid code block, no explanations."
        }
        
        self.messages[0]["content"] = role_descriptions.get(diagram_type, role_descriptions["class"])

    def diagram_to_png(self, mermaid_content, output_path):
        """Convert a Mermaid diagram to PNG format.
        
        Args:
            mermaid_content: The Mermaid diagram syntax
            output_path: Path where to save the PNG file
            
        Returns:
            Path to the generated PNG file or None on error
        """
        try:
            # Create a temporary file for the mermaid diagram
            with tempfile.NamedTemporaryFile(mode='w', suffix='.mmd', delete=False) as tmp_file:
                tmp_file.write(mermaid_content)
                tmp_mmd_path = tmp_file.name
            
            try:
                # Use mermaid-cli to render PNG
                # mmdc (mermaid-cli) command: mmdc -i input.mmd -o output.png
                result = subprocess.run(
                    ['mmdc', '-i', tmp_mmd_path, '-o', output_path],
                    capture_output=True,
                    text=True,
                    timeout=30
                )
                
                if result.returncode == 0:
                    return output_path
                else:
                    print(f"Error rendering mermaid diagram: {result.stderr}")
                    return None
            finally:
                # Clean up temporary file
                if os.path.exists(tmp_mmd_path):
                    os.remove(tmp_mmd_path)
                    
        except FileNotFoundError:
            print("Error: 'mmdc' command not found. Please install mermaid-cli with: npm install -g @mermaid-js/mermaid-cli")
            return None
        except Exception as e:
            print(f"Error converting mermaid to PNG: {e}")
            return None
