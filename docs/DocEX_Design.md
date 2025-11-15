# DocEX Design Document

![DocEX Architecture](DocEX_Architecture.jpeg)

## Architecture Principles

- **Layering Rule:** Lower layers (e.g., Storage, Documents) must never access or depend on higher layers (e.g., Route, Processing).
- **Encapsulation Rule:** Route and Processing layers should not access Storage directly. All storage access must go through the Document layer, ensuring security and extensibility.

## 1. Overview

DocEX is a document management system that provides robust document storage, metadata management, and operations tracking. It supports multiple storage backends and database systems while maintaining a consistent interface for document operations.

## 2. Architecture

### 2.1 Core Components

1. **DocEX**
   - Main entry point for the system
   - Manages system-wide configuration
   - Handles document basket creation and management
   - Provides CLI interface for system management

2. **DocBasket**
   - Container for related documents
   - Manages its own storage configuration
   - Handles document lifecycle within the basket

3. **Document**
   - Represents individual documents
   - Manages document metadata and content
   - Handles document operations

4. **Storage**
   - Abstract interface for storage backends
   - Implementations for filesystem and S3 storage
   - Handles content storage and retrieval

### 2.2 Package Structure

```
docex/
├── __init__.py
├── cli.py                 # CLI interface
├── docCore.py            # Main DocEX class
├── docbasket.py          # Document basket implementation
├── document.py           # Unified Document class
├── context.py            # User context for auditing
├── config/
│   ├── __init__.py
│   ├── docex_config.py # Configuration management
│   └── default_config.yaml
├── db/
│   ├── __init__.py
│   ├── connection.py     # Database connection management
│   ├── models.py         # Database models
│   └── abstract_database.py # Abstract database interface
├── processors/
│   ├── __init__.py
│   ├── base.py           # BaseProcessor and helpers
│   ├── factory.py        # ProcessorFactory
│   └── csv_to_json.py    # Example processor
├── transport/
│   ├── __init__.py
│   ├── base.py           # Base transport interface
│   ├── config.py         # Transport configuration
│   ├── local.py          # Local transport implementation
│   ├── models.py         # Transport models
│   └── route.py          # Route management
├── storage/
│   ├── __init__.py
│   ├── abstract_storage.py # Abstract storage interface
│   ├── filesystem_storage.py # Filesystem storage implementation
│   ├── s3_storage.py        # S3 storage implementation
│   └── storage_factory.py   # Storage factory
├── services/
│   ├── __init__.py
│   └── metadata_service.py  # Metadata management service
├── models/
│   ├── __init__.py
│   └── metadata_keys.py     # Metadata key definitions
└── utils/
    ├── __init__.py
    └── helpers.py           # Utility functions
```

> **Note:**
> - All processor and processing operation models are now in `docex/db/models.py`.
> - The `Document` class is unified in `docex/document.py` and used throughout the system.
> - The `processors/models.py` file is now a stub or empty.

### 2.3 Layering and Access Rules

- **Lower layers never access higher layers.**
- **Route and Processing layers must not access Storage directly.**
  - All storage access is performed via the Document layer, which encapsulates storage logic and ensures security/extensibility.

### 2.4 Processor Management (CLI and Factory)

- Processor registration, removal, and listing are managed via the CLI and database.
- All CLI processor commands (`register`, `remove`, `list`) import models from `docex.db.models`.
- The `ProcessorFactory` uses the database to instantiate processors and their configs.
- Example CLI usage:

```bash
docex processor register --name CSVToJSONProcessor --type format_converter --description "Converts CSV to JSON" --config '{}'
docex processor remove --name CSVToJSONProcessor
docex processor list
```

### 2.5 Document Layer

- The `Document` class in `docex/document.py` provides all content access and metadata management.
- Processors and routes must use `document.get_content()` and related methods for all content access.
- Storage details are fully encapsulated in the Document layer.

### 2.6 Storage Layer

- Storage backends (filesystem, S3, etc.) are implemented in `docex/storage/`.
- All storage access is via the `StorageService` and the Document layer.
- No direct storage access from Route or Processing layers.

### 2.7 Database Models

- All core models (Document, DocBasket, Processor, ProcessingOperation, etc.) are in `docex/db/models.py`.
- The schema and relationships are up to date with the codebase.

### 2.8 Example Processor Implementation

```python
from docex.processors.base import BaseProcessor, ProcessingResult
from docex.document import Document

class CSVToJSONProcessor(BaseProcessor):
    def can_process(self, document: Document) -> bool:
        return document.name.lower().endswith('.csv')
    
    def process(self, document: Document) -> ProcessingResult:
        csv_content = self.get_document_text(document)
        # ... process CSV ...
        # Save output using document.storage_service.storage.save(...)
        # ...
        return ProcessingResult(success=True, content='output.json')
```

### 2.9 CLI and System Initialization

- The CLI uses the updated package structure and imports.
- System initialization, basket creation, and document management are all in sync with the codebase.

### 2.10 ID Formatting

All IDs in the system follow a consistent format with a three-letter prefix followed by a UUID:

- Document IDs: `doc_<uuid>`
- Basket IDs: `bas_<uuid>`
- Route IDs: `rt_<uuid>`
- Operation IDs: `op_<uuid>`
- Route Operation IDs: `rop_<uuid>`
- Document Event IDs: `evt_<uuid>`
- Document Metadata IDs: `dmt_<uuid>`
- File History IDs: `fhi_<uuid>`
- Operation Dependency IDs: `odp_<uuid>`

### 2.11 Configuration Hierarchy

1. **System Configuration**
   - Stored in `~/.docex/config.yaml`
   - Managed through CLI commands
   - Contains database, storage, and transport settings

2. **Database Configuration**
   ```yaml
   database:
     type: sqlite  # or postgres
     sqlite:
       path: /path/to/database.db
     postgres:
       host: localhost
       port: 5432
       database: docex
       user: docex
       password: secret
       schema: docex
   ```

3. **Storage Configuration**
   ```yaml
   storage:
     default_type: filesystem
     filesystem:
       base_path: /path/to/storage
     s3:
       bucket: docex-bucket
       access_key: your-access-key
       secret_key: your-secret-key
       region: us-east-1
   ```

4. **Transport Configuration**
   ```yaml
   transport_config:
     routes:
       - name: local_backup
         purpose: backup
         protocol: local
         config:
           type: local
           name: local_backup_transport
           base_path: /path/to/backup
           create_dirs: true
         can_upload: true
         can_download: true
         can_list: true
         can_delete: false
         enabled: true
         priority: 1
         tags: [backup, local]
         metadata:
           retention_days: 30
           compression: true
     default_route: local_backup
     fallback_route: sftp_distribution
   ```

### 2.12 CLI Interface

The CLI provides comprehensive system management commands:

```bash
# System Initialization
docex init [--config CONFIG] [--force] [--db-type {sqlite,postgresql}] [--db-path DB_PATH] [--db-host DB_HOST] [--db-port DB_PORT] [--db-name DB_NAME] [--db-user DB_USER] [--db-password DB_PASSWORD] [--storage-path STORAGE_PATH] [--log-level {DEBUG,INFO,WARNING,ERROR,CRITICAL}]

# Processor Management
docex processor register --name NAME --type TYPE --description DESCRIPTION [--config CONFIG] [--enabled/--disabled]
docex processor remove --name NAME
docex processor list

# Route Management
docex route create --name NAME --type TYPE --config CONFIG [--purpose PURPOSE] [--can-upload] [--can-download] [--can-list] [--can-delete] [--enabled] [--priority PRIORITY] [--tags TAGS] [--metadata METADATA]
docex route list
docex route delete --name NAME

# Basket Management
docex basket create --name NAME
docex basket list
docex basket delete --name NAME

# Document Management
docex document add --basket BASKET --file FILE [--document-type TYPE] [--metadata METADATA]
docex document list --basket BASKET
docex document get --id ID
docex document delete --id ID

# Vector Indexing (Embeddings)
docex embed --tenant-id TENANT_ID [--all | --basket BASKET | --basket-id BASKET_ID] [--document-type TYPE] [--force] [--model MODEL] [--include-metadata/--no-include-metadata] [--batch-size SIZE] [--dry-run] [--vector-db-type {pgvector|memory}] [--limit LIMIT] [--skip SKIP] [--log-level LEVEL]
```

#### Vector Indexing Command (`docex embed`)

The `embed` command generates vector embeddings for documents to enable semantic search capabilities.

**Required Options (one of):**
- `--all` - Index all documents across all baskets
- `--basket BASKET` - Index documents in a specific basket (by name)
- `--basket-id BASKET_ID` - Index documents in a specific basket (by ID)

**Common Options:**
- `--tenant-id TENANT_ID` - Tenant ID for multi-tenant setups (required for multi-tenant deployments)
- `--document-type TYPE` - Filter documents by document type (e.g., `purchase_order`, `invoice`)
- `--force` - Force re-indexing of already indexed documents
- `--model MODEL` - Embedding model to use (default: `all-mpnet-base-v2`)
- `--include-metadata / --no-include-metadata` - Include metadata in embeddings (default: `True`)
- `--batch-size SIZE` - Number of documents to process in each batch (default: 10)
- `--dry-run` - Show what would be indexed without actually indexing
- `--vector-db-type {pgvector|memory}` - Vector database type (default: `pgvector`)
- `--limit LIMIT` - Maximum number of documents to index
- `--skip SKIP` - Number of documents to skip (for pagination)
- `--log-level LEVEL` - Logging level (`DEBUG`, `INFO`, `WARNING`, `ERROR`)

**Examples:**
```bash
# Index all documents for a tenant
docex embed --tenant-id my-tenant --all

# Index documents in a specific basket
docex embed --tenant-id my-tenant --basket my_basket_name

# Index only purchase orders
docex embed --tenant-id my-tenant --all --document-type purchase_order

# Dry run to preview
docex embed --tenant-id my-tenant --all --dry-run

# Force re-indexing with different model
docex embed --tenant-id my-tenant --all --force --model all-MiniLM-L6-v2
```

For detailed documentation, see [Vector Indexing CLI Documentation](../../LlamaSee-Document-Processing/docs/Implementation_Design/VECTOR_INDEXING_CLI.md).

### 2.2 Database Schema

#### Transport Routes Table
```sql
CREATE TABLE transport_routes (
    id VARCHAR(36) PRIMARY KEY,  -- Format: rt_<uuid>
    name VARCHAR(255) NOT NULL UNIQUE,
    purpose VARCHAR(50) NOT NULL,
    protocol VARCHAR(50) NOT NULL,
    config JSON NOT NULL,
    can_upload BOOLEAN NOT NULL DEFAULT FALSE,
    can_download BOOLEAN NOT NULL DEFAULT FALSE,
    can_list BOOLEAN NOT NULL DEFAULT FALSE,
    can_delete BOOLEAN NOT NULL DEFAULT FALSE,
    other_party_id VARCHAR(255),
    other_party_name VARCHAR(255),
    other_party_type VARCHAR(50),
    route_metadata JSON NOT NULL DEFAULT '{}',
    tags JSON NOT NULL DEFAULT '[]',
    priority INTEGER NOT NULL DEFAULT 0,
    enabled BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMP NOT NULL,
    updated_at TIMESTAMP NOT NULL
);
```

#### Route Operations Table
```sql
CREATE TABLE route_operations (
    id VARCHAR(36) PRIMARY KEY,  -- Format: rop_<uuid>
    route_id VARCHAR(36) NOT NULL REFERENCES transport_routes(id) ON DELETE CASCADE,
    operation_type VARCHAR(50) NOT NULL,
    status VARCHAR(20) NOT NULL,
    document_id VARCHAR(255),
    details JSON,
    error TEXT,
    created_at TIMESTAMP NOT NULL,
    completed_at TIMESTAMP
);
```

#### Documents Table
```sql
CREATE TABLE document (
    id VARCHAR(36) PRIMARY KEY,  -- Format: doc_<uuid>
    basket_id VARCHAR(36) NOT NULL REFERENCES docbasket(id),
    name VARCHAR(255) NOT NULL,
    source VARCHAR(255) NOT NULL,
    path VARCHAR(255) NOT NULL,
    content_type VARCHAR(100),
    document_type VARCHAR(50) NOT NULL DEFAULT 'file',
    content JSON,
    raw_content TEXT,
    size INTEGER,
    checksum VARCHAR(64) NOT NULL,
    status VARCHAR(50) NOT NULL DEFAULT 'active',
    processing_attempts INTEGER DEFAULT 0,
    created_at TIMESTAMP NOT NULL,
    updated_at TIMESTAMP NOT NULL
);
```

#### Document Metadata Table
```sql
CREATE TABLE document_metadata (
    id VARCHAR(36) PRIMARY KEY,  -- Format: dmt_<uuid>
    document_id VARCHAR(36) NOT NULL REFERENCES document(id),
    key VARCHAR(255) NOT NULL,
    value TEXT NOT NULL,
    metadata_type VARCHAR(50) NOT NULL DEFAULT 'custom',
    created_at TIMESTAMP NOT NULL,
    updated_at TIMESTAMP NOT NULL
);
```

#### Operations Table
```sql
CREATE TABLE operations (
    id VARCHAR(36) PRIMARY KEY,  -- Format: op_<uuid>
    document_id VARCHAR(36) NOT NULL REFERENCES document(id),
    operation_type VARCHAR(100) NOT NULL,
    status VARCHAR(50) NOT NULL,
    details JSON,
    error TEXT,
    created_at TIMESTAMP NOT NULL,
    completed_at TIMESTAMP
);
```

## 3. Metadata Management

### 3.1 Metadata Structure

Metadata is stored in a flexible key-value structure with support for:
- Standard metadata fields
- Custom metadata fields
- Metadata types
- Version tracking

### 3.2 Metadata Types

1. **File-related Metadata**
   - `ORIGINAL_PATH`: Original file path
   - `FILE_TYPE`: Type of file (PDF, DOCX, etc.)
   - `FILE_SIZE`: Size in bytes
   - `FILE_EXTENSION`: File extension
   - `ORIGINAL_FILE_TIMESTAMP`: File creation/modification time

2. **Document Processing Metadata**
   - `PROCESSING_STATUS`: Current processing status
   - `PROCESSING_ERROR`: Error messages
   - `PROCESSING_ATTEMPTS`: Number of processing attempts

3. **Content Metadata**
   - `CONTENT_TYPE`: Type of content
   - `CONTENT_LENGTH`: Content length
   - `CONTENT_CHECKSUM`: Content checksum
   - `CONTENT_VERSION`: Version number

4. **Business Metadata**
   - `RELATED_PO`: Related purchase order
   - `CUSTOMER_ID`: Customer identifier
   - `SUPPLIER_ID`: Supplier identifier

5. **Security Metadata**
   - `ACCESS_LEVEL`: Document access level
   - `ENCRYPTION_STATUS`: Encryption status
   - `RETENTION_PERIOD`: Document retention period

### 3.3 Metadata Operations

```python
class MetadataService:
    def get_metadata(self, document_id: str) -> Dict[str, Any]:
        """Retrieve all metadata for a document"""
    
    def update_metadata(self, document_id: str, metadata: Dict[str, Any]) -> None:
        """Update or create metadata entries"""
    
    def delete_metadata(self, document_id: str, keys: List[str]) -> None:
        """Delete specific metadata entries"""
```

## 4. Operations Management

### 4.1 Duplicate Detection

```python
class DocumentService:
    def check_for_duplicates(self, source: str, checksum: str) -> Dict[str, Any]:
        """Check for documents with same source and checksum"""
        
    def mark_as_duplicate(self, document_id: str, original_document_id: str) -> DocumentModel:
        """Mark document as duplicate and create event"""
```

### 4.2 Operation Tracking

Operations are tracked with:
- Operation type
- Status
- Timestamps
- Error information
- Dependencies

### 4.3 Operation Types

1. **Document Processing**
   - Document ingestion
   - Content extraction
   - Format conversion

2. **Status Changes**
   - Status updates
   - Error handling
   - Completion tracking

3. **Metadata Operations**
   - Metadata updates
   - Metadata validation
   - Metadata extraction

4. **File Operations**
   - File movement
   - File deletion
   - File copying

## 5. Storage Backends

### 5.1 FileSystem Storage

```python
class FileSystemStorage(AbstractStorage):
    def save(self, path: str, content: Union[str, Dict, bytes, BinaryIO]) -> None:
        """Save content to filesystem"""
    
    def load(self, path: str) -> Union[Dict, bytes]:
        """Load content from filesystem"""
    
    def delete(self, path: str) -> bool:
        """Delete content from filesystem"""
```

### 5.2 S3 Storage

```python
class S3Storage(AbstractStorage):
    def save(self, path: str, content: Union[str, Dict, bytes, BinaryIO]) -> None:
        """Save content to S3"""
    
    def load(self, path: str) -> Union[Dict, bytes]:
        """Load content from S3"""
    
    def delete(self, path: str) -> bool:
        """Delete content from S3"""
```

## 6. Transport Layer

### 6.1 Core Components

1. **Route**
   - Represents a configured transport route with a specific purpose
   - Manages document uploads and downloads
   - Tracks operations and maintains audit trail
   - Supports multiple protocols (local, SFTP, HTTP, etc.)
   - Uses consistent ID format (`rt_<uuid>`)

2. **RouteOperation**
   - Tracks operations performed on routes
   - Records operation type, status, and details
   - Maintains timestamps for operation lifecycle
   - Links to related documents when applicable
   - Uses consistent ID format (`rop_<uuid>`)

3. **Transporter**
   - Abstract interface for protocol-specific implementations
   - Handles actual file transfers
   - Manages protocol-specific configuration
   - Provides consistent interface across protocols

### 6.2 Operation Tracking

1. **Document Operations**
   - Recorded when documents are added to baskets
   - Track document status changes
   - Include operation details and timestamps
   - Link to route operations when applicable
   - Use consistent ID format (`op_<uuid>`)

2. **Route Operations**
   - Recorded for all transport operations
   - Track operation status (in_progress, success, failed)
   - Include detailed error information
   - Maintain operation lifecycle timestamps
   - Use consistent ID format (`rop_<uuid>`)

3. **Operation Dependencies**
   - Track relationships between operations
   - Support for sequential operations
   - Enable operation chaining
   - Maintain operation order
   - Use consistent ID format (`odp_<uuid>`)

### 6.3 Transport Methods

1. **Upload**
   - Upload documents to remote locations
   - Support for different protocols
   - Handle large files efficiently
   - Maintain file integrity

2. **Download**
   - Download documents from remote locations
   - Support for different protocols
   - Handle large files efficiently
   - Maintain file integrity

3. **List**
   - List available documents
   - Support for different protocols
   - Handle large directories efficiently
   - Maintain consistent interface

4. **Delete**
   - Delete documents from remote locations
   - Support for different protocols
   - Handle errors gracefully
   - Maintain audit trail

### 6.4 Configuration

```yaml
transport_config:
  routes:
    - name: local_backup
      purpose: backup
      protocol: local
      config:
        type: local
        name: local_backup_transport
        base_path: /path/to/backup
        create_dirs: true
      can_upload: true
      can_download: true
      can_list: true
      can_delete: false
      enabled: true
      priority: 1
      tags: [backup, local]
      metadata:
        retention_days: 30
        compression: true
      
    - name: sftp_distribution
      purpose: distribution
      protocol: sftp
      config:
        type: sftp
        name: sftp_distribution_transport
        host: sftp.example.com
        port: 22
        username: user
        password: secret
        base_path: /incoming
        create_dirs: true
      can_upload: true
      can_download: false
      can_list: true
      can_delete: false
      enabled: true
      priority: 2
      tags: [distribution, sftp]
      metadata:
        max_retries: 3
        retry_delay: 60
      other_party:
        id: partner1
        name: Test Partner
        type: supplier
  default_route: local_backup
  fallback_route: sftp_distribution
```

The configuration structure includes:

1. **Route Configuration**
   - `name`: Unique identifier for the route
   - `purpose`: Route purpose (backup, distribution, archive, processing, notification)
   - `protocol`: Transport protocol (local, sftp, http)
   - `config`: Protocol-specific configuration
   - `can_upload`: Whether route allows uploads
   - `can_download`: Whether route allows downloads
   - `can_list`: Whether route allows listing files
   - `can_delete`: Whether route allows file deletion
   - `enabled`: Whether route is enabled
   - `priority`: Route priority (higher numbers take precedence)
   - `tags`: List of tags for route categorization
   - `metadata`: Additional route metadata
   - `other_party`: Optional business context information

2. **Transport Configuration**
   - `type`: Transport protocol type
   - `name`: Transport instance name
   - Protocol-specific fields (e.g., host, port, base_path)
   - Additional protocol-specific settings

3. **Global Configuration**
   - `default_route`: Default route to use when no specific route is specified
   - `fallback_route`: Fallback route to use when primary route fails

## 7. Processors Layer

### 7.1 Core Components

1. **Processor**
   - Abstract interface for document processors
   - Handles document transformation and processing
   - Supports plugin architecture for different document types
   - Maintains processing history and metadata

2. **ProcessorFactory**
   - Creates appropriate processor instances
   - Manages processor registration
   - Handles processor discovery
   - Supports dynamic loading of processors

3. **ProcessingResult**
   - Tracks processing status and results
   - Maintains processing metadata
   - Handles error reporting
   - Supports processing history

### 7.2 Processor Types

1. **Format Converters**
   - CSV to JSON
   - JSON to CSV
   - PDF to Text
   - Image to Text
   - Office Documents to PDF

2. **Content Processors**
   - Text Extraction
   - Metadata Extraction
   - Content Validation
   - Content Enrichment
   - Data Normalization

3. **Business Processors**
   - Document Classification
   - Data Extraction
   - Compliance Checking
   - Data Validation
   - Business Rule Application

### 7.3 Database Schema

#### Processors Table
```sql
CREATE TABLE processors (
    id VARCHAR(36) PRIMARY KEY,  -- Format: prc_<uuid>
    name VARCHAR(255) NOT NULL UNIQUE,
    type VARCHAR(50) NOT NULL,
    description TEXT,
    config JSON NOT NULL DEFAULT '{}',
    enabled BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMP NOT NULL,
    updated_at TIMESTAMP NOT NULL
);
```

#### Processing Operations Table
```sql
CREATE TABLE processing_operations (
    id VARCHAR(36) PRIMARY KEY,  -- Format: pop_<uuid>
    document_id VARCHAR(36) NOT NULL REFERENCES document(id),
    processor_id VARCHAR(36) NOT NULL REFERENCES processors(id),
    status VARCHAR(20) NOT NULL,
    input_metadata JSON,
    output_metadata JSON,
    error TEXT,
    created_at TIMESTAMP NOT NULL,
    completed_at TIMESTAMP
);
```

### 7.4 Configuration

```yaml
processors:
  enabled_processors:
    - csv_to_json
    - pdf_to_text
    - image_to_text
  default_processors:
    csv: csv_to_json
    pdf: pdf_to_text
    image: image_to_text
  processor_configs:
    csv_to_json:
      encoding: utf-8
      delimiter: ","
      quote_char: '"'
      skip_header: true
    pdf_to_text:
      extract_images: false
      extract_tables: true
    image_to_text:
      ocr_engine: tesseract
      language: eng
```

### 7.5 Usage Example

```python
# Create a processor
processor = ProcessorFactory.create_processor('csv_to_json')

# Process a document
result = await processor.process(document)

# Check processing status
if result.success:
    # Get processed content
    processed_content = result.content
    
    # Get processing metadata
    metadata = result.metadata
    
    # Update document with processed content
    document.update_content(processed_content)
    document.update_metadata(metadata)
```

#### Processor Management
- Processors can be registered, enabled/disabled, and removed dynamically via the CLI.
- Processor metadata and configuration are managed in the database for dynamic discovery and control.
- Developers and admins can use CLI commands to:
    - Register a new processor: `docex processor register ...`
    - Remove a processor: `docex processor remove ...`
    - List all processors: `docex processor list`
- This enables runtime extensibility and operational control without code changes or redeployment.

## 8. Best Practices

### 8.1 Metadata Management
- Use standardized metadata keys
- Validate metadata values
- Track metadata changes
- Support metadata inheritance
- Enable metadata search

### 8.2 Operations
- Ensure atomic operations
- Implement transaction support
- Handle errors gracefully
- Log operations
- Track operation status
- Manage operation dependencies

### 8.3 Storage
- Implement proper error handling
- Support content validation
- Enable content versioning
- Provide efficient content retrieval
- Support content streaming

## 9. Testing

### 9.1 Test Categories
1. Unit Tests
   - Component testing
   - Service testing
   - Storage testing

2. Integration Tests
   - Database integration
   - Storage integration
   - Service integration

3. System Tests
   - End-to-end workflows
   - Performance testing
   - Load testing

### 9.2 Test Environment
- Separate test database
- Mock storage backends
- Test data management
- Environment isolation

## 10. Configuration

### 10.1 System Configuration
```yaml
# ~/.docex/config.yaml
database:
  type: sqlite  # or postgres
  sqlite:
    path: /path/to/database.db
  postgres:
    host: localhost
    port: 5432
    database: docex
    user: docex
    password: secret
    schema: docex

storage:
  default_type: filesystem
  filesystem:
    base_path: /path/to/storage
  s3:
    bucket: docex-bucket
    access_key: your-access-key
    secret_key: your-secret-key
    region: us-east-1

logging:
  level: INFO
  file: /path/to/logfile.log
```

### 10.2 Configuration Management

1. **Initialization**
   - System must be initialized using `docex init`
   - Creates configuration directory at `~/.docex`
   - Sets up default configuration
   - Initializes database and storage

2. **Configuration Loading**
   - Configuration loaded from `~/.docex/config.yaml`
   - Merged with default configuration
   - Validated against schema
   - Cached in memory for performance

3. **Configuration Updates**
   - Updates managed through CLI commands
   - Changes persisted to configuration file
   - Runtime configuration updates supported
   - Validation on all changes

## 11. Security

### 11.1 Security Design Philosophy

DocEX follows a **tenant-agnostic, composable security model** where:
- **Core Security**: DocEX provides audit logging and operation tracking infrastructure
- **Access Control**: Enforced at the application/orchestration layer by default (not in DocEX core)
- **Optional Enforcement**: Can be configured to enforce user context matching for multi-tenant safety
- **Data Protection**: Relies on underlying storage and transport layer security
- **Multi-tenancy**: Handled by the application layer using basket-based organization (with optional enforcement)

This design allows DocEX to be integrated into any security model (RBAC, ABAC, etc.) without imposing specific access control mechanisms, while optionally providing a safety net for tenant isolation when needed.

### 11.2 Access Control

#### 11.2.1 Application Layer Responsibility (Default)

**Current Status**: Access control is **not enforced in DocEX core by default**. This is an intentional design decision to keep DocEX composable and flexible.

**Implementation Approach**:
- **Document-level access**: Enforced by application layer before calling DocEX APIs
- **Basket-level access**: Managed through basket organization and application-layer filtering
- **Operation-level permissions**: Controlled by application layer based on `UserContext` roles
- **Route-level access**: Managed through route configuration and application-layer authorization

**Example Pattern**:
```python
# Application layer enforces access control
user_context = UserContext(user_id="alice", tenant_id="tenant1", roles=["admin"])

if not user_has_permission(user_context, "read", basket_id):
    raise PermissionError("Access denied")

# Then call DocEX (which logs the operation)
docEX = DocEX(user_context=user_context)
basket = docEX.get_basket(basket_id)
```

**Benefits**:
- Flexibility to implement any access control model
- No security logic embedded in document management core
- Clear separation of concerns
- Easy integration with existing IAM/RBAC systems

#### 11.2.2 Multi-Tenancy Models

DocEX supports two multi-tenancy models, each with different trade-offs. Choose based on your security, compliance, and scalability requirements.

##### Model A: Row-Level Isolation (Shared Database)

**Description**: All tenants share the same database/schema, with `tenant_id` columns providing logical isolation.

**Configuration**:
```yaml
# ~/.docex/config.yaml
security:
  multi_tenancy_model: row_level  # or "database_level"
  enforce_user_context: true       # Enable user context enforcement
  context_match_fields:           # Fields to match for enforcement
    - tenant_id                    # Require matching tenant_id
    # - user_id                    # Optional: require matching user_id
```

**How It Works**:

1. **When Creating Resources** (if `enforce_user_context: true`):
   - Basket creation stores `tenant_id` and `created_by_user_id` in the database
   - Document creation stores `tenant_id` and `created_by_user_id` in the database
   - If `UserContext` is not provided, creation fails with `ValueError`

2. **When Retrieving Resources** (if `enforce_user_context: true`):
   - `get_basket()` checks if current `UserContext.tenant_id` matches basket's `tenant_id`
   - `get_document()` checks if current `UserContext.tenant_id` matches document's `tenant_id`
   - `list_baskets()` filters results to only show baskets matching current `tenant_id`
   - If context doesn't match, raises `PermissionError` or returns empty results

3. **Database Schema Changes**:
```sql
-- Add tenant context to baskets
ALTER TABLE docbasket ADD COLUMN tenant_id VARCHAR(255);
ALTER TABLE docbasket ADD COLUMN created_by_user_id VARCHAR(255);
CREATE INDEX idx_docbasket_tenant_id ON docbasket(tenant_id);

-- Add tenant context to documents
ALTER TABLE document ADD COLUMN tenant_id VARCHAR(255);
ALTER TABLE document ADD COLUMN created_by_user_id VARCHAR(255);
CREATE INDEX idx_document_tenant_id ON document(tenant_id);
```

**Pros**:
- ✅ Simple connection management (single database)
- ✅ Easy cross-tenant analytics and reporting
- ✅ Single schema to manage and migrate
- ✅ Efficient for many small tenants
- ✅ Lower database overhead

**Cons**:
- ❌ Risk of cross-tenant data leaks (if code bug)
- ❌ Harder to scale individual tenants
- ❌ All tenants share database performance
- ❌ Less suitable for strict compliance (HIPAA, GDPR)

**When to Use**:
- Multi-tenant SaaS with many small tenants
- Applications where cross-tenant analytics are important
- Cost-sensitive deployments
- Applications with moderate compliance requirements

##### Model B: Database/Schema-Level Isolation (Per-Tenant Database)

**Description**: Each tenant has its own database (SQLite) or schema (PostgreSQL), providing physical data isolation.

**Configuration**:
```yaml
# ~/.docex/config.yaml
security:
  multi_tenancy_model: database_level  # or "row_level"
  tenant_database_routing: true        # Enable automatic database routing
  # For PostgreSQL with schemas:
  postgres:
    schema_template: "tenant_{tenant_id}"  # Schema name pattern
  # For SQLite with separate databases:
  sqlite:
    path_template: "storage/tenant_{tenant_id}/docex.db"
```

**How It Works**:

1. **Database Routing**:
   - DocEX automatically routes to tenant-specific database/schema based on `UserContext.tenant_id`
   - Each tenant gets isolated database connection
   - No `tenant_id` columns needed (physical isolation)

2. **Connection Management**:
   ```python
   # DocEX automatically routes to tenant database
   user_context = UserContext(user_id="alice", tenant_id="tenant1")
   docEX = DocEX(user_context=user_context)
   
   # Automatically connects to tenant1 database/schema
   basket = docEX.create_basket("invoices")
   
   # Different tenant gets different database
   user_context2 = UserContext(user_id="bob", tenant_id="tenant2")
   docEX2 = DocEX(user_context=user_context2)
   # Automatically connects to tenant2 database/schema
   ```

3. **PostgreSQL Schema Example**:
   ```sql
   -- Each tenant has its own schema
   CREATE SCHEMA tenant_tenant1;
   CREATE SCHEMA tenant_tenant2;
   
   -- Tables created in each schema automatically
   -- No tenant_id columns needed
   ```

4. **SQLite Database Example**:
   ```
   storage/
     tenant_tenant1/
       docex.db  # Complete database for tenant1
     tenant_tenant2/
       docex.db  # Complete database for tenant2
   ```

**Pros**:
- ✅ **Strongest Isolation**: Physical data separation
- ✅ **Best for Compliance**: HIPAA, GDPR, SOX requirements
- ✅ **Independent Scaling**: Scale tenants individually
- ✅ **No Cross-Tenant Leaks**: Impossible to query wrong tenant
- ✅ **Independent Backups**: Backup/restore per tenant
- ✅ **Schema Customization**: Different schemas per tenant if needed

**Cons**:
- ❌ More complex connection management
- ❌ Harder cross-tenant analytics (requires federation)
- ❌ More database connections (connection pool per tenant)
- ❌ Schema migrations more complex (migrate all tenant schemas)
- ❌ Higher operational overhead

**When to Use**:
- Strict compliance requirements (HIPAA, GDPR, financial)
- Large enterprise tenants requiring isolation
- Applications with regulatory requirements
- Tenants with different schema needs
- High-security environments

##### Comparison Matrix

| Feature | Row-Level Isolation | Database-Level Isolation |
|---------|-------------------|------------------------|
| **Data Isolation** | Logical (tenant_id) | Physical (separate DB/schema) |
| **Security** | Good (code-dependent) | Excellent (impossible to leak) |
| **Compliance** | Moderate | Strong (HIPAA, GDPR) |
| **Connection Management** | Simple (1 DB) | Complex (N DBs) |
| **Cross-Tenant Analytics** | Easy | Hard (federation) |
| **Scalability** | Shared resources | Per-tenant scaling |
| **Schema Migrations** | Single migration | N migrations |
| **Operational Overhead** | Low | High |
| **Best For** | Many small tenants | Few large tenants |

##### Implementation Status

**Row-Level Isolation**: **Proposed** - Not yet implemented. Requires:
1. Configuration option in `default_config.yaml`
2. Database schema migration (add `tenant_id` columns)
3. Enforcement logic in retrieval methods
4. Context storage in creation methods

**Database-Level Isolation**: **✅ Implemented** (Version 2.2.0+). Features:
1. ✅ Configuration option for `multi_tenancy_model: database_level`
2. ✅ Database routing logic based on `UserContext.tenant_id`
3. ✅ Connection pool management per tenant (`TenantDatabaseManager`)
4. ✅ Automatic schema/database creation for new tenants
5. ✅ Support for both SQLite (separate DB files) and PostgreSQL (separate schemas)
6. ✅ Thread-safe connection management
7. ⚠️ Migration tooling for multi-tenant deployments (planned)

**Implementation Details**:

The database-level isolation is implemented through `TenantDatabaseManager`, which:
- Maintains a connection pool per tenant
- Automatically creates tenant schemas/databases on first access
- Routes database operations to the correct tenant database/schema
- Provides thread-safe connection management

**Configuration Example**:
```yaml
# ~/.docex/config.yaml
security:
  multi_tenancy_model: database_level
  tenant_database_routing: true

database:
  type: postgresql
  postgres:
    host: localhost
    port: 5432
    database: docex
    user: postgres
    password: postgres
    schema_template: "tenant_{tenant_id}"  # Schema per tenant
```

**Usage**:
```python
from docex import DocEX
from docex.context import UserContext

# Tenant 1 - automatically routes to tenant1 schema
user_context1 = UserContext(user_id="alice", tenant_id="tenant1")
docEX1 = DocEX(user_context=user_context1)
basket1 = docEX1.create_basket("invoices")  # Created in tenant1 schema

# Tenant 2 - automatically routes to tenant2 schema (isolated)
user_context2 = UserContext(user_id="bob", tenant_id="tenant2")
docEX2 = DocEX(user_context=user_context2)
basket2 = docEX2.create_basket("invoices")  # Created in tenant2 schema
```

**Recommendation**: Start with **row-level isolation** for most use cases, migrate to **database-level isolation** if compliance or security requirements demand it. Database-level isolation is now available and ready for production use.

### 11.3 Data Protection

**Current Implementation**:

1. **Secure Storage**
   - **Filesystem**: Relies on OS-level file permissions and encryption (if configured)
   - **S3**: Uses AWS IAM policies, bucket encryption, and TLS for data in transit
   - **Storage Credentials**: Managed through configuration (environment variables, IAM roles)

2. **Secure Transmission**
   - **SFTP**: Uses SSH encryption for file transfers
   - **HTTP/HTTPS**: Relies on transport layer security (TLS/SSL)
   - **S3**: All operations use HTTPS by default

3. **Configuration Security**
   - **Current**: Configuration stored in plain text (`~/.docex/config.yaml`)
   - **Credentials**: Should be provided via environment variables or secret management systems
   - **Best Practice**: Use environment variables for sensitive credentials:
     ```bash
     export AWS_ACCESS_KEY_ID=...
     export AWS_SECRET_ACCESS_KEY=...
     export OPENAI_API_KEY=...
     ```

**Not Yet Implemented**:
- Content encryption at rest (relies on storage backend)
- Configuration file encryption
- Automatic credential rotation
- Key management integration

**Recommendations**:
- Use environment variables or secret management (AWS Secrets Manager, HashiCorp Vault) for credentials
- Enable encryption at rest on storage backends (S3 bucket encryption, encrypted filesystems)
- Use IAM roles instead of access keys when possible (AWS, GCP)
- Implement TLS/SSL for all network communications

### 11.4 Audit Trail (Implemented)

DocEX provides comprehensive audit logging infrastructure:

#### 11.4.1 User Context Tracking

**Implemented**: `UserContext` class tracks user identity for audit logging:

```python
from docex.context import UserContext
from docex import DocEX

user_context = UserContext(
    user_id="alice",
    user_email="alice@example.com",
    tenant_id="tenant1",
    roles=["admin", "user"]
)

docEX = DocEX(user_context=user_context)
# All operations are logged with user context
```

**What's Tracked**:
- User ID for all operations
- Tenant ID for multi-tenant scenarios
- User roles (for application-layer access control)
- Operation timestamps

#### 11.4.2 Operation Tracking

**Implemented**: Complete operation history stored in database:

1. **Document Operations** (`operations` table):
   - Operation type (e.g., "document_created", "document_updated", "document_deleted")
   - Status (pending, in_progress, success, failed)
   - Timestamps (created_at, completed_at)
   - Error details
   - Operation dependencies

2. **Processing Operations** (`processing_operations` table):
   - Processor used
   - Input/output metadata
   - Processing status
   - Error information
   - Timestamps

3. **Route Operations** (`route_operations` table):
   - Transport route used
   - Operation type (upload, download, list, delete)
   - Status and error details
   - Document references
   - Timestamps

4. **Document Events** (`doc_events` table):
   - Lifecycle events (created, updated, deleted, processed)
   - Event type and timestamp
   - Event data (JSON)
   - Source system
   - Status and error messages

**Query Examples**:
```python
# Get all operations for a document
operations = document.get_operations()

# Get all processing operations
from docex.db.models import ProcessingOperation
from sqlalchemy import select

with db.session() as session:
    query = select(ProcessingOperation).where(
        ProcessingOperation.document_id == document.id
    )
    operations = session.execute(query).scalars().all()
```

#### 11.4.3 Access Logging

**Implemented**: User context is logged for key operations:

- Basket creation: `"Basket {name} created by user {user_id}"`
- Basket access: `"Basket {basket_id} accessed by user {user_id}"`
- Document operations: Tracked via `operations` table with user context

**Logging Infrastructure**:
- Python `logging` module used throughout
- Log levels: DEBUG, INFO, WARNING, ERROR, CRITICAL
- Configurable log output (file, console, syslog)

#### 11.4.4 Change Tracking

**Implemented**: Metadata versioning and change history:

1. **Metadata Changes**: `document_metadata` table tracks:
   - Metadata key-value pairs
   - Creation and update timestamps
   - Metadata type

2. **File History**: `file_history` table tracks:
   - Original file paths
   - Internal storage paths
   - Path changes over time

3. **Document Status**: Document status changes tracked via:
   - `document.status` field
   - `operations` table for status change operations
   - `doc_events` table for lifecycle events

### 11.5 Security Best Practices

#### 11.5.1 For Application Developers

1. **Always Use UserContext**: Pass `UserContext` to DocEX for audit logging:
   ```python
   docEX = DocEX(user_context=user_context)
   ```

2. **Enforce Access Control**: Implement access control before calling DocEX:
   ```python
   if not check_permission(user, "read", resource):
       raise PermissionError()
   doc = basket.get_document(doc_id)
   ```

3. **Secure Credentials**: Never hardcode credentials:
   ```python
   # Good: Use environment variables
   api_key = os.getenv('OPENAI_API_KEY')
   
   # Bad: Hardcoded credentials
   api_key = "sk-..."
   ```

4. **Validate Input**: Validate all inputs before passing to DocEX:
   ```python
   if not is_valid_basket_name(name):
       raise ValueError("Invalid basket name")
   basket = docEX.create_basket(name)
   ```

#### 11.5.2 For System Administrators

1. **Storage Security**:
   - Enable encryption at rest on S3 buckets
   - Use IAM roles instead of access keys
   - Restrict bucket policies to least privilege
   - Enable S3 access logging

2. **Database Security**:
   - Use strong database passwords
   - Enable SSL/TLS for database connections
   - Restrict database access by IP
   - Regular database backups

3. **Configuration Security**:
   - Restrict file permissions on `~/.docex/config.yaml`:
     ```bash
     chmod 600 ~/.docex/config.yaml
     ```
   - Use environment variables for sensitive values
   - Rotate credentials regularly

4. **Network Security**:
   - Use HTTPS for all HTTP transports
   - Use SFTP (not FTP) for file transfers
   - Enable firewall rules to restrict access

### 11.6 Security Roadmap

**Planned Enhancements**:
1. **Enhanced Audit Logging**:
   - Structured audit log format
   - Integration with SIEM systems
   - Audit log retention policies

2. **Security Metadata**:
   - Document classification levels
   - Retention policies
   - Data sensitivity tags

3. **Compliance Features**:
   - GDPR compliance tools (data export, deletion)
   - SOX compliance reporting
   - HIPAA compliance features (if needed)

4. **Security Integrations**:
   - OAuth2/OIDC integration
   - LDAP/Active Directory integration
   - Secret management system integration (Vault, AWS Secrets Manager)

**Note**: Access control enforcement will remain at the application layer to maintain flexibility and composability.

## 12. Future Enhancements

1. **Planned Features**
   - Document versioning
   - Workflow management
   - Advanced search capabilities
   - Content transformation pipeline
   - Enhanced CLI interface
   - Configuration management improvements

2. **Performance Improvements**
   - Caching layer
   - Batch operations
   - Parallel processing
   - Database optimization
   - Storage optimization

3. **Integration Points**
   - External storage providers
   - Document processing services
   - Authentication providers
   - Monitoring and alerting
   - Backup and recovery

4. **Development Tools**
   - Development CLI commands
   - Testing utilities
   - Debugging tools
   - Performance profiling
   - Documentation generation

---

# Appendix: User Context and Multi-tenancy Design

## Design Philosophy

DocEX is designed to be tenant-agnostic and composable. User context is supported for auditing and logging, but all tenant management and access control are handled at the application or orchestration layer.

- **DocEX Core:** Focuses on document and basket management, processing, and storage.
- **User Context:** Used for operation tracking, audit logging, and optional metadata enrichment.
- **Multi-tenancy:** All tenant-specific logic (provisioning, access control, configuration) is managed outside DocEX, typically in the API or orchestration layer.

## UserContext Example

```python
from dataclasses import dataclass
from typing import Optional, Dict, List

@dataclass
class UserContext:
    user_id: str
    user_email: Optional[str] = None
    tenant_id: Optional[str] = None
    roles: Optional[List[str]] = None
    attributes: Optional[Dict] = None
```

- Pass `user_context` to DocEX for logging/auditing:

```python
user_ctx = UserContext(user_id="alice", tenant_id="tenant1", roles=["admin"])
docEX = DocEX(user_context=user_ctx)
docEX.create_basket("invoices")  # User action is logged
```

## Multi-tenancy Architecture

```
┌────────────────────────────┐
│  Application/Orchestration │
│  - Tenant provisioning     │
│  - Access control         │
│  - Per-tenant config      │
└─────────────┬──────────────┘
              │
              ▼
┌────────────────────────────┐
│         DocEX             │
│  - Document management    │
│  - Storage operations     │
│  - Processing             │
└────────────────────────────┘
```

## Implementation Guidelines

- **Database/Storage Config:** Application layer provides tenant-specific config to DocEX.
- **User Context:** Used for audit logging, not for business logic or access control.
- **Access Control:** Enforced outside DocEX.

## Benefits

- **Separation of Concerns:** DocEX is focused and maintainable.
- **Flexibility:** Any multi-tenancy or RBAC model can be layered on top.
- **Security:** No tenant data leakage; access control is centralized.

## Best Practices

- Keep DocEX core tenant-agnostic.
- Use `UserContext` for logging and traceability.
- Manage all tenant and user access at the orchestration or API layer.
- Pass only the necessary context to DocEX for auditing.

## Future Considerations

- Enhanced audit logging and traceability.
- User-specific configuration overrides (e.g., storage limits, processor plugins).
- Integration with external IAM or RBAC systems. 