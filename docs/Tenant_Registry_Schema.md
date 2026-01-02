# Tenant Registry Schema Definition

## Overview

The tenant registry stores metadata about all provisioned tenants in the system. It is stored in the bootstrap tenant's schema/database to ensure system-level isolation.

## Schema Definition

### SQLAlchemy Model

```python
from datetime import datetime, timezone
from sqlalchemy import Column, String, Boolean, DateTime
from docex.db.connection import get_base

Base = get_base()

class TenantRegistry(Base):
    """
    Registry of all provisioned tenants in the system.
    
    This table is stored in the bootstrap tenant's schema/database.
    """
    __tablename__ = 'tenant_registry'
    
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
        return f"<TenantRegistry(tenant_id='{self.tenant_id}', display_name='{self.display_name}', is_system={self.is_system})>"
```

### SQL Schema (PostgreSQL)

```sql
CREATE TABLE IF NOT EXISTS tenant_registry (
    tenant_id VARCHAR(255) PRIMARY KEY,
    display_name VARCHAR(255) NOT NULL,
    is_system BOOLEAN NOT NULL DEFAULT FALSE,
    isolation_strategy VARCHAR(50) NOT NULL,  -- 'schema' or 'database'
    schema_name VARCHAR(255),  -- PostgreSQL schema name (for schema-per-tenant)
    database_path VARCHAR(500),  -- SQLite database file path (for database-per-tenant)
    
    -- Standard audit fields
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    created_by VARCHAR(255) NOT NULL,
    last_updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    last_updated_by VARCHAR(255),
    
    -- Constraints
    CONSTRAINT chk_isolation_strategy CHECK (isolation_strategy IN ('schema', 'database'))
);

-- Index for system tenant lookup
CREATE INDEX IF NOT EXISTS idx_tenant_registry_is_system ON tenant_registry(is_system);

-- Index for display name searches
CREATE INDEX IF NOT EXISTS idx_tenant_registry_display_name ON tenant_registry(display_name);
```

### SQL Schema (SQLite)

```sql
CREATE TABLE IF NOT EXISTS tenant_registry (
    tenant_id TEXT PRIMARY KEY,
    display_name TEXT NOT NULL,
    is_system INTEGER NOT NULL DEFAULT 0,  -- SQLite uses INTEGER for BOOLEAN
    isolation_strategy TEXT NOT NULL CHECK (isolation_strategy IN ('schema', 'database')),
    schema_name TEXT,  -- Not used for SQLite, but kept for consistency
    database_path TEXT,  -- SQLite database file path
    
    -- Standard audit fields
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    created_by TEXT NOT NULL,
    last_updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    last_updated_by TEXT,
    
    -- Constraints
    CHECK (isolation_strategy IN ('schema', 'database'))
);

-- Indexes
CREATE INDEX IF NOT EXISTS idx_tenant_registry_is_system ON tenant_registry(is_system);
CREATE INDEX IF NOT EXISTS idx_tenant_registry_display_name ON tenant_registry(display_name);
```

## Field Descriptions

### Primary Fields

- **`tenant_id`** (VARCHAR/TEXT, PRIMARY KEY)
  - Unique identifier for the tenant
  - Must match the tenant ID used in UserContext
  - Example: `"acme"`, `"_docex_system_"`

- **`display_name`** (VARCHAR/TEXT, NOT NULL)
  - Human-readable name for the tenant
  - Example: `"Acme Corporation"`, `"DocEX System"`

- **`is_system`** (BOOLEAN/INTEGER, NOT NULL, DEFAULT FALSE)
  - Flag indicating if this is a system tenant
  - System tenants cannot be used for business operations
  - Only bootstrap tenant should have `is_system = true`

### Isolation Configuration

- **`isolation_strategy`** (VARCHAR/TEXT, NOT NULL)
  - How tenant data is isolated: `'schema'` (PostgreSQL) or `'database'` (SQLite)
  - Enforced via CHECK constraint

- **`schema_name`** (VARCHAR/TEXT, NULLABLE)
  - PostgreSQL schema name (only used when `isolation_strategy = 'schema'`)
  - Example: `"tenant_acme"`, `"docex_system"`

- **`database_path`** (VARCHAR/TEXT, NULLABLE)
  - SQLite database file path (only used when `isolation_strategy = 'database'`)
  - Example: `"storage/tenant_acme/docex.db"`

### Standard Audit Fields

- **`created_at`** (TIMESTAMP, NOT NULL)
  - When the tenant was provisioned
  - Automatically set to current timestamp on creation
  - Uses UTC timezone

- **`created_by`** (VARCHAR/TEXT, NOT NULL)
  - User ID of the user who provisioned the tenant
  - Must be provided during provisioning
  - Example: `"admin_user_123"`, `"system"` (for bootstrap tenant)

- **`last_updated_at`** (TIMESTAMP, NOT NULL)
  - When the tenant record was last modified
  - Automatically updated on any change
  - Uses UTC timezone

- **`last_updated_by`** (VARCHAR/TEXT, NULLABLE)
  - User ID of the user who last modified the tenant
  - NULL if tenant has never been updated
  - Example: `"admin_user_456"`

## Usage Examples

### Creating a Tenant (Python)

```python
from datetime import datetime, timezone
from docex.db.models import TenantRegistry
from docex.db.connection import Database

def provision_tenant(tenant_id: str, display_name: str, created_by: str):
    """Provision a new tenant"""
    db = Database()  # Bootstrap tenant database
    
    with db.session() as session:
        # Check if tenant already exists
        existing = session.query(TenantRegistry).filter_by(tenant_id=tenant_id).first()
        if existing:
            raise ValueError(f"Tenant '{tenant_id}' already exists")
        
        # Create tenant registry entry
        tenant = TenantRegistry(
            tenant_id=tenant_id,
            display_name=display_name,
            is_system=False,
            isolation_strategy='schema',  # or 'database' for SQLite
            schema_name=f"tenant_{tenant_id}",  # PostgreSQL
            database_path=f"storage/tenant_{tenant_id}/docex.db",  # SQLite
            created_at=datetime.now(timezone.utc),
            created_by=created_by,
            last_updated_at=datetime.now(timezone.utc),
            last_updated_by=None
        )
        
        session.add(tenant)
        session.commit()
        
        # Create isolation boundary (schema or database)
        # ... provisioning logic ...
        
        return tenant
```

### Updating a Tenant (Python)

```python
def update_tenant(tenant_id: str, display_name: str, updated_by: str):
    """Update tenant information"""
    db = Database()  # Bootstrap tenant database
    
    with db.session() as session:
        tenant = session.query(TenantRegistry).filter_by(tenant_id=tenant_id).first()
        if not tenant:
            raise ValueError(f"Tenant '{tenant_id}' not found")
        
        tenant.display_name = display_name
        tenant.last_updated_at = datetime.now(timezone.utc)
        tenant.last_updated_by = updated_by
        
        session.commit()
        return tenant
```

### Querying Tenants

```python
def list_all_tenants():
    """List all provisioned tenants"""
    db = Database()  # Bootstrap tenant database
    
    with db.session() as session:
        tenants = session.query(TenantRegistry).filter_by(is_system=False).all()
        return tenants

def get_system_tenant():
    """Get the bootstrap/system tenant"""
    db = Database()  # Bootstrap tenant database
    
    with db.session() as session:
        tenant = session.query(TenantRegistry).filter_by(is_system=True).first()
        return tenant
```

## Bootstrap Tenant Initialization

During `docex init`, the bootstrap tenant should be registered:

```python
def initialize_bootstrap_tenant(created_by: str = "system"):
    """Initialize bootstrap tenant during system setup"""
    db = Database()  # Default database (will become bootstrap tenant's)
    
    with db.session() as session:
        # Check if bootstrap tenant already exists
        existing = session.query(TenantRegistry).filter_by(
            tenant_id='_docex_system_'
        ).first()
        
        if existing:
            return existing  # Already initialized
        
        # Create bootstrap tenant registry entry
        bootstrap_tenant = TenantRegistry(
            tenant_id='_docex_system_',
            display_name='DocEX System',
            is_system=True,
            isolation_strategy='schema',  # or 'database'
            schema_name='docex_system',  # PostgreSQL
            database_path='storage/_docex_system_/docex.db',  # SQLite
            created_at=datetime.now(timezone.utc),
            created_by=created_by,
            last_updated_at=datetime.now(timezone.utc),
            last_updated_by=None
        )
        
        session.add(bootstrap_tenant)
        session.commit()
        
        return bootstrap_tenant
```

## Validation Rules

1. **Tenant ID Uniqueness:** `tenant_id` must be unique across all tenants
2. **System Tenant:** Only one tenant should have `is_system = true` (the bootstrap tenant)
3. **Isolation Strategy:** Must be either `'schema'` (PostgreSQL) or `'database'` (SQLite)
4. **Created By:** Must always be provided (cannot be NULL)
5. **Schema/Database Path:** Should match the isolation strategy:
   - If `isolation_strategy = 'schema'`: `schema_name` should be set
   - If `isolation_strategy = 'database'`: `database_path` should be set

## Migration Considerations

When migrating from v2.x to v3.0:

1. Create tenant registry table in bootstrap tenant schema
2. Detect existing tenant schemas/databases
3. Register each existing tenant in the registry
4. Set `created_by` to `"migration"` or the admin user who ran migration
5. Set `created_at` to current time (or attempt to infer from schema creation time)

