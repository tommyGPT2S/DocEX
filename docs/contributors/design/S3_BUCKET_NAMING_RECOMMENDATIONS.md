# S3 Bucket Naming Recommendations

## Current Situation

You're currently using: `llamasee-dp-test-tenant-001` (test bucket)

## Recommendation: Create Dedicated DocEX Bucket

### Recommended Bucket Names

**Option 1: Simple and Clear**
```
llamasee-docex
```
- ✅ Clear purpose
- ✅ Short and memorable
- ✅ Easy to reference

**Option 2: Environment-Specific**
```
llamasee-docex-dev      # Development
llamasee-docex-staging  # Staging
llamasee-docex-prod     # Production
```
- ✅ Environment separation
- ✅ Different lifecycle policies per environment
- ✅ Easier to manage permissions

**Option 3: Application-Specific**
```
llamasee-dp-docex       # LlamaSee Document Processing - DocEX
llamasee-docex          # Just DocEX
```
- ✅ Clear application association
- ✅ Good for multiple applications

## Why Create a Dedicated Bucket?

### 1. **Separation of Concerns**
- Test buckets vs production buckets
- Different retention policies
- Easier to manage and monitor

### 2. **Security & Access Control**
- Different IAM policies per bucket
- Easier to audit and control access
- Can enable bucket-level encryption settings

### 3. **Lifecycle Management**
- Different lifecycle policies for test vs prod
- Cost optimization per environment
- Easier to archive/delete test data

### 4. **Organization**
- Clear purpose and ownership
- Easier to find and manage
- Better for team collaboration

## Bucket Structure with Application Name

With the new application name feature, you can use **one bucket** for multiple environments:

```
llamasee-docex (single bucket)
├── llamasee-dp-dev/
│   └── tenant_test-tenant-001/
│       └── invoice_raw/
│           └── documents/
├── llamasee-dp-staging/
│   └── tenant_test-tenant-001/
│       └── invoice_raw/
│           └── documents/
└── llamasee-dp-prod/
    └── tenant_test-tenant-001/
        └── invoice_raw/
            └── documents/
```

**Benefits:**
- ✅ Single bucket to manage
- ✅ Environment separation via application_name prefix
- ✅ Unified lifecycle policies
- ✅ Easier IAM policy management

## Recommended Approach

### For Production: Use One Bucket with Application Names

**Bucket**: `llamasee-docex`

**Configuration** (`~/.docex/config.yaml`):

```yaml
storage:
  type: s3
  s3:
    bucket: llamasee-docex
    region: us-east-1
    application_name: llamasee-dp-dev  # Change per environment
```

**Resulting Structure:**
```
s3://llamasee-docex/
  llamasee-dp-dev/
    tenant_test-tenant-001/
      invoice_raw/
        documents/
          doc_123.pdf
```

### For Testing: Keep Separate Test Bucket

**Bucket**: `llamasee-docex-test` or `llamasee-dp-test-tenant-001`

Use for:
- Development testing
- Integration tests
- Temporary data

## Creating the Bucket

### Option 1: Let DocEX Create It (Automatic)

DocEX will automatically create the bucket if it doesn't exist (if you have permissions):

```python
# DocEX will check and create if needed
basket = docEX.create_basket(
    "test-tenant-001_invoice_raw",
    storage_config={
        'type': 's3',
        's3': {
            'bucket': 'llamasee-docex',  # Will be created if doesn't exist
            'region': 'us-east-1'
        }
    }
)
```

### Option 2: Pre-Create Bucket (Recommended for Production)

```bash
# Create bucket
aws s3 mb s3://llamasee-docex --region us-east-1

# Enable versioning (optional but recommended)
aws s3api put-bucket-versioning \
    --bucket llamasee-docex \
    --versioning-configuration Status=Enabled

# Enable encryption (optional but recommended)
aws s3api put-bucket-encryption \
    --bucket llamasee-docex \
    --server-side-encryption-configuration '{
        "Rules": [{
            "ApplyServerSideEncryptionByDefault": {
                "SSEAlgorithm": "AES256"
            }
        }]
    }'

# Block public access (security best practice)
aws s3api put-public-access-block \
    --bucket llamasee-docex \
    --public-access-block-configuration \
    "BlockPublicAcls=true,IgnorePublicAcls=true,BlockPublicPolicy=true,RestrictPublicBuckets=true"
```

## Bucket Naming Best Practices

### ✅ Good Names
- `llamasee-docex` - Clear and simple
- `llamasee-docex-prod` - Environment-specific
- `llamasee-dp-docex` - Application-specific
- `llamasee-docex-us-east-1` - Region-specific (if needed)

### ❌ Avoid
- `llamasee-dp-test-tenant-001` - Too specific, looks like test data
- `docex` - Too generic, might conflict
- `llamasee_docex` - Underscores not recommended for S3
- `LlamaSee-DocEX` - Mixed case (S3 bucket names are case-sensitive but lowercase is standard)

## Migration Strategy

### From Test Bucket to Production Bucket

1. **Create new bucket**: `llamasee-docex`
2. **Update configuration**: Change bucket name in `~/.docex/config.yaml`
3. **Test with new bucket**: Run test scripts
4. **Migrate data** (if needed): Copy from old bucket to new bucket
5. **Update IAM policies**: Point to new bucket
6. **Decommission test bucket**: After verification

### Migration Script Example

```python
import boto3

def migrate_bucket_data(source_bucket, dest_bucket, prefix=""):
    """Migrate data from source to destination bucket"""
    s3 = boto3.client('s3')
    
    paginator = s3.get_paginator('list_objects_v2')
    for page in paginator.paginate(Bucket=source_bucket, Prefix=prefix):
        if 'Contents' not in page:
            continue
        
        for obj in page['Contents']:
            key = obj['Key']
            # Copy to destination
            copy_source = {'Bucket': source_bucket, 'Key': key}
            s3.copy_object(
                CopySource=copy_source,
                Bucket=dest_bucket,
                Key=key
            )
            print(f"Migrated: {key}")
```

## Summary

### Recommended Setup

**Production:**
- **Bucket**: `llamasee-docex`
- **Application Name**: `llamasee-dp-prod` (in config)
- **Structure**: `llamasee-dp-prod/tenant_{id}/{doc_type}_{stage}/documents/`

**Development:**
- **Bucket**: `llamasee-docex` (same bucket)
- **Application Name**: `llamasee-dp-dev` (in config)
- **Structure**: `llamasee-dp-dev/tenant_{id}/{doc_type}_{stage}/documents/`

**Testing:**
- **Bucket**: `llamasee-docex-test` (separate bucket)
- **Application Name**: `test` (optional)
- **Structure**: `test/tenant_{id}/{doc_type}_{stage}/documents/`

### About `head_bucket`

✅ **Yes, it's necessary** - Used to:
- Verify bucket exists before operations
- Auto-create bucket if missing (if permissions allow)
- Provide clear error messages if bucket is inaccessible

The `head_bucket` check happens automatically in `ensure_storage_exists()` and is essential for reliable operation.

## Next Steps

1. **Decide on bucket name**: `llamasee-docex` (recommended)
2. **Create bucket** (manually or let DocEX create it)
3. **Update config**: Set bucket name in `~/.docex/config.yaml`
4. **Test**: Run test scripts with new bucket
5. **Configure application_name**: Set per environment
