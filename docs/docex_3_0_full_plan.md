# docex 3.0 — Full Plan

*Supersedes `docex_2_8_7_cleanup_review.md`. Incorporates the refined direction (vector indexing stays in core; LLM/RAG move to examples) and folds in the versioning addendum's upstream additions.*

---

## 0. Direction (final)

**docex core =**
1. Document storage layer (DocBasket, Document, DocumentMetadata, multi-tenancy, storage backends, transport).
2. **Vector indexing and semantic search** as first-class capability, **decoupled from any specific LLM provider** (the user supplies an embedding function).
3. Versioning primitives (revisions, manifests, provenance, event subscriptions) — the additions from the versioning addendum.

**Out of docex core:**
- LLM adapters (OpenAI, Claude, local LLM).
- RAG orchestration (RAG service, enhanced RAG, vector_db_monitor).
- Generic knowledge base service.
- Prompt templates.
- LLM-dependent chunking strategies (agentic, llm_based, semantic, late).
- Domain-specific extractors (PDF invoice business logic).

**Where they go:**
- The capability moves to `examples/integrations/` and `examples/patterns/` as reference demos that show users how to wire their own LLM stack on top of docex. Code is unsupported sample code, not a maintained library module.
- For the LlamaSeeBI program specifically, the supported home for these capabilities is the private llamasee fabric library.

**The single architectural pivot:** `VectorIndexingProcessor` and `SemanticSearchService` accept a callable `embedding_fn: Callable[[str], List[float]]` rather than an `llm_adapter`. This severs the dependency on `processors/llm/` and lets vector indexing stand alone with `numpy` + `pgvector` as its only meaningful deps.

---

## 1. Inventory — final

Five categories: KEEP, RECONFIGURE, MOVE TO EXAMPLES, DELETE, NEW.

### 1.1 KEEP (core, unchanged)

- `docex/__init__.py`, `docex/docCore.py` (refactor in §6.1, but stays), `docex/document.py`, `docex/docbasket.py`, `docex/docbasket/`, `docex/cli.py` (trim in §6.2).
- `docex/context.py` — `UserContext`.
- `docex/db/` — entire module.
- `docex/storage/` — entire module.
- `docex/transport/` — entire module (note §11.1 future scope question).
- `docex/models/` — `BasketRecord`, `DocumentRecord`, `DocumentMetadata`, `MetadataKey`.
- `docex/services/docbasket_service.py`, `document_service.py`, `metadata_service.py`, `storage_service.py`.
- `docex/provisioning/`.
- `docex/config/`.
- `docex/utils/`.

### 1.2 RECONFIGURE (stay, but change shape)

These stay in core but get rebuilt to remove their LLM coupling.

- `docex/processors/vector/vector_indexing_processor.py` — accepts `embedding_fn` (callable) instead of `llm_adapter`. Vector DB layer (memory, pgvector) unchanged.
- `docex/processors/vector/semantic_search_service.py` — same change.
- **Decision: chunking** — split. Keep these strategies in core (no LLM, no numpy):
  - `chunking/base.py`, `chunking/factory.py`
  - `chunking/recursive.py`
  - `chunking/document_based.py`
  - A new simple `chunking/fixed_size.py` if it doesn't already exist (`base.py` may already include it).
  Move these to examples (LLM-dependent or embedding-dependent):
  - `chunking/agentic.py` (LLM)
  - `chunking/llm_based.py` (LLM)
  - `chunking/semantic.py` (numpy + embeddings)
  - `chunking/late.py` (numpy + embeddings)
  - `chunking/hierarchical.py` — review; if it's pure text-structure-based, keep; if it relies on embeddings, move.
- **Format converters** — see §1.6 "decision required" below. Default plan: keep `pdf_to_text`, `word_to_text`, `csv_to_json`, `mapper`. Move `pdf_invoice` (business extraction).

### 1.3 MOVE TO EXAMPLES

Live as reference integration patterns, not maintained library modules.

| From | To | Notes |
|---|---|---|
| `docex/processors/llm/openai_adapter.py`, `openai_service.py` | `examples/integrations/openai/llm_adapter.py` | Simplified; shows the pattern. |
| `docex/processors/llm/claude_service.py` | `examples/integrations/anthropic/llm_adapter.py` | |
| `docex/processors/llm/local_llm_adapter.py`, `local_llm_service.py` | `examples/integrations/local_llm/` | |
| `docex/processors/llm/base_llm_processor.py` | `examples/integrations/_shared/base_llm_processor.py` | Shared by integrations. |
| `docex/processors/rag/rag_service.py` | `examples/patterns/rag/basic_rag.py` | |
| `docex/processors/rag/enhanced_rag_service.py` | `examples/patterns/rag/enhanced_rag.py` | |
| `docex/processors/rag/vector_databases.py` | `examples/patterns/rag/vector_databases.py` | Note: `vector_databases.py` here is FAISS/Pinecone; the in-core `vector/` module already provides memory + pgvector backends. |
| `docex/processors/rag/vector_db_monitor.py` | `examples/patterns/rag/vector_db_monitor.py` | |
| `docex/processors/kb/generic_kb_processor.py` | `examples/patterns/knowledge_base/generic_kb.py` | |
| `docex/services/generic_knowledge_base_service.py` | `examples/patterns/knowledge_base/kb_service.py` | |
| `docex/prompts/*.yaml` + `prompts/README.md` | `examples/integrations/_shared/prompts/` | Sample templates; users copy as starting point. |
| Chunking strategies per §1.2 | `examples/patterns/chunking/` | The advanced ones. |
| `docex/processors/pdf_invoice.py` | `examples/patterns/invoice_extraction/` | Business-domain extraction. |

`examples/` post-reorg looks like (see §4 for full layout):

```text
examples/
  basic/
  integrations/
    openai/
    anthropic/
    local_llm/
    _shared/
  patterns/
    rag/
    knowledge_base/
    chunking/
    invoice_extraction/
  transport/
```

### 1.4 DELETE

- `docex/docbasket.py.backup` — committed backup.
- `FILES_TO_MERGE.txt` — December 2025 staging artifact.
- `.DS_Store` files at top level and any committed deeper.
- `build/` directory (committed despite `.gitignore`; `git rm --cached`).
- `docex.egg-info/` (same).
- `setup.py` — "kept for compatibility" but with stale version. Modern packaging works without it. **Recommend delete** (alternative: sync version field as a test/lint check).
- `docs/LLM_ADAPTERS_GUIDE.md` — replaced by examples README.
- `docs/OPENAI_API_KEY_SETUP.md` — moves into `examples/integrations/openai/README.md`.
- `docex/services/README_GENERIC_KB_SERVICE.md` — goes with the service.
- `docex/processors/__init__.py` — keep with reduced exports if vector + format converters stay; otherwise delete.

### 1.5 NEW (additions in this release window)

- **Versioning primitives** (per `docex_2_8_7_review_for_versioning.md` §4):
  - `document_revisions` table + `DocumentRevision` model + read APIs.
  - `docex_blobs` table for content-addressed blob storage.
  - `docex_manifests` table + manifest resolver/get APIs.
  - `docex_provenance` table + forward-trace API.
  - `doc_event_subscriptions` + `doc_event_deliveries` + dispatcher.
  - New CLI subcommands: `revisions`, `manifests`, `diff`, `provenance`.
- **Docs:**
  - `docs/REVISIONS_GUIDE.md` (new)
  - `docs/MANIFESTS_GUIDE.md` (new)
  - `docs/EVENT_SUBSCRIPTIONS_GUIDE.md` (new)
  - `docs/INTEGRATION_PATTERNS.md` (new — index into `examples/integrations/` and `examples/patterns/`)
  - `docs/MIGRATION_3_0.md` (new — what changed for 2.x users)
- **Tests:**
  - Vector tests stay; rewire to use a test-time stub `embedding_fn` (no openai dep in test path).
  - Add tests for `embedding_fn` decoupling.
  - Add tests for revisions, manifests, provenance, event subscriptions.

### 1.6 Decision required — format converters

Format converters (`pdf_to_text`, `word_to_text`, `csv_to_json`, `mapper`) are not LLM-dependent but are extraction-shaped. Two options:

**(a) Keep as a thin "normalize" capability in core.** Argument: if a user stores a PDF and indexes it with vectors, they need text extraction to feed embeddings. Without thin converters in core, every user has to bring their own PDF→text stack. With vector indexing now staying in core, this argument is stronger.

**(b) Move all of `processors/` to examples.** Cleanest line: docex stores blobs and metadata; *anything* that turns blob → derived content lives in fabric or in the user's code.

**Recommendation: (a)** — keep `pdf_to_text`, `word_to_text`, `csv_to_json`, `mapper` in core, move `pdf_invoice` (business logic) to examples. Reasons:
- Vector indexing in core needs a text source; thin converters complete that story.
- `python-docx` and `pdfminer.six` are already optional extras (`[pdf]`); adding `[docx]` keeps base install lightweight.
- These converters are widely-used, well-tested infrastructure (327-line test for `word_to_text` exists), not bleeding-edge.

If you disagree, the plan adapts trivially (move one more directory to examples; drop `[pdf]` extra; drop `python-docx` from core).

---

## 2. Architectural pivot — `embedding_fn` decoupling

This is the key code change that lets vector stay while LLM goes.

### 2.1 Current shape

```python
# docex/processors/vector/vector_indexing_processor.py (current)
class VectorIndexingProcessor:
    def __init__(self, config: dict):
        self.llm_adapter = config['llm_adapter']        # tight coupling
        self.vector_db_type = config['vector_db_type']
        ...
    
    async def process(self, document):
        text = document.raw_content
        embedding = await self.llm_adapter.generate_embedding(text)
        ...
```

This forces the user to instantiate an `OpenAIAdapter` (or similar) before they can index anything, dragging `openai` into the dep tree.

### 2.2 Target shape

```python
# docex/processors/vector/vector_indexing_processor.py (target)
from typing import Callable, List, Awaitable, Union

EmbeddingFn = Callable[[str], Union[List[float], Awaitable[List[float]]]]

class VectorIndexingProcessor:
    def __init__(
        self,
        embedding_fn: EmbeddingFn,
        vector_db_type: str = 'memory',
        vector_db_config: dict | None = None,
        chunking_strategy: str | None = None,    # name of a kept strategy
    ):
        self.embedding_fn = embedding_fn
        ...
    
    async def process(self, document):
        text = document.raw_content
        embedding = await _maybe_await(self.embedding_fn(text))
        ...
```

`embedding_fn` is duck-typed: any sync or async callable that takes a string and returns a list of floats. No imports from `processors/llm`. No `openai` in the dependency tree.

`SemanticSearchService` gets the same treatment — it needs an embedding for the query text; it accepts `embedding_fn`.

### 2.3 What users do

```python
# Option A: bring-your-own embedder (most common)
from openai import OpenAI
oai = OpenAI()

def my_embed(text: str) -> list[float]:
    return oai.embeddings.create(
        input=text, model="text-embedding-3-small"
    ).data[0].embedding

vp = VectorIndexingProcessor(embedding_fn=my_embed, vector_db_type='pgvector', ...)

# Option B: use the example adapter
from examples.integrations.openai.llm_adapter import OpenAIAdapter
adapter = OpenAIAdapter(api_key=..., embedding_model="text-embedding-3-small")
vp = VectorIndexingProcessor(embedding_fn=adapter.embed, ...)

# Option C: local model (sentence-transformers, etc.)
from sentence_transformers import SentenceTransformer
st = SentenceTransformer("all-MiniLM-L6-v2")
vp = VectorIndexingProcessor(embedding_fn=lambda t: st.encode(t).tolist(), ...)
```

### 2.4 Backwards compat shim

For one minor release (3.0.x), keep an optional `llm_adapter` kwarg that wraps the adapter into `embedding_fn`:

```python
def __init__(
    self,
    embedding_fn: EmbeddingFn | None = None,
    llm_adapter=None,                   # deprecated; warns
    ...
):
    if llm_adapter is not None:
        warnings.warn(
            "llm_adapter is deprecated; pass embedding_fn=adapter.embed instead. "
            "Will be removed in docex 3.1.",
            DeprecationWarning, stacklevel=2,
        )
        embedding_fn = llm_adapter.generate_embedding
    if embedding_fn is None:
        raise ValueError("embedding_fn is required")
    ...
```

Drop the shim in 3.1.

---

## 3. Dependency story — final state

### 3.1 Core `pyproject.toml` deps (after cleanup)

```toml
dependencies = [
    "sqlalchemy>=2.0.0",
    "pyyaml>=6.0.0",
    "pydantic>=2.0.0",
    "python-dotenv>=1.0.0",
    "click>=8.0.0",
]
```

Removed from core:
- `jinja2` — used only by prompts (now in examples).
- `python-docx` — moves to a `[docx]` extra (or stays if format converters stay per §1.6).

### 3.2 Optional extras (after cleanup)

```toml
[project.optional-dependencies]
postgres = ["psycopg2-binary>=2.9.0"]

# Vector indexing — kept in core, optional because of numpy/pgvector size
vector = [
    "numpy>=1.24.0",
    "pgvector>=0.2.0",
]

storage-s3 = ["boto3>=1.26.0"]

transport-http = ["aiohttp>=3.9.0"]
transport-sftp = ["paramiko>=3.4.0"]

# Format converters (per §1.6 recommendation: keep)
pdf = ["pdfminer.six>=20221105"]
docx = ["python-docx>=1.0.0"]

# Convenience: everything for vector + storage + transport
all = [
    "psycopg2-binary>=2.9.0",
    "numpy>=1.24.0",
    "pgvector>=0.2.0",
    "boto3>=1.26.0",
    "aiohttp>=3.9.0",
    "paramiko>=3.4.0",
    "pdfminer.six>=20221105",
    "python-docx>=1.0.0",
]

dev = [
    "pytest>=7.0.0",
    "moto>=4.0.0",
    "black>=22.0.0",
    "isort>=5.0.0",
    "mypy>=0.900",
    "ruff>=0.11.0",
]
```

Removed extras:
- `[llm]` (`openai`).
- Dropped from optional set entirely (never officially supported, but were in `requirements.txt`): `anthropic`, `faiss-cpu`, `pinecone-client`.

### 3.3 `requirements.txt`

**Delete it.** It's been the source of dependency drift bugs (declaring deps that aren't even in `pyproject.toml`). Modern Python packaging makes it redundant. Update CI and contributor docs to use `pip install -e ".[all,dev]"`.

If you really want a `requirements.txt` for non-package consumers, generate it via `pip-compile` from `pyproject.toml` and document that it's auto-generated (do-not-edit-by-hand banner).

---

## 4. Examples reorganization

### 4.1 Current state (24 scripts, mostly flat)

Most live at `examples/` root. 19 of 24 touch LLM/RAG/Vector. A `custom_processors/` subfolder exists; `sample_data/` exists.

### 4.2 Target layout

```text
examples/
  README.md                              # index into the structure
  basic/
    hello_world.py                       # minimal docex usage
    basic_usage.py                       # basket + add + metadata
    multi_tenancy.py                     # was test_multi_tenancy.py
    find_document_by_metadata.py         # was test_find_document_by_metadata.py
    notes.py                             # if it adds value; otherwise drop
  vector/
    README.md
    in_memory_search.py                  # uses memory backend with stub embedder
    pgvector_search.py                   # uses pgvector backend with stub embedder
    semantic_search_demo.py              # was vector_search_example.py
  transport/
    file_transfer.py                     # was route_file_transfer.py
    route_management.py                  # was route_management.py
  integrations/
    README.md                            # explains the integration pattern
    _shared/
      base_llm_processor.py              # was processors/llm/base_llm_processor.py
      prompts/
        invoice_extraction.yaml
        product_extraction.yaml
        document_summary.yaml
        generic_extraction.yaml
        README.md
    openai/
      README.md                          # how to use; absorbs OPENAI_API_KEY_SETUP.md
      llm_adapter.py                     # was processors/llm/openai_adapter.py
      embedder.py                        # tiny: def embed(text)->List[float]
      vector_search_demo.py              # docex + openai embedder + vector
      basic_extraction.py                # was llm_adapter_usage.py
    anthropic/
      README.md
      llm_adapter.py                     # was processors/llm/claude_service.py
      basic_extraction.py                # was test_claude_adapter.py (rewritten as demo)
    local_llm/
      README.md
      llm_adapter.py                     # was processors/llm/local_llm_adapter.py
      embedder.py
      demo.py
  patterns/
    README.md                            # explains: these are reference orchestrations
    rag/
      README.md
      basic_rag.py                       # was rag_basic_example.py + rag_service.py distilled
      enhanced_rag.py                    # was rag_enhanced_example.py + enhanced_rag_service.py
      vector_databases_faiss_pinecone.py # was processors/rag/vector_databases.py
      vector_db_monitor.py
    knowledge_base/
      README.md
      generic_kb.py                      # was generic_knowledge_base_service.py + kb_processor.py
      example_run.py                     # was generic_kb_example.py
    chunking/
      README.md
      semantic_chunking.py               # numpy + embeddings
      late_chunking.py
      llm_based_chunking.py
      agentic_chunking.py
      benchmark.py                       # was chunking_benchmark.py
    invoice_extraction/
      README.md
      pipeline.py                        # was processors/pdf_invoice.py + pdf_invoice_to_purchase_order.py
  custom_processors/                     # keeps current location and contents
  sample_data/                           # keeps
```

### 4.3 Examples README (root)

```markdown
# DocEX Examples

This directory contains reference code that demonstrates how to use DocEX.
Examples are NOT a maintained library — they're reviewed alongside the library
but are starting points you should adapt to your needs.

## Categories

- `basic/` — minimal end-to-end usage of DocEX core.
- `vector/` — vector indexing and semantic search using your own embedding function.
- `transport/` — using transport routes for file movement.
- `integrations/` — examples for plugging specific LLM providers (OpenAI, Anthropic,
  local models) into DocEX. **Each integration is self-contained**; copy the relevant
  folder into your project and adapt.
- `patterns/` — reference orchestrations layered on top of DocEX:
  - `rag/` — retrieval-augmented generation patterns.
  - `knowledge_base/` — generic KB service.
  - `chunking/` — advanced chunking strategies (LLM-based, embedding-based).
  - `invoice_extraction/` — domain-specific extraction example.

## Why are LLM/RAG examples not in the core library?

DocEX 3.0 repositioned itself as a pure document storage and transport layer.
LLM- and RAG-shaped capability is intentionally NOT in the core library because:

- It couples DocEX to specific providers (OpenAI, Anthropic, etc.).
- It reduces "lightweight base install" to a slogan.
- The orchestration is application-specific and benefits from being adapted, not imported.

If you want a maintained, opinionated layer on top of DocEX with LLM and business-context
capabilities, see [llamasee fabric] — that's where it lives now.
```

---

## 5. Documentation cleanup

### 5.1 Keep

- `README.md` — major rewrite (see §5.4).
- `docs/API_Reference.md` — update for new APIs, remove LLM/RAG sections.
- `docs/CLI_GUIDE.md` — remove `embed` command, add new `revisions/manifests/diff/provenance` subcommands.
- `docs/Developer_Guide.md` — review and update.
- `docs/DocBasket_Usage_Guide.md` — keep.
- `docs/MULTI_TENANCY_GUIDE.md` — keep.
- `docs/TENANT_PROVISIONING.md` — keep.
- `docs/Platform_Integration_Guide.md` — keep.
- `docs/Release_Validation_Guide.md` — keep.
- `docs/TESTING_GUIDE.md` — keep, update test coverage expectations.
- `docs/INSTALL_DEPENDENCIES.md` — keep, update for new extras.
- `docs/DOCKER_SETUP.md`, `docs/DOCUMENTATION_ORGANIZATION.md` — keep.
- `docs/AWS_CREDENTIALS_SETUP.md` — keep (storage-s3).
- `docs/VECTOR_SEARCH_GUIDE.md` — **keep**, update to reflect `embedding_fn` API.

### 5.2 Delete (capability moved to examples)

- `docs/LLM_ADAPTERS_GUIDE.md` — replaced by `examples/integrations/README.md`.
- `docs/OPENAI_API_KEY_SETUP.md` — absorbed into `examples/integrations/openai/README.md`.
- `docex/services/README_GENERIC_KB_SERVICE.md` — goes with the service.
- `docex/processors/chunking/README.md` — replaced by `examples/patterns/chunking/README.md`.
- `docex/prompts/README.md` — replaced by `examples/integrations/_shared/prompts/README.md`.

### 5.3 New

- `docs/REVISIONS_GUIDE.md` — content addressing, doc revisions, head pointer.
- `docs/MANIFESTS_GUIDE.md` — manifest format, resolver, "as_of" semantics.
- `docs/EVENT_SUBSCRIPTIONS_GUIDE.md` — subscriber/dispatch model.
- `docs/INTEGRATION_PATTERNS.md` — index of `examples/integrations/` and `examples/patterns/`, with provider matrix.
- `docs/MIGRATION_3_0.md` — what changed, how to update.
- `docs/EMBEDDING_FN_API.md` — short reference for the new contract (or fold into VECTOR_SEARCH_GUIDE).

### 5.4 README rewrite shape

Cut sections:
- "LLM-Powered Document Processing" — replace with one paragraph and link to `examples/integrations/`.
- "Available Prompts" / "Custom Prompts" — replace with link to `examples/integrations/_shared/prompts/`.

Update sections:
- Features list — remove "LLM adapter integration", "Prompt management", "Structured data extraction", "RAG support". Keep "Vector indexing & semantic search". Add: "Document revisions and manifests", "Event subscriptions".
- Quick Start — keep current basket example. Add a vector indexing example using a stub `embedding_fn`.
- Installation — update extras names; add `[docx]` if format converters stay.

Add sections:
- "Document Revisions and Manifests" — short overview with link to `docs/REVISIONS_GUIDE.md`.
- "Integrations and Patterns" — short paragraph linking to `examples/integrations/` and `examples/patterns/`.

---

## 6. Code quality fixes (independent of the cleanup)

### 6.1 `docCore.py` split

1,338 lines, 28 methods. Split into:

```text
docex/
  docCore.py             # DocEX facade, lifecycle, basket/document accessors only (~400 lines)
  config_loader.py       # _load_default_config, _safe_load_config, setup, setup_database
  setup_validator.py     # is_initialized, is_properly_setup, get_setup_errors
  routing/
    __init__.py
    api.py               # create_route, get_route, list_routes, delete_route, send_document
```

Public API unchanged. Existing call sites (e.g., `docex.create_route(...)`) still work via thin facade methods on `DocEX`. Internally those delegate to `routing/api.py`.

### 6.2 `cli.py` split

1,254 lines. Split into:

```text
docex/cli/
  __init__.py
  main.py            # cli group entry, shared options
  init_cmd.py        # init
  tenant_cmd.py      # tenant create/list
  routing_cmd.py     # NEW: route create/list/delete/send (move from main file)
  revisions_cmd.py   # NEW: revisions, manifests, diff, provenance
```

Removed:
- `embed` command — was LLM-coupled.
- `processor` group — review whether it survives. With most processors gone, it's unclear what's left to register/list. Recommend remove with one-release deprecation warning.

### 6.3 Version sync

- Single source: `pyproject.toml` `[project] version`.
- `docex/__init__.py` reads `__version__ = importlib.metadata.version("docex")`.
- Delete `setup.py` entirely.
- README version banner removed (replace with link to RELEASE_NOTES).
- CI lint: a tiny test that checks `__version__` matches pyproject.

### 6.4 Singleton + multi-tenancy fragility

Acknowledged in 2.8.0 release notes ("Fixed `DocEX` singleton tenant switching"). The current rule "must call `close()` before switching tenants" is a footgun.

For 3.0, two viable paths:

- **Path A:** Drop the singleton entirely. `DocEX(user_context=...)` returns a regular instance. Each tenant uses its own instance. Migration: callers that today rely on the singleton import a singleton helper (which they own), or refactor.
- **Path B:** Keep the singleton but isolate state per-tenant. Internal `dict[tenant_id → state]` keyed by `UserContext.tenant_id`. Class-level singleton stays but per-tenant data doesn't collide.

Recommend **Path A** for 3.0 — clean, predictable, explicit. Document the migration as part of `MIGRATION_3_0.md`. This is the larger of the code quality fixes; if scope is tight, defer to 3.1.

### 6.5 Hygiene

- Delete `docex/docbasket.py.backup`, `FILES_TO_MERGE.txt`, `.DS_Store` files.
- `git rm --cached` on `build/`, `docex.egg-info/`.
- `setup.py` deletion (per §6.3).

---

## 7. Versioning primitives addition (per the prior addendum)

Per `docex_2_8_7_review_for_versioning.md` §4, add:

- Migration `004_add_document_revisions.sql` + `DocumentRevision` model + APIs.
- Migration `005_add_blobs.sql` + `docex_blobs` storage abstraction.
- Switch write path to mint revisions on every `basket.add()` and metadata update.
- Migration `006_add_manifests.sql` + manifest resolver/get APIs.
- Migration `007_add_provenance.sql` + provenance writer.
- Manifest + revision diff API.
- Migration `008_extend_doc_events_for_subscriptions.sql` + subscriber dispatch.
- New CLI subcommands.
- New docs (per §5.3).

This is additive; no breaking change. Lands as `3.1.0` after the 3.0 cleanup ships.

---

## 8. Release sequence

Each PR is independently reviewable and shippable.

| # | PR | Outcome | Version |
|---|---|---|---|
| 1 | Repository hygiene: delete dead files, sync versions, delete `setup.py`, fix `requirements.txt` (delete it). | Clean tree, single version source, no dependency drift. | 2.8.8 |
| 2 | Decouple `VectorIndexingProcessor` and `SemanticSearchService` from LLM adapters: introduce `embedding_fn` parameter with deprecation shim for `llm_adapter`. Tests updated to use stub embedder. | Vector module no longer imports `processors/llm`. `[llm]` extra still exists but unused by core. | 2.9.0 |
| 3 | Move `processors/llm/`, `processors/rag/`, `processors/kb/`, `services/generic_knowledge_base_service.py`, `prompts/` to `examples/`. Reorganize `examples/` per §4.2. Move LLM-dependent chunking strategies. Drop `[llm]` extra. Update README, delete `docs/LLM_ADAPTERS_GUIDE.md` and `docs/OPENAI_API_KEY_SETUP.md`. | docex core no longer ships LLM/RAG/KB code. Examples carry the integration patterns. | 3.0.0-rc1 |
| 4 | Resolve §1.6 format-converter decision. If keeping (recommended): add `[docx]` extra, finalize `[pdf]`. If removing: move to examples too. Move `pdf_invoice` regardless. | Format converter line is decided. | 3.0.0-rc2 |
| 5 | Refactor `docCore.py` and `cli.py` per §6.1 and §6.2. Remove `embed` command and `processor` CLI group (or warn). | God objects split; CLI surface aligned with new scope. | 3.0.0-rc3 |
| 6 | Drop `embedding_fn` deprecation shim. (Optional: address §6.4 singleton if scope permits.) | Final 3.0 surface. | 3.0.0 |
| 7 | Add versioning primitives: revision model, blobs, manifests, provenance, subscriptions. New CLI subcommands. New docs. | Versioning addendum delivered. | 3.1.0 |
| 8 | (Optional / later) Singleton refactor if not done in PR 6. Transport scope decision. | | 3.2.0 |

Total: 6 PRs to land 3.0.0, 7 to land 3.1.0 with versioning.

Approximate effort: PR 1 is a day. PRs 2 and 5 are small refactors (1-2 days each). PR 3 is the biggest (the move + reorg, ~3-5 days). PR 4 is small. PR 7 is the largest absolute work but doesn't gate 3.0 — can be done by a different person in parallel.

---

## 9. Backwards compatibility and migration guide

### 9.1 Strategy

Hard cut at 3.0 for everything except the `embedding_fn` decoupling:

- **`embedding_fn` decoupling:** lands in 2.9.0 with the `llm_adapter` deprecation shim. Shim kept through 3.0.x. Removed in 3.1.
- **Module removals (LLM/RAG/KB/prompts):** hard at 3.0.0. Imports raise `ModuleNotFoundError` with a helpful message (use a thin `_legacy.py` or rely on `ImportError` from missing module).
- **API changes:** documented in `MIGRATION_3_0.md`.

The argument for hard cuts on the module removals: docex is yours, the only known consumer (LlamaSeeBI v2) hasn't yet adopted, and a stub-and-warn for one release adds work without buying much. If there are real external users, switch to stub-and-warn for one release.

### 9.2 `MIGRATION_3_0.md` outline

```markdown
# Migrating from docex 2.x to docex 3.0

## Summary

DocEX 3.0 repositions as a pure document storage layer with vector indexing.
LLM adapters, RAG, and the generic knowledge base service have moved to
`examples/` as reference integrations. Vector indexing stays in core but
no longer imports LLM adapters.

## Breaking changes

### 1. `processors/llm/` removed

Before:
    from docex.processors.llm import OpenAIAdapter

After:
    # Option A: use the example integration
    from examples.integrations.openai.llm_adapter import OpenAIAdapter

    # Option B: write your own thin adapter
    # See examples/integrations/_shared/base_llm_processor.py

### 2. `VectorIndexingProcessor` API changed

Before:
    vp = VectorIndexingProcessor({'llm_adapter': adapter, 'vector_db_type': 'memory'})

After:
    vp = VectorIndexingProcessor(embedding_fn=adapter.embed, vector_db_type='memory')

(In 2.9.x and 3.0.x, both forms work; `llm_adapter` warns.)

### 3. `processors/rag/` and `processors/kb/` removed

Before:
    from docex.processors.rag.enhanced_rag_service import EnhancedRAGService

After:
    # See examples/patterns/rag/enhanced_rag.py for a reference implementation.

### 4. Generic KB service removed

Before:
    from docex.services.generic_knowledge_base_service import GenericKnowledgeBaseService

After:
    # See examples/patterns/knowledge_base/kb_service.py

### 5. Prompts removed

Before:
    OpenAIAdapter({..., 'prompt_name': 'invoice_extraction'})

After:
    # Prompts moved to examples/integrations/_shared/prompts/. Copy what you
    # need into your project; the registry was removed.

### 6. Optional `[llm]` extra removed

Before:
    pip install docex[llm]

After:
    # No longer applicable. Install your LLM provider directly.
    pip install openai  # or anthropic, etc.

### 7. `setup.py` removed

If your install relied on `python setup.py install`, switch to `pip install .`.

### 8. (If singleton change ships) `DocEX` is no longer a singleton

Before:
    docex1 = DocEX(); docex2 = DocEX()  # same instance

After:
    docex = DocEX(user_context=ctx)
    # If you need a singleton in your app, manage it yourself.

## Non-breaking changes

- Document revisions, manifests, provenance, and event subscriptions are NEW.
  Existing code continues to work; head reads return the head revision transparently.
- `pyproject.toml` is the canonical version source; `__version__` resolved at runtime.
- `requirements.txt` was removed; use `pip install -e ".[all,dev]"`.
```

### 9.3 Compatibility tests

Tests in `tests/migration/` that verify the 2.x→3.0 migration paths documented above:

- `test_vector_indexing_legacy_kwarg.py` — verifies the deprecation shim works in 2.9 and 3.0.x and is removed in 3.1.
- `test_imports_raise_helpful_errors.py` — verifies `from docex.processors.llm import OpenAIAdapter` raises a clear error pointing to examples.

---

## 10. Test plan

### 10.1 Test coverage shifts

Before (35 test files):
- 7 LLM/RAG/Vector/KB tests + chunking tests in core tree.

After 3.0:
- Vector tests stay; rewired to use a stub `embedding_fn` (no openai dependency).
- LLM/RAG/KB tests move to `examples/` as runnable demos with their own assertions, OR are removed (since examples aren't covered by docex CI).
- New tests for `embedding_fn` decoupling.
- New tests for revisions/manifests/provenance/subscriptions (in 3.1.x cycle).

### 10.2 CI matrix update

```yaml
# Approximate CI matrix
- python: [3.11, 3.12]
- extras:
    - "minimal"           # base install only
    - "[postgres]"        # core + postgres
    - "[vector]"          # core + vector (numpy + pgvector)
    - "[storage-s3]"      # core + S3
    - "[transport-http,transport-sftp]"
    - "[pdf,docx]"        # format converters
    - "[all,dev]"         # everything
```

The `minimal` row catches the regression where someone accidentally adds a heavy import to core. Today this would fail because `processors/vector/` imports numpy unconditionally — after 3.0, the vector module imports stay lazy or scoped.

---

## 11. Out-of-scope-but-flag

### 11.1 Transport scope

`docex/transport/` is 12 files (~1500-2000 lines). README leads with "document management AND transport." In the new positioning, transport is arguably a sibling concern to storage — could become `docex-transport` later. Not urgent. Decide before 4.0.

### 11.2 `processor` CLI group future

If `processors/` shrinks to just `vector/` + format converters, the `processor register/remove/list` CLI commands have little to do. Either drop, or repurpose for plugin registration if a plugin model emerges.

### 11.3 `models.py` deduplication

Multiple modules named `models.py`: `db/models.py`, `transport/models.py`, `models/` package. Worth a one-time rename pass to make the package boundary explicit (e.g., `db/orm.py`, `transport/schema.py`, `models/records.py`).

### 11.4 Pydantic vs SQLAlchemy boundary

Quick audit recommended to ensure each is used for its strength (Pydantic for request/response/config validation; SQLAlchemy for persistence) and not duplicating the other.

---

## 12. Open questions (now narrow)

1. **§1.6 format converter decision.** Recommendation: keep `pdf_to_text`, `word_to_text`, `csv_to_json`, `mapper` in core. Move `pdf_invoice` to examples. Confirm?
2. **§9.1 deprecation strategy.** Hard cut at 3.0 for module removals; deprecation shim only for the `llm_adapter` → `embedding_fn` change. Confirm? Or do you have external users that justify a stub-and-warn for the module removals too?
3. **§6.4 singleton path.** Recommendation: Path A (drop the singleton) in 3.0. If timing is tight, defer to 3.2. Confirm?
4. **§11.1 transport scope.** Stays in 3.x, with a 4.0 decision deferred. Confirm?
5. **`processor` CLI group fate.** Drop in 3.0 with a deprecation warning, or keep as a no-op for plugins? Lean toward drop.
6. **Naming.** Console script entrypoint is currently `DocEX = "docex.cli:cli"` (capital command name). Recommend lowercase `docex` to match Unix conventions and the package name. Confirm?

---

## 13. Definition of done for 3.0.0

- [ ] All LLM/RAG/KB code removed from `docex/` package tree.
- [ ] Vector module decoupled from LLM adapters via `embedding_fn`.
- [ ] `examples/` reorganized into `basic/`, `vector/`, `transport/`, `integrations/`, `patterns/`, `custom_processors/`, `sample_data/`.
- [ ] `requirements.txt` deleted.
- [ ] `setup.py` deleted.
- [ ] Single version source via `importlib.metadata`.
- [ ] Dead files removed (`.backup`, `FILES_TO_MERGE.txt`, `.DS_Store`, committed `build/`, committed `egg-info/`).
- [ ] `docCore.py` and `cli.py` split per §6.1 / §6.2.
- [ ] CLI: `embed` command removed; `processor` group resolved per §12.5.
- [ ] README rewritten per §5.4.
- [ ] `MIGRATION_3_0.md` written and reviewed.
- [ ] CI matrix updated per §10.2.
- [ ] Singleton: either Path A landed, or explicitly deferred with a 3.2 ticket.
- [ ] No `import openai` or `from openai` anywhere in `docex/` package.
- [ ] No `import numpy` outside `docex/processors/vector/` (or wherever vector lives).

## 14. Definition of done for 3.1.0 (versioning)

- [ ] Migrations 004–008 land.
- [ ] `DocumentRevision` model + APIs + tests.
- [ ] Manifest format published in `docs/MANIFESTS_GUIDE.md`.
- [ ] Manifest resolver idempotent for fixed `as_of`.
- [ ] Provenance forward-trace works end-to-end.
- [ ] Event subscription dispatcher delivers reliably under restart.
- [ ] CLI subcommands (`revisions`, `manifests`, `diff`, `provenance`) ship.
- [ ] LlamaSeeBI/fabric integration plan validated against the new docex 3.1 surface.

---

## 15. Summary

docex 3.0 is the cleanup release: vector indexing stays as a first-class core capability (decoupled from any specific LLM provider via `embedding_fn`), LLM/RAG/KB/prompt code moves to `examples/` as integration patterns, and pre-existing hygiene bugs (version drift, `requirements.txt` chaos, god-object source files, dead committed files) are fixed in the same window. The result is a lean, focused storage + vector layer that earns the "lightweight, developer-friendly document management" tagline the README already claims.

docex 3.1 lands the versioning primitives (revisions, manifests, provenance, event subscriptions) that the LlamaSee Business Context Layer's auditability promise depends on. After 3.1, the boundary between docex and llamasee fabric is clean: docex provides storage + vector + revisions; fabric provides annotations, control files, compile snapshots, and strategy pinning.

Six narrow open questions remain (§12). Once they're answered, the release sequence in §8 can begin with PR 1 immediately — it's pure hygiene work with no design dependencies.

---

*Five docs are now in the LlamaSeeBI folder:*

1. `llamasee_business_context_layer_versioning.md` — original VC addendum (will need v2 to incorporate findings).
2. `llamasee_business_context_layer_versioning_review.md` — LlamaSeeBI-side review.
3. `docex_2_8_7_review_for_versioning.md` — docex review focused on versioning gap.
4. `docex_2_8_7_cleanup_review.md` — first cleanup review (now superseded by this doc).
5. `docex_3_0_full_plan.md` — this document; the consolidated 3.0/3.1 plan.
