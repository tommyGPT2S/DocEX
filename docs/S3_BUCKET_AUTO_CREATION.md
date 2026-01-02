# S3 Bucket Auto-Creation in DocEX

## Overview

**Yes, DocEX will automatically attempt to create an S3 bucket if it doesn't exist.**

## How It Works

### Automatic Bucket Creation

When DocEX initializes S3 storage, it automatically calls `ensure_storage_exists()` which:

1. **Checks if bucket exists**: Uses `head_bucket` to verify bucket existence
2. **Creates if missing**: If bucket doesn't exist (404 error), attempts to create it
3. **Handles regions**: Properly handles region-specific bucket creation:
   - `us-east-1`: No `LocationConstraint` needed
   - Other regions: Uses `LocationConstraint` parameter

### Code Location

**File**: `docex/storage/s3_storage.py`

```python
def ensure_storage_exists(self) -> None:
    """Ensure S3 bucket exists"""
    try:
        self._retry_on_error(self.s3.head_bucket, Bucket=self.bucket)
    except ClientError as e:
        error_code = e.response.get('Error', {}).get('Code', '')
        if error_code == '404':
            # Bucket doesn't exist, create it
            try:
                create_params = {'Bucket': self.bucket}
                if self.region != 'us-east-1':
                    create_params['CreateBucketConfiguration'] = {
                        'LocationConstraint': self.region
                    }
                self._retry_on_error(self.s3.create_bucket, **create_params)
                logger.info(f"Created S3 bucket: {self.bucket}")
            except ClientError as create_error:
                logger.error(f"Failed to create S3 bucket {self.bucket}: {create_error}")
                raise
```

### When It's Called

1. **During S3Storage initialization** (line 89):
   ```python
   self.s3 = boto3.client(**client_kwargs)
   self.ensure_storage_exists()  # ← Called automatically
   ```

2. **When creating a basket** (line 183 in `docbasket.py`):
   ```python
   storage_service = StorageService(storage_config)
   storage_service.ensure_storage_exists()  # ← Called when basket is created
   ```

## Requirements

### AWS Permissions

Your AWS credentials must have the following IAM permissions:

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "s3:CreateBucket",
        "s3:HeadBucket",
        "s3:ListBucket",
        "s3:PutObject",
        "s3:GetObject",
        "s3:DeleteObject"
      ],
      "Resource": [
        "arn:aws:s3:::your-bucket-name",
        "arn:aws:s3:::your-bucket-name/*"
      ]
    }
  ]
}
```

### Bucket Naming Rules

- **Globally unique**: Bucket names must be unique across all AWS accounts
- **DNS compliant**: 
  - 3-63 characters long
  - Lowercase letters, numbers, hyphens, and periods only
  - Must start and end with a letter or number
- **No IP addresses**: Cannot be formatted as an IP address

## Behavior Examples

### Scenario 1: Bucket Exists ✅

```python
basket = docEX.create_basket(
    "my_basket",
    storage_config={
        'type': 's3',
        's3': {
            'bucket': 'existing-bucket',
            'region': 'us-east-1'
        }
    }
)
# Result: Bucket found, continues normally
```

### Scenario 2: Bucket Doesn't Exist - Auto-Created ✅

```python
basket = docEX.create_basket(
    "my_basket",
    storage_config={
        'type': 's3',
        's3': {
            'bucket': 'new-bucket-name',
            'region': 'us-east-1'
        }
    }
)
# Result: Bucket created automatically, then continues
# Log: "Created S3 bucket: new-bucket-name"
```

### Scenario 3: Bucket Creation Fails ❌

Possible reasons:
- **Insufficient permissions**: IAM user/role doesn't have `s3:CreateBucket` permission
- **Bucket name taken**: Another AWS account already has that bucket name
- **Invalid bucket name**: Doesn't meet S3 naming requirements
- **Region mismatch**: Trying to create in a region where you don't have access

**Error handling**: DocEX will raise an exception with details about why creation failed.

## Best Practices

### 1. Pre-Create Buckets (Recommended)

For production environments, it's recommended to pre-create buckets:

```bash
aws s3 mb s3://your-bucket-name --region us-east-1
```

**Benefits**:
- More control over bucket configuration (versioning, encryption, lifecycle policies)
- Better security (can set bucket policies before use)
- Avoids permission issues during runtime
- Can configure bucket logging, replication, etc.

### 2. Use IAM Policies

Create IAM policies that allow bucket creation but restrict to specific naming patterns:

```json
{
  "Effect": "Allow",
  "Action": "s3:CreateBucket",
  "Resource": "arn:aws:s3:::docex-*",
  "Condition": {
    "StringEquals": {
      "s3:LocationConstraint": "us-east-1"
    }
  }
}
```

### 3. Handle Creation Errors

In your application code, handle bucket creation failures gracefully:

```python
try:
    basket = docEX.create_basket(
        "my_basket",
        storage_config={
            'type': 's3',
            's3': {
                'bucket': 'my-bucket',
                'region': 'us-east-1'
            }
        }
    )
except Exception as e:
    if 'bucket' in str(e).lower() and 'create' in str(e).lower():
        logger.error("Failed to create S3 bucket. Please create it manually or check permissions.")
        # Fallback: use filesystem storage or existing bucket
    else:
        raise
```

## Testing

### Test Auto-Creation

To test bucket auto-creation:

```python
# Use a unique bucket name that doesn't exist
basket = docEX.create_basket(
    "test_basket",
    storage_config={
        'type': 's3',
        's3': {
            'bucket': f'docex-test-{uuid.uuid4().hex[:8]}',  # Unique name
            'region': 'us-east-1'
        }
    }
)
# Bucket will be created automatically if you have permissions
```

### Verify Bucket Creation

```bash
# Check if bucket was created
aws s3 ls | grep your-bucket-name

# Or check bucket properties
aws s3api head-bucket --bucket your-bucket-name
```

## Summary

✅ **DocEX automatically creates S3 buckets** if they don't exist  
✅ **Called during storage initialization** and basket creation  
✅ **Handles region-specific requirements**  
⚠️ **Requires appropriate IAM permissions**  
⚠️ **Bucket names must be globally unique**  
💡 **Best practice**: Pre-create buckets in production for better control

## Related Documentation

- `S3_BUCKET_STRUCTURE_EVALUATION.md` - S3 structure evaluation
- `S3_TENANT_CONFIGURATION_GUIDE.md` - Tenant configuration guide
- `AWS_CREDENTIALS_SETUP.md` - AWS credentials setup
