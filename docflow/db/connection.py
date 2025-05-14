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
from docflow.config.docflow_config import DocFlowConfig

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
    Database connection manager for DocFlow
    
    Handles both SQLite and PostgreSQL connections with proper configuration
    and connection pooling.
    """
    
    def __init__(self, config: Optional[DocFlowConfig] = None):
        """
        Initialize database connection
        
        Args:
            config: DocFlowConfig instance. If None, uses default configuration.
        """
        self.config = config or DocFlowConfig()
        self.engine = None
        self.Session = None
        self._initialize()
    
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
                    db_path = db_config.get('path', 'docflow.db')
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
                    @event.listens_for(Engine, "connect")
                    def set_sqlite_pragma(dbapi_connection, connection_record):
                        cursor = dbapi_connection.cursor()
                        cursor.execute("PRAGMA foreign_keys=ON")
                        cursor.close()
                    
                elif db_type == 'postgresql':
                    # PostgreSQL configuration
                    host = db_config.get('host', 'localhost')
                    port = db_config.get('port', 5432)
                    database = db_config.get('database', 'docflow')
                    user = db_config.get('user', 'postgres')
                    password = db_config.get('password', '')
                    
                    # Create PostgreSQL engine
                    self.engine = create_engine(
                        f'postgresql://{user}:{password}@{host}:{port}/{database}',
                        poolclass=QueuePool,
                        pool_size=5,
                        max_overflow=10,
                        pool_timeout=30,
                        pool_recycle=1800
                    )
                
                # Test connection
                with self.engine.connect() as conn:
                    conn.execute(text("SELECT 1"))
                
                # Create session factory
                self.Session = sessionmaker(
                    bind=self.engine,
                    expire_on_commit=False,
                    autocommit=False,
                    autoflush=False
                )
                
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
    
    def dispose(self) -> None:
        """Close all database connections"""
        if self.engine:
            self.engine.dispose()
            self.engine = None 