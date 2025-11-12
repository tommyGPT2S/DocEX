# DocEX LLM Prompts

This directory contains prompt templates for LLM processors. Prompts are stored in YAML format to allow easy editing and versioning without code changes.

## Prompt File Format

Each prompt file should be a YAML file with the following structure:

```yaml
name: prompt_name
description: Description of what this prompt does
version: 1.0

system_prompt: |
  Your system prompt here.
  This defines the role and behavior of the LLM.

user_prompt_template: |
  Your user prompt template here.
  Use Jinja2 template syntax for variables.
  Example: {{ content }}
```

## Available Prompts

### invoice_extraction.yaml
Extracts structured invoice data from text.

**Variables:**
- `content`: Invoice text content

### product_extraction.yaml
Extracts structured product data from descriptions.

**Variables:**
- `content`: Product description text

### document_summary.yaml
Generates summaries of documents.

**Variables:**
- `content`: Document text content

### generic_extraction.yaml
Generic structured data extraction with custom schema.

**Variables:**
- `content`: Document text content
- `schema`: Optional schema definition (if provided)

## Using Prompts in Code

```python
from docex.processors.llm import OpenAIAdapter

# Initialize adapter with prompt
adapter = OpenAIAdapter({
    'api_key': 'your-key',
    'prompt_name': 'invoice_extraction',  # Uses invoice_extraction.yaml
    'generate_summary': True,
    'generate_embedding': True
})

# Process document
result = await adapter.process(document)
```

## Creating New Prompts

1. Create a new YAML file in this directory
2. Follow the format shown above
3. Use Jinja2 template syntax for variables
4. Reference the prompt by name (without .yaml extension) in your code

## Template Variables

Prompts support Jinja2 template syntax. Common variables:

- `{{ content }}` - Document text content
- `{{ schema }}` - Data extraction schema (if applicable)
- `{{ document_type }}` - Type of document
- `{{ metadata }}` - Document metadata (if applicable)

## Best Practices

1. **Version your prompts** - Include version numbers in prompt files
2. **Be specific** - Clear system prompts lead to better results
3. **Test variations** - Create multiple versions and test which works best
4. **Document variables** - Clearly document what variables are available
5. **Keep prompts focused** - One prompt per specific task

