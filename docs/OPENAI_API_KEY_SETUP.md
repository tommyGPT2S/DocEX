# OpenAI API Key Setup Guide

This guide explains how to set up and use your OpenAI API key with DocEX's LLM adapter.

---

## Getting Your OpenAI API Key

1. **Sign up or log in** to OpenAI:
   - Go to https://platform.openai.com/
   - Create an account or log in

2. **Navigate to API Keys**:
   - Go to https://platform.openai.com/api-keys
   - Click "Create new secret key"

3. **Create and copy your key**:
   - Give it a name (e.g., "DocEX Development")
   - Click "Create secret key"
   - **Important:** Copy the key immediately - you won't be able to see it again!

---

## Setting Up the API Key

### Option 1: Environment Variable (Recommended)

**Linux/macOS:**
```bash
export OPENAI_API_KEY='sk-your-api-key-here'
```

**Windows (Command Prompt):**
```cmd
set OPENAI_API_KEY=sk-your-api-key-here
```

**Windows (PowerShell):**
```powershell
$env:OPENAI_API_KEY='sk-your-api-key-here'
```

**Make it permanent (Linux/macOS):**
Add to your `~/.bashrc` or `~/.zshrc`:
```bash
export OPENAI_API_KEY='sk-your-api-key-here'
```

### Option 2: .env File

1. Create a `.env` file in the project root:
```bash
cd /Users/tommyjiang/Projects/DocEX-1
echo 'OPENAI_API_KEY=sk-your-api-key-here' > .env
```

2. The `.env` file is already in `.gitignore`, so it won't be committed.

3. DocEX will automatically load it if you're using `python-dotenv`.

### Option 3: Pass Directly in Code

```python
from docex.processors.llm import OpenAIAdapter

adapter = OpenAIAdapter({
    'api_key': 'sk-your-api-key-here',  # Directly in code (not recommended for production)
    'model': 'gpt-4o'
})
```

---

## Testing Your API Key

### Quick Test

```python
import os
from docex.processors.llm import OpenAIAdapter

# Check if key is set
if not os.getenv('OPENAI_API_KEY'):
    print("❌ OPENAI_API_KEY not set!")
else:
    print("✅ API key found")
    
    # Test adapter initialization
    adapter = OpenAIAdapter({
        'api_key': os.getenv('OPENAI_API_KEY'),
        'model': 'gpt-4o'
    })
    print("✅ Adapter initialized successfully")
```

### Run Test Script

```bash
# Activate virtual environment
source venv/bin/activate

# Set API key (if not already set)
export OPENAI_API_KEY='sk-your-api-key-here'

# Run test script
python examples/test_llm_adapter_real.py
```

---

## Using the API Key in Code

### Example 1: Basic Usage

```python
import os
from docex import DocEX
from docex.processors.llm import OpenAIAdapter

# Initialize DocEX
docEX = DocEX()
basket = docEX.basket('my_basket')

# Initialize adapter (uses OPENAI_API_KEY from environment)
adapter = OpenAIAdapter({
    'api_key': os.getenv('OPENAI_API_KEY'),  # or pass directly
    'model': 'gpt-4o',
    'prompt_name': 'invoice_extraction'
})

# Process document
document = basket.add('invoice.pdf')
result = await adapter.process(document)
```

### Example 2: With Custom Configuration

```python
adapter = OpenAIAdapter({
    'api_key': os.getenv('OPENAI_API_KEY'),
    'model': 'gpt-4o',                    # Model to use
    'prompt_name': 'invoice_extraction',  # Prompt from docex/prompts/
    'generate_summary': True,             # Generate summary
    'generate_embedding': True,          # Generate embedding
    'return_raw_response': True          # Include raw API response
})
```

---

## Security Best Practices

### ✅ DO:
- ✅ Use environment variables or `.env` files
- ✅ Add `.env` to `.gitignore` (already done)
- ✅ Use different keys for development and production
- ✅ Rotate keys regularly
- ✅ Monitor API usage

### ❌ DON'T:
- ❌ Commit API keys to git
- ❌ Hardcode keys in source code
- ❌ Share keys publicly
- ❌ Use production keys in development

---

## Troubleshooting

### Error: "OpenAI API key is required"

**Solution:** Make sure the API key is set:
```bash
echo $OPENAI_API_KEY  # Should show your key
```

### Error: "Invalid API key"

**Solution:**
1. Check that the key starts with `sk-`
2. Verify the key is correct (no extra spaces)
3. Make sure the key hasn't been revoked
4. Check your OpenAI account has credits

### Error: "Rate limit exceeded"

**Solution:**
1. Check your OpenAI usage limits
2. Add rate limiting to your code
3. Use a different model (e.g., `gpt-3.5-turbo` instead of `gpt-4o`)

### Error: "Insufficient quota"

**Solution:**
1. Add credits to your OpenAI account
2. Check your usage dashboard: https://platform.openai.com/usage

---

## API Key Management

### Check Current Key

```bash
# Linux/macOS
echo $OPENAI_API_KEY

# Windows
echo %OPENAI_API_KEY%
```

### Unset Key

```bash
# Linux/macOS
unset OPENAI_API_KEY

# Windows
set OPENAI_API_KEY=
```

### Test Key Validity

```python
import os
from openai import OpenAI

api_key = os.getenv('OPENAI_API_KEY')
if api_key:
    client = OpenAI(api_key=api_key)
    try:
        # Simple test call
        response = client.models.list()
        print("✅ API key is valid")
    except Exception as e:
        print(f"❌ API key error: {e}")
else:
    print("❌ API key not set")
```

---

## Cost Considerations

### Model Pricing (as of 2024)

- **gpt-4o**: ~$2.50 per 1M input tokens, ~$10 per 1M output tokens
- **gpt-4**: ~$30 per 1M input tokens, ~$60 per 1M output tokens
- **gpt-3.5-turbo**: ~$0.50 per 1M input tokens, ~$1.50 per 1M output tokens
- **text-embedding-3-large**: ~$0.13 per 1M tokens

### Tips to Reduce Costs

1. **Use appropriate models**: Use `gpt-3.5-turbo` for simple tasks
2. **Limit token usage**: Set `max_tokens` parameter
3. **Cache results**: Store embeddings and summaries
4. **Batch processing**: Process multiple documents together
5. **Monitor usage**: Check OpenAI dashboard regularly

---

## Next Steps

1. ✅ Set your API key
2. ✅ Run test script: `python examples/test_llm_adapter_real.py`
3. ✅ Try different prompts from `docex/prompts/`
4. ✅ Integrate into your application

---

## Additional Resources

- OpenAI API Documentation: https://platform.openai.com/docs
- OpenAI Pricing: https://openai.com/pricing
- OpenAI Usage Dashboard: https://platform.openai.com/usage
- DocEX LLM Adapter Docs: `docs/LLM_ADAPTER_IMPLEMENTATION.md`

