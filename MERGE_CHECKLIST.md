# Merge Checklist - S3 Tenant-Aware Path Structure

## Quick Merge Steps

### 1. Verify All Changes
```bash
# Check modified files
git status

# Review key changes
git diff docex/docbasket.py
git diff docex/utils/
```

### 2. Run Tests
```bash
# Quick test
python test_s3_quick.py

# Application name test
python test_s3_with_application_name.py

# Full test suite (if available)
python tests/test_s3_tenant_path_structure.py
```

### 3. Stage Files
```bash
# Core code
git add docex/docbasket.py
git add docex/utils/s3_prefix_builder.py
git add docex/utils/tenant_basket_helper.py
git add docex/utils/__init__.py
git add docex/config/default_config.yaml

# Documentation
git add docs/S3_*.md

# Test scripts (optional - can be in separate commit)
git add test_s3_*.py
git add tests/test_s3_tenant_path_structure.py
```

### 4. Commit
```bash
git commit -m "feat: Add tenant-aware S3 path structure with application name support

- Implement documents/{id}.{ext} path structure for S3 storage
- Add application name prefix for environment separation
- Create utility functions for S3 prefix building
- Add comprehensive documentation and test scripts
- Maintain backward compatibility with existing baskets

Breaking change: New S3 baskets use documents/{id}.{ext} structure"
```

### 5. Push
```bash
git push origin <your-branch-name>
```

## Files Summary

### Modified Files
- `docex/docbasket.py` - Core path generation
- `docex/utils/__init__.py` - Exports
- `docex/config/default_config.yaml` - Config option

### New Files
- `docex/utils/s3_prefix_builder.py`
- `docex/utils/tenant_basket_helper.py`
- `docs/S3_APPLICATION_NAME_CONFIGURATION.md`
- `docs/S3_BUCKET_AUTO_CREATION.md`
- `docs/S3_BUCKET_NAMING_RECOMMENDATIONS.md`
- `docs/S3_PATH_IMPLEMENTATION_SUMMARY.md`
- `test_s3_with_application_name.py`
- `test_s3_multi_tenant_comparison.py`
- `tests/test_s3_tenant_path_structure.py`

### Updated Documentation
- `docs/S3_BUCKET_STRUCTURE_EVALUATION.md`
- `docs/S3_TENANT_CONFIGURATION_GUIDE.md`
- `docs/S3_TENANT_QUICK_REFERENCE.md`

## Key Points

✅ **Backward Compatible** - Existing baskets unaffected  
⚠️ **Breaking Change** - New S3 baskets use new path structure  
✅ **Configurable** - Application name optional  
✅ **Tested** - Comprehensive test coverage  
✅ **Documented** - Complete documentation  

## After Merge

1. Update production config with S3 settings
2. Create/verify S3 bucket exists
3. Test tenant provisioning in staging
4. Monitor S3 path structure
