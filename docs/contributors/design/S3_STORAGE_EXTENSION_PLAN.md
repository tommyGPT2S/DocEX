# S3 Storage Extension Project Plan

## Executive Summary

This document outlines a comprehensive plan to extend and improve the S3 storage implementation in DocEX. While a basic S3 storage implementation exists, there are several gaps and improvements needed to make it production-ready and fully integrated with the DocEX architecture.

## Current State Analysis

### What Exists
1. **Basic S3Storage Class** (`docex/storage/s3_storage.py`)
   - Implements all required `AbstractStorage` methods
   - Basic CRUD operations (save, load, delete, exists)
   - Directory operations (create_directory, list_directory)
   - Metadata operations (get_metadata, set_metadata)
   - URL generation (presigned URLs)
   - File operations (copy, move)

2. **Factory Integration**
   - S3Storage is registered in `StorageFactory`
   - Configuration structure documented in design docs

3. **Dependencies**
   - `boto3>=1.26.0` already in requirements.txt

### Issues Identified

1. **Critical: Constructor Mismatch**
   - `S3Storage.__init__()` expects individual parameters: `(bucket, access_key, secret_key, region)`
   - `StorageFactory.create_storage()` passes a config dictionary
   - `FileSystemStorage` correctly accepts a config dict
   - **Impact**: S3 storage cannot be instantiated through the factory

2. **Missing Features**
   - No support for AWS credentials from environment variables or IAM roles
   - No support for S3 path prefixes (bucket organization)
   - No support for multipart uploads for large files
   - No support for S3 encryption settings
   - No support for S3 storage classes (Standard, IA, Glacier, etc.)
   - Limited error handling and retry logic
   - No support for S3 versioning

3. **Testing Gaps**
   - No unit tests for S3Storage
   - No integration tests
   - No mock S3 tests using moto

4. **Configuration Issues**
   - Configuration structure inconsistent with filesystem storage
   - Missing validation for required S3 parameters
   - No support for per-basket S3 configuration

5. **Documentation Gaps**
   - Missing examples of S3 usage
   - No troubleshooting guide
   - Missing security best practices

## Project Goals

1. **Fix Critical Issues**: Make S3 storage work with the existing factory pattern
2. **Enhance Functionality**: Add production-ready features (credentials, encryption, multipart uploads)
3. **Improve Reliability**: Add proper error handling, retries, and validation
4. **Add Testing**: Comprehensive test coverage with mocks
5. **Update Documentation**: Complete examples and guides

## Project Phases

### Phase 1: Critical Fixes (Priority: HIGH)
**Goal**: Make S3 storage functional with the existing architecture

#### Tasks:
1. **Fix Constructor Interface**
   - Update `S3Storage.__init__()` to accept config dictionary (like FileSystemStorage)
   - Extract parameters from config dict: `bucket`, `access_key`, `secret_key`, `region`
   - Maintain backward compatibility if needed
   - Update type hints and docstrings

2. **Fix Configuration Handling**
   - Update `StorageService` to properly handle S3 configuration
   - Ensure S3 config is extracted correctly from nested config structure
   - Add validation for required S3 parameters

3. **Update Storage Factory**
   - Verify factory correctly instantiates S3Storage with config
   - Add error handling for missing S3 parameters

**Deliverables**:
- Fixed `S3Storage` class
- Updated `StorageService` for S3 support
- Basic integration test

**Estimated Time**: 2-3 days

---

### Phase 2: Enhanced Credentials Management (Priority: HIGH)
**Goal**: Support multiple AWS credential sources

#### Tasks:
1. **Environment Variable Support**
   - Support AWS_ACCESS_KEY_ID and AWS_SECRET_ACCESS_KEY
   - Support AWS_SESSION_TOKEN for temporary credentials
   - Support AWS_DEFAULT_REGION

2. **IAM Role Support**
   - Support IAM roles (EC2 instance profiles, ECS task roles)
   - Support AWS profile from ~/.aws/credentials
   - Support assume role functionality

3. **Credential Priority**
   - Config file credentials (highest priority)
   - Environment variables
   - IAM roles / instance profiles (lowest priority)

4. **Configuration Updates**
   - Add optional credential fields in config
   - Document credential precedence

**Deliverables**:
- Enhanced credential handling
- Updated configuration documentation
- Tests for different credential sources

**Estimated Time**: 2-3 days

---

### Phase 3: Advanced S3 Features (Priority: MEDIUM)
**Goal**: Add production-ready S3 features

#### Tasks:
1. **Path Prefix Support**
   - Support S3 key prefixes for bucket organization
   - Allow per-basket prefixes
   - Update path handling to include prefixes

2. **Multipart Upload Support**
   - Implement multipart uploads for files > 5MB
   - Configurable multipart threshold
   - Progress tracking for large uploads

3. **S3 Storage Classes**
   - Support different storage classes (Standard, IA, Glacier, etc.)
   - Configurable per-basket or per-document
   - Default to Standard

4. **Encryption Support**
   - Support SSE-S3 (server-side encryption)
   - Support SSE-KMS (KMS encryption)
   - Support SSE-C (customer-provided keys)
   - Configurable encryption settings

5. **Versioning Support**
   - Support S3 versioning (if enabled on bucket)
   - Retrieve specific versions
   - List versions

**Deliverables**:
- Enhanced S3Storage with advanced features
- Configuration options for new features
- Documentation updates

**Estimated Time**: 5-7 days

---

### Phase 4: Error Handling & Reliability (Priority: MEDIUM)
**Goal**: Improve robustness and error handling

#### Tasks:
1. **Retry Logic**
   - Implement exponential backoff for transient errors
   - Configurable retry attempts and delays
   - Handle specific S3 error codes (503, 500, etc.)

2. **Better Error Messages**
   - User-friendly error messages
   - Detailed logging for debugging
   - Error context preservation

3. **Connection Pooling**
   - Optimize boto3 client configuration
   - Connection pooling settings
   - Timeout configuration

4. **Validation**
   - Validate bucket names
   - Validate S3 keys (path names)
   - Validate configuration parameters

**Deliverables**:
- Robust error handling
- Improved logging
- Configuration validation

**Estimated Time**: 3-4 days

---

### Phase 5: Testing (Priority: HIGH)
**Goal**: Comprehensive test coverage

#### Tasks:
1. **Unit Tests**
   - Test all AbstractStorage methods
   - Test credential handling
   - Test error scenarios
   - Use moto for S3 mocking

2. **Integration Tests**
   - Test with real S3 (optional, with test bucket)
   - Test configuration loading
   - Test StorageService integration

3. **Performance Tests**
   - Test multipart uploads
   - Test large file handling
   - Benchmark operations

4. **Test Infrastructure**
   - Set up moto for S3 mocking
   - Create test fixtures
   - Add test configuration

**Deliverables**:
- Comprehensive test suite
- Test documentation
- CI/CD integration

**Estimated Time**: 4-5 days

---

### Phase 6: Documentation & Examples (Priority: MEDIUM)
**Goal**: Complete documentation and examples

#### Tasks:
1. **API Documentation**
   - Update API reference with S3 examples
   - Document all configuration options
   - Document error codes and handling

2. **Usage Examples**
   - Basic S3 setup example
   - Per-basket S3 configuration example
   - Advanced features examples
   - Migration guide (filesystem to S3)

3. **Troubleshooting Guide**
   - Common issues and solutions
   - Credential troubleshooting
   - Permission issues
   - Performance tuning

4. **Security Best Practices**
   - IAM policy recommendations
   - Encryption recommendations
   - Access control guidelines

**Deliverables**:
- Updated documentation
- Code examples
- Troubleshooting guide

**Estimated Time**: 2-3 days

---

## Implementation Details

### Phase 1: Constructor Fix

**Current Code**:
```python
def __init__(self, bucket: str, access_key: str, secret_key: str, region: str = 'us-east-1'):
```

**Proposed Fix**:
```python
def __init__(self, config: Dict[str, Any]):
    """
    Initialize S3 storage
    
    Args:
        config: Configuration dictionary with:
            - bucket: S3 bucket name (required)
            - access_key: AWS access key (optional if using IAM/env vars)
            - secret_key: AWS secret key (optional if using IAM/env vars)
            - region: AWS region (default: us-east-1)
            - prefix: Optional S3 key prefix
            - storage_class: S3 storage class (default: STANDARD)
            - encryption: Encryption settings
    """
    self.config = config
    self.bucket = config.get('bucket')
    if not self.bucket:
        raise ValueError("S3 bucket name is required")
    
    # Extract credentials with fallback to environment/IAM
    self.access_key = config.get('access_key') or os.getenv('AWS_ACCESS_KEY_ID')
    self.secret_key = config.get('secret_key') or os.getenv('AWS_SECRET_ACCESS_KEY')
    self.region = config.get('region', os.getenv('AWS_DEFAULT_REGION', 'us-east-1'))
    self.prefix = config.get('prefix', '')
    
    # Initialize S3 client
    # ... rest of initialization
```

### Phase 2: Credential Handling

**Proposed Implementation**:
```python
def _get_credentials(self, config: Dict[str, Any]) -> Dict[str, Optional[str]]:
    """Get AWS credentials from config, environment, or IAM role"""
    credentials = {
        'access_key': config.get('access_key'),
        'secret_key': config.get('secret_key'),
        'session_token': config.get('session_token'),
        'region': config.get('region', 'us-east-1')
    }
    
    # Fallback to environment variables
    if not credentials['access_key']:
        credentials['access_key'] = os.getenv('AWS_ACCESS_KEY_ID')
    if not credentials['secret_key']:
        credentials['secret_key'] = os.getenv('AWS_SECRET_ACCESS_KEY')
    if not credentials['session_token']:
        credentials['session_token'] = os.getenv('AWS_SESSION_TOKEN')
    if credentials['region'] == 'us-east-1':
        credentials['region'] = os.getenv('AWS_DEFAULT_REGION', 'us-east-1')
    
    # If still no credentials, boto3 will use IAM role or default profile
    return credentials
```

### Phase 3: Configuration Structure

**Proposed YAML Structure**:
```yaml
storage:
  default_type: s3
  s3:
    bucket: docex-bucket
    region: us-east-1
    prefix: docex/  # Optional prefix for all keys
    access_key: ${AWS_ACCESS_KEY_ID}  # Optional, can use env vars
    secret_key: ${AWS_SECRET_ACCESS_KEY}  # Optional
    storage_class: STANDARD  # STANDARD, STANDARD_IA, GLACIER, etc.
    encryption:
      type: SSE-S3  # SSE-S3, SSE-KMS, SSE-C
      kms_key_id: null  # Required for SSE-KMS
    multipart_threshold: 5242880  # 5MB
    max_retries: 3
    retry_delay: 1.0
```

## Testing Strategy

### Unit Tests (using moto)
```python
import boto3
from moto import mock_s3
from docex.storage.s3_storage import S3Storage

@mock_s3
def test_s3_storage_save():
    # Create mock S3 bucket
    s3 = boto3.client('s3', region_name='us-east-1')
    s3.create_bucket(Bucket='test-bucket')
    
    # Test storage
    storage = S3Storage({
        'bucket': 'test-bucket',
        'region': 'us-east-1'
    })
    
    storage.save('test-key', b'test content')
    assert storage.exists('test-key')
```

### Integration Tests
- Test with real S3 bucket (optional, requires AWS credentials)
- Test credential fallback mechanisms
- Test error scenarios

## Migration Path

### For Existing Users
1. Update configuration to new structure
2. Test with existing data
3. Migrate documents if needed

### Backward Compatibility
- Support old constructor signature (deprecated)
- Provide migration guide
- Log deprecation warnings

## Success Criteria

1. ✅ S3 storage works with StorageFactory
2. ✅ All AbstractStorage methods implemented and tested
3. ✅ Support for multiple credential sources
4. ✅ Comprehensive test coverage (>80%)
5. ✅ Documentation complete with examples
6. ✅ No breaking changes to existing filesystem storage
7. ✅ Performance acceptable for production use

## Risk Assessment

### High Risk
- **Breaking Changes**: Mitigation - maintain backward compatibility, thorough testing
- **Credential Security**: Mitigation - follow AWS best practices, document security

### Medium Risk
- **Performance**: Mitigation - benchmark, optimize, add caching if needed
- **Cost**: Mitigation - document S3 costs, provide optimization tips

### Low Risk
- **Compatibility**: Mitigation - test with different boto3 versions

## Timeline Estimate

**Total Estimated Time**: 18-25 days

- Phase 1: 2-3 days
- Phase 2: 2-3 days
- Phase 3: 5-7 days
- Phase 4: 3-4 days
- Phase 5: 4-5 days
- Phase 6: 2-3 days

**Recommended Approach**: 
- Start with Phase 1 (critical fixes) to make S3 functional
- Then Phase 5 (testing) to ensure quality
- Follow with Phase 2 (credentials) for production readiness
- Add Phase 3-4 features based on requirements
- Complete with Phase 6 (documentation)

## Dependencies

### External
- `boto3>=1.26.0` (already in requirements)
- `moto` (for testing) - needs to be added

### Internal
- No breaking changes to AbstractStorage interface
- StorageFactory must support config dict pattern
- StorageService must handle S3 config extraction

## Next Steps

1. **Review and Approve Plan**: Get stakeholder approval
2. **Set Up Development Environment**: 
   - Install dependencies
   - Set up test S3 bucket (optional)
   - Configure moto for testing
3. **Start Phase 1**: Fix critical constructor issue
4. **Iterate**: Follow phases sequentially, with testing at each step

## Questions for Discussion

1. **Priority**: Which phases are most critical for your use case?
2. **Features**: Are there specific S3 features you need immediately?
3. **Testing**: Do you have AWS credentials for integration testing?
4. **Backward Compatibility**: Is maintaining old constructor signature important?
5. **Performance**: Are there specific performance requirements?

---

**Document Version**: 1.0  
**Last Updated**: 2024  
**Author**: DocEX Development Team

