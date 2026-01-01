# S3 Storage Implementation Review

## Current Implementation

The S3 storage implementation uses a `prefix` configuration parameter to organize files within a bucket:

```python
self.prefix = config.get('prefix', '').strip('/')
if self.prefix and not self.prefix.endswith('/'):
    self.prefix += '/'
```

## Recommendation: Add Application Name

### ✅ **YES - Application Name Should Be Included**

**Benefits:**

1. **Multi-Application Deployments**: When multiple applications share the same S3 bucket, application name provides clear namespace separation
2. **Organization**: Better structure: `{app_name}/{tenant_id}/{document_path}` vs just `{prefix}/{document_path}`
3. **Cleanup & Management**: Easier to identify and manage files per application
4. **Security**: Can apply IAM policies per application namespace
5. **Cost Tracking**: Can track S3 costs per application

### Proposed Structure

```
s3://bucket/
  {app_name}/              # Application namespace
    {tenant_id}/           # Tenant namespace (if multi-tenant)
      documents/           # Document storage
      metadata/            # Metadata storage
```

### Implementation

Add `app_name` to S3 configuration:

```yaml
storage:
  type: s3
  s3:
    bucket: my-documents-bucket
    app_name: docex          # Application identifier
    prefix: production       # Optional: environment prefix
    region: us-east-1
```

**Key Path Construction:**
```python
# Full S3 key structure:
# {app_name}/{prefix}/{tenant_id}/{document_path}
# Example: docex/production/tenant_acme/documents/invoice_123.pdf
```

### Backward Compatibility

- If `app_name` not provided, use `prefix` only (current behavior)
- If both provided: `{app_name}/{prefix}/...`
- Migration: Existing deployments continue to work

---

## Implementation Plan

1. Add `app_name` to S3 config schema
2. Update `_get_full_key()` to include app_name
3. Update documentation
4. Add migration guide for existing deployments

