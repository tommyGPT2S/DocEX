import logging
import os
from typing import Dict, Any, Optional, List
from pathlib import Path
import yaml
from docex.config.docex_config import DocEXConfig
from docex.db.connection import Database
from docex.docbasket import DocBasket
from docex.models.metadata_keys import MetadataKey
from docex.db.models import Base
from docex.transport.models import Base as TransportBase
from docex.transport.transport_result import TransportResult
from docex.context import UserContext
from sqlalchemy import inspect, text
from datetime import datetime, timezone

# Configure logging
logger = logging.getLogger(__name__)

class DocEX:
    """
    Main entry point for DocEX document management system
    
    This class manages document baskets and provides system-wide configuration.
    """
    
    _instance = None
    _config = None
    _default_config = None
    
    @classmethod
    def _load_default_config(cls) -> Dict[str, Any]:
        """Load default configuration from package"""
        if cls._default_config is None:
            config_path = Path(__file__).parent / 'config' / 'default_config.yaml'
            with open(config_path) as f:
                cls._default_config = yaml.safe_load(f)
        return cls._default_config
    
    @classmethod
    def get_defaults(cls) -> Dict[str, Any]:
        """Get default configuration values"""
        return cls._load_default_config()
    
    @classmethod
    def _safe_load_config(cls, config_path: Path) -> Optional[Dict[str, Any]]:
        """Safely load configuration from file
        
        Args:
            config_path: Path to configuration file
            
        Returns:
            Configuration dictionary or None if loading fails
        """
        try:
            with open(config_path) as f:
                config = yaml.safe_load(f)
                if config is None:
                    logger.error("Configuration file is empty")
                    return None
                return config
        except yaml.YAMLError as e:
            logger.error(f"Invalid YAML in configuration file: {str(e)}")
            return None
        except Exception as e:
            logger.error(f"Failed to load configuration file: {str(e)}")
            return None
    
    @classmethod
    def is_initialized(cls) -> bool:
        """Check if DocEX has been initialized
        
        Returns:
            True if DocEX has been initialized, False otherwise
        """
        if cls._config is not None:
            return True
            
        # Try to load configuration from file
        config_path = Path.home() / '.docex' / 'config.yaml'
        if not config_path.exists():
            logger.error(f"Configuration file not found at {config_path}")
            return False
            
        config = cls._safe_load_config(config_path)
        if config is None:
            return False
            
        try:
            cls._config = DocEXConfig()
            cls._config.config = config
            return True
        except Exception as e:
            logger.error(f"Failed to initialize DocEX configuration: {str(e)}")
            return False
    
    @classmethod
    def is_properly_setup(cls) -> bool:
        """
        Check if DocEX is properly set up and ready for use.
        
        This performs comprehensive checks:
        - Configuration file exists and is valid
        - Database is accessible
        - Required tables exist
        - Bootstrap tenant exists (if multi-tenancy enabled)
        
        Returns:
            True if DocEX is properly set up, False otherwise
        """
        errors = cls.get_setup_errors()
        return len(errors) == 0
    
    @classmethod
    def get_setup_errors(cls) -> List[str]:
        """
        Get detailed list of setup errors.
        
        Returns:
            List of error messages describing what is not properly set up.
            Empty list if everything is properly set up.
        """
        errors = []
        
        try:
            # Check 1: Configuration exists and is valid
            if not cls.is_initialized():
                config_path = Path.home() / '.docex' / 'config.yaml'
                errors.append(f"Configuration not initialized: config file not found at {config_path}")
                return errors  # Can't continue without config
            
            config = DocEXConfig()
            
            # Check 2: Database connectivity
            try:
                # For multi-tenancy, check bootstrap tenant's database
                multi_tenancy_config = config.get('multi_tenancy', {})
                multi_tenancy_enabled = multi_tenancy_config.get('enabled', False)
                
                if multi_tenancy_enabled:
                    # Use bootstrap tenant's database for multi-tenancy
                    # Use read_only=True to avoid side effects (schema/table creation)
                    bootstrap_tenant_id = multi_tenancy_config.get('bootstrap_tenant', {}).get('id', '_docex_system_')
                    db = Database(config=config, tenant_id=bootstrap_tenant_id, read_only=True)
                else:
                    # Use default database for single-tenant
                    # Use read_only=True to avoid side effects (table creation)
                    db = Database(config=config, read_only=True)
                
                engine = db.get_engine()
                # Test connection
                with engine.connect() as conn:
                    conn.execute(text("SELECT 1"))
            except Exception as e:
                errors.append(f"Database connectivity failed: {str(e)}")
                return errors  # Can't continue without database
            
            # Check 3: Required tables exist
            try:
                from sqlalchemy import inspect
                inspector = inspect(engine)
                tables = inspector.get_table_names()
                
                required_tables = [
                    'docbasket', 'document', 'document_metadata', 
                    'file_history', 'operations', 'operation_dependencies',
                    'doc_events', 'processors', 'processing_operations'
                ]
                
                missing_tables = [t for t in required_tables if t not in tables]
                if missing_tables:
                    errors.append(f"Missing required tables: {', '.join(missing_tables)}")
            except Exception as e:
                errors.append(f"Failed to check table existence: {str(e)}")
            
            # Check 4: Bootstrap tenant exists (if multi-tenancy enabled)
            if multi_tenancy_enabled:
                try:
                    from docex.provisioning.bootstrap import BootstrapTenantManager
                    bootstrap_manager = BootstrapTenantManager(config=config)
                    if not bootstrap_manager.is_initialized():
                        errors.append("Multi-tenancy enabled but bootstrap tenant not initialized. Run BootstrapTenantManager().initialize() to set up the system tenant.")
                except Exception as e:
                    errors.append(f"Bootstrap tenant check failed: {str(e)}")
            
            # All checks passed (no errors)
            return errors
            
        except Exception as e:
            errors.append(f"Setup validation failed with unexpected error: {str(e)}")
            return errors
    
    def __new__(cls, *args, **kwargs):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self, user_context: Optional[UserContext] = None):
        """
        Initialize DocEX instance
        
        Args:
            user_context: Optional user context for user-aware operations and auditing.
                         If multi-tenancy is enabled (v3.0), user_context with tenant_id
                         is REQUIRED. If database-level multi-tenancy is enabled (v2.x),
                         tenant_id from user_context is used for database routing.
        
        Raises:
            RuntimeError: If DocEX is not initialized
            ValueError: If multi-tenancy is enabled but user_context is missing or invalid
        """
        if not hasattr(self, 'initialized'):
            if not self.is_initialized():
                raise RuntimeError("DocEX not initialized. Call 'docex init' to setup first.")
            
            config = DocEXConfig()
            
            # Check for v3.0 multi-tenancy (new format)
            multi_tenancy_config = config.get('multi_tenancy', {})
            multi_tenancy_enabled = multi_tenancy_config.get('enabled', False)
            
            # Check for v2.x multi-tenancy (legacy format)
            security_config = config.get('security', {})
            multi_tenancy_model = security_config.get('multi_tenancy_model', 'row_level')
            legacy_database_level = multi_tenancy_model == 'database_level'
            
            # Initialize tenant_id (default to None for single-tenant)
            tenant_id = None
            
            # v3.0 multi-tenancy enforcement
            if multi_tenancy_enabled:
                if not user_context:
                    raise ValueError(
                        "UserContext is required when multi-tenancy is enabled. "
                        "Please provide a UserContext with tenant_id."
                    )
                
                if not user_context.tenant_id:
                    raise ValueError(
                        "tenant_id is required in UserContext when multi-tenancy is enabled. "
                        "Please provide a valid tenant_id."
                    )
                
                # Reject bootstrap tenant for business operations
                if user_context.tenant_id == '_docex_system_':
                    raise ValueError(
                        "System tenant '_docex_system_' cannot be used for business operations. "
                        "Use a provisioned business tenant instead."
                    )
                
                # Validate tenant exists in registry
                self._validate_tenant_exists(user_context.tenant_id)
                
                tenant_id = user_context.tenant_id
                logger.info(f"DocEX 3.0 multi-tenancy: using tenant {tenant_id}")
            
            # v2.x legacy database-level multi-tenancy
            elif legacy_database_level:
                tenant_id = None
                if user_context and user_context.tenant_id:
                    tenant_id = user_context.tenant_id
                    logger.info(f"Database-level multi-tenancy (v2.x): routing to tenant {tenant_id}")
            
            # Initialize database with tenant routing if applicable
            self.db = Database(tenant_id=tenant_id)
            self.user_context = user_context
            self.initialized = True
            if user_context:
                logger.info(f"DocEX initialized for user {user_context.user_id}")
        else:
            # Update user_context if provided (for singleton pattern)
            if user_context is not None:
                # Check if we need to switch tenant database
                config = DocEXConfig()
                
                # Check for v3.0 multi-tenancy
                multi_tenancy_config = config.get('multi_tenancy', {})
                v3_multi_tenancy_enabled = multi_tenancy_config.get('enabled', False)
                
                # Check for v2.x database-level multi-tenancy
                security_config = config.get('security', {})
                multi_tenancy_model = security_config.get('multi_tenancy_model', 'row_level')
                v2_database_level = multi_tenancy_model == 'database_level'
                
                # Determine if we need to switch tenant database
                new_tenant_id = None
                if v3_multi_tenancy_enabled:
                    # v3.0: tenant_id is required
                    if user_context.tenant_id:
                        new_tenant_id = user_context.tenant_id
                elif v2_database_level:
                    # v2.x: tenant_id is optional
                    if user_context.tenant_id:
                        new_tenant_id = user_context.tenant_id
                
                # Get current tenant_id from existing database
                current_tenant_id = getattr(self.db, 'tenant_id', None) if self.db else None
                
                # ENFORCEMENT: If tenant changed, require explicit reset
                if new_tenant_id and new_tenant_id != current_tenant_id and current_tenant_id is not None:
                    raise ValueError(
                        f"Cannot switch tenant from '{current_tenant_id}' to '{new_tenant_id}' without resetting. "
                        f"All database connections must be closed before switching tenants. "
                        f"Call DocEX.reset() or DocEX.close() first, then create a new DocEX instance with the new tenant_id."
                    )
                
                # If tenant changed (and current_tenant_id is None, meaning first initialization)
                if new_tenant_id and new_tenant_id != current_tenant_id:
                    logger.info(f"Switching tenant database from {current_tenant_id} to {new_tenant_id}")
                    # Close existing database connection before creating new one
                    if self.db:
                        self.db.close()
                    self.db = Database(tenant_id=new_tenant_id)
                    logger.debug(f"Updated DocEX.db.tenant_id to: {getattr(self.db, 'tenant_id', None)}")
                
                self.user_context = user_context
                logger.info(f"UserContext updated for user {user_context.user_id}")
    
    def _validate_tenant_exists(self, tenant_id: str) -> None:
        """
        Validate that tenant exists in tenant registry.
        
        Args:
            tenant_id: Tenant identifier to validate
            
        Raises:
            ValueError: If tenant does not exist in registry
        """
        try:
            from docex.db.tenant_registry_model import TenantRegistry
            from docex.db.connection import Database
            from docex.config.docex_config import DocEXConfig
            
            # Get database connection for tenant registry query
            # Use bootstrap tenant's database for v3.0, or default for v2.x
            config = DocEXConfig()
            multi_tenancy_config = config.get('multi_tenancy', {})
            multi_tenancy_enabled = multi_tenancy_config.get('enabled', False)
            
            if multi_tenancy_enabled:
                # v3.0: Use bootstrap tenant for tenant registry
                bootstrap_tenant_id = multi_tenancy_config.get('bootstrap_tenant', {}).get('id', '_docex_system_')
                registry_db = Database(config=config, tenant_id=bootstrap_tenant_id)
            else:
                # v2.x or single-tenant: Use default database
                # Check if v2.x database-level multi-tenancy is enabled
                security_config = config.get('security', {})
                v2_multi_tenancy = security_config.get('multi_tenancy_model', 'row_level') == 'database_level'
                if v2_multi_tenancy:
                    registry_db = Database(config=config, tenant_id='docex_first_tenant')
                else:
                    registry_db = Database(config=config)
            
            # For multi-tenancy enabled, ensure we use bootstrap connection with correct search_path
            if multi_tenancy_enabled:
                with registry_db.get_bootstrap_connection() as conn:
                    # Query tenant registry using raw SQL to ensure correct schema
                    result = conn.execute(
                        text("SELECT tenant_id FROM tenant_registry WHERE tenant_id = :tenant_id"),
                        {"tenant_id": tenant_id}
                    ).fetchone()
                    if not result:
                        raise ValueError(
                            f"Tenant '{tenant_id}' not found in tenant registry. "
                            f"Please provision the tenant first using 'docex tenant create'."
                        )
            else:
                with registry_db.session() as session:
                    tenant = session.query(TenantRegistry).filter_by(tenant_id=tenant_id).first()
                    if not tenant:
                        raise ValueError(
                            f"Tenant '{tenant_id}' not found in tenant registry. "
                            f"Please provision the tenant first using 'docex tenant create'."
                        )
        except ImportError:
            # Tenant registry not available (v2.x or not initialized)
            logger.warning("Tenant registry not available - skipping tenant validation")
        except Exception as e:
            # If validation fails for other reasons, log but don't fail
            logger.warning(f"Failed to validate tenant existence: {e}")
    
    @classmethod
    def setup(cls, **config) -> None:
        """
        Set up DocEX configuration
        
        This should be called before creating a DocEX instance.
        
        Args:
            **config: Configuration options
                - config_file: Path to configuration file
                - database: Database configuration
                    - type: 'postgres' or 'sqlite'
                    - postgres: PostgreSQL configuration
                        - user: Database user
                        - password: Database password
                        - host: Database host
                        - port: Database port
                        - database: Database name
                    - sqlite: SQLite configuration
                        - path: Path to SQLite database file
                - logging: Logging configuration
                    - level: Logging level
                    - file: Path to log file
                    
        Raises:
            RuntimeError: If storage directory creation fails
            RuntimeError: If database initialization fails
            RuntimeError: If configuration setup fails
        """
        try:
            # Load defaults
            defaults = cls._load_default_config()
            
            # Ensure Default Configuration Exists
            if not Path(__file__).parent / 'config' / 'default_config.yaml':
                logger.error("Default configuration file not found at {config_path}")
                raise RuntimeError("Default configuration file not found.")
            
            # Validate User Configuration
            for key, value in config.items():
                if key not in defaults:
                    logger.warning(f"Unexpected configuration key: {key}")
                elif isinstance(value, dict) and key in defaults:
                    # Special handling for storage - allow S3 parameters in both nested and flattened format
                    if key == 'storage':
                        # Check if this is S3 storage configuration
                        if value.get('type') == 's3':
                            # For S3, allow common parameters whether nested or flattened
                            allowed_s3_keys = {'type', 'bucket', 'region', 'prefix', 'access_key', 'secret_key',
                                             'session_token', 'max_retries', 'retry_delay', 'connect_timeout',
                                             'read_timeout', 'application_name', 's3'}
                            for subkey in value:
                                if subkey not in allowed_s3_keys:
                                    logger.warning(f"Unexpected subkey in {key}: {subkey}")
                            continue
                        elif 's3' in value:
                            # Nested S3 config - allow any S3 parameters
                            continue
                    # For other nested configs, check subkeys
                    for subkey in value:
                        if subkey not in defaults[key]:
                            logger.warning(f"Unexpected subkey in {key}: {subkey}")
            
            # Merge user config with defaults
            merged_config = defaults.copy()
            for key, value in config.items():
                if isinstance(value, dict) and key in merged_config:
                    merged_config[key].update(value)
                else:
                    merged_config[key] = value
            
            # Ensure storage directory exists
            if 'storage' in merged_config and 'filesystem' in merged_config['storage']:
                try:
                    storage_path = Path(merged_config['storage']['filesystem']['path'])
                    storage_path.mkdir(parents=True, exist_ok=True)
                    
                    # Verify write permissions
                    test_file = storage_path / '.test_write'
                    try:
                        test_file.touch()
                        test_file.unlink()
                    except (PermissionError, OSError) as e:
                        raise RuntimeError(f"Storage directory {storage_path} is not writable: {str(e)}")
                except Exception as e:
                    raise RuntimeError(f"Failed to create storage directory: {str(e)}")
            
            # Initialize configuration
            try:
                cls._config = DocEXConfig()
                cls._config.setup(**merged_config)
            except Exception as e:
                raise RuntimeError(f"Failed to initialize configuration: {str(e)}")
            
            # Initialize database and create tables
            # Skip table creation for database-level multi-tenancy (tables created per tenant)
            try:
                security_config = merged_config.get('security', {})
                multi_tenancy_model = security_config.get('multi_tenancy_model', 'row_level')
                
                if multi_tenancy_model == 'database_level':
                    logger.info("Database-level multi-tenancy enabled - tables will be created per tenant schema")
                    # Don't create tables here - they'll be created in tenant schemas on first access
                    return True
                else:
                    # Ensure all models are imported
                    import docex.db.models
                    import docex.transport.models
                    db = Database()
                    
                    # Drop all tables first (only if we have permission)
                    try:
                        Base.metadata.drop_all(db.get_engine())
                        TransportBase.metadata.drop_all(db.get_engine())
                        logger.info("Dropped existing database tables")
                    except Exception as drop_error:
                        logger.warning(f"Could not drop existing tables (this is OK if tables don't exist or insufficient permissions): {drop_error}")
                        # Continue with table creation - create_tables will handle "IF NOT EXISTS" logic
                    
                    # Create tables in order
                    logger.info("Creating database tables...")
                    
                    # Create tables in dependency order
                    tables_to_create = [
                        'docbasket',
                        'document',
                        'document_metadata',
                        'file_history',
                        'operations',
                        'operation_dependencies',
                        'doc_events',
                        'processors',
                        'processing_operations',
                        'transport_routes',
                        'route_operations'
                    ]
                    
                    for table_name in tables_to_create:
                        try:
                            if table_name in Base.metadata.tables:
                                Base.metadata.tables[table_name].create(db.get_engine())
                            elif table_name in TransportBase.metadata.tables:
                                TransportBase.metadata.tables[table_name].create(db.get_engine())
                            logger.info(f"Created table: {table_name}")
                        except Exception as e:
                            logger.error(f"Failed to create table {table_name}: {str(e)}")
                            raise
                    
                    # Verify table creation
                    inspector = inspect(db.get_engine())
                    tables = inspector.get_table_names()
                    logger.info(f"Created tables: {', '.join(tables)}")
                    
                    missing_tables = [table for table in tables_to_create if table not in tables]
                    if missing_tables:
                        raise RuntimeError(f"Failed to create required tables: {', '.join(missing_tables)}")
                    
                    logger.info("Database tables initialized successfully")
            except Exception as e:
                logger.error(f"Failed to initialize database: {str(e)}")
                raise RuntimeError(f"Failed to initialize database: {str(e)}")
                
        except Exception as e:
            logger.error(f"DocEX initialization failed: {str(e)}")
            raise
    
    @classmethod
    def get_config(cls) -> Dict[str, Any]:
        """Get current configuration"""
        if cls._config is None:
            raise RuntimeError("DocEX not initialized. Call setup() first.")
        return cls._config.get_all()
    
    @classmethod
    def get_metadata_keys(cls) -> Dict[str, str]:
        """Get available metadata keys"""
        return {
            key.name: key.value 
            for key in MetadataKey
        }
    
    @classmethod
    def is_valid_metadata_key(cls, key: str) -> bool:
        """Check if a metadata key is valid"""
        return key in cls.get_metadata_keys()
    
    def create_basket(self, name: str, description: str = None, storage_config: Dict[str, Any] = None) -> DocBasket:
        """
        Create a new document basket
        
        Args:
            name: Basket name
            description: Optional basket description
            storage_config: Optional storage configuration. If not provided, uses default storage config.
            
        Returns:
            Created basket
        """
        if storage_config is None:
            storage_config = self._config.get('storage', {})
            
        # Pass tenant-aware database to create operation
        basket = DocBasket.create(name, description, storage_config, db=self.db)
        
        if self.user_context:
            # Log creation with user context for auditing
            logger.info(f"Basket {name} created by user {self.user_context.user_id}")
            
        return basket
    
    def get_basket(self, basket_id: Optional[str] = None, basket_name: Optional[str] = None) -> Optional[DocBasket]:
        """
        Get a document basket by ID (preferred) or name (fallback).
        
        Performance:
        - basket_id: O(1) primary key lookup (fastest)
        - basket_name: O(log n) unique index lookup (fast, but slower than ID)
        
        Args:
            basket_id: Basket ID (preferred for performance)
            basket_name: Basket name (fallback if ID not provided)
            
        Returns:
            Basket if found, None otherwise
            
        Raises:
            ValueError: If neither basket_id nor basket_name is provided
        """
        if not basket_id and not basket_name:
            raise ValueError("Either basket_id or basket_name must be provided")
        
        # Prefer basket_id for performance (primary key lookup)
        if basket_id:
            basket = DocBasket.get(basket_id, db=self.db)
            if basket and self.user_context:
                logger.info(f"Basket {basket_id} accessed by user {self.user_context.user_id}")
            return basket
        else:
            # Fallback to name lookup (unique index lookup)
            basket = DocBasket.find_by_name(basket_name, db=self.db)
            if basket and self.user_context:
                logger.info(f"Basket {basket_name} (ID: {basket.id}) accessed by user {self.user_context.user_id}")
            return basket
    
    def close(self) -> None:
        """
        Close all database connections and reset DocEX instance.
        
        This method should be called before switching to a different tenant
        to ensure all database connections are properly closed and re-initialized.
        
        After calling close(), you must create a new DocEX instance with the new tenant_id.
        
        Example:
            # Close current tenant connection
            docex.close()
            
            # Create new instance with different tenant
            new_docex = DocEX(user_context=UserContext(user_id='u1', tenant_id='contoso'))
        """
        if hasattr(self, 'db') and self.db:
            self.db.close()
            # Also close tenant manager connections if applicable
            if hasattr(self.db, 'tenant_manager'):
                from docex.db.tenant_database_manager import TenantDatabaseManager
                tenant_manager = TenantDatabaseManager()
                current_tenant_id = getattr(self.db, 'tenant_id', None)
                if current_tenant_id:
                    tenant_manager.close_tenant_connection(current_tenant_id)
            self.db = None
        
        # Reset user context
        self.user_context = None
        logger.info("DocEX connections closed. Create a new DocEX instance to continue.")
    
    def reset(self) -> None:
        """
        Reset DocEX instance (alias for close()).
        
        This method closes all database connections and resets the instance,
        allowing you to switch to a different tenant.
        
        See close() for details.
        """
        self.close()
    
    def list_baskets(
        self,
        status: Optional[str] = None,
        limit: Optional[int] = None,
        offset: Optional[int] = None,
        order_by: str = 'created_at',
        order_desc: bool = True
    ) -> List[DocBasket]:
        """
        List document baskets with optional filtering, pagination, and sorting.
        Optimized with proper indexes.
        
        **Note:** For better performance when you only need basic basket information,
        consider using `list_baskets_with_metadata()` which returns lightweight dictionaries
        instead of full DocBasket objects.
        
        Args:
            status: Optional filter by basket status (e.g., 'active', 'inactive')
            limit: Maximum number of results to return (for pagination)
            offset: Number of results to skip (for pagination)
            order_by: Field to sort by ('created_at', 'name', 'updated_at')
            order_desc: If True, sort in descending order (default: True)
            
        Returns:
            List of document baskets (full DocBasket objects)
            
        Example:
            >>> # List active baskets, newest first
            >>> baskets = docex.list_baskets(status='active', limit=10)
            
            >>> # List all baskets sorted by name
            >>> baskets = docex.list_baskets(order_by='name', order_desc=False)
        """
        from docex.db.models import DocBasket as DocBasketModel
        from sqlalchemy import select
        import json
        
        with self.db.session() as session:
            query = select(DocBasketModel)
            
            # Add status filter (uses idx_docbasket_status index)
            if status:
                query = query.where(DocBasketModel.status == status)
            
            # Add sorting (uses idx_docbasket_created_at index for created_at)
            if order_by == 'created_at':
                query = query.order_by(
                    DocBasketModel.created_at.desc() if order_desc 
                    else DocBasketModel.created_at.asc()
                )
            elif order_by == 'name':
                query = query.order_by(
                    DocBasketModel.name.asc() if not order_desc 
                    else DocBasketModel.name.desc()
                )
            elif order_by == 'updated_at':
                query = query.order_by(
                    DocBasketModel.updated_at.desc() if order_desc 
                    else DocBasketModel.updated_at.asc()
                )
            else:
                # Default to created_at descending
                query = query.order_by(DocBasketModel.created_at.desc())
            
            # Add pagination
            if limit is not None:
                query = query.limit(limit)
            if offset is not None:
                query = query.offset(offset)
            
            # Execute query
            basket_models = session.execute(query).scalars().all()
            
            # Convert to DocBasket instances
            baskets = []
            for basket_model in basket_models:
                storage_config = json.loads(basket_model.storage_config) if isinstance(basket_model.storage_config, str) else basket_model.storage_config
                
                basket = DocBasket(
                    id=basket_model.id,
                    name=basket_model.name,
                    description=basket_model.description,
                    storage_config=storage_config,
                    created_at=basket_model.created_at,
                    updated_at=basket_model.updated_at,
                    model=basket_model,
                    db=self.db
                )
                baskets.append(basket)
            
            return baskets
    
    def list_baskets_with_metadata(
        self,
        columns: Optional[List[str]] = None,
        filters: Optional[Dict[str, Any]] = None,
        limit: Optional[int] = None,
        offset: Optional[int] = None,
        order_by: Optional[str] = None,
        order_desc: bool = False
    ) -> List[Dict[str, Any]]:
        """
        Efficiently list baskets with selected metadata columns.
        
        This method returns lightweight dictionaries instead of full DocBasket instances,
        avoiding object instantiation overhead and providing better performance for
        listing operations where you don't need full basket functionality.
        
        **Performance Benefits:**
        - No DocBasket object instantiation (saves memory and CPU)
        - No path_helper, document_manager, or storage_service initialization
        - Direct column projection from database (index-only scans possible)
        - Faster for large result sets
        
        Args:
            columns: List of column names to include in results.
                    Default: ['id', 'name', 'status', 'created_at', 'updated_at']
                    Available: 'id', 'name', 'description', 'status', 'created_at', 'updated_at', 'document_count'
                    Note: 'document_count' requires a JOIN query and may be slower for large datasets
            filters: Optional dictionary of filters (e.g., {'status': 'active'})
            limit: Maximum number of results to return (for pagination)
            offset: Number of results to skip (for pagination)
            order_by: Field to sort by ('created_at', 'name', 'updated_at', 'status', 'document_count')
            order_desc: If True, sort in descending order
            
        Returns:
            List of dictionaries containing selected basket fields
            
        Example:
            >>> # Get lightweight basket list with basic info
            >>> baskets = docex.list_baskets_with_metadata(
            ...     columns=['id', 'name', 'status', 'created_at'],
            ...     filters={'status': 'active'},
            ...     limit=100
            ... )
            >>> # Returns:
            >>> # [
            >>> #     {'id': 'bas_123', 'name': 'invoice_raw', 'status': 'active', 'created_at': '2024-01-01T00:00:00'},
            >>> #     ...
            >>> # ]
            
            >>> # Get baskets with document count
            >>> baskets = docex.list_baskets_with_metadata(
            ...     columns=['id', 'name', 'document_count'],
            ...     order_by='document_count',
            ...     order_desc=True
            ... )
            >>> # Returns:
            >>> # [
            >>> #     {'id': 'bas_123', 'name': 'invoice_raw', 'document_count': 42},
            >>> #     ...
            >>> # ]
            
            >>> # Get basket IDs and names only (fastest)
            >>> baskets = docex.list_baskets_with_metadata(
            ...     columns=['id', 'name'],
            ...     order_by='name'
            ... )
        """
        from docex.db.models import DocBasket as DocBasketModel, Document as DocumentModel
        from sqlalchemy import select, func, outerjoin
        
        # Default columns if not specified
        if columns is None:
            columns = ['id', 'name', 'status', 'created_at', 'updated_at']
        
        # Check if document_count is requested
        include_document_count = 'document_count' in columns
        
        # Map column names to model attributes
        column_map = {
            'id': DocBasketModel.id,
            'name': DocBasketModel.name,
            'description': DocBasketModel.description,
            'status': DocBasketModel.status,
            'created_at': DocBasketModel.created_at,
            'updated_at': DocBasketModel.updated_at,
        }
        
        # Build select statement with only requested columns
        selected_columns = []
        for col in columns:
            if col in column_map:
                selected_columns.append(column_map[col])
            elif col == 'document_count':
                # document_count will be added via subquery/join
                pass
            else:
                logger.warning(f"Unknown column '{col}' requested for basket listing, skipping")
        
        if not selected_columns and not include_document_count:
            raise ValueError("No valid columns specified for basket listing")
        
        with self.db.session() as session:
            # If document_count is requested, use LEFT JOIN with COUNT
            if include_document_count:
                # Create subquery for document counts
                doc_count_subquery = (
                    select(
                        DocumentModel.basket_id,
                        func.count(DocumentModel.id).label('document_count')
                    )
                    .group_by(DocumentModel.basket_id)
                    .subquery()
                )
                
                # Build query with LEFT JOIN to get document counts
                query = select(
                    *selected_columns,
                    func.coalesce(doc_count_subquery.c.document_count, 0).label('document_count')
                ).outerjoin(
                    doc_count_subquery,
                    DocBasketModel.id == doc_count_subquery.c.basket_id
                )
            else:
                # Simple query without document count
                query = select(*selected_columns)
            
            # Add filters
            if filters:
                for key, value in filters.items():
                    if key in column_map:
                        query = query.where(column_map[key] == value)
                    else:
                        logger.warning(f"Unknown filter key '{key}' for basket listing, skipping")
            
            # Add sorting
            if order_by:
                if order_by == 'document_count':
                    if include_document_count:
                        # Sort by document count (doc_count_subquery is defined above)
                        if order_desc:
                            query = query.order_by(func.coalesce(doc_count_subquery.c.document_count, 0).desc())
                        else:
                            query = query.order_by(func.coalesce(doc_count_subquery.c.document_count, 0).asc())
                    else:
                        logger.warning("Cannot sort by 'document_count' - column not requested. Add 'document_count' to columns list.")
                        query = query.order_by(DocBasketModel.created_at.desc())
                elif order_by in column_map:
                    order_field = column_map[order_by]
                    if order_desc:
                        query = query.order_by(order_field.desc())
                    else:
                        query = query.order_by(order_field.asc())
                else:
                    logger.warning(f"Invalid order_by field: {order_by}, using default")
                    query = query.order_by(DocBasketModel.created_at.desc())
            else:
                # Default sorting by creation date (newest first)
                query = query.order_by(DocBasketModel.created_at.desc())
            
            # Add pagination
            if limit is not None:
                query = query.limit(limit)
            if offset is not None:
                query = query.offset(offset)
            
            # Execute query and convert to dictionaries
            results = session.execute(query).all()
            
            # Convert to list of dictionaries
            baskets = []
            for row in results:
                basket_dict = {}
                row_index = 0
                for col in columns:
                    if col in column_map:
                        value = row[row_index]
                        # Convert datetime to ISO format string for JSON serialization
                        if hasattr(value, 'isoformat'):
                            value = value.isoformat()
                        basket_dict[col] = value
                        row_index += 1
                    elif col == 'document_count':
                        # document_count is the last column in the row
                        value = row[-1] if include_document_count else 0
                        basket_dict[col] = int(value) if value is not None else 0
                baskets.append(basket_dict)
            
            logger.debug(f"Retrieved {len(baskets)} baskets with metadata (columns: {columns})")
            return baskets
    
    @classmethod
    def setup_database(cls, db_type: str, is_default_db: bool = False, **config) -> None:
        """
        Set up additional database configuration
        
        Args:
            db_type: Database type ('sqlite' or 'postgres')
            is_default_db: If True, sets this database as the default for new connections
            **config: Database configuration options
                For SQLite:
                    - path: Path to SQLite database file
                For PostgreSQL:
                    - host: Database host
                    - port: Database port
                    - database: Database name
                    - user: Database user
                    - password: Database password
        """
        if cls._config is None:
            raise RuntimeError("DocEX not initialized. Call setup() first.")
            
        if db_type not in ['sqlite', 'postgres']:
            raise ValueError(f"Invalid database type: {db_type}")
            
        # Update database configuration
        db_config = cls._config.get('database', {})
        if is_default_db:
            db_config['type'] = db_type
        if db_type == 'sqlite':
            db_config['sqlite'] = config
        else:
            db_config['postgres'] = config
            
        # Update configuration
        cls._config.update({'database': db_config})
        
        # Reinitialize database connection if this is the default database
        if is_default_db:
            cls._db = Database() 
    
    def get_available_transport_types(self) -> List[str]:
        """Get list of available transport types
        
        Returns:
            List of available transport type names
        """
        from docex.transport.transporter_factory import TransporterFactory
        return list(TransporterFactory._transporters.keys())
    
    def create_route(
        self,
        name: str,
        transport_type: str,
        config: Dict[str, Any],
        purpose: str = "distribution",
        can_upload: bool = True,
        can_download: bool = True,
        can_list: bool = True,
        can_delete: bool = False,
        enabled: bool = True,
        other_party: Optional[Dict[str, str]] = None
    ) -> 'Route':
        """Create a new transport route
        
        Args:
            name: Route name
            transport_type: Type of transport (e.g., 'local', 'sftp')
            config: Transport-specific configuration
            purpose: Route purpose (default: 'distribution')
            can_upload: Whether route allows uploads (default: True)
            can_download: Whether route allows downloads (default: True)
            can_list: Whether route allows listing files (default: True)
            can_delete: Whether route allows file deletion (default: False)
            enabled: Whether route is enabled (default: True)
            other_party: Optional other party information (id, name, type)
            
        Returns:
            Created route instance
        """
        from docex.transport.config import (
            RouteConfig, OtherParty, TransportType,
            LocalTransportConfig, SFTPTransportConfig, HTTPTransportConfig
        )
        from docex.transport.transporter_factory import TransporterFactory
        from docex.transport.models import Route as RouteModel
        from docex.db.connection import Database
        from uuid import uuid4
        
        # Create transport config based on type
        transport_type_enum = TransportType(transport_type)
        if transport_type_enum == TransportType.LOCAL:
            transport_config = LocalTransportConfig(
                type=transport_type_enum,
                name=f"{name}_transport",
                base_path=config.get("base_path"),
                create_dirs=config.get("create_dirs", True)
            )
        else:
            transport_config = {
                "type": transport_type,
                "name": f"{name}_transport",
                **config
            }
        
        # Create other party if provided
        other_party_obj = None
        if other_party:
            other_party_obj = OtherParty(
                id=other_party.get("id"),
                name=other_party.get("name"),
                type=other_party.get("type")
            )
        
        # Create route config
        route_config = RouteConfig(
            name=name,
            purpose=purpose,
            protocol=transport_type_enum,
            config=transport_config,
            can_upload=can_upload,
            can_download=can_download,
            can_list=can_list,
            can_delete=can_delete,
            enabled=enabled,
            other_party=other_party_obj
        )
        
        # Create route model
        # Convert TransportType enum to string value for storage
        protocol_value = transport_type_enum.value if hasattr(transport_type_enum, 'value') else str(transport_type_enum)
        route_model = RouteModel(
            id=str(uuid4()),
            name=name,
            purpose=purpose,
            protocol=protocol_value,
            config=transport_config.model_dump() if hasattr(transport_config, 'model_dump') else transport_config,
            can_upload=can_upload,
            can_download=can_download,
            can_list=can_list,
            can_delete=can_delete,
            enabled=enabled,
            other_party_id=other_party.get("id") if other_party else None,
            other_party_name=other_party.get("name") if other_party else None,
            other_party_type=other_party.get("type") if other_party else None,
            route_metadata={},
            tags=[]
        )
        
        # Save route to database using tenant-aware database
        with self.db.transaction() as session:
            session.add(route_model)
            session.commit()
            session.refresh(route_model)
        
        # Create and return route instance
        route = TransporterFactory.create_route(route_config)
        # Set route_id to match the database model ID (critical for foreign key relationships)
        route.route_id = route_model.id
        # Pass tenant-aware database to route for multi-tenancy support
        route.db = self.db
        return route
    
    def get_route(self, name: str) -> Optional['Route']:
        """Get a route by name
        
        Args:
            name: Route name
            
        Returns:
            Route instance or None if not found
        """
        from docex.transport.models import Route as RouteModel
        from docex.transport.route import Route
        
        # Use tenant-aware database from DocEX instance
        with self.db.session() as session:
            route_model = session.query(RouteModel).filter_by(name=name).first()
            if not route_model:
                return None
            route = Route.from_model(route_model)
            route.route_id = route_model.id  # Ensure we use the database ID
            # Pass tenant-aware database to route for multi-tenancy support
            route.db = self.db
            return route
    
    def list_routes(
        self,
        purpose: Optional[str] = None,
        transport_type: Optional[str] = None,
        enabled: Optional[bool] = None
    ) -> List['Route']:
        """List routes with optional filters
        
        Args:
            purpose: Filter by route purpose
            transport_type: Filter by transport type
            enabled: Filter by enabled state
            
        Returns:
            List of matching routes
        """
        from docex.transport.models import Route
        
        # Use tenant-aware database from DocEX instance
        from docex.transport.route import Route as RouteInstance
        
        with self.db.session() as session:
            query = session.query(Route)
            
            if purpose:
                query = query.filter_by(purpose=purpose)
            if transport_type:
                query = query.filter_by(protocol=transport_type)
            if enabled is not None:
                query = query.filter_by(enabled=enabled)
            
            # Convert models to Route instances and set tenant-aware database
            route_models = query.all()
            routes = []
            for route_model in route_models:
                route = RouteInstance.from_model(route_model)
                route.route_id = route_model.id
                # Pass tenant-aware database to route for multi-tenancy support
                route.db = self.db
                routes.append(route)
            
            return routes
    
    def delete_route(self, name: str) -> bool:
        """Delete a route by name
        
        Args:
            name: Route name
            
        Returns:
            True if route was deleted, False if not found
        """
        from docex.transport.models import Route
        
        # Use tenant-aware database from DocEX instance
        with self.db.transaction() as session:
            route = session.query(Route).filter_by(name=name).first()
            if route:
                session.delete(route)
                return True
            return False
    
    def send_document(
        self,
        document_id: str,
        route_name: str,
        destination: str,
        basket_id: Optional[str] = None,
        basket_name: Optional[str] = None
    ) -> TransportResult:
        """
        Send a document using a transport route
        
        Args:
            basket_id: Basket ID containing the document (preferred for performance)
            basket_name: Basket name (fallback if basket_id not provided)
            document_id: Document ID to send
            route_name: Name of the route to use
            destination: Destination path/name
            
        Returns:
            TransportResult indicating success/failure
        """
        # Get basket (supports both basket_id and basket_name)
        basket = self.get_basket(basket_id=basket_id, basket_name=basket_name)
        if not basket:
            basket_identifier = basket_id or basket_name or "unknown"
            return TransportResult(
                success=False,
                message=f"Basket {basket_identifier} not found"
            )
        
        # Get document
        document = basket.get_document(document_id)
        if not document:
            return TransportResult(
                success=False,
                message=f"Document {document_id} not found"
            )
        
        # Get route
        route = self.get_route(route_name)
        if not route:
            return TransportResult(
                success=False,
                message=f"Route {route_name} not found"
            )
        
        # Check if route is enabled and can upload
        if not route.enabled:
            return TransportResult(
                success=False,
                message=f"Route {route_name} is disabled"
            )
        if not route.can_upload:
            return TransportResult(
                success=False,
                message=f"Route {route_name} does not allow uploads"
            )
        
        # Get document content
        content = document.get_content()
        
        # Send document
        result = route.upload(content, destination)
        
        # Update document status if sent successfully
        if result.success:
            # Use tenant-aware database from DocEX instance
            with self.db.transaction() as session:
                document.model.status = "SENT"
                session.commit()
        
        return result 

    def basket(self, basket_name: str, description: Optional[str] = None, storage_config: Optional[Dict[str, Any]] = None) -> DocBasket:
        """
        Get or create a document basket by name.
        If the basket exists, return it. Otherwise, create and return a new one.
        Args:
            basket_name: Name of the basket
            description: Optional description
            storage_config: Optional storage configuration
        Returns:
            DocBasket instance
        """
        # Pass tenant-aware database to find_by_name operation
        basket = DocBasket.find_by_name(basket_name, db=self.db)
        if basket:
            return basket
        return self.create_basket(basket_name, description, storage_config)