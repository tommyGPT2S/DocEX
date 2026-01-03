"""
Test script for basket-based subdirectory document paths.

This verifies the new structure:
s3://{bucket}/{prefix}/{basket_name}/documents/{readable_name}__{document_id}.{ext}

Example:
s3://llamasee-docex/llamasee-dp-dev/test-tenant-002_potential-hold/documents/invoice_2024-01-15__doc_abc123.pdf
"""

import os
import tempfile
import logging
from docex import DocEX
from docex.context import UserContext
from docex.utils import create_tenant_basket, build_s3_prefix
import boto3
from botocore.exceptions import ClientError, NoCredentialsError

logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger(__name__)

# Configuration
BUCKET = "llamasee-dp-test-tenant-001"  # Test bucket
REGION = "us-east-1"
TENANT_ID = "test-tenant-002"
APPLICATION_NAME = "llamasee-dp-dev"  # Application name

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
    logger.info("=" * 60)
    logger.info("Basket-Based Document Paths Test")
    logger.info("=" * 60)
    logger.info(f"Bucket: {BUCKET}")
    logger.info(f"Application: {APPLICATION_NAME}")
    logger.info(f"Tenant: {TENANT_ID}")
    logger.info("=" * 60)

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

    # Create basket with application name
    logger.info(f"\n📦 Creating basket with application name prefix...")
    logger.info("-" * 60)

    # For basket-based structure, we want a simple tenant-level prefix
    # The basket name will provide the document_type/stage level
    tenant_prefix = f"{APPLICATION_NAME}/tenant_{TENANT_ID}/" if APPLICATION_NAME else f"tenant_{TENANT_ID}/"

    # Use a unique basket name to avoid conflicts
    import uuid
    unique_id = uuid.uuid4().hex[:6]
    basket_name = f"{TENANT_ID}_potential_hold_{unique_id}"

    basket = docEX.create_basket(
        basket_name,
        description="Potential hold documents",
        storage_config={
            'type': 's3',
            's3': {
                'bucket': BUCKET,
                'region': REGION,
                'prefix': tenant_prefix
            }
        }
    )

    basket_name = basket.name  # Get the actual basket name
    logger.info(f"✅ Basket created: {basket.id}")
    logger.info(f"   Basket name: {basket_name}")

    # Show expected prefix (just the tenant/application level)
    expected_prefix = f"{APPLICATION_NAME}/tenant_{TENANT_ID}/" if APPLICATION_NAME else f"tenant_{TENANT_ID}/"
    logger.info(f"   S3 prefix: {expected_prefix}")

    # Create test documents
    logger.info(f"\n📄 Adding test documents...")
    logger.info("-" * 60)

    s3_client = boto3.client('s3', region_name=REGION)
    test_files = [
        ("invoice_2024-01-15.pdf", "Invoice from January 2024"),
        ("contract_Q1_2024.pdf", "Q1 contract document"),
        ("receipt_march_2024.txt", "March receipt"),
    ]

    results = []
    for filename, description in test_files:
        logger.info(f"\nAdding: {filename} ({description})")

        # Create test file with the intended filename
        test_file = os.path.join(tempfile.gettempdir(), filename)
        with open(test_file, 'w') as f:
            f.write(f"Test content for {description}")

        try:
            # Add document
            doc = basket.add(test_file)
            logger.info(f"  ✅ Document added: {doc.id}")
            logger.info(f"     Document path: {doc.path}")

            # Expected readable name (filename without extension)
            expected_readable = os.path.splitext(filename)[0]
            file_ext = os.path.splitext(filename)[1]

            # Expected path structure: {basket_name}/documents/{readable_name}__{document_id}.{ext}
            expected_path = f"{basket.name}/documents/{expected_readable}__{doc.id}{file_ext}"
            # The full S3 key should be prefix + basket-relative path
            expected_s3_key = f"{expected_prefix}{expected_path}"

            logger.info(f"     Expected path: {expected_path}")
            logger.info(f"     Expected S3 key: s3://{BUCKET}/{expected_s3_key}")

            # Verify path structure
            if doc.path == expected_path:
                logger.info("  ✅ Path structure matches!")
                path_ok = True
            else:
                logger.error(f"  ❌ Path mismatch! Expected: {expected_path}")
                path_ok = False

            # Verify in S3
            s3_ok = False
            try:
                s3_client.head_object(Bucket=BUCKET, Key=expected_s3_key)
                logger.info("  ✅ Document verified in S3!")
                s3_ok = True
            except ClientError as e:
                error_code = e.response.get('Error', {}).get('Code', '')
                if error_code == '404':
                    logger.error(f"  ❌ Document not found in S3: {expected_s3_key}")
                else:
                    logger.error(f"  ❌ S3 error: {e}")

            results.append({
                'filename': filename,
                'doc_id': doc.id,
                'path': doc.path,
                'expected_path': expected_path,
                's3_key': expected_s3_key,
                'path_ok': path_ok,
                's3_ok': s3_ok
            })

        finally:
            if os.path.exists(test_file):
                os.unlink(test_file)

    # Summary
    logger.info("\n" + "=" * 80)
    logger.info("SUMMARY - Basket-Based Document Organization")
    logger.info("=" * 80)

    successful = sum(1 for r in results if r['path_ok'] and r['s3_ok'])
    total = len(results)

    logger.info(f"Documents processed: {total}")
    logger.info(f"Successful: {successful}/{total}")

    if successful == total:
        logger.info("\n✅ SUCCESS: Basket-based document paths working perfectly!")
        logger.info("✅ All documents organized under their basket names")
        logger.info("✅ Readable filenames with unique ID suffixes")
    else:
        logger.error(f"\n❌ Some documents failed ({successful}/{total} successful)")
        for i, result in enumerate(results, 1):
            status = "✅" if result['path_ok'] and result['s3_ok'] else "❌"
            logger.info(f"  {status} {i}. {result['filename']} -> {result['path']}")

    # Show final S3 structure
    logger.info("\n📁 Final S3 Structure:")
    logger.info(f"s3://{BUCKET}/")
    logger.info(f"  {APPLICATION_NAME}/")
    logger.info(f"    tenant_{TENANT_ID}/")
    logger.info(f"      {basket.name}/")
    logger.info(f"        documents/")
    for result in results:
        readable_name = os.path.splitext(result['filename'])[0]
        logger.info(f"          {readable_name}__{result['doc_id']}{os.path.splitext(result['filename'])[1]}")

    logger.info("\n💡 Benefits:")
    logger.info("- Documents organized under basket names")
    logger.info("- Human-readable filenames with unique suffixes")
    logger.info("- Easy navigation in S3 console")
    logger.info("- Logical grouping matches your data model")

    return 0 if successful == total else 1

if __name__ == "__main__":
    exit(main())
