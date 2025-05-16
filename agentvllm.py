import json
import requests

# vLLM library
from vllm import LLM, SamplingParams


class vllmAgentAI:
    
    # attribute to store the list of conversations
    messages = [
            ]

    def __init__(self, model_name, my_role):
        self.model_name = model_name
        self.messages = [
            {"role": "system",
             "content": my_role 
            }
        ] 

        # the part below is specific to vLLM
        self.llm = LLM(model=model_name)
        self.sampling_params = SamplingParams(temperature=0.0, max_tokens=1024)

    def get_outputs(outputs):
        for output in outputs:
            prompt = output.prompt
            generated_text = output.outputs[0].text
        
        return generated_text

    def get_response(self, prompt):
        # send a request to the ollama server
        
        # add the user prompt to the messages list
        self.messages.append({"role": "user", "content": prompt})

        headers = {'Content-Type': 'application/json'}
        
        response = self.llm.chat(messages=self.messages,
                                sampling_params=self.sampling_params,
                                use_tqdm=False)

        response_raw = get_outputs(response)
        
        self.messages.append({"role": "assistant", "content": response_raw})

        return response_raw
    
        

    def start(self):
        # the part below is specific to vLLM
        llm = LLM(model=model_name)
        sampling_params = SamplingParams(temperature=0.0, max_tokens=1024)

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