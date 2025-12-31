# Testing S3 Tenant-Aware Path Structure

## Quick Test

Run the quick test script to verify the implementation:

```bash
python test_s3_quick.py
```

This will:
1. Create a basket with tenant-aware S3 configuration
2. Add a test document
3. Verify the path structure matches: `documents/{doc_id}.{ext}`
4. Verify the document exists in S3 at the correct location

## Provision Tenant-002

Test provisioning a second tenant:

```bash
python test_s3_tenant_002.py
```

This will:
1. Create baskets for tenant-002 (invoice_raw, invoice_ready_to_pay, purchase_order_raw)
2. Add test documents to each basket
3. Verify tenant isolation in S3 paths
4. Show the complete S3 structure

## Multi-Tenant Comparison

Compare both tenants side-by-side:

```bash
python test_s3_multi_tenant_comparison.py
```

This will:
1. Provision both tenant-001 and tenant-002
2. Verify tenant isolation
3. Show complete S3 bucket structure
4. Verify no cross-tenant contamination

## Full Test Suite

Run the comprehensive test suite:

```bash
python tests/test_s3_tenant_path_structure.py
```

This includes:
- Test 1: Default S3 path structure
- Test 2: Custom path template
- Test 3: Filesystem storage (unchanged)
- Test 4: Multiple document types and stages

## Prerequisites

1. **AWS Credentials**: Configured via:
   - Environment variables (`AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`)
   - IAM role (if running on EC2/ECS)
   - AWS credentials file (`~/.aws/credentials`)

2. **DocEX Initialized**: Run `docex init` if not already done

3. **S3 Bucket**: `llamasee-dp-test-tenant-001` in `us-east-1` (already created ✅)

4. **Python Dependencies**: 
   - `boto3` (for S3 access)
   - `docex` (installed)

## Expected Output

### Quick Test Success:
```
✅ Bucket accessible: llamasee-dp-test-tenant-001
✅ Basket created: 123
✅ Document added: doc_abc123
   Document path: documents/doc_abc123.pdf
✅ Path structure matches!
✅ Document verified in S3!
✅ SUCCESS: S3 path structure implementation works correctly!
```

### Full Test Suite Success:
```
✅ Test 1 PASSED: Default S3 Path Structure
✅ Test 2 PASSED: Custom Path Template
✅ Test 3 PASSED: Filesystem Storage Unchanged
✅ Test 4 PASSED: Multiple Document Types

Total: 4/4 tests passed
```

## S3 Path Structure

Documents will be stored at:
```
s3://llamasee-dp-test-tenant-001/
  tenant_test-tenant-001/
    invoice_raw/
      documents/
        doc_abc123.pdf
```

## Troubleshooting

### "Cannot access bucket" error
- Verify AWS credentials are configured
- Check bucket name and region are correct
- Ensure IAM permissions allow S3 access

### "DocEX not initialized" error
- Run `docex init` to initialize DocEX

### "Import boto3" error
- Install boto3: `pip install boto3`

## Next Steps

After successful tests:
1. Integrate with LlamaSee-DP
2. Update basket creation in provisioning processors
3. Test end-to-end with real document processing
