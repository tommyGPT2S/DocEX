# Embedding Function API

DocEX vector indexing and semantic search use a provider-neutral embedding function:

```python
def embed(text: str) -> list[float]:
    ...
```

Async callables are also supported:

```python
async def embed(text: str) -> list[float]:
    ...
```

The callable must return a non-empty list of numeric values. DocEX validates the result and raises on invalid embeddings.

Use the same embedding function, model, and dimensionality for indexing and querying.
