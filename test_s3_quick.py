"""
Quick test script for S3 tenant-aware path structure.

Usage:
    python test_s3_quick.py

Requirements:
    - AWS credentials configured
    - DocEX initialized (docex init)
    - S3 bucket: llamasee-dp-test-tenant-001
"""

import os
import tempfile
import logging
from pathlib import Path
from docex import DocEX
from docex.context import UserContext
import boto3
from botocore.exceptions import ClientError, NoCredentialsError

logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger(__name__)

# Configuration
BUCKET = "llamasee-dp-test-tenant-001"
REGION = "us-east-1"
TENANT_ID = "test-tenant-001"

def check_aws_credentials():
    """Check if AWS credentials are available"""
    try:
        # Simply try to create a client - boto3 will use default credential chain
        # which includes ~/.aws/credentials, environment variables, IAM roles, etc.
        test_client = boto3.client('s3', region_name=REGION)
        # Try a simple operation to verify credentials work
        test_client.list_buckets()
        logger.info(f"✅ AWS credentials found and working")
        return True
    except NoCredentialsError:
        logger.error("❌ No AWS credentials found")
        logger.info("\nTo fix this:")
        logger.info("1. Ensure ~/.aws/credentials exists with format:")
        logger.info("   [default]")
        logger.info("   aws_access_key_id = YOUR_ACCESS_KEY")
        logger.info("   aws_secret_access_key = YOUR_SECRET_KEY")
        logger.info("2. Or set AWS_ACCESS_KEY_ID and AWS_SECRET_ACCESS_KEY environment variables")
        logger.info("3. If using a named profile, set AWS_PROFILE environment variable")
        return False
    except Exception as e:
        # Other errors (like permission issues) are OK - we'll catch those later
        # This just means credentials exist but might not have permissions
        logger.info(f"✅ AWS credentials found (error may be permissions: {e})")
        return True

def main():
    logger.info("=" * 60)
    logger.info("Quick S3 Path Structure Test")
    logger.info("=" * 60)
    
    # Check AWS credentials first
    if not check_aws_credentials():
        return 1
    
    # Check bucket access
    # boto3 automatically uses default credential chain:
    # 1. Environment variables (AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY)
    # 2. ~/.aws/credentials file
    # 3. IAM role (if on EC2/ECS)
    # 4. AWS config file
    try:
        s3 = boto3.client('s3', region_name=REGION)
        
        s3.head_bucket(Bucket=BUCKET)
        logger.info(f"✅ Bucket accessible: {BUCKET}")
    except NoCredentialsError:
        logger.error("❌ AWS credentials not found")
        logger.info("\nPlease configure AWS credentials:")
        logger.info("1. Create ~/.aws/credentials with:")
        logger.info("   [default]")
        logger.info("   aws_access_key_id = YOUR_ACCESS_KEY")
        logger.info("   aws_secret_access_key = YOUR_SECRET_KEY")
        logger.info("2. Or set AWS_ACCESS_KEY_ID and AWS_SECRET_ACCESS_KEY environment variables")
        return 1
    except ClientError as e:
        error_code = e.response.get('Error', {}).get('Code', '')
        if error_code == '403':
            logger.error(f"❌ Access denied to bucket {BUCKET}")
            logger.info("Please check your IAM permissions")
        elif error_code == '404':
            logger.error(f"❌ Bucket {BUCKET} not found")
            logger.info("Please verify the bucket name and region")
        else:
            logger.error(f"❌ Cannot access bucket: {e}")
        return 1
    except Exception as e:
        logger.error(f"❌ Cannot access bucket: {e}")
        return 1
    
    # Create S3 client for verification
    # boto3 will automatically use credentials from ~/.aws/credentials
    s3_client = boto3.client('s3', region_name=REGION)
    
    # Initialize DocEX
    user_context = UserContext(
        user_id="test_user",
        tenant_id=TENANT_ID,
        user_email="test@example.com"
    )
    docEX = DocEX(user_context=user_context)
    
    # Create basket
    basket_name = f"{TENANT_ID}_invoice_raw"
    logger.info(f"\nCreating basket: {basket_name}")
    
    basket = docEX.create_basket(
        basket_name,
        storage_config={
            'type': 's3',
            's3': {
                'bucket': BUCKET,
                'region': REGION,
                'prefix': f'tenant_{TENANT_ID}/invoice_raw/'
            }
        }
    )
    logger.info(f"✅ Basket created: {basket.id}")
    
    # Create test file
    with tempfile.NamedTemporaryFile(mode='w', suffix='.pdf', delete=False) as f:
        f.write("Test invoice content")
        test_file = f.name
    
    try:
        # Add document
        logger.info(f"\nAdding document: {test_file}")
        doc = basket.add(test_file)
        logger.info(f"✅ Document added: {doc.id}")
        logger.info(f"   Document path: {doc.path}")
        
        # Expected path
        expected_path = f"documents/{doc.id}.pdf"
        expected_s3_key = f"tenant_{TENANT_ID}/invoice_raw/{expected_path}"
        
        logger.info(f"\nExpected S3 key: s3://{BUCKET}/{expected_s3_key}")
        logger.info(f"Actual path: {doc.path}")
        
        # Verify path structure
        if doc.path == expected_path:
            logger.info("✅ Path structure matches!")
        else:
            logger.error(f"❌ Path mismatch! Expected: {expected_path}")
            return 1
        
        # Verify in S3
        try:
            s3_client.head_object(Bucket=BUCKET, Key=expected_s3_key)
            logger.info(f"✅ Document verified in S3!")
            logger.info(f"\n✅ SUCCESS: S3 path structure implementation works correctly!")
            return 0
        except ClientError as e:
            error_code = e.response.get('Error', {}).get('Code', '')
            if error_code == '404':
                logger.error(f"❌ Document not found in S3: {expected_s3_key}")
            else:
                logger.error(f"❌ S3 error: {e}")
            return 1
            
    finally:
        # Cleanup
        if os.path.exists(test_file):
            os.unlink(test_file)

if __name__ == "__main__":
    exit(main())
