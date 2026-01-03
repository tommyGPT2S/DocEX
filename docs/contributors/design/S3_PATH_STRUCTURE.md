# S3 Path Structure Design

## Overview

S3 paths in DocEX follow a consistent three-part structure for clarity, maintainability, and proper metadata storage.

## Three-Part Path Structure

### Part A: Fixed Configuration Path (Config Prefix)
**Location**: Determined by configuration (`config.yaml`)  
**Structure**: `{tenant_id}/{path_namespace}/{prefix}/`  
**Components**:
- `tenant_id`: Tenant identifier (runtime parameter, required for multi-tenant)
- `path_namespace`: Business identifier from config (optional, e.g., "acme-corp", "finance-dept")
- `prefix`: Environment prefix from config (optional, e.g., "production", "staging", "dev")

**Examples**:
- `acme_corp/finance_dept/production/` (all components)
- `acme_corp/finance_dept/` (no prefix)
- `acme_corp/` (minimal - tenant only)

**Storage**: Stored in `basket.storage_config['s3']['config_prefix']` (NEW)

### Part B: Relative Basket Path
**Location**: Basket-specific, built from basket ID and name  
**Structure**: `{basket_friendly_name}_{last_4_of_basket_id}/`  
**Components**:
- `basket_friendly_name`: Sanitized basket name (e.g., "invoice_raw")
- `last_4_of_basket_id`: Last 4 characters of basket ID (e.g., "2c03" from "bas_...2c03")

**Examples**:
- `invoice_raw_2c03/`
- `receipts_processed_efde/`

**Storage**: Stored in `basket.storage_config['s3']['basket_path']` (NEW)

### Part C: Relative Document Path
**Location**: Document-specific, built from document ID and name  
**Structure**: `{document_friendly_name}_{last_6_of_document_id}.{ext}`  
**Components**:
- `document_friendly_name`: Sanitized document name (e.g., "invoice_001")
- `last_6_of_document_id`: Last 6 characters of document ID (e.g., "585d29" from "doc_...585d29")
- `ext`: File extension (e.g., ".pdf")

**Examples**:
- `invoice_001_585d29.pdf`
- `receipt_001_687387.pdf`

**Storage**: Stored in `document.path` (relative to basket)

## Complete Path Examples

### Full S3 Key Structure
```
s3://bucket/{Part A}{Part B}{Part C}
```

### Example 1: Complete Path
```
s3://my-documents-bucket/acme_corp/finance_dept/production/invoice_raw_2c03/invoice_001_585d29.pdf
```
- Part A: `acme_corp/finance_dept/production/`
- Part B: `invoice_raw_2c03/`
- Part C: `invoice_001_585d29.pdf`

### Example 2: Minimal Path (No Namespace/Prefix)
```
s3://my-documents-bucket/acme_corp/receipts_processed_efde/receipt_001_687387.pdf
```
- Part A: `acme_corp/`
- Part B: `receipts_processed_efde/`
- Part C: `receipt_001_687387.pdf`

## Database Storage

### Basket Storage (`DocBasket.storage_config`)
```json
{
  "type": "s3",
  "s3": {
    "bucket": "my-documents-bucket",
    "region": "us-east-1",
    "config_prefix": "acme_corp/finance_dept/production/",  // Part A
    "basket_path": "invoice_raw_2c03/",                     // Part B
    "prefix": "acme_corp/finance_dept/production/invoice_raw_2c03/"  // A + B (for backward compatibility)
  }
}
```

**Note**: The `prefix` field contains A + B for backward compatibility, but we now store A and B separately.

### Document Storage (`Document.path`)
```python
document.path = "acme_corp/finance_dept/production/invoice_raw_2c03/invoice_001_585d29.pdf"  # Full path (A + B + C)
```

**Note**: The document path stores the **full path** for simplicity and consistency:
- **S3**: Full path = Part A + Part B + Part C
- **Filesystem**: Full relative path = Part B + Part C (relative to base_path)

This avoids reconstruction logic and ensures the path is always available directly from the database.

## Path Building Methods

### Building Part A (Config Prefix)
```python
from docex.config.config_resolver import ConfigResolver

resolver = ConfigResolver()
part_a = resolver.resolve_s3_prefix(tenant_id)
# Returns: "acme_corp/finance_dept/production/"
```

### Building Part B (Basket Path)
```python
from docex.utils.s3_prefix_builder import sanitize_basket_name

basket_id_suffix = basket_id.replace('bas_', '')[-4:]
sanitized_name = sanitize_basket_name(basket_name)
part_b = f"{sanitized_name}_{basket_id_suffix}/"
# Returns: "invoice_raw_2c03/"
```

### Building Part C (Document Path)
```python
doc_id_suffix = document_id.replace('doc_', '')[-6:]
document_filename = f"{document_name}_{doc_id_suffix}{file_ext}"
# Returns: "invoice_001_585d29.pdf"
```

### Building Full Path
```python
full_path = f"{part_a}{part_b}{part_c}"
# Returns: "acme_corp/finance_dept/production/invoice_raw_2c03/invoice_001_585d29.pdf"
```

## Benefits of Three-Part Structure

1. **Clarity**: Clear separation of concerns (config, basket, document)
2. **Consistency**: Same structure across all baskets and documents
3. **Maintainability**: Easy to understand and modify
4. **Metadata**: Proper storage of path components in database
5. **Reconstruction**: Can rebuild full paths from stored components
6. **Flexibility**: Easy to change one part without affecting others

## Implementation Details

### Basket Creation
When a basket is created with S3 storage:
1. **Part A** is built using `ConfigResolver.resolve_s3_prefix(tenant_id)`
2. **Part B** is built as `{sanitized_basket_name}_{last_4_of_basket_id}/`
3. Both parts are stored separately in `storage_config['s3']`:
   - `config_prefix`: Part A (e.g., `"acme_corp/finance_dept/production/"`)
   - `basket_path`: Part B (e.g., `"invoice_raw_2c03/"`)
   - `prefix`: Combined A + B (for backward compatibility)

### Document Creation
When a document is added to a basket:
1. **Part C** is built as `{document_friendly_name}_{last_6_of_document_id}.{ext}`
2. Full path (A + B + C for S3, or B + C for filesystem) is built for storage operations
3. **Full path** is stored in `document.path` for simplicity and consistency
4. This avoids reconstruction logic and ensures the path is always available

### Document Retrieval
When retrieving a document:
1. Full path is already stored in `document.path`
2. No reconstruction needed - use `document.path` directly
3. This ensures consistency and simplifies the code

## Implementation Notes

### Path Storage Strategy
We store the **full path** in `document.path` for simplicity:
- **S3**: `document.path` = Part A + Part B + Part C (full S3 key)
- **Filesystem**: `document.path` = Part B + Part C (full relative path)

**Rationale**:
- Simpler code: No reconstruction logic needed
- Better consistency: Path is always available directly from database
- Easier debugging: Full path visible in database
- Minimal duplication: Parts A and B are still stored separately in `basket.storage_config` for basket-level operations

### Basket Storage
- `storage_config['s3']['config_prefix']` = Part A (for reference and basket-level operations)
- `storage_config['s3']['basket_path']` = Part B (for reference and basket-level operations)
- `storage_config['s3']['prefix']` = Part A + Part B (for backward compatibility)

### Document Storage
- `document.path` = Full path (Part A + Part B + Part C for S3, or Part B + Part C for filesystem)

