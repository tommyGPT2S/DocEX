# LLM Adapter Implementation Summary

## Overview

This document summarizes the implementation of LLM adapters for DocEX, extracted from the invoice processing system with **prompts moved to external files**.

---

## What Was Implemented

### 1. Prompt Management System

**Location:** `docex/processors/llm/prompt_manager.py`

**Features:**
- ✅ Loads prompts from YAML files
- ✅ Supports Jinja2 template syntax for variables
- ✅ Caching for performance
- ✅ Easy to edit prompts without code changes

**Usage:**
```python
from docex.processors.llm import PromptManager

manager = PromptManager()
system_prompt = manager.get_system_prompt('invoice_extraction')
user_prompt = manager.get_user_prompt('invoice_extraction', content=text)
```

### 2. Prompt Files (YAML Format)

**Location:** `docex/prompts/`

**Available Prompts:**
- `invoice_extraction.yaml` - Extract invoice data
- `product_extraction.yaml` - Extract product data
- `document_summary.yaml` - Generate document summaries
- `generic_extraction.yaml` - Generic structured extraction

**Format:**
```yaml
name: prompt_name
description: Description
version: 1.0

system_prompt: |
  Your system prompt here.

user_prompt_template: |
  Your user prompt with {{ variables }}.
```

### 3. OpenAI LLM Service

**Location:** `docex/processors/llm/openai_service.py`

**Features:**
- ✅ Extracted from invoice processing system
- ✅ Async/await pattern
- ✅ Text completion
- ✅ Embedding generation
- ✅ Structured data extraction
- ✅ JSON response parsing

**Methods:**
- `generate_completion()` - Generate text
- `generate_embedding()` - Generate embeddings
- `extract_structured_data()` - Extract structured data

### 4. Base LLM Processor

**Location:** `docex/processors/llm/base_llm_processor.py`

**Features:**
- ✅ Extends DocEX's `BaseProcessor`
- ✅ Integrates with DocEX metadata system
- ✅ Automatic operation tracking
- ✅ Prompt management integration
- ✅ Document text extraction

### 5. OpenAI Adapter

**Location:** `docex/processors/llm/openai_adapter.py`

**Features:**
- ✅ Uses external prompts (not embedded in code)
- ✅ Configurable prompt selection
- ✅ Optional summary generation
- ✅ Optional embedding generation
- ✅ Stores results in DocEX metadata

**Configuration:**
```python
adapter = OpenAIAdapter({
    'api_key': 'your-key',
    'model': 'gpt-4o',
    'prompt_name': 'invoice_extraction',  # Uses external YAML file
    'generate_summary': True,
    'generate_embedding': True
})
```

---

## Key Improvements Over Invoice System

### ✅ Prompts in External Files

**Before (Invoice System):**
```python
system_prompt = """
You are an expert invoice data extraction system...
"""
# Prompt embedded in Python code
```

**After (DocEX LLM Adapter):**
```yaml
# docex/prompts/invoice_extraction.yaml
system_prompt: |
  You are an expert invoice data extraction system...
```
```python
# Code uses external prompt
system_prompt = manager.get_system_prompt('invoice_extraction')
```

**Benefits:**
- ✅ Edit prompts without code changes
- ✅ Version control prompts separately
- ✅ Easy to test different prompt variations
- ✅ Reuse prompts across processors
- ✅ Localize/translate prompts easily

### ✅ Generalization

**Before:** Invoice-specific extraction  
**After:** Generic extraction with configurable prompts

### ✅ DocEX Integration

**Before:** Custom metadata handling  
**After:** Uses DocEX's `MetadataService` and operation tracking

---

## File Structure

```
docex/
├── processors/
│   └── llm/
│       ├── __init__.py
│       ├── prompt_manager.py      # Prompt loading and management
│       ├── base_llm_processor.py   # Base class for LLM processors
│       ├── openai_service.py      # OpenAI client wrapper
│       └── openai_adapter.py      # OpenAI adapter for DocEX
└── prompts/                        # External prompt files
    ├── README.md
    ├── invoice_extraction.yaml
    ├── product_extraction.yaml
    ├── document_summary.yaml
    └── generic_extraction.yaml
```

---

## Usage Examples

### Example 1: Invoice Extraction

```python
from docex import DocEX
from docex.processors.llm import OpenAIAdapter

docEX = DocEX()
basket = docEX.basket('invoices')

# Initialize adapter with invoice extraction prompt
adapter = OpenAIAdapter({
    'api_key': os.getenv('OPENAI_API_KEY'),
    'prompt_name': 'invoice_extraction'  # Uses external YAML file
})

# Process document
document = basket.add('invoice.pdf')
result = await adapter.process(document)
```

### Example 2: Custom Prompt

1. Create `docex/prompts/my_custom_prompt.yaml`:
```yaml
name: my_custom_prompt
description: Custom extraction prompt
version: 1.0

system_prompt: |
  You are an expert at extracting custom data.

user_prompt_template: |
  Extract data from: {{ content }}
```

2. Use in code:
```python
adapter = OpenAIAdapter({
    'api_key': os.getenv('OPENAI_API_KEY'),
    'prompt_name': 'my_custom_prompt'  # Uses your custom prompt
})
```

### Example 3: With Summary and Embedding

```python
adapter = OpenAIAdapter({
    'api_key': os.getenv('OPENAI_API_KEY'),
    'prompt_name': 'generic_extraction',
    'summary_prompt_name': 'document_summary',
    'generate_summary': True,      # Generate summary
    'generate_embedding': True    # Generate embedding
})
```

---

## Dependencies Added

- `jinja2>=3.1.0` - Template rendering for prompts
- `openai>=1.0.0` - OpenAI API client

---

## Benefits

### 1. **Separation of Concerns**
- Prompts separated from code
- Easy to edit and version
- No code changes needed for prompt updates

### 2. **Reusability**
- Prompts can be reused across processors
- Easy to create variations
- Template variables for flexibility

### 3. **Maintainability**
- Clear file structure
- Easy to find and edit prompts
- Version control friendly

### 4. **Testing**
- Easy to test different prompt variations
- A/B testing different prompts
- Prompt versioning

### 5. **Localization**
- Easy to translate prompts
- Language-specific prompt files
- No code changes needed

---

## Next Steps

1. **Add More Prompts**
   - Create prompts for other document types
   - Add domain-specific prompts
   - Create prompt templates

2. **Add More LLM Providers**
   - Anthropic adapter
   - Local LLM adapter (Ollama, etc.)
   - Multi-provider support

3. **Prompt Versioning**
   - Add version management
   - Prompt migration tools
   - Version comparison

4. **Prompt Testing**
   - Prompt evaluation framework
   - A/B testing tools
   - Performance metrics

---

## Related Documents

- `docs/LLM_ADAPTER_PROPOSAL.md` - Original proposal
- `docs/INVOICE_LLM_ADAPTER_ANALYSIS.md` - Analysis of invoice implementation
- `docs/DOCEX_LEVERAGE_SUMMARY.md` - DocEX features to leverage

---

**Implementation Date:** 2024  
**Status:** ✅ Complete  
**Next:** Add more LLM providers and prompts

