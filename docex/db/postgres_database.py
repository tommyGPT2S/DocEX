from contextlib import contextmanager
from typing import ContextManager
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from docex.db.abstract_database import AbstractDatabase
from docex.config.config_manager import ConfigManager
from docex.db.models import Base

class PostgresDatabase(AbstractDatabase):
    """PostgreSQL database implementation"""
    
    def __init__(self, config: ConfigManager):
        """
        Initialize PostgreSQL database
        
        Args:
            config: Configuration manager
        """
        super().__init__(config)
        self.engine = None
        self.Session = None
    
    def _create_engine(self) -> None:
        """Create PostgreSQL engine"""
        # Get PostgreSQL configuration
        pg_config = self.config.get('database.postgres', {})
        
        # Create connection URL
        connection_url = (
            f"postgresql://{pg_config.get('user', 'postgres')}:"
            f"{pg_config.get('password', 'postgres')}@"
            f"{pg_config.get('host', 'localhost')}:"
            f"{pg_config.get('port', 5432)}/"
            f"{pg_config.get('database', 'docflow')}"
        )
        
        # Create engine with PostgreSQL specific settings
        self.engine = create_engine(
            connection_url,
            echo=self.config.get('database.echo', False),
            pool_size=self.config.get('database.pool_size', 5),
            max_overflow=self.config.get('database.max_overflow', 10),
            pool_timeout=self.config.get('database.pool_timeout', 30),
            pool_recycle=self.config.get('database.pool_recycle', 3600)
        )
        self.Session = sessionmaker(bind=self.engine)
    
    def initialize(self) -> None:
        """Initialize the database (create tables)"""
        if self.engine is None:
            self._create_engine()
        Base.metadata.create_all(self.engine)
    
    @contextmanager
    def transaction(self) -> ContextManager[Session]:
        """
        Get a database transaction context
        
        Returns:
            Context manager for database session
        """
        if self.Session is None:
            self._create_engine()
        
        session = self.Session()
        try:
            yield session
            session.commit()
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()
    
    def close(self) -> None:
        """Close the database connection"""
        if self.engine:
            self.engine.dispose()
            self.engine = None
            self.Session = None 