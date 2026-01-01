#!/usr/bin/env python3
"""
Manual test script for DocEX 3.0 Multi-Tenancy

Run this script to test the implementation:
    python test_docex3_manual.py
"""

import sys
from pathlib import Path

# Add project to path
sys.path.insert(0, str(Path(__file__).parent))

def test_config_resolution():
    """Test configuration resolution"""
    print("\n" + "="*60)
    print("TEST 1: Configuration Resolution")
    print("="*60)
    
    try:
        from docex.config.config_resolver import ConfigResolver
        from docex.db.schema_resolver import SchemaResolver
        from docex.config.docex_config import DocEXConfig
        
        config = DocEXConfig()
        
        # Test S3 prefix resolution
        print("\n1.1 Testing S3 Prefix Resolution...")
        resolver = ConfigResolver(config)
        
        # Set up test config
        if 'storage' not in config.config:
            config.config['storage'] = {}
        if 's3' not in config.config['storage']:
            config.config['storage']['s3'] = {}
        
        config.config['storage']['s3'] = {
            'app_name': 'docex',
            'prefix': 'production'
        }
        
        prefix = resolver.resolve_s3_prefix(tenant_id='acme')
        print(f"   ✅ S3 prefix for tenant 'acme': {prefix}")
        assert prefix == 'docex/production/tenant_acme/', f"Expected 'docex/production/tenant_acme/', got '{prefix}'"
        
        # Test DB schema resolution
        print("\n1.2 Testing DB Schema Resolution...")
        schema_resolver = SchemaResolver(config)
        
        if 'database' not in config.config:
            config.config['database'] = {}
        config.config['database']['type'] = 'postgres'
        if 'postgres' not in config.config['database']:
            config.config['database']['postgres'] = {}
        config.config['database']['postgres']['schema_template'] = 'tenant_{tenant_id}'
        
        schema = schema_resolver.resolve_schema_name(tenant_id='acme')
        print(f"   ✅ DB schema for tenant 'acme': {schema}")
        assert schema == 'tenant_acme', f"Expected 'tenant_acme', got '{schema}'"
        
        # Test DB path resolution
        print("\n1.3 Testing DB Path Resolution...")
        config.config['database']['type'] = 'sqlite'
        if 'sqlite' not in config.config['database']:
            config.config['database']['sqlite'] = {}
        config.config['database']['sqlite']['path_template'] = 'storage/tenant_{tenant_id}/docex.db'
        
        db_path = schema_resolver.resolve_database_path(tenant_id='acme')
        print(f"   ✅ DB path for tenant 'acme': {db_path}")
        assert db_path == 'storage/tenant_acme/docex.db', f"Expected 'storage/tenant_acme/docex.db', got '{db_path}'"
        
        print("\n   ✅ All configuration resolution tests passed!")
        return True
        
    except Exception as e:
        print(f"\n   ❌ Configuration resolution test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_tenant_id_validation():
    """Test tenant ID validation"""
    print("\n" + "="*60)
    print("TEST 2: Tenant ID Validation")
    print("="*60)
    
    try:
        from docex.provisioning.tenant_provisioner import TenantProvisioner, InvalidTenantIdError
        from docex.config.docex_config import DocEXConfig
        
        config = DocEXConfig()
        provisioner = TenantProvisioner(config)
        
        # Test invalid tenant IDs
        print("\n2.1 Testing Invalid Tenant IDs...")
        invalid_ids = [
            ('', 'empty string'),
            ('_docex_system_', 'system tenant pattern'),
            ('_docex_audit_', 'system tenant pattern'),
        ]
        
        for tenant_id, reason in invalid_ids:
            try:
                provisioner.validate_tenant_id(tenant_id)
                print(f"   ❌ Should have rejected '{tenant_id}' ({reason})")
                return False
            except InvalidTenantIdError:
                print(f"   ✅ Correctly rejected '{tenant_id}' ({reason})")
        
        # Test valid tenant IDs
        print("\n2.2 Testing Valid Tenant IDs...")
        valid_ids = ['acme', 'acme-corp', 'acme_corp', 'tenant123']
        
        for tenant_id in valid_ids:
            try:
                provisioner.validate_tenant_id(tenant_id)
                print(f"   ✅ Accepted valid tenant ID: '{tenant_id}'")
            except InvalidTenantIdError as e:
                print(f"   ❌ Incorrectly rejected valid tenant ID '{tenant_id}': {e}")
                return False
        
        print("\n   ✅ All tenant ID validation tests passed!")
        return True
        
    except Exception as e:
        print(f"\n   ❌ Tenant ID validation test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_system_tenant_detection():
    """Test system tenant pattern detection"""
    print("\n" + "="*60)
    print("TEST 3: System Tenant Detection")
    print("="*60)
    
    try:
        from docex.provisioning.tenant_provisioner import TenantProvisioner
        
        provisioner = TenantProvisioner()
        
        # Test system tenant IDs
        print("\n3.1 Testing System Tenant Pattern Detection...")
        system_tenants = ['_docex_system_', '_docex_audit_', '_docex_migration_']
        non_system_tenants = ['acme', 'tenant1', 'user_tenant']
        
        for tenant_id in system_tenants:
            is_system = TenantProvisioner.is_system_tenant(tenant_id)
            print(f"   ✅ '{tenant_id}' detected as system tenant: {is_system}")
            assert is_system, f"'{tenant_id}' should be detected as system tenant"
        
        for tenant_id in non_system_tenants:
            is_system = TenantProvisioner.is_system_tenant(tenant_id)
            print(f"   ✅ '{tenant_id}' detected as non-system tenant: {not is_system}")
            assert not is_system, f"'{tenant_id}' should not be detected as system tenant"
        
        print("\n   ✅ All system tenant detection tests passed!")
        return True
        
    except Exception as e:
        print(f"\n   ❌ System tenant detection test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """Run all tests"""
    print("\n" + "="*60)
    print("DocEX 3.0 Multi-Tenancy - Manual Test Suite")
    print("="*60)
    
    results = []
    
    # Test 1: Configuration Resolution
    results.append(("Configuration Resolution", test_config_resolution()))
    
    # Test 2: Tenant ID Validation
    results.append(("Tenant ID Validation", test_tenant_id_validation()))
    
    # Test 3: System Tenant Detection
    results.append(("System Tenant Detection", test_system_tenant_detection()))
    
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

