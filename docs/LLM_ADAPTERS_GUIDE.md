# LLM Adapters for DocEX

This document provides an overview of the LLM (Large Language Model) adapters available in DocEX, including the new Claude and Local LLM adapters.

## Available Adapters

### 1. OpenAI Adapter (Existing)
- **Provider**: OpenAI
- **Models**: GPT-4, GPT-3.5, etc.
- **Features**: Text completion, embeddings, structured data extraction
- **Status**: ✅ Fully implemented

### 2. Claude Adapter (New)
- **Provider**: Anthropic
- **Models**: Claude-3.5-Sonnet, Claude-3-Haiku, etc.
- **Features**: Text completion, structured data extraction
- **Status**: ✅ Newly implemented

### 3. Local LLM Adapter (New)
- **Provider**: Ollama (Local hosting)
- **Models**: Llama, CodeLlama, Mistral, etc.
- **Features**: Text completion, embeddings (model-dependent), structured data extraction
- **Status**: ✅ Newly implemented

## Installation & Setup

### Dependencies

Add to your `requirements.txt`:
```
anthropic>=0.34.0  # For Claude adapter
aiohttp>=3.9.0     # For Local LLM adapter (already included)
```

Install dependencies:
```bash
pip install anthropic>=0.34.0
```

### Environment Variables

#### Claude (Anthropic)
```bash
export ANTHROPIC_API_KEY="your-anthropic-api-key"
```

#### Local LLM (Ollama)
```bash
# Install Ollama first: https://ollama.ai/
ollama serve  # Start Ollama server
ollama pull llama3.2  # Pull a model
```

## Usage Examples

### Claude Adapter

```python
import asyncio
from docex import DocEX
from docex.processors.llm import ClaudeAdapter

async def main():
    # Initialize DocEX
    docex = DocEX()
    basket = docex.basket('claude_test')
    
    # Add document
    document = basket.add('invoice.pdf')
    
    # Initialize Claude adapter
    adapter = ClaudeAdapter({
        'api_key': 'your-api-key',  # Or set ANTHROPIC_API_KEY
        'model': 'claude-3-5-sonnet-20241022',
        'prompt_name': 'invoice_extraction',
        'generate_summary': True
    })
    
    # Process document
    result = await adapter.process(document)
    
    if result.success:
        print("Extracted data:", result.content)
        metadata = document.get_metadata()
        print("Provider:", metadata.get('llm_provider'))
    else:
        print("Error:", result.error)

asyncio.run(main())
```

### Local LLM Adapter

```python
import asyncio
from docex import DocEX
from docex.processors.llm import LocalLLMAdapter

async def main():
    # Initialize DocEX
    docex = DocEX()
    basket = docex.basket('local_test')
    
    # Add document
    document = basket.add('meeting_notes.txt')
    
    # Initialize Local LLM adapter
    adapter = LocalLLMAdapter({
        'base_url': 'http://localhost:11434',  # Ollama server
        'model': 'llama3.2',
        'prompt_name': 'generic_extraction',
        'generate_summary': True,
        'generate_embedding': True
    })
    
    # Process document
    result = await adapter.process(document)
    
    if result.success:
        print("Extracted data:", result.content)
    else:
        print("Error:", result.error)

asyncio.run(main())
```

## Configuration Options

### Common Options (All Adapters)
- `prompt_name`: Name of the prompt file (without .yaml extension)
- `generate_summary`: Whether to generate a summary (default: False)
- `return_raw_response`: Whether to include raw LLM response (default: True)

### Claude-Specific Options
- `api_key`: Anthropic API key (or use ANTHROPIC_API_KEY env var)
- `model`: Claude model name (default: "claude-3-5-sonnet-20241022")

### Local LLM-Specific Options
- `base_url`: Ollama server URL (default: "http://localhost:11434")
- `model`: Local model name (default: "llama3.2")
- `generate_embedding`: Whether to generate embeddings (default: False)

## Prompt Templates

All adapters use the same prompt template system. Create YAML files in `docex/prompts/`:

```yaml
# example_extraction.yaml
name: "Example Data Extraction"
description: "Extract structured data from documents"
version: "1.0"

system_prompt: |
  You are a helpful AI assistant that extracts structured data from documents.
  Always return valid JSON with the requested fields.

user_prompt: |
  Extract the following information from this document:
  - title: Document title
  - summary: Brief summary
  - key_points: List of key points
  
  Document content:
  {{ content }}
  
  Return the data as JSON.
```

## Model Availability

### Claude Models
- `claude-3-5-sonnet-20241022` (Recommended)
- `claude-3-haiku-20240307`
- `claude-3-opus-20240229`

### Local Models (via Ollama)
- `llama3.2` (General purpose)
- `codellama` (Code analysis)
- `mistral` (Efficient alternative)
- `nomic-embed-text` (Embeddings)

Install local models:
```bash
ollama pull llama3.2
ollama pull codellama
ollama pull nomic-embed-text
```

## Features Comparison

| Feature | OpenAI | Claude | Local LLM |
|---------|--------|--------|-----------|
| Text Completion | ✅ | ✅ | ✅ |
| Embeddings | ✅ | ❌ | ✅* |
| Structured Extraction | ✅ | ✅ | ✅ |
| Summary Generation | ✅ | ✅ | ✅ |
| Cost | $ | $ | Free |
| Privacy | Cloud | Cloud | Local |
| Internet Required | ✅ | ✅ | ❌ |

*Embeddings depend on the specific local model

## Error Handling

### Claude Adapter
- **API Key Missing**: Set `ANTHROPIC_API_KEY` environment variable
- **Rate Limiting**: Anthropic has rate limits, handle gracefully
- **Model Not Found**: Use valid Claude model names

### Local LLM Adapter
- **Ollama Not Running**: Start with `ollama serve`
- **Model Not Available**: Pull with `ollama pull model-name`
- **Connection Issues**: Check Ollama server URL and port

## Testing

Run tests for the new adapters:

```bash
# Test Claude adapter (requires API key)
export ANTHROPIC_API_KEY="your-key"
python examples/test_claude_adapter.py

# Test Local LLM adapter (requires Ollama)
ollama serve  # In another terminal
ollama pull llama3.2
python examples/test_local_llm_adapter.py

# Unit tests
pytest tests/test_new_llm_adapters.py
```

## Performance Considerations

### Claude
- **Latency**: ~1-3 seconds per request
- **Cost**: Pay per token (input + output)
- **Rate Limits**: Check Anthropic's limits

### Local LLM
- **Latency**: Depends on hardware (2-10 seconds)
- **Cost**: Free after setup
- **Hardware**: Benefits from GPU acceleration

## Integration Examples

### With DocEX Processor Pipeline

```python
from docex.processors.llm import ClaudeAdapter

# Register as processor
docex.register_processor('claude_invoice', ClaudeAdapter({
    'prompt_name': 'invoice_extraction',
    'generate_summary': True
}))

# Use in pipeline
result = docex.process('invoice.pdf', processors=['claude_invoice'])
```

### Batch Processing

```python
import asyncio
from docex.processors.llm import LocalLLMAdapter

async def batch_process():
    adapter = LocalLLMAdapter({'model': 'llama3.2'})
    
    documents = [...]  # List of documents
    results = []
    
    for doc in documents:
        result = await adapter.process(doc)
        results.append(result)
    
    return results
```

## Troubleshooting

### Common Issues

1. **Import Errors**
   ```bash
   pip install anthropic aiohttp
   ```

2. **API Key Issues**
   ```bash
   export ANTHROPIC_API_KEY="your-key"
   ```

3. **Ollama Connection**
   ```bash
   ollama serve  # Start server
   curl http://localhost:11434/api/tags  # Test connection
   ```

4. **Model Not Found**
   ```bash
   ollama pull llama3.2  # Pull specific model
   ollama list  # Check available models
   ```

## Contributing

To add a new LLM adapter:

1. Create service class (e.g., `new_llm_service.py`)
2. Create adapter class (e.g., `new_llm_adapter.py`)
3. Update `__init__.py` exports
4. Add tests
5. Add example usage
6. Update documentation

## Resources

- **Anthropic API**: https://docs.anthropic.com/
- **Ollama**: https://ollama.ai/
- **DocEX Documentation**: [Internal docs]
- **Prompt Engineering**: Best practices for LLM prompts

---

**Last Updated**: November 18, 2024  
**Version**: 1.0