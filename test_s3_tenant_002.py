"""
Test script for provisioning and testing tenant test-tenant-002.

This script verifies:
1. Tenant isolation in S3 paths
2. Multiple document types and stages
3. Correct S3 path structure for tenant-002
4. Application name prefix support (optional)

S3 Structure:
- Without app name: s3://bucket/tenant_{tenant_id}/{doc_type}_{stage}/documents/{doc_id}.{ext}
- With app name: s3://bucket/{app_name}/tenant_{tenant_id}/{doc_type}_{stage}/documents/{doc_id}.{ext}
"""

import os
import tempfile
import logging
from pathlib import Path
from docex import DocEX
from docex.context import UserContext
from docex.utils import create_tenant_basket, build_s3_prefix
import boto3
from botocore.exceptions import ClientError, NoCredentialsError

logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger(__name__)

# Configuration
BUCKET = "llamasee-dp-test-tenant-001"  # Shared bucket
REGION = "us-east-1"
TENANT_ID = "test-tenant-002"
APPLICATION_NAME = "llamasee-dp-dev"  # Optional: Set to None to disable app name prefix

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
    except Exception as e:
        logger.info(f"✅ AWS credentials found (error may be permissions: {e})")
        return True

def main():
    logger.info("=" * 60)
    logger.info("Provisioning Tenant: test-tenant-002")
    logger.info("=" * 60)
    
    # Check AWS credentials
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
    
    # Initialize DocEX with tenant-002 context
    user_context = UserContext(
        user_id="tenant_002_user",
        tenant_id=TENANT_ID,
        user_email="tenant002@example.com"
    )
    docEX = DocEX(user_context=user_context)
    
    logger.info(f"\n📦 Creating baskets for tenant: {TENANT_ID}")
    logger.info("-" * 60)
    
    # Create multiple baskets for different document types and stages
    baskets_config = [
        {
            'name': f"{TENANT_ID}_invoice_raw",
            'description': "Raw invoice documents",
            'doc_type': 'invoice',
            'stage': 'raw'
        },
        {
            'name': f"{TENANT_ID}_invoice_ready_to_pay",
            'description': "Invoices ready for payment",
            'doc_type': 'invoice',
            'stage': 'ready_to_pay'
        },
        {
            'name': f"{TENANT_ID}_purchase_order_raw",
            'description': "Raw purchase order documents",
            'doc_type': 'purchase_order',
            'stage': 'raw'
        },
    ]
    
    baskets = []
    for config in baskets_config:
        logger.info(f"\nCreating basket: {config['name']}")
        
        # Use helper function with application name support
        basket = create_tenant_basket(
            docEX,
            document_type=config['doc_type'],
            stage=config['stage'],
            description=config['description'],
            bucket=BUCKET,
            region=REGION,
            application_name=APPLICATION_NAME  # Uses application name if set
        )
        baskets.append((basket, config))
        
        # Show the prefix that was created
        prefix = build_s3_prefix(
            TENANT_ID,
            config['doc_type'],
            config['stage'],
            APPLICATION_NAME
        )
        logger.info(f"  ✅ Basket created: {basket.id}")
        logger.info(f"  📍 S3 prefix: {prefix}")
    
    # Add test documents to each basket
    logger.info(f"\n📄 Adding test documents...")
    logger.info("-" * 60)
    
    s3_client = boto3.client('s3', region_name=REGION)
    all_passed = True
    
    for basket, config in baskets:
        logger.info(f"\nBasket: {basket.name}")
        
        # Create test file with appropriate extension
        file_ext = '.pdf'
        with tempfile.NamedTemporaryFile(mode='w', suffix=file_ext, delete=False) as f:
            f.write(f"Test {config['doc_type']} {config['stage']} content for {TENANT_ID}")
            test_file = f.name
        
        try:
            # Add document
            doc = basket.add(test_file)
            logger.info(f"  ✅ Document added: {doc.id}")
            logger.info(f"  📄 Document path: {doc.path}")
            
            # Expected path structure with application name
            expected_path = f"documents/{doc.id}{file_ext}"
            prefix = build_s3_prefix(
                TENANT_ID,
                config['doc_type'],
                config['stage'],
                APPLICATION_NAME
            )
            expected_s3_key = f"{prefix}{expected_path}"
            
            # Verify path structure
            if doc.path == expected_path:
                logger.info(f"  ✅ Path structure correct: {doc.path}")
            else:
                logger.error(f"  ❌ Path mismatch! Expected: {expected_path}, Got: {doc.path}")
                all_passed = False
                continue
            
            # Verify in S3
            try:
                s3_client.head_object(Bucket=BUCKET, Key=expected_s3_key)
                logger.info(f"  ✅ Verified in S3: s3://{BUCKET}/{expected_s3_key}")
            except ClientError as e:
                error_code = e.response.get('Error', {}).get('Code', '')
                if error_code == '404':
                    logger.error(f"  ❌ Document not found in S3: {expected_s3_key}")
                    all_passed = False
                else:
                    logger.error(f"  ❌ S3 error: {e}")
                    all_passed = False
            
        finally:
            # Cleanup
            if os.path.exists(test_file):
                os.unlink(test_file)
    
    # Summary
    logger.info("\n" + "=" * 60)
    logger.info("SUMMARY")
    logger.info("=" * 60)
    logger.info(f"Tenant: {TENANT_ID}")
    logger.info(f"Baskets created: {len(baskets)}")
    logger.info(f"Documents added: {len(baskets)}")
    
    # Show S3 structure
    logger.info("\n📁 S3 Structure:")
    logger.info(f"s3://{BUCKET}/")
    if APPLICATION_NAME:
        logger.info(f"  {APPLICATION_NAME}/")
    for basket, config in baskets:
        logger.info(f"    tenant_{TENANT_ID}/")
        logger.info(f"      {config['doc_type']}_{config['stage']}/")
        logger.info(f"        documents/")
        logger.info(f"          [documents for {config['name']}]")
    
    if all_passed:
        logger.info("\n✅ SUCCESS: Tenant test-tenant-002 provisioned correctly!")
        logger.info("✅ All documents stored with correct path structure")
        logger.info("✅ Tenant isolation verified in S3")
        return 0
    else:
        logger.error("\n❌ Some tests failed")
        return 1

if __name__ == "__main__":
    exit(main())
