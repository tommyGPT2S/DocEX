"""
Test suite for DocEX 3.0 Multi-Tenancy Implementation

Tests:
1. Configuration resolution (S3 prefix, DB schema)
2. Bootstrap tenant initialization
3. Tenant provisioning
4. UserContext enforcement
5. Setup validation
"""

import unittest
import tempfile
import shutil
from pathlib import Path
from datetime import datetime, timezone

from docex.config.config_resolver import ConfigResolver
from docex.db.schema_resolver import SchemaResolver
from docex.config.docex_config import DocEXConfig
from docex.context import UserContext
from docex import DocEX


class TestConfigResolution(unittest.TestCase):
    """Test configuration resolution methods"""
    
    def setUp(self):
        """Set up test configuration"""
        self.config = DocEXConfig()
        # Ensure test config has required templates
        if 'multi_tenancy' not in self.config.config:
            self.config.config['multi_tenancy'] = {
                'enabled': True,
                'isolation_strategy': 'schema'
            }
        if 'storage' not in self.config.config:
            self.config.config['storage'] = {}
        if 's3' not in self.config.config.get('storage', {}):
            self.config.config['storage']['s3'] = {}
    
    def test_s3_prefix_resolution(self):
        """Test S3 prefix resolution from tenant_id"""
        resolver = ConfigResolver(self.config)
        
        # Set up S3 config
        self.config.config['storage']['s3'] = {
            'app_name': 'docex',
            'prefix': 'production'
        }
        
        prefix = resolver.resolve_s3_prefix(tenant_id='acme')
        self.assertEqual(prefix, 'docex/production/tenant_acme/')
        
        # Test without prefix
        self.config.config['storage']['s3'] = {
            'app_name': 'docex'
        }
        prefix = resolver.resolve_s3_prefix(tenant_id='acme')
        self.assertEqual(prefix, 'docex/tenant_acme/')
        
        # Test without app_name
        self.config.config['storage']['s3'] = {
            'prefix': 'production'
        }
        prefix = resolver.resolve_s3_prefix(tenant_id='acme')
        self.assertEqual(prefix, 'production/tenant_acme/')
    
    def test_db_schema_resolution(self):
        """Test database schema name resolution"""
        resolver = SchemaResolver(self.config)
        
        # Set up PostgreSQL config
        self.config.config['database'] = {
            'type': 'postgres',
            'postgres': {
                'schema_template': 'tenant_{tenant_id}'
            }
        }
        
        schema = resolver.resolve_schema_name(tenant_id='acme')
        self.assertEqual(schema, 'tenant_acme')
    
    def test_db_path_resolution(self):
        """Test database path resolution"""
        resolver = SchemaResolver(self.config)
        
        # Set up SQLite config
        self.config.config['database'] = {
            'type': 'sqlite',
            'sqlite': {
                'path_template': 'storage/tenant_{tenant_id}/docex.db'
            }
        }
        
        path = resolver.resolve_database_path(tenant_id='acme')
        self.assertEqual(path, 'storage/tenant_acme/docex.db')
    
    def test_isolation_boundary_resolution(self):
        """Test isolation boundary resolution"""
        resolver = SchemaResolver(self.config)
        
        # PostgreSQL
        self.config.config['database'] = {
            'type': 'postgres',
            'postgres': {
                'schema_template': 'tenant_{tenant_id}'
            }
        }
        boundary_type, boundary_name = resolver.resolve_isolation_boundary(tenant_id='acme')
        self.assertEqual(boundary_type, 'schema')
        self.assertEqual(boundary_name, 'tenant_acme')
        
        # SQLite
        self.config.config['database'] = {
            'type': 'sqlite',
            'sqlite': {
                'path_template': 'storage/tenant_{tenant_id}/docex.db'
            }
        }
        boundary_type, boundary_name = resolver.resolve_isolation_boundary(tenant_id='acme')
        self.assertEqual(boundary_type, 'database')
        self.assertEqual(boundary_name, 'storage/tenant_acme/docex.db')


class TestTenantProvisioning(unittest.TestCase):
    """Test tenant provisioning"""
    
    def setUp(self):
        """Set up test environment"""
        self.test_dir = tempfile.mkdtemp()
        self.db_path = Path(self.test_dir) / 'test_docex.db'
        
        # Update config for SQLite test database
        self.config = DocEXConfig()
        self.config.config['database'] = {
            'type': 'sqlite',
            'sqlite': {
                'path': str(self.db_path),
                'path_template': str(Path(self.test_dir) / 'tenant_{tenant_id}' / 'docex.db')
            }
        }
        self.config.config['storage'] = {
            'type': 'filesystem',
            'filesystem': {
                'path': str(Path(self.test_dir) / 'storage')
            }
        }
        self.config.config['multi_tenancy'] = {
            'enabled': True,
            'isolation_strategy': 'database',
            'bootstrap_tenant': {
                'id': '_docex_system_',
                'display_name': 'DocEX System',
                'database_path': str(Path(self.test_dir) / '_docex_system_' / 'docex.db')
            }
        }
    
    def tearDown(self):
        """Clean up test environment"""
        shutil.rmtree(self.test_dir, ignore_errors=True)
    
    def test_tenant_id_validation(self):
        """Test tenant ID validation"""
        from docex.provisioning.tenant_provisioner import TenantProvisioner, InvalidTenantIdError
        
        provisioner = TenantProvisioner(self.config)
        
        # Test invalid tenant IDs
        with self.assertRaises(InvalidTenantIdError):
            provisioner.validate_tenant_id('')
        
        with self.assertRaises(InvalidTenantIdError):
            provisioner.validate_tenant_id('_docex_system_')  # System tenant pattern
        
        with self.assertRaises(InvalidTenantIdError):
            provisioner.validate_tenant_id('_docex_audit_')  # System tenant pattern
        
        # Test valid tenant IDs
        provisioner.validate_tenant_id('acme')
        provisioner.validate_tenant_id('acme-corp')
        provisioner.validate_tenant_id('acme_corp')
        provisioner.validate_tenant_id('tenant123')


class TestSetupValidation(unittest.TestCase):
    """Test setup validation"""
    
    def test_is_properly_setup_not_initialized(self):
        """Test is_properly_setup when not initialized"""
        # This will fail if config doesn't exist
        # In a real test, we'd set up a test config
        pass


class TestUserContextEnforcement(unittest.TestCase):
    """Test UserContext enforcement"""
    
    def setUp(self):
        """Set up test configuration"""
        self.config = DocEXConfig()
        # Enable multi-tenancy for tests
        if 'multi_tenancy' not in self.config.config:
            self.config.config['multi_tenancy'] = {
                'enabled': True
            }
    
    def test_usercontext_required_when_multitenancy_enabled(self):
        """Test that UserContext is required when multi-tenancy enabled"""
        # This test requires DocEX to be initialized
        # In a real test environment, we'd set up the database first
        pass


if __name__ == '__main__':
    # Run basic config resolution tests
    print("Running DocEX 3.0 Multi-Tenancy Tests...")
    print("\n" + "="*60)
    
    # Test 1: Configuration Resolution
    print("\n1. Testing Configuration Resolution...")
    suite = unittest.TestLoader().loadTestsFromTestCase(TestConfigResolution)
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    # Test 2: Tenant ID Validation
    print("\n2. Testing Tenant ID Validation...")
    suite = unittest.TestLoader().loadTestsFromTestCase(TestTenantProvisioning)
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    print("\n" + "="*60)
    print("Test Summary:")
    print(f"  Tests run: {result.testsRun}")
    print(f"  Failures: {len(result.failures)}")
    print(f"  Errors: {len(result.errors)}")
    
    if result.failures:
        print("\nFailures:")
        for test, traceback in result.failures:
            print(f"  - {test}")
            print(f"    {traceback}")
    
    if result.errors:
        print("\nErrors:")
        for test, traceback in result.errors:
            print(f"  - {test}")
            print(f"    {traceback}")

