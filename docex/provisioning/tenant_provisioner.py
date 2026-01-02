"""
Tenant Provisioning for DocEX 3.0

Provides explicit tenant provisioning with deterministic schema/database creation.
"""

import logging
import re
from typing import Optional
from pathlib import Path
from datetime import datetime, timezone

from sqlalchemy import text, inspect
from sqlalchemy.exc import IntegrityError

from docex.db.connection import Database
from docex.db.tenant_registry_model import TenantRegistry
from docex.db.models import Base
from docex.db.tenant_database_manager import TenantDatabaseManager
from docex.config.docex_config import DocEXConfig

logger = logging.getLogger(__name__)

# System tenant pattern - reserved for system use
SYSTEM_TENANT_PATTERN = r'^_docex_.*_$'
SYSTEM_TENANT_ID = '_docex_system_'


class TenantExistsError(Exception):
    """Raised when attempting to create a tenant that already exists"""
    pass


class TenantProvisioningError(Exception):
    """Raised when tenant provisioning fails"""
    pass


class InvalidTenantIdError(Exception):
    """Raised when tenant ID is invalid or reserved"""
    pass


class TenantProvisioner:
    """
    Handles explicit tenant provisioning for DocEX 3.0.
    
    Tenants must be explicitly provisioned before they can be used.
    No lazy tenant creation is permitted.
    """
    
    def __init__(self, config: Optional[DocEXConfig] = None):
        """
        Initialize tenant provisioner.
        
        Args:
            config: Optional DocEXConfig instance. If None, uses default config.
        """
        self.config = config or DocEXConfig()
        self.db_config = self.config.get('database', {})
        self.db_type = self.db_config.get('type', 'sqlite')
        
        # Get bootstrap tenant database connection
        # Check if v3.0 multi-tenancy is enabled
        multi_tenancy_config = self.config.get('multi_tenancy', {})
        multi_tenancy_enabled = multi_tenancy_config.get('enabled', False)
        
        # Check if v2.x database-level multi-tenancy is enabled
        security_config = self.config.get('security', {})
        v2_multi_tenancy = security_config.get('multi_tenancy_model', 'row_level') == 'database_level'
        
        if multi_tenancy_enabled:
            # v3.0: Use bootstrap tenant for tenant registry
            bootstrap_tenant_id = multi_tenancy_config.get('bootstrap_tenant', {}).get('id', '_docex_system_')
            self.bootstrap_db = Database(config=self.config, tenant_id=bootstrap_tenant_id)
        elif v2_multi_tenancy:
            # v2.x: Use default tenant "docex_first_tenant" for provisioning operations
            # This tenant is automatically created/used in v2.x mode
            # TenantDatabaseManager will auto-create the tenant database/schema on first access
            self.bootstrap_db = Database(config=self.config, tenant_id='docex_first_tenant')
        else:
            # Single-tenant mode: use default database
            self.bootstrap_db = Database(config=self.config)
    
    @staticmethod
    def is_system_tenant(tenant_id: str) -> bool:
        """
        Check if tenant ID matches system tenant pattern.
        
        Args:
            tenant_id: Tenant identifier to check
            
        Returns:
            True if tenant ID matches system tenant pattern
        """
        return tenant_id == SYSTEM_TENANT_ID or bool(re.match(SYSTEM_TENANT_PATTERN, tenant_id))
    
    @staticmethod
    def validate_tenant_id(tenant_id: str) -> None:
        """
        Validate tenant ID format and check for reserved patterns.
        
        Args:
            tenant_id: Tenant identifier to validate
            
        Raises:
            InvalidTenantIdError: If tenant ID is invalid or reserved
        """
        if not tenant_id:
            raise InvalidTenantIdError("Tenant ID cannot be empty")
        
        if not isinstance(tenant_id, str):
            raise InvalidTenantIdError("Tenant ID must be a string")
        
        # Check for system tenant pattern
        if TenantProvisioner.is_system_tenant(tenant_id):
            raise InvalidTenantIdError(
                f"Tenant ID '{tenant_id}' matches system tenant pattern. "
                f"System tenant IDs (matching '{SYSTEM_TENANT_PATTERN}') are reserved."
            )
        
        # Basic validation: no whitespace, reasonable length
        if tenant_id.strip() != tenant_id:
            raise InvalidTenantIdError("Tenant ID cannot have leading or trailing whitespace")
        
        if len(tenant_id) > 255:
            raise InvalidTenantIdError("Tenant ID cannot exceed 255 characters")
        
        # Check for invalid characters (database identifiers)
        if re.search(r'[^\w\-]', tenant_id):
            raise InvalidTenantIdError(
                "Tenant ID can only contain alphanumeric characters, underscores, and hyphens"
            )
    
    def tenant_exists(self, tenant_id: str) -> bool:
        """
        Check if tenant already exists in registry.
        
        Args:
            tenant_id: Tenant identifier to check
            
        Returns:
            True if tenant exists, False otherwise
        """
        try:
            with self.bootstrap_db.session() as session:
                tenant = session.query(TenantRegistry).filter_by(tenant_id=tenant_id).first()
                return tenant is not None
        except Exception as e:
            logger.error(f"Error checking tenant existence: {e}")
            return False
    
    def create(
        self,
        tenant_id: str,
        display_name: str,
        created_by: str,
        isolation_strategy: Optional[str] = None
    ) -> TenantRegistry:
        """
        Provision a new tenant.
        
        This method:
        1. Validates tenant ID
        2. Checks for existing tenant
        3. Creates isolation boundary (schema or database)
        4. Initializes schema (creates all tables)
        5. Registers tenant in tenant registry
        
        Args:
            tenant_id: Unique identifier for the tenant
            display_name: Human-readable name for the tenant
            created_by: User ID who is creating the tenant
            isolation_strategy: Isolation strategy ('schema' for PostgreSQL, 'database' for SQLite).
                             If None, auto-detects based on database type.
        
        Returns:
            TenantRegistry instance for the newly created tenant
            
        Raises:
            InvalidTenantIdError: If tenant ID is invalid or reserved
            TenantExistsError: If tenant already exists
            TenantProvisioningError: If provisioning fails
        """
        # Validate tenant ID
        self.validate_tenant_id(tenant_id)
        
        # Determine isolation strategy
        if isolation_strategy is None:
            if self.db_type in ['postgresql', 'postgres']:
                isolation_strategy = 'schema'
            elif self.db_type == 'sqlite':
                isolation_strategy = 'database'
            else:
                raise TenantProvisioningError(f"Unsupported database type: {self.db_type}")
        
        if isolation_strategy not in ['schema', 'database']:
            raise TenantProvisioningError(
                f"Invalid isolation strategy: {isolation_strategy}. Must be 'schema' or 'database'"
            )
        
        # Check if tenant already exists
        if self.tenant_exists(tenant_id):
            raise TenantExistsError(f"Tenant '{tenant_id}' already exists")
        
        logger.info(f"Provisioning tenant: {tenant_id} (strategy: {isolation_strategy})")
        
        try:
            # Step 1: Create isolation boundary (schema or database)
            logger.info(f"Step 1/5: Creating isolation boundary for tenant '{tenant_id}'...")
            if isolation_strategy == 'schema':
                schema_name = self._create_postgres_schema(tenant_id)
                database_path = None
            else:  # database
                database_path = self._create_sqlite_database(tenant_id)
                schema_name = None
            logger.info(f"✅ Step 1 complete: Isolation boundary created")
            
            # Step 2: Initialize schema (create all tables)
            logger.info(f"Step 2/5: Initializing schema (creating tables) for tenant '{tenant_id}'...")
            self._initialize_tenant_schema(tenant_id, schema_name=schema_name, database_path=database_path)
            logger.info(f"✅ Step 2 complete: Schema initialized with all tables")
            
            # Step 3: Create performance indexes
            logger.info(f"Step 3/5: Creating performance indexes for tenant '{tenant_id}'...")
            self._create_performance_indexes(tenant_id, schema_name=schema_name)
            logger.info(f"✅ Step 3 complete: Performance indexes created")
            
            # Step 4: Validate schema (verify tables and indexes)
            logger.info(f"Step 4/5: Validating schema for tenant '{tenant_id}'...")
            self._validate_tenant_schema(tenant_id, schema_name=schema_name)
            logger.info(f"✅ Step 4 complete: Schema validation passed")
            
            # Step 5: Register tenant in tenant registry
            logger.info(f"Step 5/5: Registering tenant '{tenant_id}' in tenant registry...")
            tenant_registry = self._register_tenant(
                tenant_id=tenant_id,
                display_name=display_name,
                isolation_strategy=isolation_strategy,
                schema_name=schema_name,
                database_path=database_path,
                created_by=created_by
            )
            logger.info(f"✅ Step 5 complete: Tenant registered in registry")
            
            logger.info(f"✅ Successfully provisioned tenant: {tenant_id}")
            return tenant_registry
            
        except Exception as e:
            logger.error(f"Failed to provision tenant '{tenant_id}': {e}")
            # Attempt cleanup if partial provisioning occurred
            try:
                self._cleanup_partial_provisioning(tenant_id, isolation_strategy, schema_name, database_path)
            except Exception as cleanup_error:
                logger.warning(f"Failed to cleanup partial provisioning: {cleanup_error}")
            
            raise TenantProvisioningError(f"Failed to provision tenant '{tenant_id}': {str(e)}") from e
    
    def _create_postgres_schema(self, tenant_id: str) -> str:
        """
        Create PostgreSQL schema for tenant.
        
        Args:
            tenant_id: Tenant identifier
            
        Returns:
            Schema name that was created
        """
        # Resolve schema name using explicit resolver (all config from config.yaml)
        from docex.db.schema_resolver import SchemaResolver
        schema_resolver = SchemaResolver(self.config)
        schema_name = schema_resolver.resolve_schema_name(tenant_id)
        
        # Create schema using bootstrap database connection
        with self.bootstrap_db.get_engine().connect() as conn:
            # Use quoted identifier to handle special characters
            conn.execute(text(f'CREATE SCHEMA IF NOT EXISTS "{schema_name}"'))
            conn.commit()
        
        logger.info(f"Created PostgreSQL schema '{schema_name}' for tenant '{tenant_id}'")
        return schema_name
    
    def _create_sqlite_database(self, tenant_id: str) -> str:
        """
        Create SQLite database file for tenant.
        
        Args:
            tenant_id: Tenant identifier
            
        Returns:
            Database file path that was created
        """
        # Resolve database path using explicit resolver (all config from config.yaml)
        from docex.db.schema_resolver import SchemaResolver
        schema_resolver = SchemaResolver(self.config)
        database_path_str = schema_resolver.resolve_database_path(tenant_id)
        database_path = Path(database_path_str)
        
        # Ensure directory exists
        database_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Create database file if it doesn't exist
        if not database_path.exists():
            database_path.touch()
            database_path.chmod(0o644)
        
        logger.info(f"Created SQLite database '{database_path}' for tenant '{tenant_id}'")
        return str(database_path)
    
    def _initialize_tenant_schema(self, tenant_id: str, schema_name: Optional[str] = None, database_path: Optional[str] = None) -> None:
        """
        Initialize database schema for tenant (create all tables).
        
        Args:
            tenant_id: Tenant identifier
            schema_name: PostgreSQL schema name (if using schema-per-tenant)
            database_path: SQLite database path (if using database-per-tenant)
        """
        # Get tenant-specific database connection
        # IMPORTANT: During provisioning, we bypass validation because the tenant
        # hasn't been registered yet. We use _create_tenant_engine directly.
        tenant_db_manager = TenantDatabaseManager()
        # Use internal method to bypass validation during provisioning
        engine = tenant_db_manager._create_tenant_engine(tenant_id)
        
        # Cache the engine and create session factory for this tenant
        if tenant_id not in tenant_db_manager._tenant_engines:
            tenant_db_manager._tenant_engines[tenant_id] = engine
            from sqlalchemy.orm import sessionmaker
            tenant_db_manager._tenant_sessions[tenant_id] = sessionmaker(
                bind=engine,
                expire_on_commit=False,
                autocommit=False,
                autoflush=False
            )
        
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
        
        # Create all tables
        Base.metadata.create_all(engine)
        
        # Also create TransportBase tables if available
        try:
            from docex.transport.models import TransportBase
            TransportBase.metadata.create_all(engine)
        except ImportError:
            pass
        
            logger.info(f"Initialized schema for tenant '{tenant_id}'")
    
    def _create_performance_indexes(self, tenant_id: str, schema_name: Optional[str] = None) -> None:
        """
        Create performance indexes for tenant schema.
        
        Args:
            tenant_id: Tenant identifier
            schema_name: PostgreSQL schema name (if using schema-per-tenant)
        """
        try:
            from docex.db.tenant_database_manager import TenantDatabaseManager
            
            tenant_db_manager = TenantDatabaseManager()
            # During provisioning, use cached engine or create directly (bypasses validation)
            if tenant_id in tenant_db_manager._tenant_engines:
                engine = tenant_db_manager._tenant_engines[tenant_id]
            else:
                # Create engine directly during provisioning (bypasses validation)
                engine = tenant_db_manager._create_tenant_engine(tenant_id)
                tenant_db_manager._tenant_engines[tenant_id] = engine
            
            # Use the same index creation logic from TenantDatabaseManager
            # For SQLite, schema_name will be None, which is handled by the method
            tenant_db_manager._create_performance_indexes(engine, schema_name)
        except Exception as e:
            logger.warning(f"Failed to create performance indexes for tenant '{tenant_id}': {e}")
            # Don't fail provisioning if indexes fail - they're optional for functionality
            # But log as warning so it's visible
    
    def _validate_tenant_schema(self, tenant_id: str, schema_name: Optional[str] = None) -> None:
        """
        Validate that tenant schema is properly set up.
        
        Args:
            tenant_id: Tenant identifier
            schema_name: PostgreSQL schema name (if using schema-per-tenant)
            
        Raises:
            TenantProvisioningError: If validation fails
        """
        try:
            from docex.db.tenant_database_manager import TenantDatabaseManager
            from sqlalchemy import inspect
            
            tenant_db_manager = TenantDatabaseManager()
            # During provisioning, use cached engine or create directly (bypasses validation)
            if tenant_id in tenant_db_manager._tenant_engines:
                engine = tenant_db_manager._tenant_engines[tenant_id]
            else:
                # Create engine directly during provisioning (bypasses validation)
                engine = tenant_db_manager._create_tenant_engine(tenant_id)
                tenant_db_manager._tenant_engines[tenant_id] = engine
            
            inspector = inspect(engine)
            tables = inspector.get_table_names()
            
            # Required tables
            required_tables = [
                'docbasket', 'document', 'document_metadata',
                'file_history', 'operations', 'operation_dependencies',
                'doc_events', 'processors', 'processing_operations'
            ]
            
            missing_tables = [t for t in required_tables if t not in tables]
            if missing_tables:
                raise TenantProvisioningError(
                    f"Schema validation failed: Missing required tables: {missing_tables}"
                )
            
            logger.debug(f"Schema validation passed: All {len(required_tables)} required tables exist")
            
        except Exception as e:
            if isinstance(e, TenantProvisioningError):
                raise
            raise TenantProvisioningError(f"Schema validation failed: {str(e)}") from e
    
    def _register_tenant(
        self,
        tenant_id: str,
        display_name: str,
        isolation_strategy: str,
        schema_name: Optional[str],
        database_path: Optional[str],
        created_by: str
    ) -> TenantRegistry:
        """
        Register tenant in tenant registry.
        
        Args:
            tenant_id: Tenant identifier
            display_name: Display name
            isolation_strategy: Isolation strategy
            schema_name: PostgreSQL schema name
            database_path: SQLite database path
            created_by: User ID who created the tenant
            
        Returns:
            TenantRegistry instance
        """
        # Ensure TenantRegistry table schema is None (uses search_path)
        # This is important because the table schema might have been set during tenant schema creation
        from docex.db.tenant_registry_model import TenantRegistry
        if TenantRegistry.__table__.schema is not None:
            TenantRegistry.__table__.schema = None
        
        with self.bootstrap_db.session() as session:
            tenant = TenantRegistry(
                tenant_id=tenant_id,
                display_name=display_name,
                is_system=False,
                isolation_strategy=isolation_strategy,
                schema_name=schema_name,
                database_path=database_path,
                created_at=datetime.now(timezone.utc),
                created_by=created_by,
                last_updated_at=datetime.now(timezone.utc),
                last_updated_by=None
            )
            
            session.add(tenant)
            session.commit()
            session.refresh(tenant)
            
            return tenant
    
    def _cleanup_partial_provisioning(
        self,
        tenant_id: str,
        isolation_strategy: str,
        schema_name: Optional[str],
        database_path: Optional[str]
    ) -> None:
        """
        Cleanup partial provisioning if it failed.
        
        Args:
            tenant_id: Tenant identifier
            isolation_strategy: Isolation strategy used
            schema_name: PostgreSQL schema name (if created)
            database_path: SQLite database path (if created)
        """
        logger.warning(f"Cleaning up partial provisioning for tenant '{tenant_id}'")
        
        try:
            # Remove from registry if it was added
            with self.bootstrap_db.session() as session:
                tenant = session.query(TenantRegistry).filter_by(tenant_id=tenant_id).first()
                if tenant:
                    session.delete(tenant)
                    session.commit()
        except Exception as e:
            logger.warning(f"Failed to remove tenant from registry: {e}")
        
        # Note: We don't delete schemas/databases on failure to avoid data loss
        # Admin can manually clean up if needed

