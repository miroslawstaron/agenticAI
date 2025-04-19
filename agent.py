import json
import requests


class AgentAI:
    
    # attribute to store the list of conversations
    messages = [
            {"role": "system",
             "content": "You are a software that writes C programs based on prompts. Provides only the code, no description."}
            ]

    def __init__(self, server_address, model_name):
        self.server_address = server_address
        self.model_name = model_name
        self.url = f'{self.server_address}/api/chat'

    def get_response(self, prompt):
        # send a request to the ollama server
       
        # add the user prompt to the messages list
        self.messages.append({"role": "user", "content": prompt})

        
        data = {
            "model": self.model_name,
            "messages": self.messages,
            "stream": False, 
            "temperature": 0.0,
            }
        headers = {'Content-Type': 'application/json'}
        response = requests.post(self.url, 
                                 headers=headers, 
                                 json=data, 
                                 timeout=30)

        if response.status_code == 200:
            return response.json().get('text', '')
        else:
            print(f"Error: {response.status_code} - {response.text}")
            return None
        pass

    def start(self):
        print(f"Starting agent with model {self.model_name} at {self.server_address}")