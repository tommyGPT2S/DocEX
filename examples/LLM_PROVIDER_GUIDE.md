# LLM Provider Guide for Chargeback Workflow

The chargeback workflow processors support multiple LLM providers. This guide shows how to use each one.

## Supported Providers

1. **OpenAI** (default) - GPT-4o, GPT-4, GPT-3.5
2. **Local/Ollama** - Free, runs locally, no API costs
3. **Claude (Anthropic)** - Claude 3.5 Sonnet, Claude 3 Opus

## Configuration

### Option 1: OpenAI (Default)

**Setup:**
```bash
export OPENAI_API_KEY='your-openai-api-key'
export LLM_PROVIDER='openai'  # optional, this is the default
```

**Code:**
```python
extract_config = {
    'llm_provider': 'openai',  # or omit for default
    'llm_config': {
        'api_key': os.getenv('OPENAI_API_KEY'),
        'model': 'gpt-4o',
        'prompt_name': 'chargeback_modeln'
    }
}
```

**Pros:**
- ✅ High accuracy (98%+)
- ✅ Fast response times
- ✅ Reliable API

**Cons:**
- ❌ Requires API key with quota
- ❌ Costs per request

---

### Option 2: Local/Ollama (Recommended for Testing)

**Setup:**
1. Install Ollama: https://ollama.ai
2. Start Ollama server: `ollama serve`
3. Pull a model: `ollama pull llama3.2`

**Code:**
```python
extract_config = {
    'llm_provider': 'local',  # or 'ollama'
    'llm_config': {
        'model': 'llama3.2',  # or 'mistral', 'llama3', etc.
        'base_url': 'http://localhost:11434',  # Default Ollama URL
        'prompt_name': 'chargeback_modeln'
    }
}
```

**Available Models:**
- `llama3.2` - Good balance of speed and quality
- `llama3` - Larger, more capable
- `mistral` - Fast and efficient
- `codellama` - Good for structured data

**Pros:**
- ✅ Free (no API costs)
- ✅ Privacy (data stays local)
- ✅ Works offline
- ✅ No quota limits

**Cons:**
- ⚠️ Requires local setup
- ⚠️ Slower than cloud APIs
- ⚠️ May have lower accuracy than GPT-4

**Quick Start:**
```bash
# Install Ollama
curl -fsSL https://ollama.ai/install.sh | sh

# Start server
ollama serve

# In another terminal, pull a model
ollama pull llama3.2

# Run the example
export LLM_PROVIDER='local'
python examples/chargeback_workflow_example.py
```

---

### Option 3: Claude (Anthropic)

**Setup:**
```bash
export ANTHROPIC_API_KEY='your-anthropic-api-key'
export LLM_PROVIDER='claude'
```

**Install dependency:**
```bash
pip install anthropic>=0.34.0
```

**Code:**
```python
extract_config = {
    'llm_provider': 'claude',
    'llm_config': {
        'api_key': os.getenv('ANTHROPIC_API_KEY'),
        'model': 'claude-3-5-sonnet-20241022',
        'prompt_name': 'chargeback_modeln'
    }
}
```

**Available Models:**
- `claude-3-5-sonnet-20241022` - Best balance
- `claude-3-opus-20240229` - Most capable
- `claude-3-haiku-20240307` - Fastest

**Pros:**
- ✅ High accuracy
- ✅ Good for structured extraction
- ✅ Competitive with GPT-4

**Cons:**
- ❌ Requires API key
- ❌ Costs per request

---

## Example Usage

### Using Environment Variables

```bash
# For OpenAI
export OPENAI_API_KEY='your-key'
export LLM_PROVIDER='openai'
python examples/chargeback_workflow_example.py

# For Local/Ollama
export LLM_PROVIDER='local'
python examples/chargeback_workflow_example.py

# For Claude
export ANTHROPIC_API_KEY='your-key'
export LLM_PROVIDER='claude'
python examples/chargeback_workflow_example.py
```

### Using Code Configuration

```python
from docex.processors.chargeback import ExtractIdentifiersProcessor

# OpenAI
config = {
    'llm_provider': 'openai',
    'llm_config': {
        'api_key': 'your-key',
        'model': 'gpt-4o',
        'prompt_name': 'chargeback_modeln'
    }
}

# Local/Ollama
config = {
    'llm_provider': 'local',
    'llm_config': {
        'model': 'llama3.2',
        'base_url': 'http://localhost:11434',
        'prompt_name': 'chargeback_modeln'
    }
}

# Claude
config = {
    'llm_provider': 'claude',
    'llm_config': {
        'api_key': 'your-key',
        'model': 'claude-3-5-sonnet-20241022',
        'prompt_name': 'chargeback_modeln'
    }
}

processor = ExtractIdentifiersProcessor(config)
```

---

## Recommendation for Testing

**For development and testing, use Local/Ollama:**
- ✅ No API costs
- ✅ No quota limits
- ✅ Privacy (data stays local)
- ✅ Easy to set up

**For production, use OpenAI or Claude:**
- ✅ Higher accuracy
- ✅ Faster response times
- ✅ More reliable

---

## Troubleshooting

### Ollama Connection Issues

```bash
# Check if Ollama is running
curl http://localhost:11434/api/tags

# If not running, start it
ollama serve

# Check available models
ollama list

# Pull a model if needed
ollama pull llama3.2
```

### Model Not Found

If you get "model not available" error:
```bash
# List available models
ollama list

# Pull the model you need
ollama pull llama3.2
```

### API Key Issues

- OpenAI: Check `OPENAI_API_KEY` environment variable
- Claude: Check `ANTHROPIC_API_KEY` environment variable
- Make sure the key has available quota

---

## Performance Comparison

| Provider | Speed | Accuracy | Cost | Setup |
|----------|-------|----------|------|-------|
| OpenAI GPT-4o | ⚡⚡⚡ Fast | ⭐⭐⭐⭐⭐ Excellent | 💰💰💰 Paid | Easy |
| Claude 3.5 Sonnet | ⚡⚡⚡ Fast | ⭐⭐⭐⭐⭐ Excellent | 💰💰💰 Paid | Easy |
| Ollama (llama3.2) | ⚡⚡ Medium | ⭐⭐⭐⭐ Good | 💰 Free | Medium |
| Ollama (llama3) | ⚡ Slow | ⭐⭐⭐⭐ Good | 💰 Free | Medium |

---

**Last Updated:** 2024-12-19


