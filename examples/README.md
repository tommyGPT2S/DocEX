# DocEX Examples

These examples are reference code, not maintained core library modules. Copy the pattern you need into your application and adapt it to your provider, deployment, and data model.

## Categories

- `integrations/` - External LLM provider examples for OpenAI, Anthropic, and local models.
- `patterns/` - Higher-level orchestration examples: RAG, knowledge bases, advanced chunking, and invoice extraction.
- `custom_processors/` - Examples for writing application-owned processors.
- Existing root-level scripts - Older runnable demos kept as examples while the core library is being slimmed down.

## Why LLM/RAG Lives Here

DocEX core focuses on document storage, metadata, multi-tenancy, transport, and provider-neutral vector indexing. LLM adapters, prompt templates, RAG orchestration, and domain-specific extraction are application concerns, so they live here as integration examples.
