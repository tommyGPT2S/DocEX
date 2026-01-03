# S3 Tenant-Aware Configuration Guide for LlamaSee Document Processing

This guide provides step-by-step instructions for configuring DocEX to use the recommended S3 bucket structure for multi-tenant document processing.

## Overview

This configuration implements the structure:
```
s3://LlamaSee-DP-DocEX/
  tenant_{tenant_id}/
    {document_type}_{stage}/
      documents/
        {document_id}.{ext}
```

## Prerequisites

1. AWS S3 bucket created: `LlamaSee-DP-DocEX`
2. AWS credentials configured (IAM role, environment variables, or config file)
3. DocEX initialized (`docex init`)

## Configuration Steps

### Step 1: Configure Default S3 Storage

Edit `~/.docex/config.yaml`:

```yaml
storage:
  default_type: s3
  s3:
    bucket: LlamaSee-DP-DocEX
    region: us-east-1
    # Credentials will be read from environment variables or IAM role
```

### Step 2: Create Helper Function for Tenant-Aware Baskets

Create a utility module `tenant_basket_helper.py`:

```python
"""
Helper functions for creating tenant-aware baskets with proper S3 structure
"""
from typing import Optional
from docex import DocEX
from docex.context import UserContext
from docex.docbasket import DocBasket


def create_tenant_basket(
    docEX: DocEX,
    document_type: str,
    stage: str,
    description: Optional[str] = None
) -> DocBasket:
    """
    Create a tenant-aware basket with proper S3 path structure.
    
    Basket naming: {tenant_id}_{document_type}_{stage}
    S3 Path: tenant_{tenant_id}/{document_type}_{stage}/
    
    Args:
        docEX: DocEX instance with user_context containing tenant_id
        document_type: Type of document (e.g., "invoice", "purchase_order")
        stage: Processing stage (e.g., "raw", "ready_to_pay")
        description: Optional basket description
        
    Returns:
        Created DocBasket instance
        
    Example:
        basket = create_tenant_basket(docEX, "invoice", "raw")
        # Creates basket: "test-tenant-001_invoice_raw"
        # S3 prefix: "tenant_test-tenant-001/invoice_raw/"
    """
    if not docEX.user_context or not docEX.user_context.tenant_id:
        raise ValueError("DocEX instance must have user_context with tenant_id")
    
    tenant_id = docEX.user_context.tenant_id
    basket_name = f"{tenant_id}_{document_type}_{stage}"
    
    if description is None:
        description = f"{document_type} documents in {stage} stage"
    
    # Create basket with tenant-aware S3 prefix
    basket = docEX.create_basket(
        basket_name,
        description=description,
        storage_config={
            'type': 's3',
            's3': {
                'bucket': 'LlamaSee-DP-DocEX',
                'region': 'us-east-1',
                'prefix': f'tenant_{tenant_id}/{document_type}_{stage}/'
            }
        }
    )
    
    return basket


def parse_basket_name(basket_name: str) -> tuple[str, str, str]:
    """
    Parse basket name to extract tenant_id, document_type, and stage.
    
    Basket name format: {tenant_id}_{document_type}_{stage}
    
    Args:
        basket_name: Basket name to parse
        
    Returns:
        Tuple of (tenant_id, document_type, stage)
        
    Example:
        tenant_id, doc_type, stage = parse_basket_name("test-tenant-001_invoice_raw")
        # Returns: ("test-tenant-001", "invoice", "raw")
    """
    parts = basket_name.split('_', 1)
    if len(parts) != 2:
        raise ValueError(f"Invalid basket name format: {basket_name}. Expected: {{tenant_id}}_{{document_type}}_{{stage}}")
    
    tenant_id = parts[0]
    rest = parts[1]
    
    # Find the last underscore to split document_type and stage
    # Handle cases like "invoice_ready_to_pay" where stage has underscores
    # Strategy: Assume stage is the last segment after the last underscore
    # For "invoice_ready_to_pay", stage = "ready_to_pay"
    # For "invoice_raw", stage = "raw"
    
    # Try to split on last underscore
    last_underscore = rest.rfind('_')
    if last_underscore > 0:
        document_type = rest[:last_underscore]
        stage = rest[last_underscore + 1:]
    else:
        # No underscore in rest, treat entire rest as stage
        document_type = rest
        stage = ""
    
    return tenant_id, document_type, stage
```

### Step 3: Usage Example

```python
from docex import DocEX
from docex.context import UserContext
from tenant_basket_helper import create_tenant_basket

# Initialize DocEX with tenant context
user_context = UserContext(
    user_id="user123",
    tenant_id="test-tenant-001",
    user_email="user@example.com"
)

docEX = DocEX(user_context=user_context)

# Create baskets for different document types and stages
invoice_raw_basket = create_tenant_basket(
    docEX, 
    document_type="invoice",
    stage="raw",
    description="Raw invoice documents"
)

invoice_ready_basket = create_tenant_basket(
    docEX,
    document_type="invoice", 
    stage="ready_to_pay",
    description="Invoices ready for payment processing"
)

purchase_order_raw_basket = create_tenant_basket(
    docEX,
    document_type="purchase_order",
    stage="raw",
    description="Raw purchase order documents"
)

# Add documents
doc = invoice_raw_basket.add("path/to/invoice.pdf")
print(f"Document stored at: {doc.path}")
# Output: docex/basket_{id}/{doc_id}
# Full S3 key: tenant_test-tenant-001/invoice_raw/docex/basket_{id}/{doc_id}
```

## S3 Path Structure

### Current Implementation (Configuration-Only)

With the configuration above, documents are stored at:
```
s3://LlamaSee-DP-DocEX/
  tenant_test-tenant-001/
    invoice_raw/
      docex/
        basket_123/
          doc_abc123
```

**Note**: This includes `docex/basket_{id}/` in the path, which is different from the exact requirement but works with IAM policies and lifecycle rules.

### Required Structure (After Code Modification)

To achieve the exact structure:
```
s3://LlamaSee-DP-DocEX/
  tenant_test-tenant-001/
    invoice_raw/
      documents/
        doc_abc123.pdf
```

See `S3_BUCKET_STRUCTURE_EVALUATION.md` for code modification instructions.

## IAM Policy Configuration

### Shared Bucket with Tenant Prefixes

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
    },
    {
      "Effect": "Allow",
      "Action": "s3:ListBucket",
      "Resource": "arn:aws:s3:::LlamaSee-DP-DocEX",
      "Condition": {
        "StringLike": {
          "s3:prefix": "tenant_${aws:PrincipalTag/TenantID}/*"
        }
      }
    }
  ]
}
```

**Note**: The wildcard `/*` matches both the current and required path structures.

## Lifecycle Policy

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
    },
    {
      "ID": "transition-to-glacier",
      "Status": "Enabled",
      "Prefix": "",
      "Transitions": [
        {
          "Days": 90,
          "StorageClass": "GLACIER"
        }
      ]
    }
  ]
}
```

## Environment Variables

```bash
# S3 Configuration
export DOCEX_STORAGE_TYPE=s3
export DOCEX_S3_BUCKET=LlamaSee-DP-DocEX
export DOCEX_S3_REGION=us-east-1

# AWS Credentials (if not using IAM role)
export AWS_ACCESS_KEY_ID=your-access-key
export AWS_SECRET_ACCESS_KEY=your-secret-key
export AWS_DEFAULT_REGION=us-east-1
```

## Testing

### Test Script

```python
from docex import DocEX
from docex.context import UserContext
from tenant_basket_helper import create_tenant_basket
import boto3

def test_tenant_s3_structure():
    """Test that baskets are created with correct S3 structure"""
    
    # Initialize with tenant context
    user_context = UserContext(
        user_id="test_user",
        tenant_id="test-tenant-001",
        user_email="test@example.com"
    )
    
    docEX = DocEX(user_context=user_context)
    
    # Create basket
    basket = create_tenant_basket(docEX, "invoice", "raw")
    print(f"Created basket: {basket.name}")
    print(f"Storage config: {basket.storage_config}")
    
    # Verify S3 prefix
    s3_prefix = basket.storage_config.get('s3', {}).get('prefix', '')
    expected_prefix = "tenant_test-tenant-001/invoice_raw/"
    assert s3_prefix == expected_prefix, f"Expected prefix {expected_prefix}, got {s3_prefix}"
    
    print("✅ S3 prefix configuration correct")
    
    # Add a test document
    import tempfile
    with tempfile.NamedTemporaryFile(mode='w', suffix='.pdf', delete=False) as f:
        f.write("Test invoice content")
        temp_path = f.name
    
    doc = basket.add(temp_path)
    print(f"Document stored at: {doc.path}")
    
    # Verify document exists in S3
    s3_client = boto3.client('s3')
    bucket = basket.storage_config['s3']['bucket']
    full_key = f"{s3_prefix}{doc.path}"
    
    try:
        s3_client.head_object(Bucket=bucket, Key=full_key)
        print(f"✅ Document verified in S3: s3://{bucket}/{full_key}")
    except Exception as e:
        print(f"❌ Document not found in S3: {e}")
    
    # Cleanup
    import os
    os.unlink(temp_path)

if __name__ == "__main__":
    test_tenant_s3_structure()
```

## Migration from Existing Structure

If you have existing baskets with a different structure:

1. **List existing baskets**:
   ```python
   baskets = docEX.list_baskets()
   for basket in baskets:
       print(f"{basket.name}: {basket.storage_config}")
   ```

2. **Create new baskets** with tenant-aware structure

3. **Migrate documents** (if needed):
   ```python
   # Copy documents from old basket to new basket
   old_basket = docEX.get_basket(old_basket_id)
   new_basket = create_tenant_basket(docEX, "invoice", "raw")
   
   for doc in old_basket.list_documents():
       # Retrieve and re-add to new basket
       content = doc.get_content()
       # Save to temp file and add to new basket
   ```

## Troubleshooting

### Issue: S3 prefix not applied correctly

**Solution**: Ensure the storage_config is properly nested:
```python
storage_config = {
    'type': 's3',
    's3': {  # Note: nested under 's3' key
        'bucket': 'LlamaSee-DP-DocEX',
        'region': 'us-east-1',
        'prefix': f'tenant_{tenant_id}/{document_type}_{stage}/'
    }
}
```

### Issue: Documents not found in S3

**Check**:
1. AWS credentials are configured correctly
2. IAM policy allows access to the bucket/prefix
3. Bucket exists and is in the correct region
4. S3 prefix matches the expected structure

### Issue: Tenant isolation not working

**Solution**: Ensure `UserContext` is set with correct `tenant_id`:
```python
user_context = UserContext(
    user_id="user123",
    tenant_id="test-tenant-001"  # Must match basket name prefix
)
```

## Best Practices

1. **Always use UserContext**: Set tenant_id in UserContext for proper multi-tenancy
2. **Consistent naming**: Use `{tenant_id}_{document_type}_{stage}` pattern consistently
3. **Validate basket names**: Ensure basket names match the expected pattern
4. **Monitor S3 usage**: Set up CloudWatch alarms for bucket usage
5. **Backup strategy**: Implement cross-region replication if needed
6. **Cost optimization**: Use lifecycle policies to transition to cheaper storage classes

## Related Documentation

- `S3_BUCKET_STRUCTURE_EVALUATION.md`: Detailed evaluation of DocEX support
- `MULTI_TENANCY_GUIDE.md`: Multi-tenancy configuration guide
- `S3_Storage_Troubleshooting.md`: S3-specific troubleshooting
- `Developer_Guide.md`: General DocEX development guide
