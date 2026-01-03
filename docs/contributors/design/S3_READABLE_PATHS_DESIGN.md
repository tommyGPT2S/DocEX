# Readable Document Paths Design

## ✅ IMPLEMENTED: Basket-Based Document Paths

**New S3 Document Paths (Implemented):**
```
s3://bucket/{prefix}/{basket_name}/documents/{readable_name}__{document_id}.{ext}
```

Example:
```
s3://llamasee-docex/llamasee-dp-dev/test-tenant-002_potential-hold/documents/invoice_2024-01-15__doc_c4541cb671d84bc39317f52c31e20989.pdf
```

**Benefits Achieved:**
- ✅ Basket names are human-readable (`test-tenant-002_potential-hold`)
- ✅ Documents organized under their logical baskets
- ✅ Readable filenames with unique ID suffixes
- ✅ Easy navigation in S3 console
- ✅ No breaking changes (new structure for new documents)

## Proposed Solution: Readable Document Paths

### Option 1: Include Filename in Path (Recommended)

**New Structure:**
```
s3://bucket/{prefix}/documents/{document_name}__{document_id}.{ext}
```

Example:
```
s3://llamasee-docex/llamasee-dp-dev/tenant_test-001/invoice_raw/documents/invoice_2024-01-15__doc_c4541cb671d84bc39317f52c31e20989.pdf
```

**Benefits:**
- ✅ Human-readable filenames in S3
- ✅ Unique due to ID suffix
- ✅ Easy to identify documents
- ✅ Backward compatible (IDs still present)
- ✅ Safe from collisions

### Option 2: Basket-Based Subdirectories

**New Structure:**
```
s3://bucket/{prefix}/{basket_name}/documents/{document_name}__{document_id}.{ext}
```

Example:
```
s3://llamasee-docex/llamasee-dp-dev/test-tenant-001_invoice_raw/documents/invoice_2024-01-15__doc_c4541cb671d84bc39317f52c31e20989.pdf
```

**Benefits:**
- ✅ Clear basket organization
- ✅ Very readable structure
- ✅ Easy navigation in S3 console

## Implementation Options

### Option A: Basket Subdirectories (Recommended)

**Modify `_get_document_path()` to include basket name:**

```python
def _get_document_path(self, document: Any, file_path: Optional[str] = None) -> str:
    storage_type = self.storage_config.get('type', 'filesystem')

    if storage_type == 's3':
        s3_config = self.storage_config.get('s3', {})

        # Get readable document name
        readable_name = self._get_readable_document_name(document, file_path)

        # Check for custom path template
        path_template = s3_config.get('document_path_template')
        if path_template:
            return path_template.format(
                basket_id=self.id,
                basket_name=self.name,  # Add basket name
                document_id=document.id,
                document_name=readable_name,
                ext=document.name.split('.')[-1] if '.' in document.name else '',
                tenant_id=self._extract_tenant_id() or '',
            )

        # Default: {basket_name}/documents/{readable_name}__{document_id}.{ext}
        file_ext = Path(file_path).suffix if file_path else ''
        return f"{self.name}/documents/{readable_name}__{document.id}{file_ext}"

    # Filesystem unchanged
    return f"docex/basket_{self.id}/{document.id}"
```

### Option B: Keep Current Structure (Modified `_get_document_path()` Method)

```python
def _get_document_path(self, document: Any, file_path: Optional[str] = None) -> str:
    storage_type = self.storage_config.get('type', 'filesystem')
    
    if storage_type == 's3':
        s3_config = self.storage_config.get('s3', {})
        
        # Get readable document name
        readable_name = self._get_readable_document_name(document, file_path)
        
        # Check for custom path template
        path_template = s3_config.get('document_path_template')
        if path_template:
            return path_template.format(
                basket_id=self.id,
                document_id=document.id,
                document_name=readable_name,
                ext=document.name.split('.')[-1] if '.' in document.name else '',
                tenant_id=self._extract_tenant_id() or '',
            )
        
        # Default: documents/{readable_name}__{document_id}.{ext}
        file_ext = Path(file_path).suffix if file_path else ''
        return f"documents/{readable_name}__{document.id}{file_ext}"
    
    # Filesystem unchanged
    return f"docex/basket_{self.id}/{document.id}"

def _get_readable_document_name(self, document: Any, file_path: Optional[str] = None) -> str:
    """Get a readable document name, sanitized for filesystem use."""
    if file_path:
        # Use original filename, sanitized
        name = Path(file_path).stem  # Remove extension
        return self._sanitize_filename(name)
    
    # Fallback to document name if available
    if hasattr(document, 'name') and document.name:
        name = Path(document.name).stem
        return self._sanitize_filename(name)
    
    # Final fallback
    return f"document_{document.id[:8]}"

def _sanitize_filename(self, name: str) -> str:
    """Sanitize filename for safe filesystem use."""
    import re
    # Remove/replace unsafe characters
    name = re.sub(r'[<>:"/\\|?*]', '_', name)
    # Limit length
    return name[:100] if len(name) > 100 else name
```

## Configuration Options

### Default (Readable Paths)
```yaml
storage:
  s3:
    bucket: llamasee-docex
    region: us-east-1
    application_name: llamasee-dp-dev
    # Uses readable paths by default
```

### Custom Template (Advanced)
```yaml
storage:
  s3:
    bucket: llamasee-docex
    document_path_template: "{basket_name}/files/{document_name}__{document_id}.{ext}"
```

## Examples

### Default Readable Paths

**Input**: `invoice_2024-01-15.pdf`
**Basket**: `test-tenant-001_invoice_raw`
**S3 Path**: `tenant_test-tenant-001/invoice_raw/documents/invoice_2024-01-15__doc_abc123.pdf`

### With Basket Subdirectories (Recommended)

**Default behavior** (no config needed):
```
{basket_name}/documents/{document_name}__{document_id}.{ext}
```

**S3 Path**: `test-tenant-002_potential-hold/documents/invoice_2024-01-15__doc_abc123.pdf`

**Or with custom template**:
```yaml
document_path_template: "{basket_name}/files/{document_name}__{document_id}.{ext}"
```

**S3 Path**: `test-tenant-002_potential-hold/files/invoice_2024-01-15__doc_abc123.pdf`

## Benefits

### 1. **Improved Navigation**
- Can identify documents by name in S3 console
- Easier debugging and troubleshooting
- Better for manual operations

### 2. **Maintained Uniqueness**
- ID suffix prevents collisions
- Safe even with duplicate filenames
- Preserves all existing functionality

### 3. **Backward Compatible**
- Existing documents remain accessible
- No breaking changes to APIs
- Optional feature (can be disabled)

### 4. **Flexible Configuration**
- Default readable paths
- Custom templates for advanced users
- Per-basket customization possible

## Migration Strategy

### For New Documents
- New documents automatically use readable paths
- No migration needed

### For Existing Documents (Optional)
- Can migrate existing S3 objects to new paths
- Or leave them as-is (they remain accessible)
- Migration script can copy objects to new locations

## Security Considerations

### Information Disclosure
- Readable names might leak sensitive information
- Consider if filenames contain sensitive data

### Mitigation
- Sanitize filenames to remove sensitive info
- Use configuration to disable readable paths if needed
- Apply appropriate S3 bucket policies

## Performance Impact

### Minimal Impact
- Path generation happens at document creation time
- No impact on read operations
- S3 performance unaffected by path structure

## Recommendation

**Use Option 2 (Basket-Based Subdirectories)** with the format:
```
{basket_name}/documents/{document_name}__{document_id}.{ext}
```

This provides:
- ✅ **Perfect Organization**: Documents grouped by basket in S3
- ✅ **Human Readability**: Basket names like "test-tenant-002_potential-hold" are meaningful
- ✅ **Clear Hierarchy**: Easy navigation in S3 console
- ✅ **Logical Grouping**: Documents belong to their baskets
- ✅ **Matches Your Data Model**: Basket names are already human-readable
- ✅ **Uniqueness Guaranteed**: ID suffix prevents collisions

**Example S3 Structure:**
```
s3://llamasee-docex/llamasee-dp-dev/
  ├── test-tenant-002_potential-hold/
  │   └── documents/
  │       ├── invoice_2024-01-15__doc_abc123.pdf
  │       └── contract_2024-01-16__doc_def456.pdf
  └── test-tenant-002_resume_raw/
      └── documents/
          └── resume_john_doe__doc_ghi789.pdf
```

This creates a much more navigable and understandable S3 structure that matches your basket organization.