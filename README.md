# agenticAI project

This project is a simple project that illustrates how to use two different AI models to have a conversation with each other. 

The idea is to test how the models behave over time, so please let the conversation run for a while. 

This program has only one argument --prompt "What you want the model to do".

## What happens in the code
There is one class that keeps the conversation with the model. 

The main script instantiates two of these classes, starts the conversation between two models in two different servers. 

## LiteLLM Integration
This project now uses [LiteLLM](https://github.com/BerriAI/litellm) as the unified interface for communicating with various LLM providers. This allows you to easily switch between different model providers without changing your code.

### Supported Providers
LiteLLM supports 100+ LLM providers including:
- OpenAI
- Azure OpenAI
- Anthropic (Claude)
- Cohere
- Hugging Face
- Ollama (local models)
- Custom OpenAI-compatible servers

### Configuration
You can configure the agents to use different providers by setting the appropriate `server_address` and `model_name`:

```python
# OpenAI
agent = AgentAI(
    server_address="https://api.openai.com",  # or None for default
    model_name="gpt-4",
    my_role="You are a helpful assistant"
)

# Ollama (local)
agent = AgentAI(
    server_address="http://localhost:11434",
    model_name="llama2",
    my_role="You are a helpful assistant"
)

# Custom server (automatically handles /v1/chat/completions endpoints)
agent = AgentAI(
    server_address="http://your-server.com/v1/chat/completions",
    model_name="your-model",
    my_role="You are a helpful assistant"
)
```

## Using the API key
If you want to use the OpenAI servers, or another server with the API KEY, please set the OPENAI_API_KEY environment variable, for example: 
```bash
export OPENAI_API_KEY="your_token_here"
```

Alternatively, you can pass the API key directly when creating an agent:
```python
agent = AgentAI(
    server_address="https://api.openai.com",
    model_name="gpt-4",
    my_role="You are a helpful assistant",
    api_key="your_token_here"
)
``` 