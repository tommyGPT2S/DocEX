# Integration Patterns

DocEX 3.0 keeps the core library lean. External intelligence layers live in `examples/`:

- `examples/integrations/openai/` - OpenAI LLM adapter and service examples.
- `examples/integrations/anthropic/` - Anthropic adapter examples.
- `examples/integrations/local_llm/` - Local/Ollama-style adapter examples.
- `examples/patterns/rag/` - Basic and enhanced RAG reference implementations.
- `examples/patterns/knowledge_base/` - Generic knowledge-base orchestration examples.
- `examples/patterns/chunking/` - LLM- and embedding-dependent chunking examples.
- `examples/patterns/invoice_extraction/` - Domain-specific invoice extraction example.

Core vector indexing accepts an `embedding_fn`; bring your own provider or adapt one of the integration examples.
