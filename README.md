# agenticAI project

This project is a simple project that illustrates how to use two different AI models to have a conversation with each other. 

The idea is to test how the models behave over time, so please let the conversation run for a while. 

This program has only one argument --prompt "What you want the model to do".

## What happens in the code
There is one class that keeps the conversation with the model. 

The main script instantiates two of these classes, starts the conversation between two models in two different servers. 

## Using the key
If you want to use the OpenAI servers, or another server with the API KEY, please set the OPENAI_API_KEY environment variable, for example: export OPENAI_API_KEY="your_token_here" 