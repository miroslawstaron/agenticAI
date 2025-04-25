import json
import requests


class AgentAI:
    
    # attribute to store the list of conversations
    messages = [
            ]

    def __init__(self, server_address, model_name, my_role):
        self.server_address = server_address
        self.model_name = model_name
        self.url = f'{self.server_address}/api/chat'
        self.messages = [
            {"role": "system",
             "content": my_role 
            }
        ] 

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

        retries = 3
        for attempt in range(retries):
            try:
                response = requests.post(self.url,
                                        headers=headers,
                                        json=data,
                                        timeout=600)

                if response.status_code == 200:
                    # get the response from the server
                    response_dict = json.loads(response.text)

                    # since the response contains a lot of other things, we need to extract the content
                    response_raw = response_dict['message']['content']

                    # add the response to the messages list
                    self.messages.append({"role": "assistant", "content": response_raw})
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
        

    def start(self):
        print(f"Starting agent with model {self.model_name} at {self.server_address}")

    # this function saves the messages to a file
    def save_to_csv(self,filename):
        # open the file in write mode
        with open(filename, 'w') as f:
            # write the header with $ as separator
            f.write('role$content\n')
            # write the messages with $ as separator
            for message in self.messages:
                f.write(f"{message['role']}${message['content']}\n")

    # this function saves the messages to an Excel file
    def save_to_excel(self, filename):
        import pandas as pd
        # convert the messages list to a DataFrame and rename columns if necessary
        df = pd.DataFrame(self.messages)
        # save the DataFrame to an Excel file without an index column
        df.to_excel(filename, index=False)