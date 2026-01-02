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
        
        Constructs S3 prefix with tenant_id FIRST for better tenant isolation:
        - {tenant_id}/{path_namespace}/{prefix}/  (if prefix provided)
        - {tenant_id}/{path_namespace}/            (if prefix not provided)
        - {tenant_id}/                              (if neither path_namespace nor prefix provided)
        
        All parts come from config.yaml except tenant_id.
        
        Rationale for tenant_id first:
        - Better tenant isolation: All tenant data is grouped together
        - Easier IAM policies: Can grant access to specific tenant paths
        - Better cost tracking: Can track costs per tenant easily
        - Easier cleanup: Can delete all data for a tenant in one operation
        
        Configuration:
        - tenant_id: Tenant identifier (runtime parameter, simplified - no "tenant_" prefix)
                     Example: "acme_corp", "contoso", "tenant_001"
        - path_namespace: Business identifier (organization, business unit, or deployment name)
                          Optional, for multi-application deployments
                          Supports backward compatibility with 'app_name' config key
                          Example: "acme-corp", "finance-department", "production-instance"
        - prefix: Environment-level namespace (optional, e.g., "production", "staging", "dev")
        
        Examples:
        - With prefix: "acme_corp/acme-corp/production/" 
          (tenant_id="acme_corp", path_namespace="acme-corp", prefix="production")
        - Without prefix: "acme_corp/acme-corp/"
          (tenant_id="acme_corp", path_namespace="acme-corp")
        - Without path_namespace: "acme_corp/production/"
          (tenant_id="acme_corp", prefix="production")
        - Minimal: "acme_corp/"
          (tenant_id="acme_corp" only)
        
        Args:
            tenant_id: Tenant identifier (only runtime parameter, required)
            
        Returns:
            S3 prefix string (e.g., "acme_corp/acme-corp/production/" or "acme_corp/acme-corp/")
        """
        storage_config = self.config.get('storage', {})
        s3_config = storage_config.get('s3', {})
        
        # Get path_namespace (supports backward compatibility with app_name)
        path_namespace = s3_config.get('path_namespace', s3_config.get('app_name', '')).strip('/')
        prefix = s3_config.get('prefix', '').strip('/')
        
        # Build prefix parts with tenant_id FIRST
        prefix_parts = []
        
        # 1. tenant_id FIRST (required, runtime parameter)
        if tenant_id:
            prefix_parts.append(tenant_id)
        
        # 2. path_namespace (optional, from config)
        if path_namespace:
            prefix_parts.append(path_namespace)
        
        # 3. prefix (optional, from config)
        if prefix:
            prefix_parts.append(prefix)
        
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
    
    def resolve_s3_bucket_name(self) -> str:
        """
        Resolve S3 bucket name from configuration.
        
        Resolution order:
        1. Use 'bucket' if explicitly provided
        2. Build from 'bucket_application' if provided: {bucket_application}-documents-bucket
        3. Raise error if neither is provided
        
        Returns:
            S3 bucket name
            
        Raises:
            ValueError: If neither bucket nor bucket_application is provided
        """
        storage_config = self.config.get('storage', {})
        s3_config = storage_config.get('s3', {})
        
        # Check for explicit bucket name
        bucket = s3_config.get('bucket')
        if bucket:
            return bucket
        
        # Build bucket name from bucket_application
        bucket_application = s3_config.get('bucket_application')
        if bucket_application:
            # Build bucket name: {bucket_application}-documents-bucket
            bucket_name = f"{bucket_application}-documents-bucket"
            logger.debug(f"Resolved S3 bucket name from bucket_application '{bucket_application}': {bucket_name}")
            return bucket_name
        
        # Neither bucket nor bucket_application provided
        raise ValueError(
            "S3 bucket name must be specified. Either provide 'bucket' directly, "
            "or provide 'bucket_application' to build bucket name as '{bucket_application}-documents-bucket'"
        )
    
    def get_storage_config_for_tenant(self, tenant_id: str) -> Dict[str, Any]:
        """
        Get storage configuration for a tenant with tenant-aware prefix and bucket name.
        
        For S3 storage:
        - Resolves bucket name from 'bucket' or 'bucket_application'
        - Automatically includes tenant_id in prefix using 'path_namespace' (NOT bucket_application)
        - path_namespace is used for path prefix, bucket_application is used for bucket name
        
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
            
            # Resolve bucket name (from bucket or bucket_application)
            bucket_name = self.resolve_s3_bucket_name()
            s3_config['bucket'] = bucket_name
            
            # Resolve tenant-aware prefix (uses path_namespace, NOT bucket_application)
            tenant_prefix = self.resolve_s3_prefix(tenant_id)
            
            # Update prefix in config
            # The resolved prefix already includes path_namespace, base prefix, and tenant_id
            # So we set prefix to the full resolved prefix and clear path_namespace to avoid duplication
            s3_config['prefix'] = tenant_prefix.rstrip('/')
            # Clear path_namespace since it's already in the prefix
            s3_config.pop('path_namespace', None)
            # Keep bucket_application in config (it's used for bucket name, not path)
            
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

