# DocFlow Developer Guide

Welcome to the DocFlow developer guide! This document will help you get started with DocFlow, understand its core concepts, and extend it with your own processors and integrations.

---

## 1. Setup & Installation

1. **Install DocFlow** (from PyPI or GitHub):
   ```sh
   pip install docflow
   # or for latest development version:
   pip install git+https://github.com/tommyGPT2S/DocFlow.git
   ```
2. **Initialize DocFlow** (run once per environment):
   ```sh
   docflow init
   # Follow the prompts to set up config and database
   ```

---

## 2. Getting Started: DocFlow, Baskets, and Documents

```python
from docflow import DocFlow

# Create DocFlow instance
flow = DocFlow()

# Create or get a basket
basket = flow.basket('mybasket')

# Add a document
doc = basket.add('path/to/file.txt', metadata={'source': 'example'})

# List all baskets
for b in flow.list_baskets():
    print(b.name)
```

---

## 3. Document Capabilities

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
  from docflow.services.metadata_service import MetadataService
  MetadataService().update_metadata(doc.id, {'my_key': 'my_value'})
  ```
- **Get document operations:**
  ```python
  print(doc.get_operations())
  ```

---

## 4. Using Routes (Upload/Download)

- **List routes:**
  ```python
  for route in flow.list_routes():
      print(route.name, route.protocol)
  ```
- **Download a file:**
  ```python
  route = flow.get_route('my_download_route')
  result = route.download('remote_file.txt', 'local_file.txt')
  print(result.message)
  ```
- **Upload a document:**
  ```python
  upload_route = flow.get_route('my_upload_route')
  result = upload_route.upload_document(doc)
  print(result.message)
  ```

---

## 5. Using Processors (Processing Documents)

- **List available processors:**
  ```sh
  docflow processor list
  ```
- **Get a processor for a document:**
  ```python
  from docflow.processors.factory import factory
  processor_cls = factory.map_document_to_processor(doc)
  if processor_cls:
      processor = processor_cls(config={})
      result = processor.process(doc)
      print(result.content)
  else:
      print('No processor found for this document.')
  ```

---

## 6. Building Your Own Processor

1. **Create a new processor class:**
   ```python
   from docflow.processors.base import BaseProcessor, ProcessingResult
   from docflow.document import Document

   class MyTextProcessor(BaseProcessor):
       def can_process(self, document: Document) -> bool:
           return document.name.lower().endswith('.txt')

       def process(self, document: Document) -> ProcessingResult:
           text = self.get_document_text(document)
           # Do something with text...
           return ProcessingResult(success=True, content=text.upper())
   ```
2. **Register your processor:**
   ```sh
   docflow processor register --name MyTextProcessor --type content_processor --description "Uppercases text files" --config '{}'
   ```
3. **Add a mapping rule (optional):**
   Edit `docflow/processors/mapper.py` to add a rule for your processor.

---

## 7. Best Practices & Tips

- Always use the Document API for content and metadata access (never access storage directly).
- Use baskets to organize documents by business context.
- Use metadata to enrich and search documents.
- Add custom processors for your business logic and register them via the CLI.
- Keep mapping logic in `mapper.py` for easy extensibility.

---

## 8. Configuring Storage and Database Backends

DocFlow supports multiple storage and database backends. You can configure these in your config file (usually `~/.docflow/config.yaml`) or during `docflow init`.

### Change Database Backend to Postgres

Edit your config file or use the CLI to set:

```yaml
database:
  type: postgres
  postgres:
    host: localhost
    port: 5432
    database: docflow
    user: docflow
    password: secret
    schema: docflow
```

- Make sure the Postgres server is running and the user/database exist.
- Re-run `docflow init` if you want to reinitialize the database.

### Change Storage Backend to S3

Edit your config file:

```yaml
storage:
  default_type: s3
  s3:
    bucket: docflow-bucket
    access_key: your-access-key
    secret_key: your-secret-key
    region: us-east-1
```

- Make sure your AWS credentials and bucket are correct.
- You can also configure per-basket storage by passing a storage config when creating a basket:
  ```python
  basket = flow.create_basket('mybasket', storage_config={
      'type': 's3',
      'bucket': 'my-bucket',
      'access_key': '...',
      'secret_key': '...',
      'region': 'us-east-1'
  })
  ```

### Change Storage Backend to Filesystem (default)

```yaml
storage:
  default_type: filesystem
  filesystem:
    base_path: /path/to/storage
```

---

## 9. Reference: Standard Metadata Keys (ENUM)

DocFlow provides a set of standard metadata keys in `docflow/models/metadata_keys.py` via the `MetadataKey` enum. These help you use consistent, searchable metadata across your documents.

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
from docflow.models.metadata_keys import MetadataKey
from docflow.services.metadata_service import MetadataService

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

- You can use any of the keys in `MetadataKey` for consistent metadata.
- For custom fields, use the `get_custom_key` helper to ensure proper prefixing.

---

## User Context and Multi-tenancy

### User Context
DocFlow supports user context for audit logging and operation tracking. The `UserContext` class provides a way to track user operations without implementing tenant-specific logic.

```python
from docflow.context import UserContext
from docflow.docflow import DocFlow

# Create user context
user_context = UserContext(
    user_id="user123",
    user_email="user@example.com",
    roles=["admin"]
)

# Initialize DocFlow with user context
df = DocFlow(user_context=user_context)
```

The user context is used for:
- Audit logging of operations
- Operation tracking
- User-aware logging

### Multi-tenancy
DocFlow is designed to be tenant-agnostic, focusing on its core document management responsibilities. Tenant management should be handled at the upper layer:

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
class TenantAwareDocFlow:
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
        
    def get_docflow(self, user_context: UserContext):
        # Initialize DocFlow with tenant-specific config
        DocFlow.setup(
            database=self.db_config,
            storage=self.storage_config
        )
        return DocFlow(user_context=user_context)
```

### Best Practices
1. **Keep DocFlow Focused**
   - Use DocFlow for document management only
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

Happy coding with DocFlow! 