import agent
import re
import requests
import json
import os


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

    def get_response(self, source_code):
        """Generate a Mermaid diagram from source code.
        
        Args:
            source_code: The source code to analyze and diagram
            
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

        data = {
            "model": self.model_name,
            "messages": self.messages,
            "stream": False,
            "temperature": 0.3,
            "max_tokens": self.max_tokens,
        }

        headers = {'Content-Type': 'application/json'}
        
        if self.api_key:
            headers['Authorization'] = f'Bearer {self.api_key}'

        retries = 3
        for attempt in range(retries):
            try:
                response = requests.post(self.url,
                                        headers=headers,
                                        json=data,
                                        timeout=300)

                if response.status_code == 200:
                    # Get the response from the server
                    response_dict = json.loads(response.text)

                    # Extract the content
                    response_raw = response_dict['choices'][0]['message']['content']

                    # Add the response to the messages list
                    self.messages.append({"role": "assistant", "content": response_raw})
                    
                    return response_raw
                else:
                    # On error, print the error message
                    print(f"Error: {response.status_code} - {response.text}")
                    return None
            except requests.exceptions.Timeout:
                print(f"Timeout occurred. Retrying {attempt + 1}/{retries}...")
                if attempt == retries - 1:
                    print("Max retries reached. Exiting.")
                    return None
        
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
