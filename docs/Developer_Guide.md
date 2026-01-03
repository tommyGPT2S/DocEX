# DocEX Developer Guide

Welcome to the DocEX developer guide! This document will help you get started with DocEX, understand its core concepts, and extend it with your own processors and integrations.

---
![DocEX Architecture](DocEX_Architecture.jpeg)

## Table of Contents

1. [Setup & Installation](#1-setup--installation)
2. [Getting Started: DocEX, Baskets, and Documents](#2-getting-started-docex-baskets-and-documents)
3. [Document Capabilities](#3-document-capabilities)
4. [Performance Optimization](#4-performance-optimization)
5. [Platform Integration](#5-platform-integration)
6. [Multi-tenancy](#6-user-context-and-multi-tenancy)
7. [System Status and Validation](#7-system-status-and-validation)
8. [Reference Documentation](#8-reference-documentation)

## 1. Setup & Installation

1. **Install DocEX** (from PyPI or GitHub):
   ```sh
   pip install docex
   # or for latest development version:
   pip install git+https://github.com/tommyGPT2S/DocEX.git
   ```
2. **Initialize DocEX** (run once per environment):
   ```sh
   docex init
   # Follow the prompts to set up config and database
   ```

---

## 2. Getting Started: DocEX, Baskets, and Documents

### Basic Usage (Single-Tenant)

```python
from docex import DocEX

# Initialize DocEX (one-time setup)
DocEX.setup(
    database={'type': 'sqlite', 'sqlite': {'path': 'docex.db'}}
)

# Create DocEX instance
docEX = DocEX()

# Create or get a basket
basket = docEX.create_basket('mybasket', description='My document basket')

# Add a document
doc = basket.add('path/to/file.txt', metadata={'source': 'example'})

# List all baskets
for b in docEX.list_baskets():
    print(b.name)
```

### Multi-Tenant Usage

```python
from docex import DocEX
from docex.context import UserContext
from docex.provisioning.bootstrap import BootstrapTenantManager
from docex.provisioning.tenant_provisioner import TenantProvisioner

# Step 1: Setup and bootstrap (one-time)
DocEX.setup(
    database={'type': 'postgresql', 'postgres': {...}},
    multi_tenancy={'enabled': True, ...}
)

bootstrap_manager = BootstrapTenantManager()
if not bootstrap_manager.is_initialized():
    bootstrap_manager.initialize(created_by='admin')

# Step 2: Provision tenant (one-time per tenant)
provisioner = TenantProvisioner()
if not provisioner.tenant_exists('acme_corp'):
    provisioner.create(
        tenant_id='acme_corp',
        display_name='Acme Corporation',
        created_by='admin'
    )

# Step 3: Use DocEX with tenant
user_context = UserContext(
    user_id='user123',
    tenant_id='acme_corp'  # Required
)
docEX = DocEX(user_context=user_context)
basket = docEX.create_basket('invoices')
```

Please reference examples folders for sample files. 
---

## 3. Platform Integration

For platform integrators who need to bootstrap DocEX from their platform's system settings, see the comprehensive [Platform Integration Guide](Platform_Integration_Guide.md).

### Quick Integration Overview

```python
from docex import DocEX
from docex.provisioning.bootstrap import BootstrapTenantManager
from docex.provisioning.tenant_provisioner import TenantProvisioner
from docex.context import UserContext

# Step 1: Build configuration from platform settings
config = build_docex_config_from_platform(platform_settings)

# Step 2: Initialize DocEX
DocEX.setup(**config)

# Step 3: Bootstrap system tenant (if multi-tenancy enabled)
if config.get('multi_tenancy', {}).get('enabled', False):
    bootstrap_manager = BootstrapTenantManager()
    if not bootstrap_manager.is_initialized():
        bootstrap_manager.initialize(created_by='platform')

# Step 4: Validate setup
if DocEX.is_properly_setup():
    print("✅ DocEX is ready")
else:
    errors = DocEX.get_setup_errors()
    print(f"Setup issues: {errors}")

# Step 5: Provision business tenants
provisioner = TenantProvisioner()
if not provisioner.tenant_exists('acme_corp'):
    provisioner.create(
        tenant_id='acme_corp',
        display_name='Acme Corporation',
        created_by='admin'
    )

# Step 6: Use DocEX with tenant
user_context = UserContext(user_id='user123', tenant_id='acme_corp')
docex = DocEX(user_context=user_context)
basket = docex.create_basket('invoices')
```

**Key Methods for Platform Integration:**
- `DocEX.setup(**config)` - Initialize DocEX with configuration
- `DocEX.is_initialized()` - Check if configuration is loaded
- `DocEX.is_properly_setup()` - Comprehensive validation (read-only)
- `DocEX.get_setup_errors()` - Get detailed error messages
- `BootstrapTenantManager.initialize()` - Bootstrap system tenant
- `TenantProvisioner.create()` - Provision business tenants

See [Platform_Integration_Guide.md](Platform_Integration_Guide.md) for complete integration examples, error handling, and best practices.

---

## 4. Document Capabilities

- **Get document details:**
  ```python
  print(doc.get_details())
  ```
- **Get document content:**
  ```python
  text = doc.get_content(mode='text')
  data = doc.get_content(mode='json')
  bytes_data = doc.get_content(mode='bytes')
  ```
- **Get and update metadata:**
  ```python
  meta = doc.get_metadata()
  # Update metadata
  from docex.services.metadata_service import MetadataService
  MetadataService().update_metadata(doc.id, {'my_key': 'my_value'})
  ```
- **Get document operations:**
  ```python
  print(doc.get_operations())
  ```
- **Efficient document listing with metadata (NEW):**
  ```python
  # Get lightweight document list with selected columns (avoids N+1 queries)
  documents = basket.list_documents_with_metadata(
      columns=['id', 'name', 'document_type', 'status', 'created_at'],
      filters={'document_type': 'invoice', 'status': 'RECEIVED'},
      limit=100,
      offset=0,
      order_by='created_at',
      order_desc=True
  )
  # Returns: [{'id': 'doc_123', 'name': 'invoice_001.pdf', ...}, ...]
  # Much faster than basket.list_documents() for simple listing operations
  ```

---

## 3.1 Choosing the Right Listing Method

DocEX provides multiple methods for listing baskets and documents. Choose the right one based on your needs:

### Basket Listing: `list_baskets()` vs `list_baskets_with_metadata()`

**Use `list_baskets_with_metadata()` when:**
- ✅ You only need basic basket information (id, name, status, dates)
- ✅ You're building dropdowns, lists, or selection UIs
- ✅ Performance is critical for large result sets
- ✅ You need document counts per basket
- ✅ You don't need to call basket methods like `list_documents()`

**Use `list_baskets()` when:**
- ✅ You need full `DocBasket` functionality
- ✅ You'll call methods like `basket.list_documents()`, `basket.add()`, etc.
- ✅ You need access to `storage_config` or other complex properties
- ✅ You need to perform operations on the baskets

**Examples:**

```python
# ✅ FASTEST: Get lightweight basket list with document counts
baskets = docex.list_baskets_with_metadata(
    columns=['id', 'name', 'status', 'document_count'],
    filters={'status': 'active'},
    order_by='document_count',
    order_desc=True,
    limit=50
)
# Returns: [{'id': 'bas_123', 'name': 'invoice_raw', 'status': 'active', 'document_count': 42}, ...]

# ✅ GOOD: Get baskets for dropdown/selection
baskets = docex.list_baskets_with_metadata(
    columns=['id', 'name'],
    order_by='name'
)
# Returns: [{'id': 'bas_123', 'name': 'invoice_raw'}, ...]

# ⚠️  HEAVIER: Use full objects when you need basket methods
baskets = docex.list_baskets(status='active', limit=50)
for basket in baskets:
    # Can call basket methods
    documents = basket.list_documents(limit=10)
    basket.add('path/to/file.pdf')
```

### Document Listing: `list_documents()` vs `list_documents_with_metadata()`

**Use `list_documents_with_metadata()` when:**
- ✅ You only need specific document fields (id, name, status, etc.)
- ✅ You're displaying document lists in UIs
- ✅ Performance is critical (avoids N+1 queries)
- ✅ You don't need full Document object functionality

**Use `list_documents()` when:**
- ✅ You need full `Document` objects with all methods
- ✅ You'll call methods like `document.get_content()`, `document.get_metadata()`, etc.
- ✅ You need to perform operations on the documents

**Examples:**

```python
# ✅ FASTEST: Get lightweight document list
documents = basket.list_documents_with_metadata(
    columns=['id', 'name', 'status', 'created_at'],
    filters={'status': 'RECEIVED'},
    limit=100
)
# Returns: [{'id': 'doc_123', 'name': 'invoice_001.pdf', ...}, ...]

# ⚠️  HEAVIER: Use full objects when you need document methods
documents = basket.list_documents(status='RECEIVED', limit=100)
for doc in documents:
    # Can call document methods
    content = doc.get_content(mode='text')
    metadata = doc.get_metadata()
```

### Performance Comparison

| Operation | Method | Performance | Use Case |
|-----------|--------|-------------|----------|
| List baskets (1000) | `list_baskets()` | ~10ms | Need basket methods |
| List baskets (1000) | `list_baskets_with_metadata()` | ~5ms | Display/selection only |
| List documents (10k) | `list_documents()` | ~50ms | Need document methods |
| List documents (10k) | `list_documents_with_metadata()` | ~20ms | Display/listing only |

*Note: Actual performance depends on database type, hardware, and data distribution*

### Recommended Pattern: Lazy Object Instantiation

**Best Practice:** Even when you need full object functionality, it's often more efficient to:
1. First use `*_with_metadata()` to get IDs and basic info
2. Then instantiate full objects only for items you actually need to work with

This pattern avoids instantiating many objects that might never be used.

**Example: Efficient Basket Operations**

```python
# ✅ EFFICIENT: Get IDs first, then instantiate only what you need
baskets_metadata = docex.list_baskets_with_metadata(
    columns=['id', 'name', 'status', 'document_count'],
    filters={'status': 'active'},
    order_by='document_count',
    order_desc=True,
    limit=100
)

# Display list to user (no object instantiation needed)
for basket_info in baskets_metadata:
    print(f"{basket_info['name']}: {basket_info['document_count']} documents")

# User selects a basket - NOW instantiate the full object
selected_basket_id = baskets_metadata[0]['id']
basket = docex.get_basket(basket_id=selected_basket_id)

# Now use full basket functionality
documents = basket.list_documents(limit=10)
basket.add('path/to/file.pdf')
```

**Example: Efficient Document Operations**

```python
# ✅ EFFICIENT: Get document IDs first, then instantiate only what you need
documents_metadata = basket.list_documents_with_metadata(
    columns=['id', 'name', 'status', 'created_at'],
    filters={'status': 'RECEIVED'},
    limit=100
)

# Display list to user (no object instantiation needed)
for doc_info in documents_metadata:
    print(f"{doc_info['name']} - {doc_info['status']}")

# User selects documents to process - NOW instantiate only those
selected_doc_ids = [doc['id'] for doc in documents_metadata[:5]]  # First 5

for doc_id in selected_doc_ids:
    # Only instantiate objects for documents we actually process
    document = basket.get_document(doc_id)
    content = document.get_content(mode='text')
    # Process document...
```

**Performance Benefits:**

| Scenario | Traditional Approach | Lazy Instantiation | Improvement |
|----------|---------------------|-------------------|-------------|
| List 1000 baskets, use 10 | Instantiate 1000 objects | Instantiate 10 objects | **100x fewer objects** |
| List 10k documents, process 5 | Instantiate 10k objects | Instantiate 5 objects | **2000x fewer objects** |
| Memory usage (1000 baskets) | ~50MB | ~0.5MB | **100x less memory** |

**When to Use Each Pattern:**

- **Use lazy instantiation when:**
  - ✅ Displaying lists/selections to users
  - ✅ Filtering/searching before operations
  - ✅ Processing only a subset of items
  - ✅ Memory is constrained
  - ✅ You have large result sets

- **Use direct full objects when:**
  - ✅ You need to process ALL items
  - ✅ Result set is small (< 100 items)
  - ✅ You need to iterate and call methods immediately
  - ✅ Code simplicity is more important than performance

---

## 6. Using Routes (Upload/Download)

- **List routes:**
  ```python
  for route in docEX.list_routes():
      print(route.name, route.protocol)
  ```
- **Download a file:**
  ```python
  route = docEX.get_route('my_download_route')
  result = route.download('remote_file.txt', 'local_file.txt')
  print(result.message)
  ```
- **Upload a document:**
  ```python
  upload_route = docEX.get_route('my_upload_route')
  result = upload_route.upload_document(doc)
  print(result.message)
  ```

---

## 7. Using Processors (Processing Documents)

- **List available processors:**
  ```sh
  docex processor list
  ```
- **Get a processor for a document:**
  ```python
  from docex.processors.factory import factory
  processor_cls = factory.map_document_to_processor(doc)
  if processor_cls:
      processor = processor_cls(config={})
      result = processor.process(doc)
      print(result.content)
  else:
      print('No processor found for this document.')
  ```

---

## 8. Building Your Own Processor

1. **Create a new processor class:**
   ```python
   from docex.processors.base import BaseProcessor, ProcessingResult
   from docex.document import Document
   from pdfminer.high_level import extract_text
   import io

   class MyPDFTextProcessor(BaseProcessor):
       def can_process(self, document: Document) -> bool:
           return document.name.lower().endswith('.pdf')

       def process(self, document: Document) -> ProcessingResult:
           pdf_bytes = document.get_content(mode='bytes')
           text = extract_text(io.BytesIO(pdf_bytes))
           return ProcessingResult(success=True, content=text)
   ```
2. **Dynamically add a processor mapping rule:**
   Instead of editing the main package, you can patch the processor mapping at runtime:
   ```python
   from docex.processors.factory import factory
   from my_pdf_text_processor import MyPDFTextProcessor

   def pdf_rule(document):
       if document.name.lower().endswith('.pdf'):
           return MyPDFTextProcessor
       return None

   factory.mapper.rules.insert(0, pdf_rule)  # Highest priority
   ```
   This allows you to use your custom processor for PDFs (or any custom logic) without modifying DocEX internals.
3. **Register your processor (optional):**
   ```sh
   docex processor register --name MyPDFTextProcessor --type content_processor --description "Extracts text from PDFs" --config '{}'
   ```
4. **Add a mapping rule (optional):**
   You can still edit `docex/processors/mapper.py` for static rules, but dynamic patching is recommended for custom/external processors.

---

## 9. Best Practices & Tips

- Always use the Document API for content and metadata access (never access storage directly).
- Use baskets to organize documents by business context.
- Use metadata to enrich and search documents.
- Add custom processors for your business logic and register them via the CLI.
- Keep mapping logic in `mapper.py` for easy extensibility.

---

## 10. Configuring Storage and Database Backends

DocEX supports multiple storage and database backends. You can configure these in your config file (usually `~/.docex/config.yaml`) or during `docex init`.

### Change Database Backend to Postgres

Edit your config file or use the CLI to set:

```yaml
database:
  type: postgres
  postgres:
    host: localhost
    port: 5432
    database: docex
    user: docex
    password: secret
    schema: docex
```

- Make sure the Postgres server is running and the user/database exist.
- Re-run `docex init` if you want to reinitialize the database.

### Change Storage Backend to S3

Edit your config file:

```yaml
storage:
  type: s3
  s3:
    bucket: docex-bucket
    region: us-east-1
    # Optional: credentials (can also use environment variables or IAM roles)
    access_key: your-access-key
    secret_key: your-secret-key
    # S3 path configuration
    path_namespace: finance_dept  # Optional: business identifier
    prefix: production  # Optional: environment prefix
    # Optional: retry configuration
    max_retries: 3
    retry_delay: 1.0
    # Optional: timeout configuration
    connect_timeout: 60
    read_timeout: 60
```

**S3 Path Structure:**
DocEX uses a three-part S3 path structure for organization:
- **Part A (Config Prefix)**: `{tenant_id}/{path_namespace}/{prefix}/` - Set from configuration
- **Part B (Basket Path)**: `{basket_name}_{last_4_of_basket_id}/` - Set when basket is created
- **Part C (Document Path)**: `{document_name}_{last_6_of_document_id}.{ext}` - Set when document is added

**Example S3 Path:**
```
s3://my-bucket/acme_corp/finance_dept/production/invoice_raw_2c03/invoice_001_585d29.pdf
```
- Part A: `acme_corp/finance_dept/production/`
- Part B: `invoice_raw_2c03/`
- Part C: `invoice_001_585d29.pdf`

See [S3_PATH_STRUCTURE.md](S3_PATH_STRUCTURE.md) for detailed documentation.

**Credential Sources (in priority order):**
1. Config file credentials (highest priority)
2. Environment variables (`AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`, `AWS_SESSION_TOKEN`)
3. IAM role / instance profile (for EC2/ECS)
4. AWS profile from `~/.aws/credentials` (lowest priority)

**Using Environment Variables:**
```yaml
storage:
  default_type: s3
  s3:
    bucket: docex-bucket
    region: us-east-1
    # Credentials will be read from environment variables
```

```bash
export AWS_ACCESS_KEY_ID=your-access-key
export AWS_SECRET_ACCESS_KEY=your-secret-key
export AWS_DEFAULT_REGION=us-east-1
```

**Using IAM Roles (EC2/ECS):**
```yaml
storage:
  default_type: s3
  s3:
    bucket: docex-bucket
    region: us-east-1
    # No credentials needed - IAM role will be used automatically
```

**Per-Basket S3 Configuration:**
You can configure per-basket storage by passing a storage config when creating a basket:
  ```python
  basket = docEX.create_basket('mybasket', storage_config={
      'type': 's3',
      's3': {
          'bucket': 'my-bucket',
          'region': 'us-east-1',
          'prefix': 'mybasket/',  # Optional prefix for this basket
          'access_key': '...',  # Optional
          'secret_key': '...'   # Optional
      }
  })
  ```

**S3 Storage Features:**
- Automatic retry on transient errors (500, 503, throttling, timeouts)
- Configurable retry attempts and delays
- Support for S3 key prefixes for organizing files
- Presigned URL generation for secure access
- Comprehensive error handling and logging

### Change Storage Backend to Filesystem (default)

```yaml
storage:
  default_type: filesystem
  filesystem:
    base_path: /path/to/storage
```

---

## 11. Reference: Standard Metadata Keys (ENUM)

DocEX provides a set of standard metadata keys in `docex/models/metadata_keys.py` via the `MetadataKey` enum. These help you use consistent, searchable metadata across your documents.

### Common Metadata Keys

- File-related:
  - `MetadataKey.ORIGINAL_PATH` → 'original_path'
  - `MetadataKey.FILE_TYPE` → 'file_type'
  - `MetadataKey.FILE_SIZE` → 'file_size'
  - `MetadataKey.FILE_EXTENSION` → 'file_extension'
  - `MetadataKey.ORIGINAL_FILE_TIMESTAMP` → 'original_file_timestamp'
- Processing:
  - `MetadataKey.PROCESSING_STATUS` → 'processing_status'
  - `MetadataKey.PROCESSING_ERROR` → 'processing_error'
- Business:
  - `MetadataKey.RELATED_PO` → 'related_po'
  - `MetadataKey.CUSTOMER_ID` → 'customer_id'
  - `MetadataKey.INVOICE_NUMBER` → 'invoice_number'
- Security:
  - `MetadataKey.ACCESS_LEVEL` → 'access_level'
- Audit:
  - `MetadataKey.CREATED_BY` → 'created_by'
  - `MetadataKey.CREATED_AT` → 'created_at'

### Usage Example

```python
from docex.models.metadata_keys import MetadataKey
from docex.services.metadata_service import MetadataService

# Set standard metadata
MetadataService().update_metadata(doc.id, {
    MetadataKey.FILE_TYPE.value: 'pdf',
    MetadataKey.CUSTOMER_ID.value: 'CUST-123',
    MetadataKey.INVOICE_NUMBER.value: 'INV-2024-001',
})

# Get metadata
meta = doc.get_metadata()
print(meta[MetadataKey.FILE_TYPE.value])  # e.g., 'pdf'

# Use custom metadata keys
custom_key = MetadataKey.get_custom_key('my_custom_field')
MetadataService().update_metadata(doc.id, {custom_key: 'custom_value'})
```

---

## 12. User Context and Multi-tenancy

### User Context
DocEX supports user context for audit logging and operation tracking. The `UserContext` class provides a way to track user operations and enforce multi-tenancy.

```python
from docex.context import UserContext
from docex import DocEX

# Create user context (user_id is required)
user_context = UserContext(
    user_id="user123",  # Required
    user_email="user@example.com",
    tenant_id="acme_corp",  # Required for multi-tenant setups
    roles=["admin"],
    attributes={"department": "finance"}
)

# Initialize DocEX with user context
# Note: When multi-tenancy is enabled, UserContext with tenant_id is REQUIRED
docEX = DocEX(user_context=user_context)
```

The user context is used for:
- Audit logging of operations
- Operation tracking
- User-aware logging
- Multi-tenancy enforcement (tenant_id is required when multi-tenancy is enabled)

### Multi-tenancy

DocEX 3.0 supports explicit tenant provisioning with schema-level isolation. Each tenant has its own database schema (PostgreSQL) or database file (SQLite), providing physical data isolation.

#### DocEX 3.0 Multi-tenancy (Recommended) ✅

**Key Features:**
- Explicit tenant provisioning (no lazy creation)
- Schema-level isolation (PostgreSQL) or database-level isolation (SQLite)
- Bootstrap tenant for system metadata
- Tenant registry for managing all tenants
- Strong data isolation and compliance-ready

**Configuration:**
```yaml
# ~/.docex/config.yaml
multi_tenancy:
  enabled: true
  isolation_strategy: schema  # 'schema' for PostgreSQL, 'database' for SQLite
  bootstrap_tenant:
    id: _docex_system_
    display_name: DocEX System
    schema: docex_system
    database_path: null  # Only for SQLite
```

**Initialization Flow:**
```python
from docex import DocEX
from docex.provisioning.bootstrap import BootstrapTenantManager
from docex.provisioning.tenant_provisioner import TenantProvisioner
from docex.context import UserContext

# Step 1: Setup DocEX configuration
DocEX.setup(
    database={'type': 'postgresql', 'postgres': {...}},
    multi_tenancy={'enabled': True, ...}
)

# Step 2: Bootstrap system tenant (one-time setup)
bootstrap_manager = BootstrapTenantManager()
if not bootstrap_manager.is_initialized():
    bootstrap_manager.initialize(created_by='admin')

# Step 3: Validate setup (read-only check, no side effects)
if DocEX.is_properly_setup():
    print("✅ DocEX is ready")
else:
    errors = DocEX.get_setup_errors()
    print(f"Setup issues: {errors}")

# Step 4: Provision business tenants
provisioner = TenantProvisioner()
if not provisioner.tenant_exists('acme_corp'):
    provisioner.create(
        tenant_id='acme_corp',
        display_name='Acme Corporation',
        created_by='admin'
    )

# Step 5: Use DocEX with tenant
user_context = UserContext(
    user_id='user123',
    tenant_id='acme_corp'  # Required for multi-tenant
)
docex = DocEX(user_context=user_context)
basket = docex.create_basket('invoices')
```

**Tenant Provisioning:**
```python
from docex.provisioning.tenant_provisioner import TenantProvisioner, TenantExistsError, InvalidTenantIdError

provisioner = TenantProvisioner()

# Check if tenant exists (always fresh query, no stale cache)
if provisioner.tenant_exists('acme_corp'):
    print("Tenant already exists")

# Provision a new tenant
try:
    tenant = provisioner.create(
        tenant_id='acme_corp',
        display_name='Acme Corporation',
        created_by='admin',
        isolation_strategy='schema'  # Auto-detected if None
    )
    print(f"✅ Tenant provisioned: {tenant.tenant_id}")
except TenantExistsError:
    print("Tenant already exists")
except InvalidTenantIdError as e:
    print(f"Invalid tenant ID: {e}")
```

#### Legacy: Database-Level Isolation (v2.x)

For backward compatibility, DocEX still supports v2.x database-level multi-tenancy:

**Configuration**:
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

# Tenant 1
user_context1 = UserContext(user_id="alice", tenant_id="tenant1")
docEX1 = DocEX(user_context=user_context1)
basket1 = docEX1.create_basket("invoices")  # Uses tenant1 schema

# Tenant 2 (isolated)
user_context2 = UserContext(user_id="bob", tenant_id="tenant2")
docEX2 = DocEX(user_context=user_context2)
basket2 = docEX2.create_basket("invoices")  # Uses tenant2 schema
```

**Features**:
- ✅ Automatic database/schema routing based on `UserContext.tenant_id`
- ✅ Connection pooling per tenant
- ✅ Automatic schema/database creation for new tenants
- ✅ Thread-safe connection management
- ✅ Support for SQLite (separate DB files) and PostgreSQL (separate schemas)

**Benefits**:
- Strongest data isolation (physical separation)
- Best for compliance (HIPAA, GDPR, SOX)
- Independent scaling per tenant
- No risk of cross-tenant data leaks

#### Application Layer Tenant Management

For applications using row-level isolation or custom tenant management, tenant logic should be handled at the upper layer:

1. **Database Configuration**
   - Configure separate databases or schemas per tenant
   - Use connection pooling with tenant-specific credentials
   - Handle database routing at the application layer

2. **Storage Configuration**
   - Configure separate storage paths per tenant
   - Manage storage quotas and access at the application layer
   - Handle storage path routing based on tenant context

3. **Access Control**
   - Implement tenant-specific access control at the application layer
   - Use middleware or decorators for tenant validation
   - Handle user-tenant mapping in the application layer

Example of tenant management at the application layer:
```python
class TenantAwareDocEX:
    def __init__(self, tenant_id: str):
        self.tenant_id = tenant_id
        self.db_config = self._get_tenant_db_config()
        self.storage_config = self._get_tenant_storage_config()
        
    def _get_tenant_db_config(self):
        # Get tenant-specific database configuration
        return {
            "type": "postgres",
            "database": f"tenant_{self.tenant_id}",
            # ... other config
        }
        
    def _get_tenant_storage_config(self):
        # Get tenant-specific storage configuration
        return {
            "filesystem": {
                "path": f"/storage/tenant_{self.tenant_id}"
            }
        }
        
    def get_docex(self, user_context: UserContext):
        # Initialize DocEX with tenant-specific config
        DocEX.setup(
            database=self.db_config,
            storage=self.storage_config
        )
        return DocEX(user_context=user_context)
```

### Best Practices
1. **Keep DocEX Focused**
   - Use DocEX for document management only
   - Handle tenant logic at the application layer
   - Use user context for auditing and logging

2. **Configuration Management**
   - Store tenant configurations separately
   - Use environment variables for sensitive data
   - Implement configuration validation

3. **Security**
   - Validate tenant access at the application layer
   - Use proper authentication and authorization
   - Implement audit logging for all operations

4. **Performance**
   - Use connection pooling for database access
   - Implement caching where appropriate
   - Monitor resource usage per tenant

---

## 13. System Status and Validation

### Checking DocEX Setup Status

DocEX provides read-only status checking methods that do not modify system state:

```python
from docex import DocEX

# Quick check if configuration is loaded
if DocEX.is_initialized():
    print("✅ DocEX configuration is loaded")

# Comprehensive setup validation (read-only, no side effects)
if DocEX.is_properly_setup():
    print("✅ DocEX is properly set up and ready for use")
else:
    # Get detailed error messages
    errors = DocEX.get_setup_errors()
    for error in errors:
        print(f"  - {error}")
```

**Important:** `is_properly_setup()` is a **read-only** status check. It does not create schemas, tables, or perform any setup operations. It only validates that everything is already set up correctly.

### Bootstrap Tenant Status

```python
from docex.provisioning.bootstrap import BootstrapTenantManager

bootstrap_manager = BootstrapTenantManager()

# Check if bootstrap tenant is initialized
if bootstrap_manager.is_initialized():
    print("✅ Bootstrap tenant is ready")
else:
    print("⚠️  Bootstrap tenant not initialized")
    bootstrap_manager.initialize(created_by='admin')
```

### Tenant Existence Check

```python
from docex.provisioning.tenant_provisioner import TenantProvisioner

provisioner = TenantProvisioner()

# Check if tenant exists (always fresh query, no stale cache)
if provisioner.tenant_exists('acme_corp'):
    print("Tenant exists")
else:
    print("Tenant does not exist")
```

**Note:** `tenant_exists()` always queries the database directly to ensure fresh results and avoid stale cache issues.

---

## 14. Reference Documentation

- **[API Reference](API_Reference.md)** - Complete API documentation
- **[Platform Integration Guide](Platform_Integration_Guide.md)** - Platform integration patterns and examples
- **[Multi-Tenancy Guide](MULTI_TENANCY_GUIDE.md)** - Detailed multi-tenancy documentation
- **[Tenant Provisioning](TENANT_PROVISIONING.md)** - Tenant provisioning guide
- **[S3 Path Structure](S3_PATH_STRUCTURE.md)** - S3 path structure documentation
- **[CLI Guide](CLI_GUIDE.md)** - Command-line interface reference
- **[DocBasket Usage Guide](DocBasket_Usage_Guide.md)** - Basket operations guide
- **[Test Scripts Summary](Test_Scripts_Summary.md)** - Available test scripts

---

Happy coding with DocEX! 