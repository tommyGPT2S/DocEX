# S3 Storage Troubleshooting Guide

This guide helps you troubleshoot common issues when using S3 storage with DocEX.

## Table of Contents

1. [Authentication Issues](#authentication-issues)
2. [Bucket Access Issues](#bucket-access-issues)
3. [Configuration Issues](#configuration-issues)
4. [Performance Issues](#performance-issues)
5. [Error Messages](#error-messages)

---

## Authentication Issues

### Issue: "NoCredentialsError" or "Unable to locate credentials"

**Symptoms:**
- Error message: `NoCredentialsError: Unable to locate credentials`
- Storage operations fail immediately

**Solutions:**

1. **Check Configuration:**
   ```yaml
   storage:
     type: s3
     s3:
       bucket: your-bucket
       access_key: your-access-key  # Make sure this is set
       secret_key: your-secret-key  # Make sure this is set
       region: us-east-1
   ```

2. **Check Environment Variables:**
   ```bash
   echo $AWS_ACCESS_KEY_ID
   echo $AWS_SECRET_ACCESS_KEY
   echo $AWS_DEFAULT_REGION
   ```
   
   If not set, export them:
   ```bash
   export AWS_ACCESS_KEY_ID=your-access-key
   export AWS_SECRET_ACCESS_KEY=your-secret-key
   export AWS_DEFAULT_REGION=us-east-1
   ```

3. **Check IAM Role (for EC2/ECS):**
   - Verify the instance has an IAM role attached
   - Verify the IAM role has S3 permissions
   - Check IAM role trust relationship

4. **Check AWS Profile:**
   ```bash
   aws configure list
   cat ~/.aws/credentials
   ```

### Issue: "InvalidAccessKeyId" or "SignatureDoesNotMatch"

**Symptoms:**
- Error message: `InvalidAccessKeyId` or `SignatureDoesNotMatch`
- Authentication appears to work but operations fail

**Solutions:**

1. **Verify Credentials:**
   - Double-check access key and secret key are correct
   - Ensure no extra spaces or newlines in credentials
   - Verify credentials haven't been rotated

2. **Test with AWS CLI:**
   ```bash
   aws s3 ls s3://your-bucket
   ```

3. **Check Credential Format:**
   - Access keys should be 20 characters
   - Secret keys should be 40 characters
   - No special characters or spaces

---

## Bucket Access Issues

### Issue: "AccessDenied" or "403 Forbidden"

**Symptoms:**
- Error message: `AccessDenied` or `403 Forbidden`
- Cannot read or write to bucket

**Solutions:**

1. **Check IAM Permissions:**
   ```json
   {
     "Version": "2012-10-17",
     "Statement": [
       {
         "Effect": "Allow",
         "Action": [
           "s3:GetObject",
           "s3:PutObject",
           "s3:DeleteObject",
           "s3:ListBucket"
         ],
         "Resource": [
           "arn:aws:s3:::your-bucket",
           "arn:aws:s3:::your-bucket/*"
         ]
       }
     ]
   }
   ```

2. **Check Bucket Policy:**
   - Verify bucket policy allows your IAM user/role
   - Check for IP restrictions or VPC endpoint requirements

3. **Check Bucket Ownership:**
   - Verify you own the bucket or have proper permissions
   - Check if bucket is in a different AWS account

4. **Check Region:**
   - Ensure the bucket exists in the specified region
   - Verify region configuration matches bucket location

### Issue: "NoSuchBucket" or "404 Not Found"

**Symptoms:**
- Error message: `NoSuchBucket` or `404 Not Found`
- Bucket doesn't exist or can't be found

**Solutions:**

1. **Verify Bucket Name:**
   ```yaml
   storage:
     type: s3
     s3:
       bucket: your-bucket-name  # Check spelling and case
       region: us-east-1
   ```

2. **Check Bucket Exists:**
   ```bash
   aws s3 ls s3://your-bucket-name
   ```

3. **Check Region:**
   - S3 bucket names are globally unique
   - Verify the bucket exists in the specified region
   - Some regions require explicit region specification

4. **Bucket Name Requirements:**
   - 3-63 characters long
   - Lowercase letters, numbers, dots, and hyphens
   - Must start and end with letter or number
   - Cannot be formatted as an IP address

---

## Configuration Issues

### Issue: "ValueError: S3 bucket name is required"

**Symptoms:**
- Error during storage initialization
- Configuration validation fails

**Solutions:**

1. **Check Configuration Structure:**
   ```yaml
   storage:
     type: s3
     s3:
       bucket: your-bucket  # Must be present
       region: us-east-1
   ```

2. **Check Per-Basket Configuration:**
   ```python
   storage_config = {
       'type': 's3',
       's3': {  # Note: nested under 's3' key
           'bucket': 'your-bucket',
           'region': 'us-east-1'
       }
   }
   ```

3. **Validate Bucket Name:**
   - Must be 3-63 characters
   - Must follow S3 naming rules

### Issue: "Invalid S3 bucket name"

**Symptoms:**
- Error message: `Invalid S3 bucket name: <name>`
- Bucket name validation fails

**Solutions:**

1. **Check Bucket Name Format:**
   - Must be 3-63 characters long
   - Can contain lowercase letters, numbers, dots, and hyphens
   - Must start and end with letter or number
   - Cannot contain consecutive dots
   - Cannot be formatted as an IP address (e.g., 192.168.1.1)

2. **Examples:**
   - ✅ Valid: `my-bucket`, `my.bucket`, `mybucket123`
   - ❌ Invalid: `MyBucket` (uppercase), `my_bucket` (underscore), `ab` (too short)

---

## Performance Issues

### Issue: Slow Upload/Download Operations

**Symptoms:**
- Operations take longer than expected
- Timeouts occur

**Solutions:**

1. **Adjust Timeout Settings:**
   ```yaml
   storage:
     type: s3
     s3:
       bucket: your-bucket
       region: us-east-1
       connect_timeout: 120  # Increase connection timeout
       read_timeout: 120      # Increase read timeout
   ```

2. **Check Network Connectivity:**
   - Verify network connection to AWS
   - Check for firewall or proxy issues
   - Consider using VPC endpoint for S3

3. **Check Region:**
   - Use bucket in same region as your application
   - Consider using CloudFront for global access

4. **Monitor S3 Metrics:**
   - Check CloudWatch metrics for S3
   - Look for throttling or rate limiting

### Issue: Retry Failures

**Symptoms:**
- Operations fail after multiple retries
- Error logs show retry attempts

**Solutions:**

1. **Adjust Retry Configuration:**
   ```yaml
   storage:
     type: s3
     s3:
       bucket: your-bucket
       region: us-east-1
       max_retries: 5        # Increase retry attempts
       retry_delay: 2.0      # Increase delay between retries
   ```

2. **Check Error Type:**
   - Transient errors (500, 503, throttling) are retried automatically
   - Permanent errors (400, 403, 404) are not retried
   - Check logs for specific error codes

3. **Check S3 Service Status:**
   - Verify AWS S3 service is operational
   - Check AWS Service Health Dashboard

---

## Error Messages

### Common Error Messages and Solutions

#### "Failed to save content to S3 key: ..."
- **Cause:** Network issue, permissions, or bucket configuration
- **Solution:** Check network connectivity, IAM permissions, and bucket configuration

#### "File not found in S3: ..."
- **Cause:** Object doesn't exist at specified key
- **Solution:** Verify key path, check prefix configuration, ensure object was uploaded

#### "Failed to generate presigned URL for ..."
- **Cause:** Invalid key or permissions issue
- **Solution:** Verify key exists, check IAM permissions for presigned URL generation

#### "Failed to access S3 bucket: ..."
- **Cause:** Bucket doesn't exist, wrong region, or permissions issue
- **Solution:** Verify bucket name and region, check IAM permissions

#### "S3 operation failed (attempt X/Y): ..."
- **Cause:** Transient error being retried
- **Solution:** Check specific error code, verify S3 service status, adjust retry configuration

---

## Debugging Tips

### Enable Debug Logging

```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

### Test S3 Connection

```python
from docex.storage.s3_storage import S3Storage

config = {
    'bucket': 'your-bucket',
    'region': 'us-east-1',
    'access_key': 'your-key',
    'secret_key': 'your-secret'
}

storage = S3Storage(config)
print(f"Bucket: {storage.bucket}")
print(f"Region: {storage.region}")
print(f"Prefix: {storage.prefix}")

# Test basic operation
storage.save('test-key', b'test content')
content = storage.load('test-key')
print(f"Content: {content}")
```

### Verify Configuration

```python
from docex.services.storage_service import StorageService

storage_config = {
    'type': 's3',
    's3': {
        'bucket': 'your-bucket',
        'region': 'us-east-1'
    }
}

try:
    service = StorageService(storage_config)
    print(f"Storage type: {type(service.storage)}")
    print(f"Bucket: {service.storage.bucket}")
except Exception as e:
    print(f"Error: {e}")
```

### Check AWS CLI

```bash
# List buckets
aws s3 ls

# List objects in bucket
aws s3 ls s3://your-bucket

# Test upload
echo "test" | aws s3 cp - s3://your-bucket/test.txt

# Test download
aws s3 cp s3://your-bucket/test.txt -
```

---

## Best Practices

1. **Use IAM Roles:** Prefer IAM roles over access keys when possible (EC2, ECS, Lambda)

2. **Use Environment Variables:** Store credentials in environment variables, not in config files

3. **Use Prefixes:** Organize files with prefixes for better management:
   ```yaml
   s3:
     bucket: your-bucket
     prefix: docex/baskets/
   ```

4. **Monitor Costs:** Be aware of S3 costs (storage, requests, data transfer)

5. **Set Up Alarms:** Configure CloudWatch alarms for S3 errors and throttling

6. **Use Lifecycle Policies:** Set up S3 lifecycle policies for old documents

7. **Enable Versioning:** Consider enabling S3 versioning for important documents

8. **Use Encryption:** Enable S3 encryption for sensitive documents

---

## Getting Help

If you continue to experience issues:

1. Check the [AWS S3 Documentation](https://docs.aws.amazon.com/s3/)
2. Review [AWS S3 Error Responses](https://docs.aws.amazon.com/AmazonS3/latest/API/ErrorResponses.html)
3. Check DocEX logs for detailed error messages
4. Verify your AWS account and billing status
5. Contact AWS Support if issue persists

---

**Last Updated:** 2024

