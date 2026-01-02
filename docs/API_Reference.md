# DocEX Python API Reference

![DocEX Architecture](DocEX_Architecture.jpeg)

This reference covers the main public classes and methods in DocEX. For more details and advanced usage, see the [Developer Guide](Developer_Guide.md).

---

## DocEX

The main entry point for all document and transport operations.

### Class Methods

```python
from docex import DocEX

# Setup DocEX configuration (one-time)
DocEX.setup(
    database={'type': 'postgresql', 'postgres': {...}},
    storage={'type': 's3', 's3': {...}},
    multi_tenancy={'enabled': True, ...}
)

# Check if DocEX is initialized
if DocEX.is_initialized():
    print("Configuration loaded")

# Check if DocEX is properly set up (read-only, no side effects)
if DocEX.is_properly_setup():
    print("✅ DocEX is ready")
else:
    errors = DocEX.get_setup_errors()
    print(f"Issues: {errors}")

# Get default configuration
defaults = DocEX.get_defaults()
```

### Instance Methods

```python
from docex import DocEX
from docex.context import UserContext

# Create an instance (with UserContext for multi-tenant)
user_context = UserContext(user_id='user123', tenant_id='acme_corp')
docEX = DocEX(user_context=user_context)

# List baskets
baskets = docEX.list_baskets()

# Create a basket
basket = docEX.create_basket('mybasket', description='My basket')

# Get a basket by name
basket = docEX.basket('mybasket')

# Get a basket by ID
basket = docEX.get_basket('bas_123...')

# List routes
routes = docEX.list_routes()

# Get a route
route = docEX.get_route('local_backup')
```

---

## DocBasket

A container for related documents with its own storage configuration.

### Class Methods

```python
from docex.docbasket import DocBasket

# Create a basket
basket = DocBasket.create(
    name='invoices',
    description='Invoice documents',
    storage_config={'type': 's3', 's3': {...}}
)

# Get basket by ID
basket = DocBasket.get('bas_123...')

# Find basket by name
basket = DocBasket.find_by_name('invoices')

# List all baskets
baskets = DocBasket.list()
```

### Instance Methods

```python
# Add a document
doc = basket.add('path/to/file.txt', document_type='file', metadata={'source': 'example'})

# List documents (returns full Document objects)
docs = basket.list_documents(limit=100, offset=0, order_by='created_at', order_desc=True)

# Efficient document listing with metadata (NEW - lightweight, avoids N+1 queries)
documents = basket.list_documents_with_metadata(
    columns=['id', 'name', 'document_type', 'status', 'created_at'],
    filters={'document_type': 'invoice', 'status': 'RECEIVED'},
    limit=100,
    offset=0,
    order_by='created_at',
    order_desc=True
)
# Returns: [{'id': 'doc_123', 'name': 'invoice_001.pdf', ...}, ...]

# Count documents
count = basket.count_documents(status='RECEIVED')

# Find documents by metadata
docs = basket.find_documents_by_metadata(
    metadata={'category': 'invoice'},
    limit=50
)

# Get document by ID
doc = basket.get_document('doc_123...')

# Update document
updated_doc = basket.update_document('doc_123...', 'path/to/new_file.txt')

# Delete document
basket.delete_document('doc_123...')

# Get basket statistics
stats = basket.get_stats()
# Returns: {'document_count': 10, 'total_size': 1024000, ...}

# Delete basket
basket.delete()
```

---

## Document

Represents an individual document and its metadata.

```python
# Get document details
print(doc.get_details())

# Get content
text = doc.get_content(mode='text')

# Get and update metadata
meta = doc.get_metadata()
doc.update_metadata({'my_key': 'my_value'})

# Get document operations
ops = doc.get_operations()

# Get metadata as a plain dictionary
meta_dict = doc.get_metadata_dict()
```

---

## Route

Represents a transport route for uploading, downloading, and managing files.

```python
# Upload a document
result = route.upload_document(doc)
print(result.message)

# Download a file
result = route.download('remote_file.txt', 'local_file.txt')
print(result.message)

# List files
result = route.list_files()
print(result.details)
```

---

## BaseProcessor & Processor Registration

Processors transform or extract data from documents. You can create and register your own.

```python
from docex.processors.base import BaseProcessor, ProcessingResult
from docex.document import Document

class MyTextProcessor(BaseProcessor):
    def can_process(self, document: Document) -> bool:
        return document.name.lower().endswith('.txt')

    def process(self, document: Document) -> ProcessingResult:
        text = self.get_document_text(document)
        return ProcessingResult(success=True, content=text.upper())

# Register via CLI
# docex processor register --name MyTextProcessor --type content_processor --description "Uppercases text files" --config '{}'
```

---

## MetadataService

Service for managing document metadata.

```python
from docex.services.metadata_service import MetadataService

# Get metadata
meta = MetadataService().get_metadata(doc.id)

# Update metadata
MetadataService().update_metadata(doc.id, {'key': 'value'})
```

---

## UserContext

Context object for carrying user-specific information through DocEX operations. **Required** when multi-tenancy is enabled.

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

# Check if user has role
if user_context.has_role("admin"):
    print("User is admin")

# Get user attribute
dept = user_context.get_attribute("department", default="unknown")

# Initialize DocEX with user context
docEX = DocEX(user_context=user_context)
```

**Attributes:**
- `user_id` (str, required): Unique identifier for the user
- `user_email` (str, optional): Email address of the user
- `tenant_id` (str, optional): Tenant identifier (required for multi-tenant)
- `roles` (List[str], optional): List of user roles for RBAC
- `attributes` (Dict, optional): Custom user attributes and settings

---

## File History

Track file movements and history for a document.

```python
from docex.services.document_service import DocumentService
from docex.db.connection import Database

# Get file history for a document
db = Database()
service = DocumentService(db, basket_id)
history = service.get_file_history(doc.id)
for entry in history:
    print(entry.original_path, entry.internal_path)
```

---

## Duplicate Detection

Check for and mark duplicate documents.

```python
from docex.services.document_service import DocumentService
from docex.db.connection import Database

# Check for duplicates
db = Database()
service = DocumentService(db, basket_id)
info = service.check_for_duplicates(source, checksum)
print(info['is_duplicate'])

# Mark a document as duplicate
service.mark_as_duplicate(dup_id, orig_id)
```

---

## Operation Tracking

Track document operations and their dependencies.

```python
# Get document operations
ops = doc.get_operations()
for op in ops:
    print(op['operation_type'], op['status'])

# Get operation dependencies
from docex.db.repository import BaseRepository
deps = BaseRepository.get_dependencies(operation_id)
```

---

## Advanced Metadata

Retrieve extended metadata for a document.

```python
# Get all metadata as a plain dictionary
meta_dict = doc.get_metadata_dict()
```

---

## Storage Backends

DocEX supports multiple storage backends including filesystem and S3.

### Filesystem Storage

Default storage backend using local filesystem:

```python
# Configured in config.yaml
storage:
  type: filesystem
  filesystem:
    path: /path/to/storage
```

### S3 Storage

Amazon S3 storage backend with support for multiple credential sources:

```python
# Configured in config.yaml
storage:
  type: s3
  s3:
    bucket: docex-bucket
    region: us-east-1
    # Optional: credentials (can use env vars or IAM roles)
    access_key: your-access-key
    secret_key: your-secret-key
    # Optional: prefix for organizing files
    prefix: docex/
```

**S3 Storage Features:**
- Automatic retry on transient errors
- Support for environment variables and IAM roles
- Configurable timeouts and retry settings
- Presigned URL generation
- Prefix support for file organization

**Example: Using S3 Storage**
```python
from docex import DocEX

# Configure S3 storage
docEX = DocEX()

# Create basket with S3 storage
basket = docEX.create_basket('mybasket', storage_config={
    'type': 's3',
    's3': {
        'bucket': 'my-bucket',
        'region': 'us-east-1',
        'prefix': 'mybasket/'
    }
})

# Add document (stored in S3)
doc = basket.add('path/to/file.pdf')
```

## TenantProvisioner

Handles explicit tenant provisioning for DocEX 3.0 multi-tenancy.

```python
from docex.provisioning.tenant_provisioner import TenantProvisioner, TenantExistsError, InvalidTenantIdError

provisioner = TenantProvisioner()

# Check if tenant exists (always fresh query, no stale cache)
if provisioner.tenant_exists('acme_corp'):
    print("Tenant exists")

# Validate tenant ID
provisioner.validate_tenant_id('acme_corp')  # Raises InvalidTenantIdError if invalid

# Check if tenant is system tenant
if TenantProvisioner.is_system_tenant('_docex_system_'):
    print("System tenant")

# Provision a new tenant
try:
    tenant = provisioner.create(
        tenant_id='acme_corp',
        display_name='Acme Corporation',
        created_by='admin',
        isolation_strategy='schema'  # 'schema' for PostgreSQL, 'database' for SQLite (auto-detected if None)
    )
    print(f"✅ Tenant provisioned: {tenant.tenant_id}")
except TenantExistsError:
    print("Tenant already exists")
except InvalidTenantIdError as e:
    print(f"Invalid tenant ID: {e}")
```

**Methods:**
- `tenant_exists(tenant_id: str, use_cache: bool = False) -> bool`: Check if tenant exists
- `validate_tenant_id(tenant_id: str) -> None`: Validate tenant ID format
- `create(tenant_id: str, display_name: str, created_by: str, isolation_strategy: Optional[str] = None) -> TenantRegistry`: Provision a new tenant
- `is_system_tenant(tenant_id: str) -> bool`: Check if tenant ID is a system tenant

## BootstrapTenantManager

Manages the bootstrap/system tenant for DocEX 3.0.

```python
from docex.provisioning.bootstrap import BootstrapTenantManager

bootstrap_manager = BootstrapTenantManager()

# Check if bootstrap tenant is initialized
if bootstrap_manager.is_initialized():
    print("✅ Bootstrap tenant ready")
else:
    # Initialize bootstrap tenant (one-time setup)
    tenant = bootstrap_manager.initialize(created_by='admin')
    print(f"✅ Bootstrap tenant initialized: {tenant.tenant_id}")

# Get bootstrap tenant
bootstrap_tenant = bootstrap_manager.get_bootstrap_tenant()
```

**Methods:**
- `is_initialized() -> bool`: Check if bootstrap tenant is initialized
- `initialize(created_by: str = "system") -> TenantRegistry`: Initialize bootstrap tenant
- `get_bootstrap_tenant() -> Optional[TenantRegistry]`: Get bootstrap tenant record

## S3 Path Structure

DocEX uses a three-part S3 path structure for organization:

- **Part A (Config Prefix)**: `{tenant_id}/{path_namespace}/{prefix}/` - From configuration
- **Part B (Basket Path)**: `{basket_name}_{last_4_of_basket_id}/` - Set when basket is created
- **Part C (Document Path)**: `{document_name}_{last_6_of_document_id}.{ext}` - Set when document is added

**Example:**
```
s3://my-bucket/acme_corp/finance_dept/production/invoice_raw_2c03/invoice_001_585d29.pdf
```

**Storage in Database:**
- Part A + Part B: Stored in `basket.storage_config['s3']['config_prefix']` and `basket.storage_config['s3']['basket_path']`
- Full path (A+B+C): Stored in `document.path`

See [S3_PATH_STRUCTURE.md](S3_PATH_STRUCTURE.md) for detailed documentation.

## More
- See the [Developer Guide](Developer_Guide.md) for advanced topics, configuration, and extensibility.
- See the [Platform Integration Guide](Platform_Integration_Guide.md) for platform integration patterns.
- See the [Design Document](DocEX_Design.md) for architecture and design principles.
- See the [S3 Storage Troubleshooting Guide](S3_Storage_Troubleshooting.md) for S3-specific issues.
- See the [S3 Path Structure Guide](S3_PATH_STRUCTURE.md) for S3 path organization. 