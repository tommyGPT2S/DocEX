"""
Test script for S3 tenant-aware path structure implementation.

This script tests the new S3 path structure:
s3://bucket/tenant_{tenant_id}/{document_type}_{stage}/documents/{document_id}.{ext}

Test bucket: llamasee-dp-test-tenant-001
Region: us-east-1
"""

import os
import sys
import tempfile
import logging
from pathlib import Path
from docex import DocEX
from docex.context import UserContext
import boto3
from botocore.exceptions import ClientError

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Test configuration
TEST_BUCKET = "llamasee-dp-test-tenant-001"
TEST_REGION = "us-east-1"
TEST_TENANT_ID = "test-tenant-001"


def create_test_document(content: str = "Test invoice content", suffix: str = ".pdf") -> str:
    """Create a temporary test document file."""
    with tempfile.NamedTemporaryFile(mode='w', suffix=suffix, delete=False) as f:
        f.write(content)
        return f.name


def verify_s3_object_exists(bucket: str, key: str) -> bool:
    """Verify that an S3 object exists at the given key."""
    try:
        s3_client = boto3.client('s3', region_name=TEST_REGION)
        s3_client.head_object(Bucket=bucket, Key=key)
        return True
    except ClientError as e:
        if e.response['Error']['Code'] == '404':
            return False
        raise


def test_default_s3_path_structure():
    """Test 1: Default S3 path structure (documents/{doc_id}.{ext})"""
    logger.info("=" * 80)
    logger.info("TEST 1: Default S3 Path Structure")
    logger.info("=" * 80)
    
    try:
        # Initialize DocEX with tenant context
        user_context = UserContext(
            user_id="test_user",
            tenant_id=TEST_TENANT_ID,
            user_email="test@example.com"
        )
        docEX = DocEX(user_context=user_context)
        
        # Create basket with tenant-aware S3 configuration
        basket_name = f"{TEST_TENANT_ID}_invoice_raw"
        logger.info(f"Creating basket: {basket_name}")
        
        basket = docEX.create_basket(
            basket_name,
            description="Test invoice raw basket",
            storage_config={
                'type': 's3',
                's3': {
                    'bucket': TEST_BUCKET,
                    'region': TEST_REGION,
                    'prefix': f'tenant_{TEST_TENANT_ID}/invoice_raw/'
                }
            }
        )
        
        logger.info(f"✅ Basket created: {basket.id}")
        logger.info(f"   Storage config: {basket.storage_config}")
        
        # Create and add a test document
        test_file = create_test_document("Test invoice PDF content", ".pdf")
        logger.info(f"Adding document: {test_file}")
        
        doc = basket.add(test_file)
        logger.info(f"✅ Document added: {doc.id}")
        logger.info(f"   Document path: {doc.path}")
        
        # Expected S3 key structure
        expected_prefix = f"tenant_{TEST_TENANT_ID}/invoice_raw/"
        expected_path = f"documents/{doc.id}.pdf"
        expected_full_key = f"{expected_prefix}{expected_path}"
        
        logger.info(f"Expected S3 key: s3://{TEST_BUCKET}/{expected_full_key}")
        logger.info(f"Actual document path: {doc.path}")
        
        # Verify the path matches expected structure
        if doc.path == expected_path:
            logger.info("✅ Document path structure matches expected format!")
        else:
            logger.error(f"❌ Path mismatch! Expected: {expected_path}, Got: {doc.path}")
            return False
        
        # Verify document exists in S3
        if verify_s3_object_exists(TEST_BUCKET, expected_full_key):
            logger.info(f"✅ Document verified in S3: s3://{TEST_BUCKET}/{expected_full_key}")
        else:
            logger.error(f"❌ Document not found in S3: s3://{TEST_BUCKET}/{expected_full_key}")
            return False
        
        # Cleanup
        os.unlink(test_file)
        logger.info("✅ Test 1 PASSED")
        return True
        
    except Exception as e:
        logger.error(f"❌ Test 1 FAILED: {e}", exc_info=True)
        return False


def test_custom_path_template():
    """Test 2: Custom path template"""
    logger.info("\n" + "=" * 80)
    logger.info("TEST 2: Custom Path Template")
    logger.info("=" * 80)
    
    try:
        user_context = UserContext(
            user_id="test_user",
            tenant_id=TEST_TENANT_ID,
            user_email="test@example.com"
        )
        docEX = DocEX(user_context=user_context)
        
        basket_name = f"{TEST_TENANT_ID}_purchase_order_raw"
        logger.info(f"Creating basket: {basket_name}")
        
        basket = docEX.create_basket(
            basket_name,
            description="Test PO raw basket with custom template",
            storage_config={
                'type': 's3',
                's3': {
                    'bucket': TEST_BUCKET,
                    'region': TEST_REGION,
                    'prefix': f'tenant_{TEST_TENANT_ID}/purchase_order_raw/',
                    'document_path_template': 'files/{tenant_id}/{document_id}.{ext}'
                }
            }
        )
        
        logger.info(f"✅ Basket created: {basket.id}")
        
        # Create and add a test document
        test_file = create_test_document("Test PO content", ".pdf")
        logger.info(f"Adding document: {test_file}")
        
        doc = basket.add(test_file)
        logger.info(f"✅ Document added: {doc.id}")
        logger.info(f"   Document path: {doc.path}")
        
        # Expected path with custom template
        expected_path = f"files/{TEST_TENANT_ID}/{doc.id}.pdf"
        expected_full_key = f"tenant_{TEST_TENANT_ID}/purchase_order_raw/{expected_path}"
        
        logger.info(f"Expected S3 key: s3://{TEST_BUCKET}/{expected_full_key}")
        
        if doc.path == expected_path:
            logger.info("✅ Custom template path structure matches!")
        else:
            logger.error(f"❌ Path mismatch! Expected: {expected_path}, Got: {doc.path}")
            return False
        
        # Verify in S3
        if verify_s3_object_exists(TEST_BUCKET, expected_full_key):
            logger.info(f"✅ Document verified in S3: s3://{TEST_BUCKET}/{expected_full_key}")
        else:
            logger.error(f"❌ Document not found in S3: s3://{TEST_BUCKET}/{expected_full_key}")
            return False
        
        # Cleanup
        os.unlink(test_file)
        logger.info("✅ Test 2 PASSED")
        return True
        
    except Exception as e:
        logger.error(f"❌ Test 2 FAILED: {e}", exc_info=True)
        return False


def test_filesystem_storage_unchanged():
    """Test 3: Verify filesystem storage still uses old structure"""
    logger.info("\n" + "=" * 80)
    logger.info("TEST 3: Filesystem Storage (Unchanged)")
    logger.info("=" * 80)
    
    try:
        user_context = UserContext(
            user_id="test_user",
            tenant_id=TEST_TENANT_ID,
            user_email="test@example.com"
        )
        docEX = DocEX(user_context=user_context)
        
        basket_name = "test_filesystem_basket"
        logger.info(f"Creating basket: {basket_name}")
        
        basket = docEX.create_basket(
            basket_name,
            description="Test filesystem basket",
            storage_config={
                'type': 'filesystem',
                'filesystem': {
                    'path': './storage/test'
                }
            }
        )
        
        logger.info(f"✅ Basket created: {basket.id}")
        
        # Create and add a test document
        test_file = create_test_document("Test filesystem content", ".txt")
        logger.info(f"Adding document: {test_file}")
        
        doc = basket.add(test_file)
        logger.info(f"✅ Document added: {doc.id}")
        logger.info(f"   Document path: {doc.path}")
        
        # Expected filesystem path (unchanged)
        expected_path = f"docex/basket_{basket.id}/{doc.id}"
        
        if doc.path == expected_path:
            logger.info("✅ Filesystem path structure unchanged (as expected)!")
        else:
            logger.error(f"❌ Path mismatch! Expected: {expected_path}, Got: {doc.path}")
            return False
        
        # Cleanup
        os.unlink(test_file)
        logger.info("✅ Test 3 PASSED")
        return True
        
    except Exception as e:
        logger.error(f"❌ Test 3 FAILED: {e}", exc_info=True)
        return False


def test_multiple_document_types():
    """Test 4: Multiple document types and stages"""
    logger.info("\n" + "=" * 80)
    logger.info("TEST 4: Multiple Document Types and Stages")
    logger.info("=" * 80)
    
    try:
        user_context = UserContext(
            user_id="test_user",
            tenant_id=TEST_TENANT_ID,
            user_email="test@example.com"
        )
        docEX = DocEX(user_context=user_context)
        
        test_cases = [
            ("invoice", "raw", ".pdf"),
            ("invoice", "ready_to_pay", ".pdf"),
            ("purchase_order", "raw", ".pdf"),
        ]
        
        results = []
        for doc_type, stage, ext in test_cases:
            basket_name = f"{TEST_TENANT_ID}_{doc_type}_{stage}"
            logger.info(f"\nTesting: {basket_name}")
            
            basket = docEX.create_basket(
                basket_name,
                description=f"Test {doc_type} {stage} basket",
                storage_config={
                    'type': 's3',
                    's3': {
                        'bucket': TEST_BUCKET,
                        'region': TEST_REGION,
                        'prefix': f'tenant_{TEST_TENANT_ID}/{doc_type}_{stage}/'
                    }
                }
            )
            
            test_file = create_test_document(f"Test {doc_type} {stage} content", ext)
            doc = basket.add(test_file)
            
            expected_path = f"documents/{doc.id}{ext}"
            expected_full_key = f"tenant_{TEST_TENANT_ID}/{doc_type}_{stage}/{expected_path}"
            
            if doc.path == expected_path:
                logger.info(f"  ✅ Path correct: {doc.path}")
                if verify_s3_object_exists(TEST_BUCKET, expected_full_key):
                    logger.info(f"  ✅ Verified in S3: {expected_full_key}")
                    results.append(True)
                else:
                    logger.error(f"  ❌ Not found in S3: {expected_full_key}")
                    results.append(False)
            else:
                logger.error(f"  ❌ Path mismatch: {doc.path} != {expected_path}")
                results.append(False)
            
            os.unlink(test_file)
        
        if all(results):
            logger.info("\n✅ Test 4 PASSED - All document types work correctly")
            return True
        else:
            logger.error(f"\n❌ Test 4 FAILED - {sum(results)}/{len(results)} passed")
            return False
        
    except Exception as e:
        logger.error(f"❌ Test 4 FAILED: {e}", exc_info=True)
        return False


def main():
    """Run all tests"""
    logger.info("=" * 80)
    logger.info("S3 Tenant-Aware Path Structure Test Suite")
    logger.info("=" * 80)
    logger.info(f"Test Bucket: {TEST_BUCKET}")
    logger.info(f"Test Region: {TEST_REGION}")
    logger.info(f"Test Tenant: {TEST_TENANT_ID}")
    logger.info("=" * 80)
    
    # Check AWS credentials
    try:
        s3_client = boto3.client('s3', region_name=TEST_REGION)
        s3_client.head_bucket(Bucket=TEST_BUCKET)
        logger.info(f"✅ Bucket access verified: {TEST_BUCKET}")
    except Exception as e:
        logger.error(f"❌ Cannot access bucket {TEST_BUCKET}: {e}")
        logger.error("Please ensure AWS credentials are configured correctly.")
        return 1
    
    # Run tests
    tests = [
        ("Default S3 Path Structure", test_default_s3_path_structure),
        ("Custom Path Template", test_custom_path_template),
        ("Filesystem Storage Unchanged", test_filesystem_storage_unchanged),
        ("Multiple Document Types", test_multiple_document_types),
    ]
    
    results = []
    for test_name, test_func in tests:
        try:
            result = test_func()
            results.append((test_name, result))
        except Exception as e:
            logger.error(f"Test '{test_name}' crashed: {e}", exc_info=True)
            results.append((test_name, False))
    
    # Summary
    logger.info("\n" + "=" * 80)
    logger.info("TEST SUMMARY")
    logger.info("=" * 80)
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for test_name, result in results:
        status = "✅ PASSED" if result else "❌ FAILED"
        logger.info(f"{status}: {test_name}")
    
    logger.info("=" * 80)
    logger.info(f"Total: {passed}/{total} tests passed")
    logger.info("=" * 80)
    
    return 0 if passed == total else 1


if __name__ == "__main__":
    sys.exit(main())
