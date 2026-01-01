# AWS Credentials Setup for S3 Testing

## Quick Fix

The test script now properly handles AWS credentials from `~/.aws/credentials`. 

### Verify Your Credentials File

Check that your credentials file exists and has the correct format:

```bash
cat ~/.aws/credentials
```

Should look like:
```ini
[default]
aws_access_key_id = YOUR_ACCESS_KEY_ID
aws_secret_access_key = YOUR_SECRET_ACCESS_KEY
```

### If Using a Named Profile

If your credentials use a profile name other than `default`:

```bash
export AWS_PROFILE=your-profile-name
python test_s3_quick.py
```

Or in your `~/.aws/credentials`:
```ini
[your-profile-name]
aws_access_key_id = YOUR_ACCESS_KEY_ID
aws_secret_access_key = YOUR_SECRET_ACCESS_KEY
```

## Troubleshooting

### Error: "Unable to locate credentials"

**Solution 1**: Verify credentials file exists and is readable
```bash
ls -la ~/.aws/credentials
cat ~/.aws/credentials
```

**Solution 2**: Check file permissions (should be readable)
```bash
chmod 600 ~/.aws/credentials
```

**Solution 3**: Use environment variables instead
```bash
export AWS_ACCESS_KEY_ID=your-access-key
export AWS_SECRET_ACCESS_KEY=your-secret-key
python test_s3_quick.py
```

### Error: "Access denied" or "403 Forbidden"

- Check IAM permissions for the bucket
- Verify the bucket name is correct: `llamasee-dp-test-tenant-001`
- Ensure your IAM user/role has `s3:GetObject`, `s3:PutObject`, `s3:ListBucket` permissions

### Error: "Bucket not found" or "404"

- Verify bucket name: `llamasee-dp-test-tenant-001`
- Check region: `us-east-1`
- Ensure bucket exists in your AWS account

## Testing Credentials

Test if boto3 can find your credentials:

```python
import boto3
from botocore import session

# Test default profile
aws_session = session.Session(profile_name='default')
credentials = aws_session.get_credentials()
if credentials:
    print("✅ Credentials found!")
    print(f"Access Key: {credentials.access_key[:10]}...")
else:
    print("❌ No credentials found")
```

## DocEX S3 Configuration

DocEX uses boto3's default credential chain, which includes:
1. Environment variables (`AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`)
2. `~/.aws/credentials` file
3. IAM role (if running on EC2/ECS)
4. AWS config file (`~/.aws/config`)

So if your credentials work with `aws s3 ls`, they should work with DocEX.

## Quick Test

```bash
# Test AWS CLI access
aws s3 ls s3://llamasee-dp-test-tenant-001/

# If that works, the Python script should work too
python test_s3_quick.py
```
