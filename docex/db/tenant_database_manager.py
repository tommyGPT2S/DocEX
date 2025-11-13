"""
Tenant-aware database connection manager for database-level multi-tenancy.

This module provides connection management for Model B multi-tenancy,
where each tenant has its own database (SQLite) or schema (PostgreSQL).
"""

import os
import logging
from contextlib import contextmanager
from typing import Dict, Any, Optional, Generator
from pathlib import Path
import threading
from sqlalchemy import create_engine, text, inspect, event
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import QueuePool
from sqlalchemy.exc import SQLAlchemyError
from docex.config.docex_config import DocEXConfig
from docex.db.models import Base

logger = logging.getLogger(__name__)


class TenantDatabaseManager:
    """
    Manages database connections per tenant for database-level multi-tenancy.
    
    Supports:
    - PostgreSQL: One schema per tenant (e.g., tenant_tenant1, tenant_tenant2)
    - SQLite: One database file per tenant (e.g., tenant_tenant1/docex.db)
    
    Maintains a connection pool per tenant for efficient connection reuse.
    """
    
    _instance = None
    _lock = threading.Lock()
    
    def __new__(cls):
        """Singleton pattern to ensure one manager instance"""
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        """Initialize tenant database manager"""
        if hasattr(self, '_initialized') and self._initialized:
            return
        
        self.config = DocEXConfig()
        self._tenant_engines: Dict[str, Any] = {}  # tenant_id -> engine
        self._tenant_sessions: Dict[str, sessionmaker] = {}  # tenant_id -> sessionmaker
        self._tenant_locks: Dict[str, threading.Lock] = {}  # tenant_id -> lock
        self._initialized = True
        
        # Check if database-level multi-tenancy is enabled
        security_config = self.config.get('security', {})
        self.multi_tenancy_model = security_config.get('multi_tenancy_model', 'row_level')
        self.tenant_database_routing = security_config.get('tenant_database_routing', False)
        
        if self.multi_tenancy_model == 'database_level':
            logger.info("Database-level multi-tenancy enabled")
    
    def get_tenant_engine(self, tenant_id: str) -> Any:
        """
        Get or create database engine for a specific tenant.
        
        Args:
            tenant_id: Tenant identifier
            
        Returns:
            SQLAlchemy engine for the tenant
            
        Raises:
            ValueError: If tenant_id is not provided and multi-tenancy is enabled
            RuntimeError: If database connection fails
        """
        if not tenant_id:
            if self.multi_tenancy_model == 'database_level':
                raise ValueError("tenant_id is required when database-level multi-tenancy is enabled")
            # Fallback to default database
            return self._get_default_engine()
        
        # Check if engine already exists
        if tenant_id in self._tenant_engines:
            return self._tenant_engines[tenant_id]
        
        # Create engine for tenant (thread-safe)
        if tenant_id not in self._tenant_locks:
            self._tenant_locks[tenant_id] = threading.Lock()
        
        with self._tenant_locks[tenant_id]:
            # Double-check after acquiring lock
            if tenant_id in self._tenant_engines:
                return self._tenant_engines[tenant_id]
            
            # Create new engine for tenant
            engine = self._create_tenant_engine(tenant_id)
            self._tenant_engines[tenant_id] = engine
            
            # Create session factory
            self._tenant_sessions[tenant_id] = sessionmaker(
                bind=engine,
                expire_on_commit=False,
                autocommit=False,
                autoflush=False
            )
            
            logger.info(f"Created database connection for tenant: {tenant_id}")
            return engine
    
    def _create_tenant_engine(self, tenant_id: str) -> Any:
        """
        Create database engine for a specific tenant.
        
        Args:
            tenant_id: Tenant identifier
            
        Returns:
            SQLAlchemy engine
        """
        db_config = self.config.get('database', {})
        db_type = db_config.get('type', 'sqlite')
        
        if db_type == 'sqlite':
            return self._create_sqlite_engine(tenant_id, db_config)
        elif db_type in ['postgresql', 'postgres']:
            return self._create_postgres_engine(tenant_id, db_config)
        else:
            raise ValueError(f"Unsupported database type: {db_type}")
    
    def _create_sqlite_engine(self, tenant_id: str, db_config: Dict[str, Any]) -> Any:
        """
        Create SQLite engine for tenant (separate database file per tenant).
        
        Args:
            tenant_id: Tenant identifier
            db_config: Database configuration
            
        Returns:
            SQLAlchemy engine
        """
        sqlite_config = db_config.get('sqlite', {})
        
        # Get path template (e.g., "storage/tenant_{tenant_id}/docex.db")
        path_template = sqlite_config.get('path_template', 'storage/tenant_{tenant_id}/docex.db')
        db_path = Path(path_template.format(tenant_id=tenant_id))
        
        # Ensure directory exists
        db_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Create database file if it doesn't exist
        if not db_path.exists():
            db_path.touch()
            db_path.chmod(0o644)
            logger.info(f"Created SQLite database for tenant {tenant_id}: {db_path}")
        
        # Create engine
        engine = create_engine(
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
        @event.listens_for(engine, "connect")
        def set_sqlite_pragma(dbapi_connection, connection_record):
            cursor = dbapi_connection.cursor()
            cursor.execute("PRAGMA foreign_keys=ON")
            cursor.close()
        
        # Initialize schema for tenant
        self._initialize_tenant_schema(engine, tenant_id)
        
        return engine
    
    def _create_postgres_engine(self, tenant_id: str, db_config: Dict[str, Any]) -> Any:
        """
        Create PostgreSQL engine for tenant (separate schema per tenant).
        
        Args:
            tenant_id: Tenant identifier
            db_config: Database configuration
            
        Returns:
            SQLAlchemy engine
        """
        postgres_config = db_config.get('postgres', {})
        
        # Get base connection parameters
        host = postgres_config.get('host', 'localhost')
        port = postgres_config.get('port', 5432)
        database = postgres_config.get('database', 'docex')
        user = postgres_config.get('user', 'postgres')
        password = postgres_config.get('password', '')
        
        # Get schema template (e.g., "tenant_{tenant_id}")
        schema_template = postgres_config.get('schema_template', 'tenant_{tenant_id}')
        schema_name = schema_template.format(tenant_id=tenant_id)
        
        # Create connection URL
        connection_url = f'postgresql://{user}:{password}@{host}:{port}/{database}'
        
        # Create engine with schema in search_path
        engine = create_engine(
            connection_url,
            poolclass=QueuePool,
            pool_size=5,
            max_overflow=10,
            pool_timeout=30,
            pool_recycle=1800,
            connect_args={
                'options': f'-csearch_path={schema_name}'
            }
        )
        
        # Set search path on connection
        @event.listens_for(engine, "connect")
        def set_search_path(dbapi_connection, connection_record):
            with dbapi_connection.cursor() as cursor:
                cursor.execute(f"SET search_path TO {schema_name}")
        
        # Create schema and initialize for tenant
        self._create_postgres_schema(engine, schema_name, tenant_id)
        self._initialize_tenant_schema(engine, tenant_id)
        
        return engine
    
    def _create_postgres_schema(self, engine: Any, schema_name: str, tenant_id: str) -> None:
        """
        Create PostgreSQL schema for tenant if it doesn't exist.
        
        Args:
            engine: SQLAlchemy engine
            schema_name: Schema name
            tenant_id: Tenant identifier
        """
        try:
            with engine.connect() as conn:
                # Create schema if it doesn't exist
                conn.execute(text(f"CREATE SCHEMA IF NOT EXISTS {schema_name}"))
                conn.commit()
                logger.info(f"Created PostgreSQL schema for tenant {tenant_id}: {schema_name}")
        except SQLAlchemyError as e:
            logger.error(f"Failed to create schema {schema_name} for tenant {tenant_id}: {e}")
            raise
    
    def _initialize_tenant_schema(self, engine: Any, tenant_id: str) -> None:
        """
        Initialize database schema for tenant (create tables).
        
        Args:
            engine: SQLAlchemy engine
            tenant_id: Tenant identifier
        """
        try:
            # Create all tables in tenant's database/schema
            Base.metadata.create_all(engine)
            
            # Verify table creation
            inspector = inspect(engine)
            tables = inspector.get_table_names()
            required_tables = [
                'docbasket', 'document', 'document_metadata', 'file_history',
                'operations', 'operation_dependencies', 'doc_events',
                'transport_routes', 'route_operations', 'processors', 'processing_operations'
            ]
            missing_tables = [table for table in required_tables if table not in tables]
            
            if missing_tables:
                logger.warning(f"Some tables missing for tenant {tenant_id}: {missing_tables}")
            else:
                logger.info(f"Schema initialized for tenant {tenant_id}")
        except Exception as e:
            logger.error(f"Failed to initialize schema for tenant {tenant_id}: {e}")
            raise
    
    def get_tenant_session(self, tenant_id: Optional[str] = None) -> Session:
        """
        Get database session for tenant.
        
        Args:
            tenant_id: Tenant identifier. If None and multi-tenancy is disabled, uses default.
            
        Returns:
            SQLAlchemy session
        """
        if self.multi_tenancy_model == 'database_level' and tenant_id:
            engine = self.get_tenant_engine(tenant_id)
            session_factory = self._tenant_sessions.get(tenant_id)
            if session_factory:
                return session_factory()
            else:
                # Fallback: create session factory
                session_factory = sessionmaker(
                    bind=engine,
                    expire_on_commit=False,
                    autocommit=False,
                    autoflush=False
                )
                self._tenant_sessions[tenant_id] = session_factory
                return session_factory()
        else:
            # Use default database
            return self._get_default_session()
    
    @contextmanager
    def tenant_transaction(self, tenant_id: Optional[str] = None) -> Generator[Session, None, None]:
        """
        Get database session with transaction management for tenant.
        
        Args:
            tenant_id: Tenant identifier
            
        Yields:
            SQLAlchemy session
        """
        session = self.get_tenant_session(tenant_id)
        try:
            yield session
            session.commit()
        except Exception as e:
            session.rollback()
            logger.error(f"Database transaction error for tenant {tenant_id}: {str(e)}")
            raise
        finally:
            session.close()
    
    def _get_default_engine(self) -> Any:
        """Get default database engine (for non-multi-tenant mode)"""
        from docex.db.connection import Database
        db = Database()
        return db.get_engine()
    
    def _get_default_session(self) -> Session:
        """Get default database session (for non-multi-tenant mode)"""
        from docex.db.connection import Database
        db = Database()
        return db.session()
    
    def close_tenant_connection(self, tenant_id: str) -> None:
        """
        Close database connection for a specific tenant.
        
        Args:
            tenant_id: Tenant identifier
        """
        if tenant_id in self._tenant_engines:
            engine = self._tenant_engines[tenant_id]
            engine.dispose()
            del self._tenant_engines[tenant_id]
            if tenant_id in self._tenant_sessions:
                del self._tenant_sessions[tenant_id]
            logger.info(f"Closed database connection for tenant: {tenant_id}")
    
    def close_all_connections(self) -> None:
        """Close all tenant database connections"""
        for tenant_id in list(self._tenant_engines.keys()):
            self.close_tenant_connection(tenant_id)
    
    def list_tenant_databases(self) -> list[str]:
        """
        List all tenant databases/schemas.
        
        Returns:
            List of tenant IDs
        """
        return list(self._tenant_engines.keys())

