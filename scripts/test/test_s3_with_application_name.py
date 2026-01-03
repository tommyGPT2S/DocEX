"""
Test script for S3 path structure with application name prefix.

This demonstrates the new structure:
s3://{bucket}/{application_name}/{tenant_id}/{document_type}_{stage}/documents/{doc_id}.{ext}

Example:
s3://llamasee-dp-test-tenant-001/llamasee-dp-dev/tenant_test-tenant-001/invoice_raw/documents/doc_123.pdf
"""

import os
import tempfile
import logging
from docex import DocEX
from docex.context import UserContext
from docex.utils import create_tenant_basket, build_s3_prefix
from docex.config.docex_config import DocEXConfig
import boto3
from botocore.exceptions import ClientError, NoCredentialsError

logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger(__name__)

# Configuration
# Bucket can be set here or in ~/.docex/config.yaml
# If not set here, will use bucket from config.yaml
BUCKET = None  # Set to None to use config.yaml, or specify: "llamasee-docex"
REGION = None  # Set to None to use config.yaml, or specify: "us-east-1"
TENANT_ID = "test-tenant-003"
APPLICATION_NAME = "llamasee-dp-dev"  # Your application name

# Load from config if not specified
from docex.config.docex_config import DocEXConfig
if BUCKET is None or REGION is None:
    config = DocEXConfig()
    
    # Try different key variations (case-insensitive)
    if BUCKET is None:
        # Try standard path
        BUCKET = config.get('storage.s3.bucket')
        # If not found, try to find it in storage config
        if not BUCKET:
            storage_config = config.get('storage', {})
            s3_config = storage_config.get('s3', {}) or storage_config.get('S3', {})
            BUCKET = s3_config.get('bucket') or s3_config.get('Bucket')
    
    if REGION is None:
        # Try standard path
        REGION = config.get('storage.s3.region', 'us-east-1')
        # If not found, try to find it in storage config
        if REGION == 'us-east-1':  # Only if default was used
            storage_config = config.get('storage', {})
            s3_config = storage_config.get('s3', {}) or storage_config.get('S3', {})
            REGION = s3_config.get('region') or s3_config.get('Region') or 'us-east-1'

if not BUCKET:
    # Provide helpful error message
    config_obj = DocEXConfig()
    storage_config = config_obj.get('storage', {})
    s3_config = storage_config.get('s3', {})
    
    print("=" * 60)
    print("S3 Bucket Configuration Error")
    print("=" * 60)
    print("S3 bucket not found in configuration.")
    print(f"\nCurrent storage.s3 config keys: {list(s3_config.keys())}")
    
    if 'application_name' in s3_config:
        print(f"✅ Found: application_name = {s3_config['application_name']}")
    print("❌ Missing: bucket")
    print("❌ Missing: region")
    
    print("\n" + "=" * 60)
    print("Please add to your ~/.docex/config.yaml:")
    print("=" * 60)
    print("storage:")
    print("  s3:")
    if 'application_name' in s3_config:
        print(f"    application_name: {s3_config['application_name']}  # Already set")
    print("    bucket: llamasee-docex  # ← Add this")
    print("    region: us-east-1        # ← Add this")
    print("\nOr set BUCKET variable in the script to override.")
    
    raise ValueError(
        "S3 bucket must be specified either in BUCKET variable or in ~/.docex/config.yaml"
    )

def check_aws_credentials():
    """Check if AWS credentials are available"""
    try:
        test_client = boto3.client('s3', region_name=REGION)
        test_client.list_buckets()
        logger.info(f"✅ AWS credentials found and working")
        return True
    except NoCredentialsError:
        logger.error("❌ No AWS credentials found")
        return False
    except Exception:
        return True

def main():
    # Get config for display
    config_obj = DocEXConfig()
    config_bucket = config_obj.get('storage.s3.bucket')
    config_region = config_obj.get('storage.s3.region', 'us-east-1')
    
    # Determine bucket source
    if BUCKET == config_bucket:
        bucket_source = 'config.yaml'
    else:
        bucket_source = 'script (overrides config.yaml)'
    
    logger.info("=" * 60)
    logger.info("S3 Path Structure with Application Name")
    logger.info("=" * 60)
    logger.info(f"Application Name: {APPLICATION_NAME}")
    logger.info(f"Tenant: {TENANT_ID}")
    logger.info(f"Bucket: {BUCKET} (from {bucket_source})")
    logger.info(f"Region: {REGION}")
    if config_bucket and BUCKET != config_bucket:
        logger.info(f"  ⚠️  Note: config.yaml has bucket: {config_bucket} (will be used by helper function)")
    
    if not check_aws_credentials():
        return 1
    
    # Check bucket access
    try:
        s3 = boto3.client('s3', region_name=REGION)
        s3.head_bucket(Bucket=BUCKET)
        logger.info(f"✅ Bucket accessible: {BUCKET}")
    except Exception as e:
        logger.error(f"❌ Cannot access bucket: {e}")
        return 1
    
    # Initialize DocEX
    user_context = UserContext(
        user_id="test_user",
        tenant_id=TENANT_ID,
        user_email="test@example.com"
    )
    docEX = DocEX(user_context=user_context)
    
    # Create baskets using the helper function with application_name
    logger.info(f"\n📦 Creating baskets with application name prefix...")
    logger.info("-" * 60)
    
    baskets_config = [
        {'doc_type': 'invoice', 'stage': 'raw'},
        {'doc_type': 'invoice', 'stage': 'ready_to_pay'},
    ]
    
    baskets = []
    for config in baskets_config:
        logger.info(f"\nCreating basket: {TENANT_ID}_{config['doc_type']}_{config['stage']}")
        
        # Use the helper function with application_name
        # Pass None for bucket/region to use config.yaml, or pass explicitly to override
        basket = create_tenant_basket(
            docEX,
            document_type=config['doc_type'],
            stage=config['stage'],
            bucket=None,  # Use bucket from config.yaml (set to BUCKET to override)
            region=None,  # Use region from config.yaml (set to REGION to override)
            application_name=APPLICATION_NAME  # ← Application name here
        )
        baskets.append((basket, config))
        
        # Show the prefix that was created
        expected_prefix = build_s3_prefix(
            TENANT_ID,
            config['doc_type'],
            config['stage'],
            APPLICATION_NAME
        )
        logger.info(f"  ✅ Basket created: {basket.id}")
        logger.info(f"  📍 S3 prefix: {expected_prefix}")
    
    # Add test documents
    logger.info(f"\n📄 Adding test documents...")
    logger.info("-" * 60)
    
    s3_client = boto3.client('s3', region_name=REGION)
    all_passed = True
    
    for basket, config in baskets:
        logger.info(f"\nBasket: {basket.name}")
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.pdf', delete=False) as f:
            f.write(f"Test {config['doc_type']} {config['stage']} content")
            test_file = f.name
        
        try:
            doc = basket.add(test_file)
            logger.info(f"  ✅ Document added: {doc.id}")
            logger.info(f"  📄 Document path: {doc.path}")
            
            # Expected S3 key with application name
            expected_path = f"documents/{doc.id}.pdf"
            expected_prefix = build_s3_prefix(
                TENANT_ID,
                config['doc_type'],
                config['stage'],
                APPLICATION_NAME
            )
            expected_s3_key = f"{expected_prefix}{expected_path}"
            
            # Verify path structure
            if doc.path == expected_path:
                logger.info(f"  ✅ Path structure correct")
            else:
                logger.error(f"  ❌ Path mismatch!")
                all_passed = False
                continue
            
            # Verify in S3
            try:
                s3_client.head_object(Bucket=BUCKET, Key=expected_s3_key)
                logger.info(f"  ✅ Verified in S3")
                logger.info(f"  🔗 s3://{BUCKET}/{expected_s3_key}")
            except ClientError as e:
                error_code = e.response.get('Error', {}).get('Code', '')
                if error_code == '404':
                    logger.error(f"  ❌ Document not found in S3")
                    all_passed = False
                else:
                    logger.error(f"  ❌ S3 error: {e}")
                    all_passed = False
            
        finally:
            if os.path.exists(test_file):
                os.unlink(test_file)
    
    # Summary
    logger.info("\n" + "=" * 60)
    logger.info("SUMMARY")
    logger.info("=" * 60)
    logger.info(f"Application Name: {APPLICATION_NAME}")
    logger.info(f"Tenant: {TENANT_ID}")
    logger.info(f"Baskets created: {len(baskets)}")
    
    logger.info("\n📁 S3 Structure:")
    logger.info(f"s3://{BUCKET}/")
    logger.info(f"  {APPLICATION_NAME}/")
    logger.info(f"    tenant_{TENANT_ID}/")
    for basket, config in baskets:
        logger.info(f"      {config['doc_type']}_{config['stage']}/")
        logger.info(f"        documents/")
        logger.info(f"          [documents for {basket.name}]")
    
    if all_passed:
        logger.info("\n✅ SUCCESS: Application name prefix working correctly!")
        logger.info(f"✅ All documents stored at: {APPLICATION_NAME}/tenant_{TENANT_ID}/...")
        return 0
    else:
        logger.error("\n❌ Some tests failed")
        return 1

if __name__ == "__main__":
    exit(main())
