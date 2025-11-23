# Migration Guide: LiteLLM Integration

This document explains the changes made to migrate agenticAI from direct HTTP requests to LiteLLM.

## What Changed?

### Dependencies
- **Added**: `litellm` package for unified LLM provider interface
- **Still Required**: `requests` is still in requirements.txt but no longer used directly for API calls

### Code Changes

#### Before (Old API with requests)
```python
import requests
import json

response = requests.post(
    url,
    headers={'Content-Type': 'application/json', 'Authorization': f'Bearer {api_key}'},
    json={
        "model": model_name,
        "messages": messages,
        "stream": False,
        "temperature": 0.5
    },
    timeout=300
)

response_dict = json.loads(response.text)
response_raw = response_dict['choices'][0]['message']['content']
```

#### After (New API with LiteLLM)
```python
from litellm import completion

response = completion(
    model=model_name,
    messages=messages,
    temperature=0.5,
    max_tokens=max_tokens,
    api_base=api_base,
    api_key=api_key,
    timeout=300
)

response_raw = response.choices[0].message.content
```

## Benefits of the Migration

1. **Provider Flexibility**: Switch between OpenAI, Ollama, Azure, Anthropic, and 100+ other providers without code changes
2. **Better Error Handling**: LiteLLM provides unified error handling across different providers
3. **Cleaner Code**: Simplified API calls with less boilerplate
4. **Built-in Features**: 
   - Automatic retries
   - Cost tracking
   - Streaming support
   - Async support
   - Request caching

## Backward Compatibility

The migration maintains full backward compatibility with existing code:

✅ All existing scripts work without modification
✅ Server address format is automatically normalized (strips `/v1/chat/completions` endpoints)
✅ API key handling remains the same (environment variable or explicit parameter)
✅ All agent classes maintain the same interface

## Example: Before and After

### Before Migration
```python
from agent import AgentAI

# Old code - still works!
agent = AgentAI(
    server_address="http://localhost:11434/v1/chat/completions",
    model_name="llama2",
    my_role="You are a helpful assistant"
)
```

### After Migration
```python
from agent import AgentAI

# Same code works, but now uses LiteLLM internally
agent = AgentAI(
    server_address="http://localhost:11434/v1/chat/completions",
    model_name="llama2",
    my_role="You are a helpful assistant"
)

# You can now also use other providers:
agent_openai = AgentAI(
    server_address="https://api.openai.com",
    model_name="gpt-4",
    my_role="You are a helpful assistant",
    api_key="sk-..."
)

agent_anthropic = AgentAI(
    server_address="https://api.anthropic.com",
    model_name="claude-3-opus-20240229",
    my_role="You are a helpful assistant",
    api_key="sk-ant-..."
)
```

## Testing

All agent classes have been tested and verified:
- ✅ AgentAI
- ✅ AgentAIC
- ✅ AgentCompiler
- ✅ AgentStaticAnalyzer
- ✅ AgentH

### Running Tests
You can verify the migration by running the existing main scripts:

```bash
# Test basic conversation
python main.py --prompt "Write a hello world program in C"

# Test with compilation
python main_agentc.py --prompt "Write a sorting algorithm in C"

# Test different models
python mainT.py --prompt "Explain recursion"
```

## Troubleshooting

### Issue: "Module not found: litellm"
**Solution**: Install dependencies
```bash
pip install -r requirements.txt
```

### Issue: API endpoint errors
**Solution**: The code now automatically strips `/v1/chat/completions` and `/v1` from server addresses. If you're using a custom endpoint, ensure it follows OpenAI-compatible format.

### Issue: Authentication errors
**Solution**: Ensure your API key is set:
```bash
export OPENAI_API_KEY="your-key-here"
```
Or pass it explicitly when creating agents.

## Further Reading

- [LiteLLM Documentation](https://docs.litellm.ai/)
- [Supported Providers](https://docs.litellm.ai/docs/providers)
- [LiteLLM GitHub](https://github.com/BerriAI/litellm)
