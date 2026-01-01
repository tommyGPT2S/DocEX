# App Name Configuration - Business Meaningful Terms

## Current State

### Configuration Item: `app_name`

**Location:** `storage.s3.app_name` in `config.yaml`

**Current Default:** `docex`

**Usage in Path Resolution:**
```
{app_name}/{prefix}/tenant_{tenant_id}/
```

**Example:** `docex/production/tenant_acme/`

---

## Issue

The term `app_name` is:
- ✅ **Configurable** (not hardcoded in path algorithm)
- ⚠️ **Technical term** - might not be business-meaningful
- ⚠️ **Default value "docex"** - too specific to the framework

---

## Proposal: More Business-Meaningful Configuration

### Option 1: Rename to `organization_name` or `business_unit`

**Rationale:**
- More business-oriented terminology
- Better reflects real-world use cases
- Clearer intent for enterprise deployments

**Structure:**
```yaml
storage:
  s3:
    organization_name: acme-corp    # Business unit or organization
    prefix: production
```

**Path:** `acme-corp/production/tenant_acme/`

---

### Option 2: Rename to `namespace` or `deployment_name`

**Rationale:**
- Generic, flexible term
- Can represent organization, business unit, or deployment
- Common in cloud infrastructure

**Structure:**
```yaml
storage:
  s3:
    namespace: acme-document-system
    prefix: production
```

**Path:** `acme-document-system/production/tenant_acme/`

---

### Option 3: Keep `app_name` but improve documentation

**Rationale:**
- `app_name` is already established
- Can be used for any business identifier
- Just needs better examples/documentation

**Structure:**
```yaml
storage:
  s3:
    app_name: acme-document-management    # Can be organization, business unit, or deployment name
    prefix: production
```

**Path:** `acme-document-management/production/tenant_acme/`

---

## Recommendation

### Option 3: Keep `app_name`, Improve Documentation

**Reasons:**
1. **Already configurable** - No code changes needed
2. **Flexible** - Can represent any business identifier
3. **Clear examples** - Show business use cases in docs
4. **Backward compatible** - No breaking changes

**Action Items:**
1. ✅ Update default config to use a more generic example
2. ✅ Update documentation to show business use cases
3. ✅ Add examples for different scenarios:
   - Organization: `acme-corp`
   - Business Unit: `finance-department`
   - Deployment: `production-instance`
   - Application: `document-management-system`

---

## Alternative: Add Alias Support

If we want to support both terms:

```yaml
storage:
  s3:
    app_name: acme-corp          # Primary (required)
    organization_name: acme-corp  # Alias (optional, falls back to app_name)
    business_unit: finance        # Alternative (optional)
```

**Code would check:**
```python
app_name = s3_config.get('organization_name') or \
           s3_config.get('business_unit') or \
           s3_config.get('app_name', '')
```

---

## Current Implementation Status

✅ **`app_name` is NOT hardcoded** - it's fully configurable
✅ **Path algorithm is generic** - works with any `app_name` value
⚠️ **Default value is "docex"** - should be changed to a more generic example
⚠️ **Documentation uses "docex"** - should show business examples

---

## Proposed Changes

1. **Update default_config.yaml:**
   ```yaml
   storage:
     s3:
       app_name: my-organization    # Change from "docex" to generic example
   ```

2. **Update documentation:**
   - Show business use cases
   - Explain that `app_name` can be any identifier
   - Provide examples for different scenarios

3. **Update code comments:**
   - Clarify that `app_name` is business-configurable
   - Remove framework-specific references

