"""
Configuration Resolver for DocEX 3.0

Provides explicit methods to resolve tenant-specific configurations from config.yaml.
Only tenant_id is required at runtime; all other configuration comes from config.yaml.
"""

import logging
from typing import Optional, Dict, Any
from docex.config.docex_config import DocEXConfig

logger = logging.getLogger(__name__)


class ConfigResolver:
    """
    Resolves tenant-specific configurations from config.yaml.
    
    All configuration comes from config.yaml file. Only tenant_id is required at runtime.
    """
    
    def __init__(self, config: Optional[DocEXConfig] = None):
        """
        Initialize configuration resolver.
        
        Args:
            config: Optional DocEXConfig instance. If None, uses default config.
        """
        self.config = config or DocEXConfig()
    
    def resolve_s3_prefix(self, tenant_id: str) -> str:
        """
        Resolve S3 prefix for a tenant.
        
        Constructs S3 prefix from configuration templates:
        - {app_name}/{prefix}/{tenant_id}/
        
        All parts come from config.yaml except tenant_id.
        
        Args:
            tenant_id: Tenant identifier (only runtime parameter)
            
        Returns:
            S3 prefix string (e.g., "docex/production/tenant_acme/")
        """
        storage_config = self.config.get('storage', {})
        s3_config = storage_config.get('s3', {})
        
        # Get app_name and prefix from config
        app_name = s3_config.get('app_name', '').strip('/')
        prefix = s3_config.get('prefix', '').strip('/')
        
        # Build prefix parts
        prefix_parts = []
        if app_name:
            prefix_parts.append(app_name)
        if prefix:
            prefix_parts.append(prefix)
        
        # Add tenant_id (only runtime parameter)
        if tenant_id:
            prefix_parts.append(f"tenant_{tenant_id}")
        
        # Join and ensure trailing slash
        full_prefix = '/'.join(prefix_parts)
        if full_prefix and not full_prefix.endswith('/'):
            full_prefix += '/'
        
        logger.debug(f"Resolved S3 prefix for tenant '{tenant_id}': {full_prefix}")
        return full_prefix
    
    def resolve_db_schema_name(self, tenant_id: str) -> str:
        """
        Resolve database schema name for a tenant (PostgreSQL).
        
        Uses schema_template from config.yaml:
        - Default: "tenant_{tenant_id}"
        - Configurable via: database.postgres.schema_template
        
        Args:
            tenant_id: Tenant identifier (only runtime parameter)
            
        Returns:
            Schema name (e.g., "tenant_acme")
        """
        db_config = self.config.get('database', {})
        db_type = db_config.get('type', 'sqlite')
        
        if db_type not in ['postgresql', 'postgres']:
            raise ValueError(f"Schema resolution only applicable for PostgreSQL, not {db_type}")
        
        postgres_config = db_config.get('postgres', {})
        schema_template = postgres_config.get('schema_template', 'tenant_{tenant_id}')
        
        schema_name = schema_template.format(tenant_id=tenant_id)
        
        logger.debug(f"Resolved DB schema name for tenant '{tenant_id}': {schema_name}")
        return schema_name
    
    def resolve_db_path(self, tenant_id: str) -> str:
        """
        Resolve database file path for a tenant (SQLite).
        
        Uses path_template from config.yaml:
        - Default: "storage/tenant_{tenant_id}/docex.db"
        - Configurable via: database.sqlite.path_template
        
        Args:
            tenant_id: Tenant identifier (only runtime parameter)
            
        Returns:
            Database file path (e.g., "storage/tenant_acme/docex.db")
        """
        db_config = self.config.get('database', {})
        db_type = db_config.get('type', 'sqlite')
        
        if db_type != 'sqlite':
            raise ValueError(f"Database path resolution only applicable for SQLite, not {db_type}")
        
        sqlite_config = db_config.get('sqlite', {})
        path_template = sqlite_config.get('path_template', 'storage/tenant_{tenant_id}/docex.db')
        
        db_path = path_template.format(tenant_id=tenant_id)
        
        logger.debug(f"Resolved DB path for tenant '{tenant_id}': {db_path}")
        return db_path
    
    def get_storage_config_for_tenant(self, tenant_id: str) -> Dict[str, Any]:
        """
        Get storage configuration for a tenant with tenant-aware prefix.
        
        For S3 storage, automatically includes tenant_id in prefix.
        For filesystem storage, returns as-is.
        
        Args:
            tenant_id: Tenant identifier (only runtime parameter)
            
        Returns:
            Storage configuration dictionary with tenant-aware settings
        """
        storage_config = self.config.get('storage', {}).copy()
        storage_type = storage_config.get('type', 'filesystem')
        
        if storage_type == 's3':
            # Get S3 config
            s3_config = storage_config.get('s3', {}).copy()
            
            # Resolve tenant-aware prefix
            tenant_prefix = self.resolve_s3_prefix(tenant_id)
            
            # Update prefix in config
            # The resolved prefix already includes app_name, base prefix, and tenant_id
            # So we set prefix to the full resolved prefix and clear app_name to avoid duplication
            s3_config['prefix'] = tenant_prefix.rstrip('/')
            # Clear app_name since it's already in the prefix
            s3_config.pop('app_name', None)
            
            storage_config['s3'] = s3_config
        elif storage_type == 'filesystem':
            # For filesystem, could add tenant-specific path if needed
            # For now, return as-is
            pass
        
        return storage_config
    
    def get_isolation_strategy(self) -> str:
        """
        Get isolation strategy from configuration.
        
        Returns:
            Isolation strategy: 'schema' (PostgreSQL) or 'database' (SQLite)
        """
        multi_tenancy_config = self.config.get('multi_tenancy', {})
        isolation_strategy = multi_tenancy_config.get('isolation_strategy', 'schema')
        
        # Auto-detect if not explicitly set
        if isolation_strategy == 'schema':
            db_type = self.config.get('database', {}).get('type', 'sqlite')
            if db_type == 'sqlite':
                isolation_strategy = 'database'
        
        return isolation_strategy

