import os
import logging
from contextlib import contextmanager
from typing import Dict, Any, List, Optional, Generator, Type, TypeVar, Union
from pathlib import Path
import time

from sqlalchemy import create_engine, text, MetaData, Table, Column, String, Integer, DateTime, JSON, ForeignKey, select, insert, update, delete, event, inspect
from sqlalchemy.orm import sessionmaker, Session, declarative_base
from sqlalchemy.pool import QueuePool, StaticPool
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.engine import Engine
from docex.config.docex_config import DocEXConfig

# Configure logging
logger = logging.getLogger(__name__)

# Global variables
metadata = MetaData()
Base = declarative_base(metadata=metadata)
Session = sessionmaker()

# Type variable for model classes
T = TypeVar('T', bound='Base')

def get_base() -> Type:
    """
    Get the base class for declarative models
    
    Returns:
        Base class for declarative models
    """
    return Base

class Database:
    """
    Database connection manager for DocEX
    
    Handles both SQLite and PostgreSQL connections with proper configuration
    and connection pooling.
    
    Supports both single-tenant and multi-tenant (database-level) modes.
    When multi-tenancy is enabled, uses TenantDatabaseManager for tenant routing.
    """
    
    def __init__(self, config: Optional[DocEXConfig] = None, tenant_id: Optional[str] = None):
        """
        Initialize database connection

        Args:
            config: DocEXConfig instance. If None, uses DocEX configuration if available, otherwise default.
            tenant_id: Optional tenant identifier for database-level multi-tenancy.
        """
        # Try to use DocEX's config first, then fallback to provided config or default
        if config is not None:
            self.config = config
        else:
            # Try to get config from DocEX if it's initialized
            try:
                from docex import DocEX
                if DocEX._config is not None:
                    self.config = DocEX._config
                else:
                    self.config = DocEXConfig()
            except:
                self.config = DocEXConfig()
        self.tenant_id = tenant_id
        self.engine = None
        self.Session = None
        
        # Check if database-level multi-tenancy is enabled (v2.x)
        security_config = self.config.get('security', {})
        self.multi_tenancy_model = security_config.get('multi_tenancy_model', 'row_level')
        self.tenant_database_routing = security_config.get('tenant_database_routing', False)

        # Check if v3.0 multi-tenancy is enabled
        multi_tenancy_config = self.config.get('multi_tenancy', {})
        v3_multi_tenancy_enabled = multi_tenancy_config.get('enabled', False)

        # Use TenantDatabaseManager if:
        # 1. v2.x database-level multi-tenancy is enabled, OR
        # 2. v3.0 multi-tenancy is enabled AND tenant_id is provided
        if self.multi_tenancy_model == 'database_level' or (v3_multi_tenancy_enabled and tenant_id):
            if self.multi_tenancy_model == 'database_level' and not tenant_id:
                # Allow system/bootstrap operations without tenant_id
                # Initialize directly for system operations to avoid recursion
                self._initialize_system_database()
                return
            # Use tenant-aware database manager
            from docex.db.tenant_database_manager import TenantDatabaseManager
            self.tenant_manager = TenantDatabaseManager()
            self.engine = self.tenant_manager.get_tenant_engine(tenant_id)
            # Get session factory from tenant manager
            session_factory = self.tenant_manager._tenant_sessions.get(tenant_id)
            if session_factory:
                self.Session = session_factory
            else:
                # Create session factory if not already created
                self.Session = sessionmaker(
                    bind=self.engine,
                    expire_on_commit=False,
                    autocommit=False,
                    autoflush=False
                )
        else:
            # Use standard single-tenant initialization
            self._initialize()
<<<<<<< HEAD

    def _initialize_system_database(self):
        """Initialize database for system/bootstrap operations (bypasses tenant manager)."""
        # Get database configuration
        db_config = self.config.get('database', {})
        db_type = db_config.get('type', 'sqlite')

        for attempt in range(3):  # max_retries
            try:
                if db_type == 'sqlite':
                    # SQLite configuration
                    db_path = db_config.get('path', 'docex.db')
                    db_path = Path(db_path)

                    # Ensure directory exists
                    db_path.parent.mkdir(parents=True, exist_ok=True)

                    # Create database file if it doesn't exist
                    if not db_path.exists():
                        db_path.touch()
                        db_path.chmod(0o644)

                    # Create SQLite engine
                    from sqlalchemy import create_engine, event
                    self.engine = create_engine(
                        f'sqlite:///{db_path}',
                        poolclass=QueuePool,
                        pool_size=5,
                        max_overflow=10,
                        pool_timeout=30,
                        pool_recycle=1800,
                        connect_args={
                            'timeout': 30,
                            'check_same_thread': False
                        }
                    )

                    # Enable foreign key support
                    @event.listens_for(self.engine, "connect")
                    def set_sqlite_pragma(dbapi_connection, connection_record):
                        cursor = dbapi_connection.cursor()
                        cursor.execute("PRAGMA foreign_keys=ON")
                        cursor.close()

                elif db_type in ['postgresql', 'postgres']:
                    # PostgreSQL configuration
                    from urllib.parse import quote_plus
                    from sqlalchemy import create_engine, text

                    postgres_config = db_config.get('postgres', db_config.get('postgresql', {}))
                    host = postgres_config.get('host', 'localhost')
                    port = postgres_config.get('port', 5432)
                    database = postgres_config.get('database', 'docex')
                    user = postgres_config.get('user', 'postgres')
                    password = postgres_config.get('password', '')

                    # URL-encode user and password
                    user_encoded = quote_plus(user)
                    password_encoded = quote_plus(password)
                    sslmode = postgres_config.get('sslmode', 'disable' if host in ['localhost', '127.0.0.1'] else 'require')

                    connection_url = f'postgresql://{user_encoded}:{password_encoded}@{host}:{port}/{database}?sslmode={sslmode}'
                    self.engine = create_engine(
                        connection_url,
                        poolclass=QueuePool,
                        pool_size=5,
                        max_overflow=10,
                        pool_timeout=30,
                        pool_recycle=1800
                    )

                # Test connection
                with self.engine.connect() as conn:
                    conn.execute(text("SELECT 1"))

                # Ensure tenant registry schema for PostgreSQL
                if db_type in ['postgresql', 'postgres']:
                    self.ensure_tenant_registry_schema()

                # Create session factory
                from sqlalchemy.orm import sessionmaker
                self.Session = sessionmaker(
                    bind=self.engine,
                    expire_on_commit=False,
                    autocommit=False,
                    autoflush=False
                )

                # Mark as initialized
                self._initialized = True
                return

            except Exception as e:
                if attempt == 2:  # Last attempt
                    logger.error(f"Failed to initialize system database after 3 attempts: {str(e)}")
                    raise RuntimeError(f"Failed to initialize system database: {str(e)}")
                logger.warning(f"Database connection attempt {attempt + 1} failed: {str(e)}. Retrying in 1 seconds...")
                import time
                time.sleep(1)

=======
    
    @classmethod
    def get_default_connection(cls, config: Optional[DocEXConfig] = None) -> 'Database':
        """
        Get default database connection, bypassing tenant routing.
        
        This is useful for system operations like tenant provisioning where
        we need to access the default database regardless of multi-tenancy mode.
        
        Args:
            config: Optional DocEXConfig instance. If None, uses default config.
            
        Returns:
            Database instance connected to default database
        """
        config = config or DocEXConfig()
        db = cls.__new__(cls)
        db.config = config
        db.tenant_id = None
        db.engine = None
        db.Session = None
        db.multi_tenancy_model = 'row_level'  # Force single-tenant mode
        db.tenant_database_routing = False
        db._initialize()
        return db
    
>>>>>>> origin/release/2.7.0
    def _initialize(self):
        """Initialize database connection and session"""
        max_retries = 3
        retry_delay = 1  # seconds
        
        for attempt in range(max_retries):
            try:
                # Get database configuration
                db_config = self.config.get('database', {})
                db_type = db_config.get('type', 'sqlite')
                
                if db_type == 'sqlite':
                    # Get database path from config
                    db_path = db_config.get('path', 'docex.db')
                    db_path = Path(db_path)
                    
                    # Ensure directory exists
                    db_path.parent.mkdir(parents=True, exist_ok=True)
                    
                    # Create database file if it doesn't exist
                    if not db_path.exists():
                        db_path.touch()
                        # Set permissions to 644 (rw-r--r--)
                        db_path.chmod(0o644)
                    
                    # Create SQLite engine with proper configuration
                    self.engine = create_engine(
                        f'sqlite:///{db_path}',
                        poolclass=QueuePool,
                        pool_size=5,
                        max_overflow=10,
                        pool_timeout=30,
                        pool_recycle=1800,
                        connect_args={
                            'timeout': 30,  # Connection timeout in seconds
                            'check_same_thread': False  # Allow multiple threads
                        }
                    )
                    
                    # Enable foreign key support
                    @event.listens_for(self.engine, "connect")
                    def set_sqlite_pragma(dbapi_connection, connection_record):
                        cursor = dbapi_connection.cursor()
                        cursor.execute("PRAGMA foreign_keys=ON")
                        cursor.close()
                    
                    
                elif db_type in ['postgresql', 'postgres']:
                    # PostgreSQL configuration
                    from urllib.parse import quote_plus
<<<<<<< HEAD

                    postgres_config = db_config.get('postgres', db_config.get('postgresql', {}))
                    host = postgres_config.get('host', 'localhost')
                    port = postgres_config.get('port', 5432)
                    database = postgres_config.get('database', 'docex')
                    user = postgres_config.get('user', 'postgres')
                    password = postgres_config.get('password', '')
=======
                    
                    # Get PostgreSQL-specific config (nested under 'postgres' key)
                    postgres_config = db_config.get('postgres', {})
                    
                    host = postgres_config.get('host', db_config.get('host', 'localhost'))
                    port = postgres_config.get('port', db_config.get('port', 5432))
                    database = postgres_config.get('database', db_config.get('database', 'docex'))
                    user = postgres_config.get('user', db_config.get('user', 'postgres'))
                    password = postgres_config.get('password', db_config.get('password', ''))
>>>>>>> origin/release/2.7.0
                    
                    # URL-encode user and password to handle special characters
                    user_encoded = quote_plus(user)
                    password_encoded = quote_plus(password)
                    
                    # Create PostgreSQL engine with properly encoded credentials
<<<<<<< HEAD
                    # Add SSL mode - disable for local, require for remote/RDS
                    sslmode = db_config.get('sslmode', 'disable' if host in ['localhost', '127.0.0.1'] else 'require')
=======
                    # SSL mode: prefer (use SSL if available, otherwise allow non-SSL)
                    # This works for both local Docker (no SSL) and AWS RDS (with SSL)
                    # Falls back to disable for localhost if prefer doesn't work
                    if host in ['localhost', '127.0.0.1']:
                        sslmode = postgres_config.get('sslmode', 'prefer')
                    else:
                        sslmode = postgres_config.get('sslmode', 'prefer')
>>>>>>> origin/release/2.7.0
                    connection_url = f'postgresql://{user_encoded}:{password_encoded}@{host}:{port}/{database}?sslmode={sslmode}'
                    self.engine = create_engine(
                        connection_url,
                        poolclass=QueuePool,
                        pool_size=5,
                        max_overflow=10,
                        pool_timeout=30,
                        pool_recycle=1800
                    )
                
                # Test connection
                with self.engine.connect() as conn:
                    conn.execute(text("SELECT 1"))

                # Ensure tenant registry schema for PostgreSQL
                if db_type in ['postgresql', 'postgres']:
                    self.ensure_tenant_registry_schema()

                # Create session factory
                self.Session = sessionmaker(
                    bind=self.engine,
                    expire_on_commit=False,
                    autocommit=False,
                    autoflush=False
                )
                
                # Skip table creation if database-level multi-tenancy is enabled
                # In multi-tenant mode, tables should only exist in tenant schemas, not default schema
                if self.multi_tenancy_model == 'database_level':
                    logger.info("Database-level multi-tenancy enabled - skipping table creation in default schema")
                    logger.info("Tables will be created in tenant schemas on first access")
                    return
                
                # Create all tables
                Base.metadata.create_all(self.engine)
                
                # Verify table creation
                inspector = inspect(self.engine)
                tables = inspector.get_table_names()
                required_tables = ['docbasket', 'document', 'document_metadata', 'file_history', 'operations', 'operation_dependencies', 'doc_events', 'transport_routes', 'route_operations', 'processors', 'processing_operations']
                missing_tables = [table for table in required_tables if table not in tables]
                
                if missing_tables:
                    raise RuntimeError(f"Failed to create required tables: {', '.join(missing_tables)}")
                
                logger.info("Database tables initialized successfully")
                return
                
            except SQLAlchemyError as e:
                if attempt < max_retries - 1:
                    logger.warning(f"Database connection attempt {attempt + 1} failed: {str(e)}. Retrying in {retry_delay} seconds...")
                    time.sleep(retry_delay)
                    retry_delay *= 2  # Exponential backoff
                else:
                    raise RuntimeError(f"Failed to connect to database after {max_retries} attempts: {str(e)}")
            except Exception as e:
                raise RuntimeError(f"Unexpected error during database initialization: {str(e)}")
    
    def get_engine(self):
        """Get SQLAlchemy engine instance"""
        return self.engine
    
    def get_session(self):
        """Get database session"""
        if not self.Session:
            self._initialize()
        return self.Session()
    
    def close(self):
        """Close database connection"""
        if self.engine:
            self.engine.dispose()
    
    def session(self):
        """
        Get a database session
        
        Returns:
            SQLAlchemy session
        """
        if self.Session is None:
            if self.multi_tenancy_model == 'database_level' and self.tenant_id:
                # For tenant-aware mode, get session from tenant manager
                return self.tenant_manager.get_tenant_session(self.tenant_id)
            else:
                self._initialize()
        return self.Session()
    
    def transaction(self):
        """
        Get a database session with transaction
        
        Returns:
            SQLAlchemy session
        """
        return self.session()
    
    def initialize(self):
        """Initialize database schema"""
        Base.metadata.create_all(self.engine)
    
    def drop_all(self):
        """Drop all tables"""
        Base.metadata.drop_all(self.engine)
    
    @contextmanager
    def transaction(self) -> Generator[Session, None, None]:
        """
        Get a database session with transaction management
        
        Yields:
            SQLAlchemy session
        """
        if self.multi_tenancy_model == 'database_level' and self.tenant_id:
            # Use tenant-aware transaction
            with self.tenant_manager.tenant_transaction(self.tenant_id) as session:
                yield session
        else:
            # Use standard transaction
            session = self.Session()
            try:
                yield session
                session.commit()
            except Exception as e:
                session.rollback()
                logger.error(f"Database transaction error: {str(e)}")
                raise
            finally:
                session.close()
    
    def execute(self, query: Union[str, Any], params: Optional[Dict] = None) -> Any:
        """
        Execute a SQL query
        
        Args:
            query: SQL query string or SQLAlchemy query
            params: Query parameters
            
        Returns:
            Query result
        """
        with self.transaction() as session:
            if isinstance(query, str):
                return session.execute(text(query), params or {})
            else:
                return session.execute(query)
    
    def fetch_one(self, query: Union[str, Any], params: Optional[Dict] = None) -> Optional[Dict]:
        """
        Fetch a single row from the database
        
        Args:
            query: SQL query string or SQLAlchemy query
            params: Query parameters
            
        Returns:
            Dictionary with row data or None if no results
        """
        result = self.execute(query, params)
        row = result.fetchone()
        if row is None:
            return None
        return dict(row._mapping) if hasattr(row, '_mapping') else dict(row)
    
    def fetch_all(self, query: Union[str, Any], params: Optional[Dict] = None) -> List[Dict]:
        """
        Fetch all rows from the database
        
        Args:
            query: SQL query string or SQLAlchemy query
            params: Query parameters
            
        Returns:
            List of dictionaries with row data
        """
        result = self.execute(query, params)
        rows = result.fetchall()
        return [dict(row._mapping) if hasattr(row, '_mapping') else dict(row) for row in rows]
    
    def create_tables(self) -> None:
        """Create all tables defined in the metadata"""
        try:
            Base = get_base()
            Base.metadata.create_all(self.engine)
            logger.info("Database tables created successfully")
        except Exception as e:
            logger.error(f"Failed to create database tables: {str(e)}")
            raise
    
    def drop_tables(self) -> None:
        """Drop all tables defined in the metadata"""
        Base = get_base()
        Base.metadata.drop_all(self.engine)
    
    def get_bootstrap_connection(self):
        """
        Get a database connection configured for bootstrap/system operations.

        This ensures that system tables (like tenant_registry) are created in
        the bootstrap schema instead of the public schema.

        Returns:
            SQLAlchemy connection object with proper search path set
        """
        # Get bootstrap schema from config
        db_config = self.config.get('database', {})
        postgres_config = db_config.get('postgres', db_config.get('postgresql', {}))
        bootstrap_schema = postgres_config.get('system_schema', 'docex_system')

        # Create connection and set search path to bootstrap schema
        conn = self.engine.connect()

        # Set search path to bootstrap schema for system operations
        if db_config.get('type') in ['postgresql', 'postgres']:
            conn.execute(text(f'SET search_path TO {bootstrap_schema}'))
            # Create schema if it doesn't exist
            conn.execute(text(f'CREATE SCHEMA IF NOT EXISTS {bootstrap_schema}'))
            conn.commit()

        return conn

    def execute_system_query(self, query: str, params: Optional[Dict[str, Any]] = None) -> Any:
        """
        Execute a system-level query using the bootstrap schema.

        This ensures that system tables (like tenant_registry) are accessed
        in the correct bootstrap schema instead of the public schema.

        Args:
            query: SQL query string
            params: Query parameters

        Returns:
            Query result
        """
        with self.get_bootstrap_connection() as conn:
            result = conn.execute(text(query), params or {})
            conn.commit()
            return result

    def ensure_tenant_registry_schema(self) -> None:
        """
        Ensure tenant registry table exists in the bootstrap schema.

        This fixes the bug where tenant_registry table is created in public schema
        instead of the configured bootstrap schema.
        """
        db_config = self.config.get('database', {})
        if db_config.get('type') not in ['postgresql', 'postgres']:
            return  # Only applies to PostgreSQL

        postgres_config = db_config.get('postgres', db_config.get('postgresql', {}))
        bootstrap_schema = postgres_config.get('system_schema', 'docex_system')

        # SQL to create tenant_registry table in bootstrap schema
        create_table_sql = f"""
        CREATE TABLE IF NOT EXISTS {bootstrap_schema}.tenant_registry (
            tenant_id VARCHAR(255) NOT NULL,
            display_name VARCHAR(255) NOT NULL,
            is_system BOOLEAN NOT NULL DEFAULT FALSE,
            isolation_strategy VARCHAR(50) NOT NULL DEFAULT 'schema',
            schema_name VARCHAR(255),
            database_path VARCHAR(500),
            created_at TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
            created_by VARCHAR(255) NOT NULL,
            last_updated_at TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
            last_updated_by VARCHAR(255),
            PRIMARY KEY (tenant_id)
        )
        """

        try:
            with self.engine.connect() as conn:
                # Create schema if it doesn't exist
                conn.execute(text(f'CREATE SCHEMA IF NOT EXISTS {bootstrap_schema}'))
                # Create table in bootstrap schema
                conn.execute(text(create_table_sql))
                conn.commit()
                logger.info(f"Ensured tenant_registry table exists in schema: {bootstrap_schema}")
        except Exception as e:
            logger.warning(f"Failed to create tenant_registry table in bootstrap schema: {e}")

    def get_bootstrap_schema(self) -> str:
        """Get the bootstrap/system schema name."""
        db_config = self.config.get('database', {})
        postgres_config = db_config.get('postgres', db_config.get('postgresql', {}))
        return postgres_config.get('system_schema', 'docex_system')

    def dispose(self) -> None:
        """Close all database connections"""
        if self.engine:
            self.engine.dispose()
            self.engine = None 