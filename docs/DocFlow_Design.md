# DocFlow Design Document

![DocFlow Architecture](/New%20Era%20of%20Supply%20Chain/image.png)

## Architecture Principles

- **Layering Rule:** Lower layers (e.g., Storage, Documents) must never access or depend on higher layers (e.g., Route, Processing).
- **Encapsulation Rule:** Route and Processing layers should not access Storage directly. All storage access must go through the Document layer, ensuring security and extensibility.

## 1. Overview

DocFlow is a document management system that provides robust document storage, metadata management, and operations tracking. It supports multiple storage backends and database systems while maintaining a consistent interface for document operations.

## 2. Architecture

### 2.1 Core Components

1. **DocFlow**
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
docflow/
├── __init__.py
├── cli.py                 # CLI interface
├── docflow.py            # Main DocFlow class
├── docbasket.py          # Document basket implementation
├── document.py           # Unified Document class
├── context.py            # User context for auditing
├── config/
│   ├── __init__.py
│   ├── docflow_config.py # Configuration management
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
> - All processor and processing operation models are now in `docflow/db/models.py`.
> - The `Document` class is unified in `docflow/document.py` and used throughout the system.
> - The `processors/models.py` file is now a stub or empty.

### 2.3 Layering and Access Rules

- **Lower layers never access higher layers.**
- **Route and Processing layers must not access Storage directly.**
  - All storage access is performed via the Document layer, which encapsulates storage logic and ensures security/extensibility.

### 2.4 Processor Management (CLI and Factory)

- Processor registration, removal, and listing are managed via the CLI and database.
- All CLI processor commands (`register`, `remove`, `list`) import models from `docflow.db.models`.
- The `ProcessorFactory` uses the database to instantiate processors and their configs.
- Example CLI usage:

```bash
docflow processor register --name CSVToJSONProcessor --type format_converter --description "Converts CSV to JSON" --config '{}'
docflow processor remove --name CSVToJSONProcessor
docflow processor list
```

### 2.5 Document Layer

- The `Document` class in `docflow/document.py` provides all content access and metadata management.
- Processors and routes must use `document.get_content()` and related methods for all content access.
- Storage details are fully encapsulated in the Document layer.

### 2.6 Storage Layer

- Storage backends (filesystem, S3, etc.) are implemented in `docflow/storage/`.
- All storage access is via the `StorageService` and the Document layer.
- No direct storage access from Route or Processing layers.

### 2.7 Database Models

- All core models (Document, DocBasket, Processor, ProcessingOperation, etc.) are in `docflow/db/models.py`.
- The schema and relationships are up to date with the codebase.

### 2.8 Example Processor Implementation

```python
from docflow.processors.base import BaseProcessor, ProcessingResult
from docflow.document import Document

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
   - Stored in `~/.docflow/config.yaml`
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
       database: docflow
       user: docflow
       password: secret
       schema: docflow
   ```

3. **Storage Configuration**
   ```yaml
   storage:
     default_type: filesystem
     filesystem:
       base_path: /path/to/storage
     s3:
       bucket: docflow-bucket
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
docflow init [--config CONFIG] [--force] [--db-type {sqlite,postgresql}] [--db-path DB_PATH] [--db-host DB_HOST] [--db-port DB_PORT] [--db-name DB_NAME] [--db-user DB_USER] [--db-password DB_PASSWORD] [--storage-path STORAGE_PATH] [--log-level {DEBUG,INFO,WARNING,ERROR,CRITICAL}]

# Processor Management
docflow processor register --name NAME --type TYPE --description DESCRIPTION [--config CONFIG] [--enabled/--disabled]
docflow processor remove --name NAME
docflow processor list

# Route Management
docflow route create --name NAME --type TYPE --config CONFIG [--purpose PURPOSE] [--can-upload] [--can-download] [--can-list] [--can-delete] [--enabled] [--priority PRIORITY] [--tags TAGS] [--metadata METADATA]
docflow route list
docflow route delete --name NAME

# Basket Management
docflow basket create --name NAME
docflow basket list
docflow basket delete --name NAME

# Document Management
docflow document add --basket BASKET --file FILE [--document-type TYPE] [--metadata METADATA]
docflow document list --basket BASKET
docflow document get --id ID
docflow document delete --id ID
```

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
    - Register a new processor: `docflow processor register ...`
    - Remove a processor: `docflow processor remove ...`
    - List all processors: `docflow processor list`
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
# ~/.docflow/config.yaml
database:
  type: sqlite  # or postgres
  sqlite:
    path: /path/to/database.db
  postgres:
    host: localhost
    port: 5432
    database: docflow
    user: docflow
    password: secret
    schema: docflow

storage:
  default_type: filesystem
  filesystem:
    base_path: /path/to/storage
  s3:
    bucket: docflow-bucket
    access_key: your-access-key
    secret_key: your-secret-key
    region: us-east-1

logging:
  level: INFO
  file: /path/to/logfile.log
```

### 10.2 Configuration Management

1. **Initialization**
   - System must be initialized using `docflow init`
   - Creates configuration directory at `~/.docflow`
   - Sets up default configuration
   - Initializes database and storage

2. **Configuration Loading**
   - Configuration loaded from `~/.docflow/config.yaml`
   - Merged with default configuration
   - Validated against schema
   - Cached in memory for performance

3. **Configuration Updates**
   - Updates managed through CLI commands
   - Changes persisted to configuration file
   - Runtime configuration updates supported
   - Validation on all changes

## 11. Security

### 11.1 Access Control
- Document-level access control
- Basket-level access control
- Operation-level permissions
- Route-level access control

### 11.2 Data Protection
- Content encryption
- Secure storage
- Secure transmission
- Configuration encryption

### 11.3 Audit Trail
- Operation logging
- Access logging
- Change tracking
- Route operation tracking

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

DocFlow is designed to be tenant-agnostic and composable. User context is supported for auditing and logging, but all tenant management and access control are handled at the application or orchestration layer.

- **DocFlow Core:** Focuses on document and basket management, processing, and storage.
- **User Context:** Used for operation tracking, audit logging, and optional metadata enrichment.
- **Multi-tenancy:** All tenant-specific logic (provisioning, access control, configuration) is managed outside DocFlow, typically in the API or orchestration layer.

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

- Pass `user_context` to DocFlow for logging/auditing:

```python
user_ctx = UserContext(user_id="alice", tenant_id="tenant1", roles=["admin"])
df = DocFlow(user_context=user_ctx)
df.create_basket("invoices")  # User action is logged
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
│         DocFlow            │
│  - Document management    │
│  - Storage operations     │
│  - Processing             │
└────────────────────────────┘
```

## Implementation Guidelines

- **Database/Storage Config:** Application layer provides tenant-specific config to DocFlow.
- **User Context:** Used for audit logging, not for business logic or access control.
- **Access Control:** Enforced outside DocFlow.

## Benefits

- **Separation of Concerns:** DocFlow is focused and maintainable.
- **Flexibility:** Any multi-tenancy or RBAC model can be layered on top.
- **Security:** No tenant data leakage; access control is centralized.

## Best Practices

- Keep DocFlow core tenant-agnostic.
- Use `UserContext` for logging and traceability.
- Manage all tenant and user access at the orchestration or API layer.
- Pass only the necessary context to DocFlow for auditing.

## Future Considerations

- Enhanced audit logging and traceability.
- User-specific configuration overrides (e.g., storage limits, processor plugins).
- Integration with external IAM or RBAC systems. 