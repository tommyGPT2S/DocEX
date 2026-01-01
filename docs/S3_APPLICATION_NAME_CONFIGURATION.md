# S3 Application Name Configuration

## Overview

DocEX now supports an optional **application name** prefix in S3 paths. This allows you to organize multiple applications or environments (dev, staging, prod) within the same S3 bucket.

## S3 Path Structure

### Without Application Name (Default)
```
s3://{bucket}/tenant_{tenant_id}/{document_type}_{stage}/documents/{doc_id}.{ext}
```

### With Application Name
```
s3://{bucket}/{application_name}/tenant_{tenant_id}/{document_type}_{stage}/documents/{doc_id}.{ext}
```

## Configuration

### Option 1: Global Configuration (Recommended)

Add `application_name` to your `~/.docex/config.yaml`:

```yaml
storage:
  type: s3
  s3:
    bucket: llamasee-dp-test-tenant-001
    region: us-east-1
    application_name: llamasee-dp-dev  # ← Application name here
```

**Examples:**
- `llamasee-dp-dev` - Development environment
- `llamasee-dp-staging` - Staging environment
- `llamasee-dp-prod` - Production environment
- `my-application` - Custom application name

### Option 2: Per-Basket Override

You can override the application name when creating a specific basket:

```python
from docex.utils import create_tenant_basket

basket = create_tenant_basket(
    docEX,
    document_type="invoice",
    stage="raw",
    application_name="llamasee-dp-dev"  # Override config
)
```

### Option 3: Manual Prefix Construction

Build the prefix manually:

```python
from docex.utils import build_s3_prefix

prefix = build_s3_prefix(
    tenant_id="test-tenant-001",
    document_type="invoice",
    stage="raw",
    application_name="llamasee-dp-dev"
)
# Returns: "llamasee-dp-dev/tenant_test-tenant-001/invoice_raw/"

basket = docEX.create_basket(
    "test-tenant-001_invoice_raw",
    storage_config={
        'type': 's3',
        's3': {
            'bucket': 'my-bucket',
            'region': 'us-east-1',
            'prefix': prefix
        }
    }
)
```

## Usage Examples

### Example 1: Using Helper Function

```python
from docex import DocEX
from docex.context import UserContext
from docex.utils import create_tenant_basket

# Initialize with tenant
user_context = UserContext(
    user_id="user123",
    tenant_id="test-tenant-001"
)
docEX = DocEX(user_context=user_context)

# Create basket with application name from config
basket = create_tenant_basket(
    docEX,
    document_type="invoice",
    stage="raw"
)
# Uses application_name from ~/.docex/config.yaml
```

### Example 2: Override Application Name

```python
# Override application name for this basket
basket = create_tenant_basket(
    docEX,
    document_type="invoice",
    stage="raw",
    application_name="llamasee-dp-prod"  # Override
)
```

### Example 3: Multiple Environments

```python
# Development
dev_basket = create_tenant_basket(
    docEX,
    document_type="invoice",
    stage="raw",
    application_name="llamasee-dp-dev"
)
# S3: s3://bucket/llamasee-dp-dev/tenant_test-tenant-001/invoice_raw/...

# Production
prod_basket = create_tenant_basket(
    docEX,
    document_type="invoice",
    stage="raw",
    application_name="llamasee-dp-prod"
)
# S3: s3://bucket/llamasee-dp-prod/tenant_test-tenant-001/invoice_raw/...
```

## Benefits

### 1. Environment Separation
- **Dev**: `llamasee-dp-dev/tenant_...`
- **Staging**: `llamasee-dp-staging/tenant_...`
- **Prod**: `llamasee-dp-prod/tenant_...`

### 2. Multiple Applications
- **App 1**: `app1/tenant_...`
- **App 2**: `app2/tenant_...`

### 3. Better Organization
- Clear separation in S3 console
- Easier to apply lifecycle policies per environment
- Simpler IAM policy management

## IAM Policy Example

With application name, you can restrict access to specific environments:

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
      "Resource": "arn:aws:s3:::my-bucket/llamasee-dp-dev/*"
    },
    {
      "Effect": "Allow",
      "Action": "s3:ListBucket",
      "Resource": "arn:aws:s3:::my-bucket",
      "Condition": {
        "StringLike": {
          "s3:prefix": "llamasee-dp-dev/*"
        }
      }
    }
  ]
}
```

## Lifecycle Policy Example

Apply different lifecycle policies per environment:

```json
{
  "Rules": [
    {
      "ID": "dev-short-retention",
      "Status": "Enabled",
      "Prefix": "llamasee-dp-dev/",
      "Expiration": {
        "Days": 30
      }
    },
    {
      "ID": "prod-long-retention",
      "Status": "Enabled",
      "Prefix": "llamasee-dp-prod/",
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

## Migration

### From No Application Name to With Application Name

If you have existing baskets without application name:

1. **Option 1**: Leave existing documents as-is, new documents use application name
2. **Option 2**: Migrate documents in S3 from old path to new path
3. **Option 3**: Use custom `document_path_template` to match old structure if needed

### Example Migration Script

```python
import boto3
from botocore.exceptions import ClientError

def migrate_to_application_name(bucket, old_prefix, new_prefix):
    """Migrate S3 objects from old prefix to new prefix"""
    s3 = boto3.client('s3')
    
    # List all objects with old prefix
    paginator = s3.get_paginator('list_objects_v2')
    for page in paginator.paginate(Bucket=bucket, Prefix=old_prefix):
        if 'Contents' not in page:
            continue
        
        for obj in page['Contents']:
            old_key = obj['Key']
            new_key = old_key.replace(old_prefix, new_prefix, 1)
            
            # Copy to new location
            s3.copy_object(
                Bucket=bucket,
                CopySource={'Bucket': bucket, 'Key': old_key},
                Key=new_key
            )
            
            # Delete old object (optional)
            # s3.delete_object(Bucket=bucket, Key=old_key)
            
            print(f"Migrated: {old_key} -> {new_key}")
```

## Testing

Run the test script to verify application name functionality:

```bash
python test_s3_with_application_name.py
```

This will:
1. Create baskets with application name prefix
2. Add test documents
3. Verify S3 path structure includes application name
4. Show complete S3 bucket structure

## Summary

✅ **Application name is optional** - Works with or without it  
✅ **Configurable globally** - Set in `~/.docex/config.yaml`  
✅ **Override per basket** - Can specify when creating baskets  
✅ **Backward compatible** - Existing code works without changes  
✅ **Environment separation** - Perfect for dev/staging/prod  
✅ **Better organization** - Clear structure in S3

## Related Documentation

- `S3_BUCKET_STRUCTURE_EVALUATION.md` - S3 structure evaluation
- `S3_TENANT_CONFIGURATION_GUIDE.md` - Tenant configuration guide
- `S3_BUCKET_AUTO_CREATION.md` - Bucket auto-creation
