# S3 Tenant Configuration - Quick Reference

## Answer: Can DocEX Support the Required S3 Structure?

**✅ YES - IMPLEMENTED** - DocEX now fully supports the recommended S3 bucket structure with the exact path format. Implementation completed!

## Quick Configuration

### 1. Default Config (`~/.docex/config.yaml`)

```yaml
storage:
  default_type: s3
  s3:
    bucket: LlamaSee-DP-DocEX
    region: us-east-1
```

### 2. Create Tenant-Aware Basket

```python
from docex import DocEX
from docex.context import UserContext

# Initialize with tenant
user_context = UserContext(
    user_id="user123",
    tenant_id="test-tenant-001"
)
docEX = DocEX(user_context=user_context)

# Create basket with tenant-aware S3 prefix
basket = docEX.create_basket(
    "test-tenant-001_invoice_raw",
    storage_config={
        'type': 's3',
        's3': {
            'bucket': 'LlamaSee-DP-DocEX',
            'region': 'us-east-1',
            'prefix': 'tenant_test-tenant-001/invoice_raw/'
        }
    }
)
```

## Path Structure

### Implemented ✅
```
s3://LlamaSee-DP-DocEX/tenant_{tenant_id}/{doc_type}_{stage}/documents/{doc_id}.{ext}
```

**Status**: Exact match achieved! S3 storage now uses `documents/{document_id}.{ext}` by default.

## Basket Naming Convention

**Format**: `{tenant_id}_{document_type}_{stage}`

**Examples**:
- `test-tenant-001_invoice_raw`
- `test-tenant-001_invoice_ready_to_pay`
- `pacifiko_purchase_order_raw`

## Key Points

1. ✅ **Multi-tenancy**: Supported via `UserContext.tenant_id`
2. ✅ **S3 Prefix**: Configurable per basket
3. ✅ **Shared Bucket**: Single bucket with tenant prefixes
4. ✅ **Exact Path Match**: Implemented! Uses `documents/{doc_id}.{ext}` for S3

## Implementation Status

**✅ Complete**: Code changes implemented in `docex/docbasket.py`
- Default S3 path: `documents/{document_id}.{ext}`
- Custom templates supported via `document_path_template`
- Filesystem storage unchanged (backward compatible)

## Full Documentation

- **Evaluation**: `S3_BUCKET_STRUCTURE_EVALUATION.md` - Detailed analysis
- **Configuration Guide**: `S3_TENANT_CONFIGURATION_GUIDE.md` - Step-by-step setup
- **This Document**: Quick reference
