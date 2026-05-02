# Migrating To DocEX 3.0

DocEX 3.0 removes LLM, RAG, generic knowledge-base, prompt-template, and domain-specific extraction modules from the core package.

## What Changed

- Removed `docex.processors.llm`.
- Removed `docex.processors.rag`.
- Removed `docex.processors.kb`.
- Removed `docex.prompts`.
- Removed `docex.services.generic_knowledge_base_service`.
- Removed the LLM-coupled `docex embed` CLI command.
- Removed the processor registry CLI group.
- Moved LLM/RAG/KB/prompt/invoice examples under `examples/`.
- Vector indexing now requires `embedding_fn`.

## Vector Indexing

Before:

```python
VectorIndexingProcessor({"llm_adapter": adapter})
```

After:

```python
VectorIndexingProcessor(embedding_fn=adapter.embed)
```

`embedding_fn` can be sync or async and must return a non-empty `list[float]`.

## LLM And RAG

Use `examples/integrations/` and `examples/patterns/` as reference code. These modules are intentionally examples, not stable core APIs.
