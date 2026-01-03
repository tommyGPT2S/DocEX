# S3 Bucket Structure Evaluation for LlamaSee Document Processing

## Executive Summary

**✅ IMPLEMENTED**: DocEX now fully supports the recommended S3 bucket structure with the exact path format. The implementation has been completed according to the modification plan.

## Current DocEX S3 Capabilities

### What DocEX Already Supports

1. **S3 Storage Backend**: Full S3 storage implementation with:
   - Configurable bucket name
   - Prefix support for organizing files
   - Automatic retry on transient errors
   - Presigned URL generation
   - Support for IAM roles, environment variables, and config-based credentials

2. **Multi-Tenancy Support**: 
   - `UserContext` with `tenant_id` field
   - Database-level multi-tenancy (separate databases/schemas per tenant)
   - Tenant-aware database routing

3. **Per-Basket Storage Configuration**:
   - Each basket can have its own S3 configuration
   - Customizable S3 prefix per basket
   - Basket-specific bucket configuration (if needed)

### Current S3 Path Structure

When a basket is created with S3 storage, DocEX currently uses:
- **S3 Prefix**: `baskets/{basket_id}/` (default if not specified)
- **Document Path**: `docex/basket_{basket_id}/{document_id}`
- **Full S3 Key**: `baskets/{basket_id}/docex/basket_{basket_id}/{document_id}`

## Required Structure from LlamaSee Document Processing

The requirement specifies:
```
s3://LlamaSee-DP-DocEX/
  tenant_{tenant_id}/
    {document_type}_{stage}/
      documents/
        {document_id}.{ext}
```

**Basket Naming Convention**: `{tenant_id}_{document_type}_{stage}`

**Example**:
- Basket: `test-tenant-001_invoice_raw`
- S3 Path: `tenant_test-tenant-001/invoice_raw/documents/doc_123.pdf`

## Gap Analysis

### What Works Out of the Box

1. ✅ **Shared Bucket Configuration**: DocEX supports a single shared bucket
2. ✅ **Prefix Configuration**: DocEX supports custom S3 prefixes per basket
3. ✅ **Tenant Context**: DocEX has `UserContext.tenant_id` available
4. ✅ **Basket Naming**: Can name baskets as `{tenant_id}_{document_type}_{stage}`

### Implementation Status

1. ✅ **Document Path Structure**: 
   - **Implemented**: Now uses `documents/{document_id}.{ext}` for S3 storage
   - **Location**: Modified `docex/docbasket.py` with `_get_document_path()` method
   - **Status**: Fully implemented and tested

2. ✅ **S3 Prefix Construction**:
   - **Current**: Configurable via `storage_config` when creating baskets
   - **Required**: `tenant_{tenant_id}/{document_type}_{stage}/`
   - **Solution**: Configure when creating baskets (see configuration guide)

## Recommended Configuration

### Option 1: Configuration-Based Approach (Recommended)

Configure S3 prefix when creating baskets based on basket name pattern:

```python
from docex import DocEX
from docex.context import UserContext

# Initialize with tenant context
user_context = UserContext(
    user_id="user123",
    tenant_id="test-tenant-001",
    user_email="user@example.com"
)

docEX = DocEX(user_context=user_context)

# Parse basket name to extract document_type and stage
basket_name = "test-tenant-001_invoice_raw"
# Basket name format: {tenant_id}_{document_type}_{stage}
parts = basket_name.split('_', 1)  # Split on first underscore
if len(parts) == 2:
    tenant_id, rest = parts
    # Parse document_type_stage (may have multiple underscores)
    # For "invoice_raw", rest = "invoice_raw"
    # For "invoice_ready_to_pay", rest = "invoice_ready_to_pay"
    document_type_stage = rest
    
    # Create basket with tenant-aware S3 prefix
    basket = docEX.create_basket(
        basket_name,
        description="Invoice raw documents",
        storage_config={
            'type': 's3',
            's3': {
                'bucket': 'LlamaSee-DP-DocEX',
                'region': 'us-east-1',
                'prefix': f'tenant_{tenant_id}/{document_type_stage}/'
            }
        }
    )
```

**Resulting S3 Path**: `tenant_test-tenant-001/invoice_raw/docex/basket_{basket_id}/{document_id}`

**Note**: This still includes `docex/basket_{basket_id}/` in the path, which doesn't match the exact requirement.

### Option 2: Code Modification (For Exact Match)

To achieve the exact path structure `tenant_{tenant_id}/{document_type}_{stage}/documents/{document_id}.{ext}`, modify `docex/docbasket.py`:

**Current Code** (line 423):
```python
document_path = f"docex/basket_{self.id}/{document.id}"
```

**Modified Code**:
```python
# Check if S3 storage with tenant-aware prefix
storage_type = self.storage_config.get('type', 'filesystem')
if storage_type == 's3':
    # Extract tenant_id from basket name or user context
    # Basket name format: {tenant_id}_{document_type}_{stage}
    basket_name_parts = self.name.split('_', 1)
    if len(basket_name_parts) == 2:
        # Use documents/ subdirectory for S3
        file_ext = Path(file_path).suffix if file_path else ''
        document_path = f"documents/{document.id}{file_ext}"
    else:
        # Fallback to default structure
        document_path = f"docex/basket_{self.id}/{document.id}"
else:
    # Filesystem storage uses original structure
    document_path = f"docex/basket_{self.id}/{document.id}"
```

## Recommended Implementation Strategy

### Phase 1: Configuration-Only Approach (No Code Changes)

1. **Create baskets with explicit S3 prefix**:
   ```python
   def create_tenant_basket(docEX, tenant_id, document_type, stage):
       basket_name = f"{tenant_id}_{document_type}_{stage}"
       return docEX.create_basket(
           basket_name,
           storage_config={
               'type': 's3',
               's3': {
                   'bucket': 'LlamaSee-DP-DocEX',
                   'region': 'us-east-1',
                   'prefix': f'tenant_{tenant_id}/{document_type}_{stage}/'
               }
           }
       )
   ```

2. **Resulting Path**: 
   - S3 Key: `tenant_{tenant_id}/{document_type}_{stage}/docex/basket_{basket_id}/{document_id}`
   - **Difference**: Includes `docex/basket_{basket_id}/` instead of just `documents/`

3. **Acceptable if**: The extra path components don't cause issues with your IAM policies or lifecycle rules

### Phase 2: Code Modification (For Exact Match)

If the exact path structure is required:

1. **Modify `docex/docbasket.py`** to detect S3 storage and use `documents/` subdirectory
2. **Add file extension** to document path when storing
3. **Test thoroughly** to ensure backward compatibility

## Configuration Example

### Environment Variables

```bash
# S3 Configuration
DOCEX_STORAGE_TYPE=s3
DOCEX_S3_BUCKET=LlamaSee-DP-DocEX
DOCEX_S3_REGION=us-east-1

# AWS Credentials (or use IAM role)
AWS_ACCESS_KEY_ID=your-access-key
AWS_SECRET_ACCESS_KEY=your-secret-key
AWS_DEFAULT_REGION=us-east-1
```

### Config File (`~/.docex/config.yaml`)

```yaml
storage:
  default_type: s3
  s3:
    bucket: LlamaSee-DP-DocEX
    region: us-east-1
    # Note: prefix should be set per-basket, not globally
```

### Python Code Example

```python
from docex import DocEX
from docex.context import UserContext

# Initialize DocEX with tenant context
user_context = UserContext(
    user_id="user123",
    tenant_id="test-tenant-001",
    user_email="user@example.com"
)

docEX = DocEX(user_context=user_context)

# Helper function to create tenant-aware baskets
def create_tenant_basket(docEX, document_type, stage):
    tenant_id = docEX.user_context.tenant_id
    basket_name = f"{tenant_id}_{document_type}_{stage}"
    
    return docEX.create_basket(
        basket_name,
        description=f"{document_type} documents in {stage} stage",
        storage_config={
            'type': 's3',
            's3': {
                'bucket': 'LlamaSee-DP-DocEX',
                'region': 'us-east-1',
                'prefix': f'tenant_{tenant_id}/{document_type}_{stage}/'
            }
        }
    )

# Create baskets
invoice_raw_basket = create_tenant_basket(docEX, "invoice", "raw")
invoice_ready_basket = create_tenant_basket(docEX, "invoice", "ready_to_pay")
po_raw_basket = create_tenant_basket(docEX, "purchase_order", "raw")

# Add documents
doc = invoice_raw_basket.add("path/to/invoice.pdf")
# Document stored at: s3://LlamaSee-DP-DocEX/tenant_test-tenant-001/invoice_raw/docex/basket_{id}/{doc_id}
```

## Path Structure Comparison

### Current DocEX (with recommended config)
```
s3://LlamaSee-DP-DocEX/
  tenant_test-tenant-001/
    invoice_raw/
      docex/
        basket_123/
          doc_abc123
```

### Required Structure
```
s3://LlamaSee-DP-DocEX/
  tenant_test-tenant-001/
    invoice_raw/
      documents/
        doc_abc123.pdf
```

### Difference
- Extra `docex/basket_{id}/` path component
- Missing file extension in document path

## Implementation Complete ✅

### Changes Made

1. ✅ **Modified `docex/docbasket.py`**:
   - Added `_get_document_path()` method that detects S3 storage
   - Uses `documents/{document_id}.{ext}` structure for S3 by default
   - Supports custom `document_path_template` in storage config
   - Filesystem storage unchanged (backward compatible)

2. ✅ **Added `_extract_tenant_id()` helper**:
   - Extracts tenant_id from basket name pattern: `{tenant_id}_{document_type}_{stage}`
   - Used for custom path template variable substitution

3. ✅ **Configuration**:
   - Default S3 path: `documents/{document_id}.{ext}`
   - Custom templates supported via `document_path_template` in S3 config
   - Basket naming: Use `{tenant_id}_{document_type}_{stage}` pattern

### Usage

```python
# Default S3 path structure (no additional config needed)
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
# Result: s3://LlamaSee-DP-DocEX/tenant_test-tenant-001/invoice_raw/documents/doc_123.pdf
```

## IAM Policy Compatibility

The recommended IAM policy from the requirement document will work with DocEX:

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "s3:GetObject",
        "s3:PutObject",
        "s3:DeleteObject"
      ],
      "Resource": "arn:aws:s3:::LlamaSee-DP-DocEX/tenant_${aws:PrincipalTag/TenantID}/*"
    }
  ]
}
```

**Note**: The wildcard `/*` will match both:
- `tenant_{tenant_id}/{document_type}_{stage}/docex/basket_{id}/{doc_id}` (current)
- `tenant_{tenant_id}/{document_type}_{stage}/documents/{doc_id}.{ext}` (required)

## Lifecycle Policy Compatibility

Lifecycle policies work at the bucket or prefix level, so both path structures are compatible:

```json
{
  "Rules": [
    {
      "ID": "transition-to-ia",
      "Status": "Enabled",
      "Prefix": "",
      "Transitions": [
        {
          "Days": 30,
          "StorageClass": "STANDARD_IA"
        }
      ]
    }
  ]
}
```

## Conclusion

**DocEX can support the recommended S3 bucket structure** with the following:

1. ✅ **Immediate Support**: Configuration-based approach works with minor path differences
2. ⚠️ **Exact Match**: Requires code modification to match exact path structure
3. ✅ **Multi-Tenancy**: Fully supported through `UserContext.tenant_id`
4. ✅ **Basket Organization**: Compatible with `{tenant_id}_{document_type}_{stage}` naming
5. ✅ **IAM & Lifecycle Policies**: Compatible with recommended policies

**Recommended Next Steps**:
1. Test the configuration-based approach first
2. Verify if the path difference is acceptable
3. If exact match is required, implement code modifications
4. Update documentation with tenant-aware basket creation patterns
