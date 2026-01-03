# ID-Centric Operations Architecture

## Overview

All DocEX operations now center around `basket_id` and `document_id`. Paths are internal implementation details that users never need to interpret or work with directly.

## Architecture Principles

1. **Users work with IDs only**: All user-facing operations use `basket_id` and `document_id`
2. **Paths are built internally**: `DocEXPathBuilder` builds full paths from IDs
3. **Storage receives full paths**: S3Storage and other storage backends receive complete, pre-resolved paths (no interpretation)
4. **Centralized path building**: All path building logic is in `DocEXPathBuilder`

## Class Responsibilities

### DocEXPathBuilder
**Location**: `docex/storage/path_builder.py`

**Purpose**: Builds complete operational paths from `basket_id` and `document_id`

**Key Methods**:
- `build_document_path(basket_id, document_id, basket_name, document_name, file_ext, tenant_id)` → Full document path
- `build_basket_path(basket_id, basket_name, tenant_id)` → Full basket path

**Used By**: `DocBasket` for all storage operations

### DocEXPathResolver
**Location**: `docex/config/path_resolver.py`

**Purpose**: Resolves configuration-based path components from `config.yaml`

**Key Methods**:
- `resolve_s3_prefix(tenant_id)` → Tenant prefix
- `resolve_s3_basket_prefix(tenant_id, basket_id, basket_name)` → Basket prefix

**Used By**: `DocEXPathBuilder` internally for configuration-based prefixes

### S3Storage
**Location**: `docex/storage/s3_storage.py`

**Purpose**: Low-level storage abstraction - accepts full paths, no interpretation

**Key Changes**:
- ❌ Removed: `_get_full_key()` and prefix interpretation logic
- ✅ Added: `_normalize_key()` - only normalizes path format (removes leading slashes)
- ✅ All methods now accept full paths and document this requirement

### DocBasket
**Location**: `docex/docbasket.py`

**Purpose**: User-facing basket operations - all centered around IDs

**Key Changes**:
- ✅ Initializes `DocEXPathBuilder` in `__init__`
- ✅ `_get_document_path()` now uses `DocEXPathBuilder.build_document_path()`
- ✅ `add()` builds full path from IDs before storing
- ✅ `get_document()` rebuilds path from IDs for consistency
- ✅ `delete_document()` builds path from IDs before deleting

### StorageService
**Location**: `docex/services/storage_service.py`

**Purpose**: Service layer for storage operations

**Key Changes**:
- ✅ `store_document(source_path, full_document_path)` - accepts full path
- ✅ `retrieve_document(full_document_path)` - accepts full path
- ✅ `delete_document(full_document_path)` - accepts full path

## Operation Flow

### Adding a Document

```
User: basket.add(file_path, metadata={...})
  ↓
DocBasket.add():
  1. Create DocumentModel with document_id
  2. Build full path: path_builder.build_document_path(
       basket_id=self.id,
       document_id=document.id,
       basket_name=self.name,
       document_name=readable_name,
       file_ext=ext,
       tenant_id=tenant_id
     )
  3. Store: storage_service.store_document(source_path, full_path)
  4. Save full_path to database
  ↓
S3Storage.save(full_path, content)  ← Receives full path, no interpretation
```

### Getting a Document

```
User: basket.get_document(document_id)
  ↓
DocBasket.get_document():
  1. Load DocumentModel from database
  2. Rebuild full path from IDs: path_builder.build_document_path(...)
     (Ensures consistency even if config changed)
  3. Return Document with full_path
  ↓
Document.get_content():
  storage_service.retrieve_document(full_path)
  ↓
S3Storage.load(full_path)  ← Receives full path, no interpretation
```

### Deleting a Document

```
User: basket.delete_document(document_id)
  ↓
DocBasket.delete_document():
  1. Load DocumentModel from database
  2. Build full path from IDs: path_builder.build_document_path(...)
  3. Delete from storage: storage.delete(full_path)
  4. Delete from database
  ↓
S3Storage.delete(full_path)  ← Receives full path, no interpretation
```

## Benefits

1. **User Simplicity**: Users only work with `basket_id` and `document_id` - no path interpretation needed
2. **Consistency**: All paths are built from IDs using the same logic
3. **Storage Simplicity**: S3Storage is a pure storage abstraction - no path interpretation
4. **Maintainability**: All path building logic is centralized in `DocEXPathBuilder`
5. **Flexibility**: Can change path structure without affecting user code or storage backends

## Example Usage

```python
# User operations - all centered around IDs
docex = DocEX(user_context=UserContext(user_id="user1", tenant_id="acme"))
basket = docex.get_basket("bas_1234567890abcdef")  # basket_id

# Add document - user provides file, gets document_id
doc = basket.add("/path/to/file.pdf", metadata={"category": "invoice"})
document_id = doc.id  # "doc_9876543210fedcba"

# Get document - user provides document_id
doc = basket.get_document(document_id)

# Delete document - user provides document_id
basket.delete_document(document_id)

# Search documents - user searches by metadata, gets document_ids
docs = basket.find_documents_by_metadata({"category": "invoice"})
for doc in docs:
    print(doc.id)  # document_id
```

## Path Building Details

### S3 Path Structure
```
{path_namespace}/{prefix}/{tenant_id}/{basket_friendly_name}_{last_4}/{document_friendly_name}_{last_6}.{ext}
```

**Example**:
```
acme-corp/production/acme/invoices_a1b2/invoice_001_c3d4e5.pdf
```

### Filesystem Path Structure
```
{base_path}/{tenant_id}/{basket_friendly_name}_{last_4}/{document_friendly_name}_{last_6}.{ext}
```

**Example**:
```
storage/acme/invoices_a1b2/invoice_001_c3d4e5.pdf
```

## Summary

✅ **Users**: Work with `basket_id` and `document_id` only  
✅ **DocBasket**: Builds full paths from IDs using `DocEXPathBuilder`  
✅ **StorageService**: Accepts full paths (built from IDs)  
✅ **S3Storage**: Receives full paths, no interpretation  
✅ **DocEXPathBuilder**: Centralized path building from IDs  
✅ **DocEXPathResolver**: Configuration-based path resolution  

All operations are now ID-centric, with paths as internal implementation details.

