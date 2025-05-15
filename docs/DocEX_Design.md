# DocEX Design Document

![DocEX Architecture](/New%20Era%20of%20Supply%20Chain/image.png)

## Overview

DocEX is a document management system that provides robust document storage, metadata management, and operations tracking. It supports multiple storage backends and database systems while maintaining a clean, extensible architecture.

## Core Components

1. **DocEX**
   - Main entry point for the system
   - Manages configuration and initialization
   - Provides high-level API for document operations

2. **Document Management**
   - Document storage and retrieval
   - Metadata management
   - Version control
   - Access control

3. **Database Layer**
   - SQLite and PostgreSQL support
   - Connection pooling
   - Transaction management
   - Schema versioning

4. **Storage Backends**
   - Local filesystem
   - Cloud storage (S3, GCS)
   - Custom storage providers

## Architecture

```
docex/
├── __init__.py
├── docex.py            # Main DocEX class
├── config/
│   ├── __init__.py
│   └── docex_config.py # Configuration management
├── db/
│   ├── __init__.py
│   ├── connection.py   # Database connection
│   └── models.py       # SQLAlchemy models
├── storage/
│   ├── __init__.py
│   ├── base.py        # Storage interface
│   └── local.py       # Local storage implementation
└── utils/
    ├── __init__.py
    └── helpers.py     # Utility functions
```

## Multi-tenancy

DocEX is designed to be tenant-agnostic and composable. User context is supported for auditing and logging, but all tenant management and access control are handled at the application or orchestration layer.

Key principles:
- **DocEX Core:** Focuses on document and basket management, processing, and storage.
- **Multi-tenancy:** All tenant-specific logic (provisioning, access control, configuration) is managed outside DocEX, typically in the API or orchestration layer.

Example usage with multi-tenancy:

```python
# Application layer handles tenant context
user_ctx = UserContext(
    user_id="user123",
    tenant_id="tenant456"
)

# Pass user_context to DocEX for logging/auditing
df = DocEX(user_context=user_ctx)
```

Architecture diagram:
```
┌─────────────────┐
│  Application    │
│  Layer          │
│                 │
│  ┌───────────┐  │
│  │  DocEX    │  │
│  └───────────┘  │
└─────────────────┘
```

Key points:
- **Database/Storage Config:** Application layer provides tenant-specific config to DocEX.
- **Access Control:** Enforced outside DocEX.
- **User Context:** Passed to DocEX for auditing.

Benefits:
- **Separation of Concerns:** DocEX is focused and maintainable.
- **Flexibility:** Application layer can implement any multi-tenant strategy.
- **Simplicity:** Core functionality remains clean and straightforward.

Best practices:
- Keep DocEX core tenant-agnostic.
- Handle tenant isolation at the application layer.
- Pass only the necessary context to DocEX for auditing. 