"""
Database Schema Resolver for DocEX 3.0

Provides explicit method to resolve database schema/database path from tenant_id.
All configuration comes from config.yaml; only tenant_id is required at runtime.
"""

import logging
from typing import Optional
from docex.config.docex_config import DocEXConfig
from docex.config.config_resolver import ConfigResolver

logger = logging.getLogger(__name__)


class SchemaResolver:
    """
    Resolves database schema/database path from tenant_id.
    
    All configuration comes from config.yaml file. Only tenant_id is required at runtime.
    """
    
    def __init__(self, config: Optional[DocEXConfig] = None):
        """
        Initialize schema resolver.
        
        Args:
            config: Optional DocEXConfig instance. If None, uses default config.
        """
        self.config = config or DocEXConfig()
        self.resolver = ConfigResolver(config)
    
    def resolve_schema_name(self, tenant_id: str) -> str:
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
        return self.resolver.resolve_db_schema_name(tenant_id)
    
    def resolve_database_path(self, tenant_id: str) -> str:
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
        return self.resolver.resolve_db_path(tenant_id)
    
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
        db_config = self.config.get('database', {})
        db_type = db_config.get('type', 'sqlite')
        
        if db_type in ['postgresql', 'postgres']:
            schema_name = self.resolve_schema_name(tenant_id)
            return ('schema', schema_name)
        elif db_type == 'sqlite':
            db_path = self.resolve_database_path(tenant_id)
            return ('database', db_path)
        else:
            raise ValueError(f"Unsupported database type: {db_type}")

