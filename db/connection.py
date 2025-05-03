import os
import logging
from contextlib import contextmanager
from typing import Dict, Any, List, Optional, Generator, Type, TypeVar, Union

from sqlalchemy import create_engine, text, MetaData, Table, Column, String, Integer, DateTime, JSON, ForeignKey, select, insert, update, delete
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session, scoped_session
from sqlalchemy.pool import QueuePool
from sqlalchemy.exc import SQLAlchemyError

# Configure logging
logger = logging.getLogger(__name__)

# Create base class for declarative models
Base = declarative_base()

# Type variable for model classes
T = TypeVar('T', bound=Base)

class Database:
    """
    Database connection manager for DocFlow
    
    Provides a unified interface for database operations using SQLAlchemy.
    Handles connection pooling, transaction management, and error handling.
    """
    
    _instance = None
    _engine = None
    _session_factory = None
    
    def __new__(cls, *args, **kwargs):
        """Singleton pattern to ensure only one database instance exists"""
        if cls._instance is None:
            cls._instance = super(Database, cls).__new__(cls)
        return cls._instance
    
    def __init__(self, environment: str = None):
        """
        Initialize database connection
        
        Args:
            environment: Environment name (development, testing, production)
        """
        if self._engine is not None:
            return
            
        # Get database configuration from environment variables
        db_config = {
            'username': os.getenv('DB_USER', 'postgres'),
            'password': os.getenv('DB_PASSWORD', 'postgres'),
            'host': os.getenv('DB_HOST', 'localhost'),
            'port': os.getenv('DB_PORT', '5432'),
            'database': os.getenv('DB_NAME', 'docflow'),
            'schema': os.getenv('DB_SCHEMA', 'docflow'),
            'pool_size': int(os.getenv('DB_POOL_SIZE', '5')),
            'max_overflow': int(os.getenv('DB_MAX_OVERFLOW', '10')),
            'pool_timeout': int(os.getenv('DB_POOL_TIMEOUT', '30')),
            'pool_recycle': int(os.getenv('DB_POOL_RECYCLE', '1800')),
            'echo': os.getenv('DB_ECHO', 'false').lower() == 'true'
        }
        
        # Create connection URL
        connection_url = f"postgresql://{db_config['username']}:{db_config['password']}@{db_config['host']}:{db_config['port']}/{db_config['database']}"
        
        # Create engine with connection pooling
        self._engine = create_engine(
            connection_url,
            poolclass=QueuePool,
            pool_size=db_config['pool_size'],
            max_overflow=db_config['max_overflow'],
            pool_timeout=db_config['pool_timeout'],
            pool_recycle=db_config['pool_recycle'],
            echo=db_config['echo'],
            connect_args={
                "application_name": "docflow",
                "options": f"-c search_path={db_config['schema']}"
            }
        )
        
        # Create session factory
        self._session_factory = scoped_session(
            sessionmaker(
                autocommit=False,
                autoflush=False,
                bind=self._engine
            )
        )
        
        # Create metadata
        self.metadata = MetaData(schema=db_config['schema'])
        
        logger.info(f"Database connection initialized for environment: {environment}")
    
    @contextmanager
    def session(self) -> Generator[Session, None, None]:
        """
        Get a database session
        
        Yields:
            SQLAlchemy session
        """
        session = self._session_factory()
        try:
            yield session
            session.commit()
        except Exception as e:
            session.rollback()
            logger.error(f"Database session error: {str(e)}")
            raise
        finally:
            session.close()
    
    @contextmanager
    def transaction(self) -> Generator[Session, None, None]:
        """
        Get a database session with transaction management
        
        Yields:
            SQLAlchemy session
        """
        with self.session() as session:
            yield session
    
    def execute(self, query: Union[str, Any], params: Optional[Dict] = None) -> Any:
        """
        Execute a SQL query
        
        Args:
            query: SQL query string or SQLAlchemy query
            params: Query parameters
            
        Returns:
            Query result
        """
        with self.session() as session:
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
        Base.metadata.create_all(self._engine)
    
    def drop_tables(self) -> None:
        """Drop all tables defined in the metadata"""
        Base.metadata.drop_all(self._engine)
    
    def dispose(self) -> None:
        """Close all database connections"""
        if self._engine:
            self._engine.dispose()
            self._engine = None
            self._session_factory = None 