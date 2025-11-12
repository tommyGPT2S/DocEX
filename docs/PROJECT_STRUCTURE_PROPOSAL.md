# Project Structure Proposal: Customer Engagement Platform

## Overview

This document proposes a new project structure for building a **Customer Engagement Platform with LLM-Powered Knowledge Base** that uses **DocEX as a library dependency**.

---

## Project Name Suggestions

- `docex-engagement` - Customer engagement platform built on DocEX
- `docex-kb` - Knowledge base platform built on DocEX
- `docex-ai` - AI-powered document platform built on DocEX
- `engagement-platform` - Generic customer engagement platform
- `customer-engagement-platform` - Full name

**Recommended:** `docex-engagement` or `docex-kb`

---

## Proposed Project Structure

```
customer-engagement-platform/
├── README.md                          # Project overview and quick start
├── LICENSE                            # MIT License (or your choice)
├── pyproject.toml                     # Project configuration and dependencies
├── requirements.txt                   # Python dependencies
├── requirements-dev.txt               # Development dependencies
├── .env.example                       # Example environment variables
├── .gitignore                         # Git ignore patterns
├── .pre-commit-config.yaml            # Pre-commit hooks
├── CONTRIBUTING.md                    # Contribution guidelines
├── CODE_OF_CONDUCT.md                 # Code of conduct
├── SECURITY.md                        # Security policy
│
├── src/                               # Source code
│   └── engagement/                    # Main package
│       ├── __init__.py
│       ├── config.py                  # Configuration management
│       ├── app.py                     # Main application entry point
│       │
│       ├── processors/                # DocEX processors
│       │   ├── __init__.py
│       │   ├── base.py                # Base processor utilities
│       │   │
│       │   ├── llm/                   # LLM adapters
│       │   │   ├── __init__.py
│       │   │   ├── base_llm_adapter.py
│       │   │   ├── openai_adapter.py
│       │   │   ├── anthropic_adapter.py
│       │   │   └── local_llm_adapter.py
│       │   │
│       │   ├── vector/                # Vector indexing processors
│       │   │   ├── __init__.py
│       │   │   ├── vector_indexing_processor.py
│       │   │   └── pgvector_setup.py
│       │   │
│       │   ├── rag/                   # RAG processors
│       │   │   ├── __init__.py
│       │   │   └── rag_query_processor.py
│       │   │
│       │   └── engagement/           # Customer engagement processors
│       │       ├── __init__.py
│       │       ├── meeting_transcript_processor.py
│       │       ├── email_processor.py
│       │       └── document_processor.py
│       │
│       ├── services/                  # Business logic services
│       │   ├── __init__.py
│       │   ├── semantic_search.py     # Semantic search service
│       │   ├── knowledge_base.py      # Knowledge base service
│       │   ├── engagement.py          # Customer engagement service
│       │   └── analytics.py          # Analytics service
│       │
│       ├── api/                       # API layer (optional)
│       │   ├── __init__.py
│       │   ├── rest/                  # REST API
│       │   │   ├── __init__.py
│       │   │   ├── app.py
│       │   │   ├── routes/
│       │   │   │   ├── __init__.py
│       │   │   │   ├── documents.py
│       │   │   │   ├── search.py
│       │   │   │   ├── knowledge_base.py
│       │   │   │   └── engagement.py
│       │   │   └── models/            # Pydantic models
│       │   │       ├── __init__.py
│       │   │       ├── document.py
│       │   │       ├── search.py
│       │   │       └── query.py
│       │   │
│       │   └── graphql/                # GraphQL API (optional)
│       │       ├── __init__.py
│       │       ├── schema.py
│       │       └── resolvers.py
│       │
│       ├── models/                    # Data models
│       │   ├── __init__.py
│       │   ├── engagement.py          # Engagement models
│       │   ├── customer.py            # Customer models
│       │   └── metadata.py            # Metadata extensions
│       │
│       └── utils/                     # Utilities
│           ├── __init__.py
│           ├── text_chunking.py       # Text chunking utilities
│           ├── embeddings.py          # Embedding utilities
│           └── helpers.py             # General helpers
│
├── tests/                             # Tests
│   ├── __init__.py
│   ├── conftest.py                    # Pytest configuration
│   │
│   ├── unit/                          # Unit tests
│   │   ├── __init__.py
│   │   ├── test_processors/
│   │   │   ├── test_llm_adapters.py
│   │   │   ├── test_vector_indexing.py
│   │   │   └── test_rag_processor.py
│   │   ├── test_services/
│   │   │   ├── test_semantic_search.py
│   │   │   └── test_knowledge_base.py
│   │   └── test_utils/
│   │       └── test_text_chunking.py
│   │
│   ├── integration/                  # Integration tests
│   │   ├── __init__.py
│   │   ├── test_llm_integration.py
│   │   ├── test_vector_integration.py
│   │   └── test_rag_integration.py
│   │
│   └── fixtures/                     # Test fixtures
│       ├── sample_documents/
│       └── test_data.py
│
├── examples/                          # Example code
│   ├── basic_usage.py                 # Basic usage example
│   ├── llm_processing.py              # LLM processing example
│   ├── vector_indexing.py             # Vector indexing example
│   ├── semantic_search.py             # Semantic search example
│   ├── rag_query.py                   # RAG query example
│   └── customer_engagement.py          # Customer engagement example
│
├── docs/                              # Documentation
│   ├── README.md                      # Documentation index
│   ├── installation.md                # Installation guide
│   ├── configuration.md               # Configuration guide
│   ├── processors/                    # Processor documentation
│   │   ├── llm_adapters.md
│   │   ├── vector_indexing.md
│   │   └── rag_processing.md
│   ├── services/                      # Service documentation
│   │   ├── semantic_search.md
│   │   └── knowledge_base.md
│   ├── api/                           # API documentation
│   │   ├── rest_api.md
│   │   └── graphql_api.md
│   └── deployment.md                  # Deployment guide
│
├── scripts/                           # Utility scripts
│   ├── setup_db.py                    # Database setup script
│   ├── setup_pgvector.py              # pgvector setup script
│   ├── migrate.py                     # Migration script
│   └── seed_data.py                   # Seed test data
│
├── migrations/                        # Database migrations (if needed)
│   └── alembic/                       # Alembic migrations
│       ├── versions/
│       └── env.py
│
├── docker/                            # Docker files
│   ├── Dockerfile
│   ├── docker-compose.yml
│   └── docker-compose.dev.yml
│
└── .github/                           # GitHub workflows
    ├── workflows/
    │   ├── ci.yml                     # CI/CD pipeline
    │   ├── test.yml                   # Test workflow
    │   └── release.yml                # Release workflow
    └── ISSUE_TEMPLATE/
        ├── bug_report.md
        └── feature_request.md
```

---

## Key Files Explained

### 1. `pyproject.toml` - Project Configuration

```toml
[build-system]
requires = ["setuptools>=42", "wheel"]
build-backend = "setuptools.build_meta"

[project]
name = "docex-engagement"
version = "0.1.0"
description = "Customer Engagement Platform with LLM-Powered Knowledge Base built on DocEX"
readme = "README.md"
authors = [{ name = "Your Name", email = "your.email@example.com" }]
license = { file = "LICENSE" }
classifiers = [
    "Programming Language :: Python :: 3",
    "License :: OSI Approved :: MIT License",
    "Operating System :: OS Independent",
]
requires-python = ">=3.11"
dependencies = [
    "docex>=2.0.0",                    # DocEX as library dependency
    "openai>=1.0.0",                   # OpenAI SDK
    "anthropic>=0.18.0",               # Anthropic SDK
    "pgvector>=0.2.0",                 # pgvector for PostgreSQL
    "sqlalchemy>=2.0.0",               # SQLAlchemy (for pgvector)
    "fastapi>=0.104.0",                # FastAPI for REST API (optional)
    "uvicorn>=0.24.0",                # ASGI server (optional)
    "pydantic>=2.0.0",                 # Data validation
    "python-dotenv>=1.0.0",            # Environment variables
    "click>=8.0.0",                     # CLI
]

[project.optional-dependencies]
dev = [
    "pytest>=7.0.0",
    "pytest-asyncio>=0.21.0",
    "pytest-cov>=4.1.0",
    "black>=23.0.0",
    "isort>=5.12.0",
    "mypy>=1.7.0",
    "ruff>=0.1.0",
]
llm = [
    "openai>=1.0.0",
    "anthropic>=0.18.0",
]
api = [
    "fastapi>=0.104.0",
    "uvicorn>=0.24.0",
    "graphql-core>=3.2.0",             # For GraphQL (optional)
]

[project.scripts]
engagement = "engagement.app:main"

[tool.setuptools]
packages = { find = { where = ["src"] } }

[tool.black]
line-length = 88
target-version = ['py311']

[tool.isort]
profile = "black"
line_length = 88

[tool.mypy]
python_version = "3.11"
warn_return_any = true
warn_unused_configs = true
disallow_untyped_defs = true

[tool.pytest.ini_options]
testpaths = ["tests"]
python_files = ["test_*.py"]
python_classes = ["Test*"]
python_functions = ["test_*"]
addopts = "-v --cov=engagement --cov-report=html --cov-report=term"
```

### 2. `requirements.txt` - Dependencies

```txt
# Core dependencies
docex>=2.0.0
pgvector>=0.2.0
sqlalchemy>=2.0.0

# LLM providers
openai>=1.0.0
anthropic>=0.18.0

# API (optional)
fastapi>=0.104.0
uvicorn>=0.24.0

# Utilities
pydantic>=2.0.0
python-dotenv>=1.0.0
click>=8.0.0
```

### 3. `src/engagement/__init__.py` - Package Entry Point

```python
"""
Customer Engagement Platform with LLM-Powered Knowledge Base

Built on top of DocEX for document management and processing.
"""

__version__ = "0.1.0"

from docex import DocEX

# Re-export commonly used classes
from .config import Config
from .app import EngagementApp

__all__ = [
    "DocEX",
    "Config",
    "EngagementApp",
]
```

### 4. `src/engagement/config.py` - Configuration

```python
"""Configuration management for the engagement platform"""

import os
from pathlib import Path
from typing import Dict, Any, Optional
from pydantic import BaseModel, Field
from dotenv import load_dotenv

# Load environment variables
load_dotenv()


class LLMConfig(BaseModel):
    """LLM provider configuration"""
    provider: str = Field(default="openai", description="LLM provider")
    model: str = Field(default="gpt-4", description="Model name")
    api_key: Optional[str] = Field(default=None, description="API key")
    temperature: float = Field(default=0.7, description="Temperature")
    max_tokens: int = Field(default=1000, description="Max tokens")


class VectorConfig(BaseModel):
    """Vector database configuration"""
    use_pgvector: bool = Field(default=True, description="Use pgvector")
    embedding_dim: int = Field(default=1536, description="Embedding dimension")
    index_type: str = Field(default="ivfflat", description="Index type")
    index_lists: int = Field(default=100, description="Index lists")


class Config(BaseModel):
    """Main configuration"""
    # DocEX configuration
    docex_config_path: Optional[Path] = Field(
        default=None,
        description="Path to DocEX config file"
    )
    
    # LLM configuration
    llm: LLMConfig = Field(default_factory=LLMConfig)
    
    # Vector configuration
    vector: VectorConfig = Field(default_factory=VectorConfig)
    
    # Database configuration
    database_url: Optional[str] = Field(
        default=None,
        description="Database URL (overrides DocEX config)"
    )
    
    @classmethod
    def from_env(cls) -> "Config":
        """Load configuration from environment variables"""
        return cls(
            docex_config_path=os.getenv("DOCEX_CONFIG_PATH"),
            llm=LLMConfig(
                provider=os.getenv("LLM_PROVIDER", "openai"),
                model=os.getenv("LLM_MODEL", "gpt-4"),
                api_key=os.getenv("OPENAI_API_KEY") or os.getenv("ANTHROPIC_API_KEY"),
                temperature=float(os.getenv("LLM_TEMPERATURE", "0.7")),
                max_tokens=int(os.getenv("LLM_MAX_TOKENS", "1000")),
            ),
            vector=VectorConfig(
                use_pgvector=os.getenv("USE_PGVECTOR", "true").lower() == "true",
                embedding_dim=int(os.getenv("EMBEDDING_DIM", "1536")),
                index_type=os.getenv("INDEX_TYPE", "ivfflat"),
                index_lists=int(os.getenv("INDEX_LISTS", "100")),
            ),
            database_url=os.getenv("DATABASE_URL"),
        )
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert configuration to dictionary"""
        return self.model_dump()
```

### 5. `src/engagement/app.py` - Main Application

```python
"""Main application entry point"""

import logging
from typing import Optional
from docex import DocEX
from .config import Config
from .processors.llm import OpenAIAdapter
from .processors.vector import VectorIndexingProcessor
from .services.semantic_search import SemanticSearchService

logger = logging.getLogger(__name__)


class EngagementApp:
    """Main application class for customer engagement platform"""
    
    def __init__(self, config: Optional[Config] = None):
        """
        Initialize the engagement platform
        
        Args:
            config: Configuration instance. If None, loads from environment.
        """
        self.config = config or Config.from_env()
        self.doc_ex = DocEX()
        
        # Initialize processors
        self._initialize_processors()
        
        # Initialize services
        self._initialize_services()
    
    def _initialize_processors(self):
        """Initialize DocEX processors"""
        from docex.processors.factory import factory
        
        # Register LLM adapter
        llm_adapter = OpenAIAdapter(self.config.llm.to_dict())
        factory.register(OpenAIAdapter)
        
        # Register vector indexing processor
        vector_processor = VectorIndexingProcessor({
            **self.config.vector.to_dict(),
            **self.config.llm.to_dict(),
        })
        factory.register(VectorIndexingProcessor)
        
        logger.info("Processors initialized")
    
    def _initialize_services(self):
        """Initialize services"""
        from .processors.llm import OpenAIAdapter
        
        llm_adapter = OpenAIAdapter(self.config.llm.to_dict())
        self.semantic_search = SemanticSearchService(
            self.doc_ex,
            llm_adapter
        )
        
        logger.info("Services initialized")
    
    def process_document(self, document_path: str, basket_name: str = "default"):
        """
        Process a document through the engagement platform
        
        Args:
            document_path: Path to document
            basket_name: Basket name
            
        Returns:
            Processed document
        """
        # Get or create basket
        basket = self.doc_ex.basket(basket_name)
        
        # Add document
        doc = basket.add(document_path)
        
        # Process with vector indexing
        from docex.processors.factory import factory
        processor = factory.get_processor("VectorIndexingProcessor")
        if processor:
            result = processor.process(doc)
            logger.info(f"Document processed: {result.success}")
        
        return doc
    
    def search(self, query: str, basket_name: Optional[str] = None, top_k: int = 10):
        """
        Semantic search across documents
        
        Args:
            query: Search query
            basket_name: Optional basket name to search within
            top_k: Number of results
            
        Returns:
            List of search results
        """
        return self.semantic_search.search(query, basket_name, top_k)


def main():
    """Main entry point"""
    import sys
    
    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # Initialize app
    app = EngagementApp()
    
    # Example usage
    if len(sys.argv) > 1:
        doc = app.process_document(sys.argv[1])
        print(f"Document processed: {doc.id}")
    else:
        print("Usage: engagement <document_path>")


if __name__ == "__main__":
    main()
```

---

## Installation and Setup

### 1. Create Project

```bash
# Create project directory
mkdir customer-engagement-platform
cd customer-engagement-platform

# Initialize git
git init

# Create virtual environment
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install DocEX and dependencies
pip install docex>=2.0.0
pip install -r requirements.txt
```

### 2. Initialize DocEX

```bash
# Initialize DocEX (required before using)
docex init

# Configure DocEX (edit ~/.docex/config.yaml)
# Set up PostgreSQL with pgvector extension
```

### 3. Set Up pgvector

```bash
# Run setup script
python scripts/setup_pgvector.py

# Or manually:
# psql -U postgres -d your_database
# CREATE EXTENSION IF NOT EXISTS vector;
# ALTER TABLE documents ADD COLUMN embedding vector(1536);
# CREATE INDEX documents_embedding_idx ON documents USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100);
```

### 4. Configure Environment

```bash
# Copy example environment file
cp .env.example .env

# Edit .env with your settings
# OPENAI_API_KEY=your_key_here
# ANTHROPIC_API_KEY=your_key_here
# DATABASE_URL=postgresql://user:password@localhost:5432/database
```

---

## Usage Example

```python
from engagement import EngagementApp, Config

# Initialize app
app = EngagementApp()

# Process a document
doc = app.process_document("meeting_transcript.txt", basket_name="customer_001")

# Search documents
results = app.search("What were the action items from the meeting?", top_k=5)

# Access results
for result in results:
    print(f"Document: {result['document'].name}")
    print(f"Relevance: {result['relevance_score']}")
    print(f"Content: {result['document'].get_content(mode='text')[:200]}")
```

---

## Development Workflow

### 1. Install Development Dependencies

```bash
pip install -r requirements-dev.txt
```

### 2. Run Tests

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=engagement --cov-report=html

# Run specific test
pytest tests/unit/test_processors/test_llm_adapters.py
```

### 3. Code Quality

```bash
# Format code
black src/ tests/

# Sort imports
isort src/ tests/

# Type checking
mypy src/

# Linting
ruff check src/ tests/
```

### 4. Pre-commit Hooks

```bash
# Install pre-commit hooks
pre-commit install

# Run manually
pre-commit run --all-files
```

---

## Benefits of This Structure

### 1. **Separation of Concerns**
- ✅ DocEX is a library dependency (not part of the project)
- ✅ Clear separation between platform code and DocEX
- ✅ Easy to update DocEX independently

### 2. **Modularity**
- ✅ Processors organized by type (llm, vector, rag, engagement)
- ✅ Services separated from processors
- ✅ API layer optional and separate

### 3. **Testability**
- ✅ Unit tests for each component
- ✅ Integration tests for end-to-end workflows
- ✅ Test fixtures for reusable test data

### 4. **Scalability**
- ✅ Easy to add new processors
- ✅ Easy to add new services
- ✅ Easy to add new API endpoints

### 5. **Maintainability**
- ✅ Clear project structure
- ✅ Comprehensive documentation
- ✅ Type hints and validation

---

## Next Steps

1. **Create Project Structure**
   ```bash
   mkdir -p customer-engagement-platform/{src/engagement,tests,examples,docs,scripts}
   ```

2. **Initialize Project**
   ```bash
   cd customer-engagement-platform
   git init
   python3 -m venv venv
   source venv/bin/activate
   ```

3. **Create Core Files**
   - `pyproject.toml`
   - `requirements.txt`
   - `README.md`
   - `.env.example`

4. **Implement Core Components**
   - LLM adapters
   - Vector indexing processor
   - Semantic search service

5. **Add Tests**
   - Unit tests
   - Integration tests

6. **Documentation**
   - Installation guide
   - Usage examples
   - API documentation

---

**See Also:**
- `docs/LLM_ADAPTER_PROPOSAL.md` - LLM adapter implementation details
- `docs/VECTOR_DB_RECOMMENDATION.md` - Vector database recommendations
- `docs/CUSTOMER_ENGAGEMENT_PLATFORM_RECOMMENDATION.md` - Architecture recommendations

