#!/usr/bin/env python3
"""
Simple test script for DocEX 3.0 Multi-Tenancy (isolated tests)

Tests only the resolver classes without importing full DocEX module.
"""

import sys
from pathlib import Path

# Add project to path
sys.path.insert(0, str(Path(__file__).parent))


def test_config_resolver_direct():
    """Test ConfigResolver directly"""
    print("\n" + "="*60)
    print("TEST 1: ConfigResolver (Direct Import)")
    print("="*60)
    
    try:
        # Import directly to avoid boto3 dependency
        from docex.config.config_resolver import ConfigResolver
        from docex.config.docex_config import DocEXConfig
        
        config = DocEXConfig()
        
        # Set up test config
        if 'storage' not in config.config:
            config.config['storage'] = {}
        if 's3' not in config.config['storage']:
            config.config['storage']['s3'] = {}
        
        config.config['storage']['s3'] = {
            'app_name': 'docex',
            'prefix': 'production'
        }
        
        resolver = ConfigResolver(config)
        prefix = resolver.resolve_s3_prefix(tenant_id='acme')
        
        print(f"   Input: tenant_id='acme'")
        print(f"   Config: app_name='docex', prefix='production'")
        print(f"   Output: {prefix}")
        
        expected = 'docex/production/tenant_acme/'
        if prefix == expected:
            print(f"   ✅ PASSED: Expected '{expected}', got '{prefix}'")
            return True
        else:
            print(f"   ❌ FAILED: Expected '{expected}', got '{prefix}'")
            return False
            
    except Exception as e:
        print(f"   ❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_schema_resolver_direct():
    """Test SchemaResolver directly"""
    print("\n" + "="*60)
    print("TEST 2: SchemaResolver (Direct Import)")
    print("="*60)
    
    try:
        from docex.db.schema_resolver import SchemaResolver
        from docex.config.docex_config import DocEXConfig
        
        config = DocEXConfig()
        
        # Test PostgreSQL schema
        print("\n2.1 PostgreSQL Schema Resolution...")
        config.config['database'] = {
            'type': 'postgres',
            'postgres': {
                'schema_template': 'tenant_{tenant_id}'
            }
        }
        
        resolver = SchemaResolver(config)
        schema = resolver.resolve_schema_name(tenant_id='acme')
        
        print(f"   Input: tenant_id='acme'")
        print(f"   Config: schema_template='tenant_{{tenant_id}}'")
        print(f"   Output: {schema}")
        
        if schema == 'tenant_acme':
            print(f"   ✅ PASSED: Expected 'tenant_acme', got '{schema}'")
        else:
            print(f"   ❌ FAILED: Expected 'tenant_acme', got '{schema}'")
            return False
        
        # Test SQLite path
        print("\n2.2 SQLite Path Resolution...")
        config.config['database'] = {
            'type': 'sqlite',
            'sqlite': {
                'path_template': 'storage/tenant_{tenant_id}/docex.db'
            }
        }
        
        db_path = resolver.resolve_database_path(tenant_id='acme')
        
        print(f"   Input: tenant_id='acme'")
        print(f"   Config: path_template='storage/tenant_{{tenant_id}}/docex.db'")
        print(f"   Output: {db_path}")
        
        if db_path == 'storage/tenant_acme/docex.db':
            print(f"   ✅ PASSED: Expected 'storage/tenant_acme/docex.db', got '{db_path}'")
            return True
        else:
            print(f"   ❌ FAILED: Expected 'storage/tenant_acme/docex.db', got '{db_path}'")
            return False
            
    except Exception as e:
        print(f"   ❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_tenant_provisioner_validation():
    """Test TenantProvisioner validation (without full initialization)"""
    print("\n" + "="*60)
    print("TEST 3: TenantProvisioner Validation")
    print("="*60)
    
    try:
        # Import only the validation methods
        from docex.provisioning.tenant_provisioner import (
            TenantProvisioner, 
            InvalidTenantIdError,
            SYSTEM_TENANT_PATTERN,
            SYSTEM_TENANT_ID
        )
        
        print(f"\n3.1 System Tenant Pattern: {SYSTEM_TENANT_PATTERN}")
        print(f"   System Tenant ID: {SYSTEM_TENANT_ID}")
        
        # Test is_system_tenant
        print("\n3.2 Testing is_system_tenant()...")
        system_tenants = ['_docex_system_', '_docex_audit_']
        non_system_tenants = ['acme', 'tenant1']
        
        all_passed = True
        for tenant_id in system_tenants:
            is_system = TenantProvisioner.is_system_tenant(tenant_id)
            if is_system:
                print(f"   ✅ '{tenant_id}' correctly identified as system tenant")
            else:
                print(f"   ❌ '{tenant_id}' should be system tenant")
                all_passed = False
        
        for tenant_id in non_system_tenants:
            is_system = TenantProvisioner.is_system_tenant(tenant_id)
            if not is_system:
                print(f"   ✅ '{tenant_id}' correctly identified as non-system tenant")
            else:
                print(f"   ❌ '{tenant_id}' should not be system tenant")
                all_passed = False
        
        # Test validate_tenant_id (requires config, but we can test the logic)
        print("\n3.3 Testing validate_tenant_id()...")
        from docex.config.docex_config import DocEXConfig
        config = DocEXConfig()
        provisioner = TenantProvisioner(config)
        
        # Test invalid IDs
        invalid_cases = [
            ('', 'empty string'),
            ('_docex_system_', 'system tenant'),
        ]
        
        for tenant_id, reason in invalid_cases:
            try:
                provisioner.validate_tenant_id(tenant_id)
                print(f"   ❌ Should have rejected '{tenant_id}' ({reason})")
                all_passed = False
            except InvalidTenantIdError:
                print(f"   ✅ Correctly rejected '{tenant_id}' ({reason})")
        
        # Test valid IDs
        valid_ids = ['acme', 'acme-corp', 'tenant123']
        for tenant_id in valid_ids:
            try:
                provisioner.validate_tenant_id(tenant_id)
                print(f"   ✅ Accepted valid tenant ID: '{tenant_id}'")
            except InvalidTenantIdError as e:
                print(f"   ❌ Incorrectly rejected '{tenant_id}': {e}")
                all_passed = False
        
        return all_passed
        
    except Exception as e:
        print(f"   ❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """Run all tests"""
    print("\n" + "="*60)
    print("DocEX 3.0 Multi-Tenancy - Simple Test Suite")
    print("="*60)
    
    results = []
    
    # Test 1: ConfigResolver
    results.append(("ConfigResolver", test_config_resolver_direct()))
    
    # Test 2: SchemaResolver
    results.append(("SchemaResolver", test_schema_resolver_direct()))
    
    # Test 3: TenantProvisioner Validation
    results.append(("TenantProvisioner Validation", test_tenant_provisioner_validation()))
    
    # Summary
    print("\n" + "="*60)
    print("TEST SUMMARY")
    print("="*60)
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for test_name, result in results:
        status = "✅ PASSED" if result else "❌ FAILED"
        print(f"  {status}: {test_name}")
    
    print(f"\nTotal: {passed}/{total} tests passed")
    
    if passed == total:
        print("\n🎉 All tests passed!")
        return 0
    else:
        print(f"\n⚠️  {total - passed} test(s) failed")
        return 1


if __name__ == '__main__':
    sys.exit(main())

