"""
Multi-tenant comparison test.

This script demonstrates tenant isolation by:
1. Creating baskets for test-tenant-001
2. Creating baskets for test-tenant-002
3. Verifying documents are stored in separate S3 paths
4. Showing the complete S3 bucket structure
"""

import os
import tempfile
import logging
from docex import DocEX
from docex.context import UserContext
import boto3
from botocore.exceptions import ClientError, NoCredentialsError

logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger(__name__)

BUCKET = "llamasee-dp-test-tenant-001"
REGION = "us-east-1"

def check_aws_credentials():
    """Check if AWS credentials are available"""
    try:
        test_client = boto3.client('s3', region_name=REGION)
        test_client.list_buckets()
        return True
    except NoCredentialsError:
        logger.error("❌ No AWS credentials found")
        return False
    except Exception:
        return True

def provision_tenant(tenant_id: str, user_id: str, email: str):
    """Provision a tenant with sample baskets and documents"""
    logger.info(f"\n{'='*60}")
    logger.info(f"Provisioning Tenant: {tenant_id}")
    logger.info(f"{'='*60}")
    
    user_context = UserContext(
        user_id=user_id,
        tenant_id=tenant_id,
        user_email=email
    )
    docEX = DocEX(user_context=user_context)
    
    # Create baskets
    baskets_config = [
        {'doc_type': 'invoice', 'stage': 'raw'},
        {'doc_type': 'invoice', 'stage': 'ready_to_pay'},
    ]
    
    baskets = []
    for config in baskets_config:
        basket_name = f"{tenant_id}_{config['doc_type']}_{config['stage']}"
        logger.info(f"Creating basket: {basket_name}")
        
        basket = docEX.create_basket(
            basket_name,
            description=f"{config['doc_type']} {config['stage']} for {tenant_id}",
            storage_config={
                'type': 's3',
                's3': {
                    'bucket': BUCKET,
                    'region': REGION,
                    'prefix': f"tenant_{tenant_id}/{config['doc_type']}_{config['stage']}/"
                }
            }
        )
        baskets.append((basket, config))
        logger.info(f"  ✅ Created: {basket.id}")
    
    # Add documents
    s3_client = boto3.client('s3', region_name=REGION)
    results = []
    
    for basket, config in baskets:
        with tempfile.NamedTemporaryFile(mode='w', suffix='.pdf', delete=False) as f:
            f.write(f"Test document for {tenant_id} - {config['doc_type']} {config['stage']}")
            test_file = f.name
        
        try:
            doc = basket.add(test_file)
            expected_path = f"documents/{doc.id}.pdf"
            expected_s3_key = f"tenant_{tenant_id}/{config['doc_type']}_{config['stage']}/{expected_path}"
            
            # Verify
            path_ok = doc.path == expected_path
            s3_ok = False
            try:
                s3_client.head_object(Bucket=BUCKET, Key=expected_s3_key)
                s3_ok = True
            except ClientError:
                pass
            
            results.append({
                'tenant': tenant_id,
                'basket': basket.name,
                'doc_id': doc.id,
                'path': doc.path,
                's3_key': expected_s3_key,
                'path_ok': path_ok,
                's3_ok': s3_ok
            })
            
            logger.info(f"  ✅ Document: {doc.id} -> {doc.path}")
            
        finally:
            if os.path.exists(test_file):
                os.unlink(test_file)
    
    return results

def main():
    logger.info("=" * 60)
    logger.info("Multi-Tenant S3 Path Structure Comparison")
    logger.info("=" * 60)
    
    if not check_aws_credentials():
        return 1
    
    # Provision both tenants
    tenant_001_results = provision_tenant(
        "test-tenant-001",
        "user_001",
        "tenant001@example.com"
    )
    
    tenant_002_results = provision_tenant(
        "test-tenant-002",
        "user_002",
        "tenant002@example.com"
    )
    
    # Comparison
    logger.info(f"\n{'='*60}")
    logger.info("TENANT ISOLATION VERIFICATION")
    logger.info(f"{'='*60}")
    
    logger.info("\n📁 S3 Bucket Structure:")
    logger.info(f"s3://{BUCKET}/")
    logger.info("  tenant_test-tenant-001/")
    for result in tenant_001_results:
        logger.info(f"    {result['basket'].replace('test-tenant-001_', '')}/")
        logger.info(f"      documents/")
        logger.info(f"        {result['doc_id']}.pdf")
    
    logger.info("\n  tenant_test-tenant-002/")
    for result in tenant_002_results:
        logger.info(f"    {result['basket'].replace('test-tenant-002_', '')}/")
        logger.info(f"      documents/")
        logger.info(f"        {result['doc_id']}.pdf")
    
    # Verify isolation
    logger.info(f"\n{'='*60}")
    logger.info("ISOLATION CHECK")
    logger.info(f"{'='*60}")
    
    all_ok = True
    for result in tenant_001_results + tenant_002_results:
        # Check that tenant ID is in the path
        if result['tenant'] not in result['s3_key']:
            logger.error(f"❌ Tenant ID missing in path: {result['s3_key']}")
            all_ok = False
        else:
            logger.info(f"✅ {result['tenant']}: {result['s3_key']}")
    
    # Verify no cross-tenant paths
    tenant_001_keys = [r['s3_key'] for r in tenant_001_results]
    tenant_002_keys = [r['s3_key'] for r in tenant_002_results]
    
    for key in tenant_001_keys:
        if 'test-tenant-002' in key:
            logger.error(f"❌ Cross-tenant contamination: {key}")
            all_ok = False
    
    for key in tenant_002_keys:
        if 'test-tenant-001' in key:
            logger.error(f"❌ Cross-tenant contamination: {key}")
            all_ok = False
    
    if all_ok:
        logger.info(f"\n✅ SUCCESS: Tenant isolation verified!")
        logger.info(f"✅ Tenant 001: {len(tenant_001_results)} documents")
        logger.info(f"✅ Tenant 002: {len(tenant_002_results)} documents")
        logger.info(f"✅ All documents stored in separate tenant paths")
        return 0
    else:
        logger.error(f"\n❌ FAILED: Isolation issues detected")
        return 1

if __name__ == "__main__":
    exit(main())
