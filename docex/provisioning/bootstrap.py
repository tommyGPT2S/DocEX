"""
Bootstrap Tenant Management for DocEX 3.0

Handles creation and management of the bootstrap/system tenant.
"""

import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from sqlalchemy import text, inspect
from sqlalchemy.exc import IntegrityError

from docex.db.connection import Database
from docex.db.tenant_registry_model import TenantRegistry
from docex.db.models import Base
from docex.config.docex_config import DocEXConfig

logger = logging.getLogger(__name__)

# Bootstrap tenant ID
BOOTSTRAP_TENANT_ID = '_docex_system_'


class BootstrapTenantManager:
    """
    Manages the bootstrap/system tenant for DocEX 3.0.
    
    The bootstrap tenant:
    - Owns system metadata (tenant registry, etc.)
    - Is created during system initialization
    - Must never be used for business operations
    """
    
    def __init__(self, config: Optional[DocEXConfig] = None):
        """
        Initialize bootstrap tenant manager.
        
        Args:
            config: Optional DocEXConfig instance. If None, uses default config.
        """
        self.config = config or DocEXConfig()
        self.db_config = self.config.get('database', {})
        self.db_type = self.db_config.get('type', 'sqlite')
        
        # Get database connection for bootstrap tenant operations
        # Check if v3.0 multi-tenancy is enabled
        multi_tenancy_config = self.config.get('multi_tenancy', {})
        multi_tenancy_enabled = multi_tenancy_config.get('enabled', False)
        
        # Check if v2.x database-level multi-tenancy is enabled
        security_config = self.config.get('security', {})
        v2_multi_tenancy = security_config.get('multi_tenancy_model', 'row_level') == 'database_level'
        
        if multi_tenancy_enabled:
            # v3.0: For bootstrap initialization, we need to create the database directly
            # because the tenant doesn't exist yet (chicken-and-egg problem)
            # We'll create the database connection manually during initialization
            # For now, use default connection to create tenant registry table
            # Then switch to bootstrap tenant's database after it's created
            self.db = Database.get_default_connection(config=self.config)
        elif v2_multi_tenancy:
            # For v2.x, use default tenant "docex_first_tenant" for bootstrap operations
            # This tenant is automatically created/used in v2.x mode
            self.db = Database(config=self.config, tenant_id='docex_first_tenant')
        else:
            # Single-tenant mode: use default database
            self.db = Database(config=self.config)
    
    def is_initialized(self) -> bool:
        """
        Check if bootstrap tenant has been initialized.
        
        Returns:
            True if bootstrap tenant exists in registry, False otherwise
        """
        try:
            # For v3.0 multi-tenancy, we need to check the bootstrap tenant's database/schema
            # not the default database
            multi_tenancy_config = self.config.get('multi_tenancy', {})
            multi_tenancy_enabled = multi_tenancy_config.get('enabled', False)
            
            if multi_tenancy_enabled:
                # Use bootstrap tenant's database connection
                bootstrap_tenant_id = multi_tenancy_config.get('bootstrap_tenant', {}).get('id', '_docex_system_')
                bootstrap_db = Database(config=self.config, tenant_id=bootstrap_tenant_id)
                with bootstrap_db.session() as session:
                    tenant = session.query(TenantRegistry).filter_by(
                        tenant_id=BOOTSTRAP_TENANT_ID
                    ).first()
                    return tenant is not None
            else:
                # For v2.x or single-tenant, use default database
                with self.db.session() as session:
                    tenant = session.query(TenantRegistry).filter_by(
                        tenant_id=BOOTSTRAP_TENANT_ID
                    ).first()
                    return tenant is not None
        except Exception as e:
            # If table doesn't exist yet or database doesn't exist, bootstrap is not initialized
            logger.debug(f"Error checking bootstrap tenant: {e}")
            return False
    
    def initialize(self, created_by: str = "system") -> TenantRegistry:
        """
        Initialize bootstrap tenant during system setup.
        
        This method:
        1. Creates tenant registry table (if it doesn't exist)
        2. Creates bootstrap tenant isolation boundary (schema or database)
        3. Initializes bootstrap tenant schema
        4. Registers bootstrap tenant in tenant registry
        
        Args:
            created_by: User ID who is initializing the system (default: "system")
            
        Returns:
            TenantRegistry instance for bootstrap tenant
            
        Raises:
            RuntimeError: If bootstrap tenant already exists or initialization fails
        """
        if self.is_initialized():
            logger.info("Bootstrap tenant already initialized")
            # Use bootstrap tenant's database connection for v3.0
            multi_tenancy_config = self.config.get('multi_tenancy', {})
            multi_tenancy_enabled = multi_tenancy_config.get('enabled', False)
            
            if multi_tenancy_enabled:
                bootstrap_tenant_id = multi_tenancy_config.get('bootstrap_tenant', {}).get('id', '_docex_system_')
                bootstrap_db = Database(config=self.config, tenant_id=bootstrap_tenant_id)
                with bootstrap_db.session() as session:
                    return session.query(TenantRegistry).filter_by(
                        tenant_id=BOOTSTRAP_TENANT_ID
                    ).first()
            else:
                with self.db.session() as session:
                    return session.query(TenantRegistry).filter_by(
                        tenant_id=BOOTSTRAP_TENANT_ID
                    ).first()
        
        logger.info("Initializing bootstrap tenant...")
        
        try:
            # First, ensure tenant registry table exists
            self._ensure_tenant_registry_table()
            
            # Determine isolation strategy
            if self.db_type in ['postgresql', 'postgres']:
                isolation_strategy = 'schema'
                schema_name = self._get_bootstrap_schema_name()
                database_path = None
            elif self.db_type == 'sqlite':
                isolation_strategy = 'database'
                database_path = self._get_bootstrap_database_path()
                schema_name = None
            else:
                raise RuntimeError(f"Unsupported database type: {self.db_type}")
            
            # Create isolation boundary
            if isolation_strategy == 'schema':
                self._create_bootstrap_schema(schema_name)
            else:
                self._create_bootstrap_database(database_path)
            
            # Switch to bootstrap tenant's database for v3.0 mode
            # After creating the database, we need to use it for the tenant registry
            multi_tenancy_config = self.config.get('multi_tenancy', {})
            multi_tenancy_enabled = multi_tenancy_config.get('enabled', False)
            if multi_tenancy_enabled:
                bootstrap_tenant_id = multi_tenancy_config.get('bootstrap_tenant', {}).get('id', '_docex_system_')
                # Now we can use the bootstrap tenant's database (it's been created)
                # Create engine directly without validation
                from docex.db.tenant_database_manager import TenantDatabaseManager
                tenant_manager = TenantDatabaseManager()
                # Get engine directly by calling internal method (bypasses validation)
                # Use the method that creates engine without validation
                if self.db_type == 'sqlite':
                    bootstrap_engine = tenant_manager._create_sqlite_engine(bootstrap_tenant_id, self.db_config)
                elif self.db_type in ['postgresql', 'postgres']:
                    bootstrap_engine = tenant_manager._create_postgres_engine(bootstrap_tenant_id, self.db_config)
                else:
                    raise RuntimeError(f"Unsupported database type: {self.db_type}")
                from sqlalchemy.orm import sessionmaker
                Session = sessionmaker(bind=bootstrap_engine)
                # Create a temporary Database-like object
                bootstrap_db = Database.__new__(Database)
                bootstrap_db.config = self.config
                bootstrap_db.tenant_id = bootstrap_tenant_id
                bootstrap_db.engine = bootstrap_engine
                bootstrap_db.Session = Session
                self.db = bootstrap_db
            
            # Initialize schema (create all tables including tenant_registry)
            self._initialize_bootstrap_schema(schema_name)
            
            # Register bootstrap tenant in tenant registry
            bootstrap_tenant = self._register_bootstrap_tenant(
                isolation_strategy=isolation_strategy,
                schema_name=schema_name,
                database_path=database_path,
                created_by=created_by
            )
            
            logger.info(f"Bootstrap tenant initialized: {BOOTSTRAP_TENANT_ID}")
            return bootstrap_tenant
            
        except Exception as e:
            logger.error(f"Failed to initialize bootstrap tenant: {e}")
            raise RuntimeError(f"Bootstrap tenant initialization failed: {str(e)}") from e
    
    def _ensure_tenant_registry_table(self) -> None:
        """Ensure tenant_registry table exists in default database."""
        try:
            # Create tenant_registry table if it doesn't exist
            Base.metadata.create_all(self.db.get_engine(), tables=[TenantRegistry.__table__])
            logger.debug("Tenant registry table ensured")
        except Exception as e:
            logger.error(f"Failed to create tenant registry table: {e}")
            raise
    
    def _get_bootstrap_schema_name(self) -> str:
        """Get PostgreSQL schema name for bootstrap tenant."""
        multi_tenancy_config = self.config.get('multi_tenancy', {})
        bootstrap_config = multi_tenancy_config.get('bootstrap_tenant', {})
        return bootstrap_config.get('schema', 'docex_system')
    
    def _get_bootstrap_database_path(self) -> str:
        """Get SQLite database path for bootstrap tenant."""
        multi_tenancy_config = self.config.get('multi_tenancy', {})
        bootstrap_config = multi_tenancy_config.get('bootstrap_tenant', {})
        database_path = bootstrap_config.get('database_path', 'storage/_docex_system_/docex.db')
        return str(Path(database_path))
    
    def _create_bootstrap_schema(self, schema_name: str) -> None:
        """Create PostgreSQL schema for bootstrap tenant."""
        with self.db.get_engine().connect() as conn:
            conn.execute(text(f'CREATE SCHEMA IF NOT EXISTS "{schema_name}"'))
            conn.commit()
        logger.info(f"Created bootstrap schema: {schema_name}")
    
    def _create_bootstrap_database(self, database_path: str) -> None:
        """Create SQLite database file for bootstrap tenant."""
        db_path = Path(database_path)
        db_path.parent.mkdir(parents=True, exist_ok=True)
        
        if not db_path.exists():
            db_path.touch()
            db_path.chmod(0o644)
        logger.info(f"Created bootstrap database: {database_path}")
    
    def _initialize_bootstrap_schema(self, schema_name: Optional[str] = None) -> None:
        """
        Initialize bootstrap tenant schema (create all tables).
        
        Args:
            schema_name: PostgreSQL schema name (if using schema-per-tenant)
        """
        engine = self.db.get_engine()
        
        # Set schema on tables if using PostgreSQL
        if schema_name:
            for table in Base.metadata.tables.values():
                table.schema = schema_name
            
            # Also set schema on TransportBase tables if available
            try:
                from docex.transport.models import TransportBase
                for table in TransportBase.metadata.tables.values():
                    table.schema = schema_name
            except ImportError:
                pass
        
        # Create all tables (including tenant_registry)
        Base.metadata.create_all(engine)
        
        # Also create TransportBase tables if available
        try:
            from docex.transport.models import TransportBase
            TransportBase.metadata.create_all(engine)
        except ImportError:
            pass
        
        logger.info("Initialized bootstrap tenant schema")
    
    def _register_bootstrap_tenant(
        self,
        isolation_strategy: str,
        schema_name: Optional[str],
        database_path: Optional[str],
        created_by: str
    ) -> TenantRegistry:
        """Register bootstrap tenant in tenant registry."""
        # Ensure TenantRegistry table schema is None (uses search_path)
        # This is important because the table schema might have been set during tenant schema creation
        if TenantRegistry.__table__.schema is not None:
            TenantRegistry.__table__.schema = None
        
        with self.db.session() as session:
            bootstrap_tenant = TenantRegistry(
                tenant_id=BOOTSTRAP_TENANT_ID,
                display_name='DocEX System',
                is_system=True,
                isolation_strategy=isolation_strategy,
                schema_name=schema_name,
                database_path=database_path,
                created_at=datetime.now(timezone.utc),
                created_by=created_by,
                last_updated_at=datetime.now(timezone.utc),
                last_updated_by=None
            )
            
            session.add(bootstrap_tenant)
            session.commit()
            session.refresh(bootstrap_tenant)
            
            logger.info(f"Registered bootstrap tenant: {BOOTSTRAP_TENANT_ID}")
            return bootstrap_tenant
    
    def get_bootstrap_tenant(self) -> Optional[TenantRegistry]:
        """
        Get bootstrap tenant from registry.
        
        Returns:
            TenantRegistry instance for bootstrap tenant, or None if not initialized
        """
        if not self.is_initialized():
            return None
        
        with self.db.session() as session:
            return session.query(TenantRegistry).filter_by(
                tenant_id=BOOTSTRAP_TENANT_ID
            ).first()

