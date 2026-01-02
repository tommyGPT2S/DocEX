"""
Unified Path Resolver for DocEX 3.0

Provides consistent path resolution across all storage backends and database types.
All configuration comes from config.yaml; only tenant_id is required at runtime.
"""

import logging
import re
from typing import Optional, Dict, Any
from pathlib import Path
from docex.config.docex_config import DocEXConfig
from docex.config.config_resolver import ConfigResolver
from docex.db.schema_resolver import SchemaResolver

logger = logging.getLogger(__name__)


def sanitize_basket_name(name: str) -> str:
    """
    Sanitize basket name for use in file paths.
    
    Converts basket name to a filesystem-safe, URL-safe string:
    - Lowercase
    - Replace spaces and special characters with underscores
    - Remove consecutive underscores
    - Remove leading/trailing underscores
    
    Args:
        name: Basket name to sanitize
        
    Returns:
        Sanitized basket name suitable for paths
    """
    if not name:
        return "basket"
    
    # Convert to lowercase
    sanitized = name.lower()
    
    # Replace spaces and special characters with underscores
    # Keep alphanumeric, hyphens, and underscores
    sanitized = re.sub(r'[^a-z0-9_-]', '_', sanitized)
    
    # Replace multiple consecutive underscores with single underscore
    sanitized = re.sub(r'_+', '_', sanitized)
    
    # Remove leading and trailing underscores
    sanitized = sanitized.strip('_')
    
    # Ensure it's not empty
    if not sanitized:
        sanitized = "basket"
    
    return sanitized


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
        
        Structure: {tenant_id}/{path_namespace}/{prefix}/
        - tenant_id: Tenant identifier (runtime parameter, required) - FIRST for tenant isolation
        - path_namespace: Business identifier (optional, from config)
        - prefix: Environment prefix (optional, from config)
        
        Tenant ID is FIRST in the path for better tenant isolation, IAM policies, and cost tracking.
        
        Examples:
        - With all: "acme_corp/acme-corp/production/"
        - Without prefix: "acme_corp/acme-corp/"
        - Minimal: "acme_corp/"
        
        Args:
            tenant_id: Tenant identifier (only runtime parameter, required)
            
        Returns:
            S3 prefix string
        """
        return self.config_resolver.resolve_s3_prefix(tenant_id)
    
    # ==================== Filesystem Path Resolution ====================
    
    def resolve_filesystem_path(self, tenant_id: Optional[str] = None, basket_id: Optional[str] = None, basket_name: Optional[str] = None) -> str:
        """
        Resolve filesystem storage path for a tenant and optional basket.
        
        Structure: {base_path}/{tenant_id}/{basket_friendly_name}_{last_4_of_basket_id}/
        - base_path: Base storage path from config
        - tenant_id: Optional tenant identifier (runtime parameter)
        - basket_name: Optional basket name (for friendly path)
        - basket_id: Optional basket identifier (for uniqueness)
        
        Args:
            tenant_id: Optional tenant identifier (only runtime parameter)
            basket_id: Optional basket identifier for basket-specific paths
            basket_name: Optional basket name for friendly path generation
            
        Returns:
            Filesystem storage path
        """
        storage_config = self.config.get('storage', {})
        fs_config = storage_config.get('filesystem', {})
        base_path = fs_config.get('path', 'storage')
        
        # Build path parts
        path_parts = [base_path]
        
        # Add tenant path if tenant_id provided - simplified: just tenant_id, no "tenant_" prefix
        if tenant_id:
            path_parts.append(tenant_id)
        
        # Add basket path if provided - will be set by DocBasket.create() with friendly name
        # This method is used for base path resolution; basket-specific paths are handled in DocBasket
        if basket_id:
            if basket_name:
                # Use friendly name format: {sanitized_name}_{last_4_of_id}
                sanitized_name = sanitize_basket_name(basket_name)
                basket_path = f"{sanitized_name}_{basket_id[-4:]}"
            else:
                # Fallback to basket_{id} if no name provided
                basket_path = f"basket_{basket_id}"
            path_parts.append(basket_path)
        
        # Join and return
        full_path = Path('/'.join(path_parts))
        
        logger.debug(f"Resolved filesystem path for tenant '{tenant_id}', basket '{basket_id}' (name: '{basket_name}'): {full_path}")
        return str(full_path)
    
    def resolve_s3_basket_prefix(self, tenant_id: str, basket_id: str, basket_name: str) -> str:
        """
        Resolve S3 prefix for a basket within a tenant.
        
        Structure: {tenant_id}/{path_namespace}/{prefix}/{basket_friendly_name}_{last_4_of_basket_id}/
        - Tenant ID is FIRST for tenant isolation
        - Uses basket's friendly name (sanitized) + last 4 characters of basket_id for uniqueness
        
        Args:
            tenant_id: Tenant identifier (only runtime parameter, required)
            basket_id: Basket identifier (full ID)
            basket_name: Basket friendly name (will be sanitized)
            
        Returns:
            S3 prefix string for the basket
        """
        from docex.utils.s3_prefix_builder import sanitize_basket_name
        
        tenant_prefix = self.resolve_s3_prefix(tenant_id)
        # Get last 4 characters of basket_id (remove 'bas_' prefix if present)
        basket_id_suffix = basket_id.replace('bas_', '')[-4:] if basket_id.startswith('bas_') else basket_id[-4:]
        # Sanitize basket name for filesystem safety
        sanitized_name = sanitize_basket_name(basket_name)
        # Build basket path: {friendly_name}_{last_4_of_id}
        basket_path = f"{sanitized_name}_{basket_id_suffix}"
        basket_prefix = f"{tenant_prefix}{basket_path}/"
        logger.debug(f"Resolved S3 basket prefix for tenant '{tenant_id}', basket '{basket_id}' (name: '{basket_name}'): {basket_prefix}")
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

