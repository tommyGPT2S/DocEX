# DSPy Integration Guide

This guide explains how to use DSPy (Declarative Self-improving Python) with DocEX workflows for better structured extraction and automatic prompt optimization.

## What is DSPy?

[DSPy](https://dspy.ai/) is a framework for building modular AI software. Instead of wrangling prompts, DSPy allows you to:

- **Program with LMs** using declarative signatures instead of prompt strings
- **Automatically optimize** prompts and weights using optimizers
- **Iterate faster** with structured code rather than brittle strings
- **Improve over time** by applying the latest optimizers

## Installation

```bash
pip install dspy-ai
```

## Basic Usage

### Simple Extraction with DSPy

```python
from docex import DocEX
from docex.processors.chargeback import ExtractIdentifiersDSPyProcessor

# Initialize DocEX
docex = DocEX()

# Configure DSPy processor
config = {
    'model': 'openai/gpt-4o-mini',
    'use_chain_of_thought': True  # Use ChainOfThought for better reasoning
}

# Create processor
processor = ExtractIdentifiersDSPyProcessor(config, db=docex.db)

# Process document
result = await processor.process(document)
```

### Using Different Models

```python
# OpenAI
config = {
    'model': 'openai/gpt-4o-mini',
    'api_key': 'your-key'  # Optional, uses OPENAI_API_KEY env var
}

# Claude
config = {
    'model': 'anthropic/claude-sonnet-4-5-20250929',
    'api_key': 'your-key'  # Optional, uses ANTHROPIC_API_KEY env var
}

# Ollama (Local)
config = {
    'model': 'ollama/llama3.2',
    'base_url': 'http://localhost:11434'
}
```

## DSPy Signatures

DSPy uses **signatures** to define input/output schemas declaratively:

```python
# Instead of writing prompts, define signatures:
signature = "chargeback_document_text -> customer_name, hin, dea, contract_number"

# DSPy automatically generates optimized prompts from signatures
```

The `ExtractIdentifiersDSPyProcessor` automatically creates a signature from the chargeback fields, but you can customize it:

```python
config = {
    'model': 'openai/gpt-4o-mini',
    'signature': 'document_text -> field1, field2, field3'  # Custom signature
}
```

## Optimization

DSPy optimizers automatically improve extraction quality using training examples:

### BootstrapFewShot (Fast, Good Quality)

```python
config = {
    'model': 'openai/gpt-4o-mini',
    'optimizer': {
        'type': 'BootstrapFewShot',
        'metric': lambda example, prediction, trace=None: 
            example.customer_name == prediction.customer_name
    },
    'training_data': [
        {
            'chargeback_document_text': '...',
            'customer_name': 'ABC Healthcare',
            'hin': '123456789',
            # ... other fields
        }
    ]
}
```

### MIPROv2 (Advanced, Best Quality)

```python
config = {
    'model': 'anthropic/claude-sonnet-4-5-20250929',
    'optimizer': {
        'type': 'MIPROv2',
        'metric': lambda example, prediction, trace=None: (
            example.customer_name == prediction.customer_name and
            example.hin == prediction.hin
        )
    },
    'training_data': training_examples
}
```

### BootstrapFinetune (Fine-tune Model)

```python
config = {
    'model': 'openai/gpt-4o-mini',
    'optimizer': {
        'type': 'BootstrapFinetune',
        'metric': lambda example, prediction, trace=None: 
            example.customer_name == prediction.customer_name
    },
    'training_data': training_examples
}
```

## DSPy Adapter

The `DSPyAdapter` is a low-level adapter that wraps DSPy modules:

```python
from docex.processors.llm.dspy_adapter import DSPyAdapter, DSPySignatureBuilder

# Build signature from field list
signature = DSPySignatureBuilder.from_field_list(
    ['customer_name', 'hin', 'dea', 'contract_number'],
    input_name='document_text'
)

# Create adapter
adapter = DSPyAdapter({
    'signature': signature,
    'model': 'openai/gpt-4o-mini',
    'use_chain_of_thought': True
})

# Process document
result = await adapter.process(document)
```

## Comparison: YAML Prompts vs DSPy

### YAML Prompt (Traditional)

```yaml
# chargeback_modeln.yaml
system_prompt: |
  You are an expert chargeback data extraction system...
  
  Return a JSON object with these exact fields:
  {
    "customer_name": "string",
    "hin": "string",
    ...
  }

user_prompt_template: |
  Please extract the chargeback data from this text:
  {{ content }}
```

**Pros:**
- Simple, human-readable
- Easy to edit manually
- Works with any LLM

**Cons:**
- No automatic optimization
- Manual prompt engineering
- Hard to iterate and improve

### DSPy Signature (Declarative)

```python
signature = "chargeback_document_text -> customer_name, hin, dea, contract_number"

# DSPy automatically:
# - Generates optimized prompts
# - Can optimize with training data
# - Improves over time
```

**Pros:**
- Automatic prompt optimization
- Better extraction quality over time
- Structured, type-safe
- Easy to iterate

**Cons:**
- Requires DSPy dependency
- Initial setup more complex

## Examples

### Example 1: Basic DSPy Extraction

See `examples/chargeback_workflow_dspy_example.py`

```bash
export LLM_PROVIDER=openai  # or 'claude', 'local'
export OPENAI_API_KEY=your-key
python examples/chargeback_workflow_dspy_example.py
```

### Example 2: Optimized DSPy Extraction

See `examples/chargeback_workflow_dspy_optimized_example.py`

```bash
export LLM_PROVIDER=openai
export OPENAI_API_KEY=your-key
python examples/chargeback_workflow_dspy_optimized_example.py
```

## Integration with Workflows

DSPy processors integrate seamlessly with DocEX workflows:

```python
from docex.processors.chargeback import (
    ExtractIdentifiersDSPyProcessor,
    ChargebackWorkflowOrchestrator
)

# Use DSPy processor in workflow
steps = [
    {
        'processor': ExtractIdentifiersDSPyProcessor,
        'config': {'model': 'openai/gpt-4o-mini'},
        'name': 'extract_identifiers'
    },
    # ... other steps
]

orchestrator = ChargebackWorkflowOrchestrator(steps, db=docex.db)
result = await orchestrator.execute(document)
```

## When to Use DSPy

**Use DSPy when:**
- You want automatic prompt optimization
- You have training examples to improve quality
- You need better extraction quality over time
- You want to iterate faster on extraction logic

**Use YAML prompts when:**
- You need simple, manual control
- You don't have training data
- You want to avoid additional dependencies
- You're prototyping quickly

## Advanced: Custom DSPy Modules

You can create custom DSPy modules for complex workflows:

```python
import dspy
from dspy import Signature, ChainOfThought

# Define custom signature
class ChargebackExtraction(dspy.Signature):
    """Extract chargeback data from document"""
    chargeback_document_text: str = dspy.InputField()
    customer_name: str = dspy.OutputField()
    hin: str = dspy.OutputField()
    dea: str = dspy.OutputField()
    contract_number: str = dspy.OutputField()

# Create module
extract = ChainOfThought(ChargebackExtraction)

# Use in processor
result = extract(chargeback_document_text=text)
```

## References

- [DSPy Documentation](https://dspy.ai/)
- [DSPy GitHub](https://github.com/stanfordnlp/dspy)
- [DSPy Tutorials](https://dspy.ai/tutorials/)

## Troubleshooting

### Import Error: "DSPy is not installed"

```bash
pip install dspy-ai
```

### Model Not Found

Make sure your model identifier is correct:
- OpenAI: `openai/gpt-4o-mini`
- Claude: `anthropic/claude-sonnet-4-5-20250929`
- Ollama: `ollama/llama3.2`

### Optimization Takes Too Long

Use `BootstrapFewShot` instead of `MIPROv2` for faster optimization:

```python
'optimizer': {
    'type': 'BootstrapFewShot',  # Faster
    # instead of 'MIPROv2'  # Slower but better
}
```

### Local Model Not Working

Make sure Ollama is running:

```bash
ollama serve
ollama pull llama3.2
```

Then use:

```python
config = {
    'model': 'ollama/llama3.2',
    'base_url': 'http://localhost:11434'
}
```

