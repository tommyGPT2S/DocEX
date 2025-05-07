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

Happy coding with DocFlow! 