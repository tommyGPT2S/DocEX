"""
Tenant Registry Model for DocEX 3.0 Multi-Tenancy

This model stores metadata about all provisioned tenants in the system.
The tenant registry itself is stored in the bootstrap tenant's schema/database.
"""

from datetime import datetime, timezone
from sqlalchemy import Column, String, Boolean, DateTime
from docex.db.connection import get_base

Base = get_base()


class TenantRegistry(Base):
    """
    Registry of all provisioned tenants in the system.
    
    This table is stored in the bootstrap tenant's schema/database to ensure
    system-level isolation. It tracks all tenants (both system and business tenants).
    
    Attributes:
        tenant_id: Unique identifier for the tenant (primary key)
        display_name: Human-readable name for the tenant
        is_system: Flag indicating if this is a system tenant (bootstrap tenant)
        isolation_strategy: How tenant data is isolated ('schema' or 'database')
        schema_name: PostgreSQL schema name (for schema-per-tenant)
        database_path: SQLite database file path (for database-per-tenant)
        created_at: When the tenant was provisioned
        created_by: User ID who created the tenant
        last_updated_at: When the tenant record was last modified
        last_updated_by: User ID who last updated the tenant
    """
    __tablename__ = 'tenant_registry'
    # Note: Schema is determined by the database connection's search_path
    # For PostgreSQL, the search_path is set to the bootstrap tenant's schema
    # For SQLite, the table is in the bootstrap tenant's database file
    
    # Primary key
    tenant_id = Column(String(255), primary_key=True)
    
    # Tenant information
    display_name = Column(String(255), nullable=False)
    is_system = Column(Boolean, nullable=False, default=False)
    
    # Isolation strategy configuration
    isolation_strategy = Column(String(50), nullable=False)  # 'schema' or 'database'
    
    # Database-specific paths
    schema_name = Column(String(255), nullable=True)  # PostgreSQL schema name
    database_path = Column(String(500), nullable=True)  # SQLite database file path
    
    # Standard audit fields
    created_at = Column(DateTime, nullable=False, default=lambda: datetime.now(timezone.utc))
    created_by = Column(String(255), nullable=False)  # User ID who created the tenant
    last_updated_at = Column(DateTime, nullable=False, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))
    last_updated_by = Column(String(255), nullable=True)  # User ID who last updated the tenant
    
    def __repr__(self):
        return (
            f"<TenantRegistry(tenant_id='{self.tenant_id}', "
            f"display_name='{self.display_name}', "
            f"is_system={self.is_system}, "
            f"isolation_strategy='{self.isolation_strategy}')>"
        )
    
    def to_dict(self):
        """Convert tenant registry entry to dictionary"""
        return {
            'tenant_id': self.tenant_id,
            'display_name': self.display_name,
            'is_system': self.is_system,
            'isolation_strategy': self.isolation_strategy,
            'schema_name': self.schema_name,
            'database_path': self.database_path,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'created_by': self.created_by,
            'last_updated_at': self.last_updated_at.isoformat() if self.last_updated_at else None,
            'last_updated_by': self.last_updated_by,
        }

