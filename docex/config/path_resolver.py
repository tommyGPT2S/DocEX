"""
Unified Path Resolver for DocEX 3.0

Provides consistent path resolution across all storage backends and database types.
All configuration comes from config.yaml; only tenant_id is required at runtime.
"""

import logging
from typing import Optional, Dict, Any
from pathlib import Path
from docex.config.docex_config import DocEXConfig
from docex.config.config_resolver import ConfigResolver
from docex.db.schema_resolver import SchemaResolver

logger = logging.getLogger(__name__)


class DocEXPathResolver:
    """
    Unified path resolver for DocEX storage and database paths.
    
    Provides consistent path resolution across:
    - S3 storage prefixes
    - Filesystem storage paths
    - Database schema names (PostgreSQL)
    - Database file paths (SQLite)
    
    All configuration comes from config.yaml. Only tenant_id is required at runtime.
    """
    
    def __init__(self, config: Optional[DocEXConfig] = None):
        """
        Initialize path resolver.
        
        Args:
            config: Optional DocEXConfig instance. If None, uses default config.
        """
        self.config = config or DocEXConfig()
        self.config_resolver = ConfigResolver(config)
        self.schema_resolver = SchemaResolver(config)
    
    # ==================== S3 Path Resolution ====================
    
    def resolve_s3_prefix(self, tenant_id: str) -> str:
        """
        Resolve S3 prefix for a tenant.
        
        Structure: {app_name}/{prefix}/tenant_{tenant_id}/
        - app_name: Business identifier (organization, business unit, or deployment name) - required
        - prefix: Environment prefix (optional, e.g., "production", "staging")
        - tenant_id: Tenant identifier (runtime parameter)
        
        Examples:
        - With prefix: "acme-corp/production/tenant_acme/"
        - Without prefix: "acme-corp/tenant_acme/"
        
        Args:
            tenant_id: Tenant identifier (only runtime parameter)
            
        Returns:
            S3 prefix string
        """
        return self.config_resolver.resolve_s3_prefix(tenant_id)
    
    # ==================== Filesystem Path Resolution ====================
    
    def resolve_filesystem_path(self, tenant_id: Optional[str] = None, basket_id: Optional[str] = None) -> str:
        """
        Resolve filesystem storage path for a tenant and optional basket.
        
        Structure: {base_path}/tenant_{tenant_id}/basket_{basket_id}/
        - base_path: Base storage path from config
        - tenant_id: Optional tenant identifier (runtime parameter)
        - basket_id: Optional basket identifier
        
        Args:
            tenant_id: Optional tenant identifier (only runtime parameter)
            basket_id: Optional basket identifier for basket-specific paths
            
        Returns:
            Filesystem storage path
        """
        storage_config = self.config.get('storage', {})
        fs_config = storage_config.get('filesystem', {})
        base_path = fs_config.get('path', 'storage')
        
        # Build path parts
        path_parts = [base_path]
        
        # Add tenant path if tenant_id provided
        if tenant_id:
            path_parts.append(f"tenant_{tenant_id}")
        
        # Add basket path if provided
        if basket_id:
            path_parts.append(f"basket_{basket_id}")
        
        # Join and return
        full_path = Path('/'.join(path_parts))
        
        logger.debug(f"Resolved filesystem path for tenant '{tenant_id}', basket '{basket_id}': {full_path}")
        return str(full_path)
    
    def resolve_s3_basket_prefix(self, tenant_id: str, basket_id: str) -> str:
        """
        Resolve S3 prefix for a basket within a tenant.
        
        Structure: {app_name}/{prefix}/tenant_{tenant_id}/baskets/{basket_id}/
        
        Args:
            tenant_id: Tenant identifier (only runtime parameter)
            basket_id: Basket identifier (only runtime parameter)
            
        Returns:
            S3 prefix string for the basket
        """
        tenant_prefix = self.resolve_s3_prefix(tenant_id)
        basket_prefix = f"{tenant_prefix}baskets/{basket_id}/"
        logger.debug(f"Resolved S3 basket prefix for tenant '{tenant_id}', basket '{basket_id}': {basket_prefix}")
        return basket_prefix
    
    # ==================== Database Path Resolution ====================
    
    def resolve_db_schema(self, tenant_id: str) -> str:
        """
        Resolve database schema name for a tenant (PostgreSQL).
        
        Uses schema_template from config.yaml:
        - Default: "tenant_{tenant_id}"
        - Configurable via: database.postgres.schema_template
        
        Args:
            tenant_id: Tenant identifier (only runtime parameter)
            
        Returns:
            Schema name (e.g., "tenant_acme")
            
        Raises:
            ValueError: If database type is not PostgreSQL
        """
        return self.schema_resolver.resolve_schema_name(tenant_id)
    
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
            
        Raises:
            ValueError: If database type is not SQLite
        """
        return self.schema_resolver.resolve_database_path(tenant_id)
    
    def resolve_isolation_boundary(self, tenant_id: str) -> tuple[str, str]:
        """
        Resolve isolation boundary for a tenant.
        
        Returns tuple of (isolation_type, boundary_name):
        - For PostgreSQL: ('schema', 'tenant_acme')
        - For SQLite: ('database', 'storage/tenant_acme/docex.db')
        
        Args:
            tenant_id: Tenant identifier (only runtime parameter)
            
        Returns:
            Tuple of (isolation_type, boundary_name)
            - isolation_type: 'schema' or 'database'
            - boundary_name: Schema name (PostgreSQL) or database path (SQLite)
        """
        return self.schema_resolver.resolve_isolation_boundary(tenant_id)
    
    # ==================== Storage Config Resolution ====================
    
    def get_storage_config_for_tenant(self, tenant_id: str) -> Dict[str, Any]:
        """
        Get storage configuration for a tenant with tenant-aware paths.
        
        For S3 storage, automatically includes tenant_id in prefix.
        For filesystem storage, includes tenant_id in path.
        
        Args:
            tenant_id: Tenant identifier (only runtime parameter)
            
        Returns:
            Storage configuration dictionary with tenant-aware settings
        """
        return self.config_resolver.get_storage_config_for_tenant(tenant_id)

