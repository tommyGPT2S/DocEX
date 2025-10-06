from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, List, Union, ContextManager
from contextlib import contextmanager
from sqlalchemy.orm import Session
from docflow.config.config_manager import ConfigManager

class AbstractDatabase(ABC):
    """
    Abstract base class for database backends
    
    Defines the interface for database operations.
    Implementations can use different database systems (SQLite, PostgreSQL, etc.).
    """
    
    def __init__(self, config: ConfigManager):
        """
        Initialize the database
        
        Args:
            config: Configuration manager
        """
        self.config = config
    
    @abstractmethod
    def connect(self) -> None:
        """
        Connect to the database
        """
        pass
    
    @abstractmethod
    def disconnect(self) -> None:
        """
        Disconnect from the database
        """
        pass
    
    @abstractmethod
    def execute(self, query: str, params: Optional[Dict] = None) -> Any:
        """
        Execute a query
        
        Args:
            query: SQL query
            params: Optional query parameters
            
        Returns:
            Query result
        """
        pass
    
    @abstractmethod
    def fetch_one(self, query: str, params: Optional[Dict] = None) -> Optional[Dict]:
        """
        Fetch one row from a query
        
        Args:
            query: SQL query
            params: Optional query parameters
            
        Returns:
            Single row as dictionary or None
        """
        pass
    
    @abstractmethod
    def fetch_all(self, query: str, params: Optional[Dict] = None) -> List[Dict]:
        """
        Fetch all rows from a query
        
        Args:
            query: SQL query
            params: Optional query parameters
            
        Returns:
            List of rows as dictionaries
        """
        pass
    
    @abstractmethod
    def insert(self, table: str, data: Dict) -> Any:
        """
        Insert a row into a table
        
        Args:
            table: Table name
            data: Row data as dictionary
            
        Returns:
            Inserted row ID or other identifier
        """
        pass
    
    @abstractmethod
    def update(self, table: str, data: Dict, where: Dict) -> int:
        """
        Update rows in a table
        
        Args:
            table: Table name
            data: Update data as dictionary
            where: WHERE clause conditions as dictionary
            
        Returns:
            Number of rows updated
        """
        pass
    
    @abstractmethod
    def delete(self, table: str, where: Dict) -> int:
        """
        Delete rows from a table
        
        Args:
            table: Table name
            where: WHERE clause conditions as dictionary
            
        Returns:
            Number of rows deleted
        """
        pass
    
    @abstractmethod
    def begin_transaction(self) -> None:
        """
        Begin a transaction
        """
        pass
    
    @abstractmethod
    def commit(self) -> None:
        """
        Commit a transaction
        """
        pass
    
    @abstractmethod
    def rollback(self) -> None:
        """
        Rollback a transaction
        """
        pass
    
    @contextmanager
    def transaction(self):
        """
        Context manager for transactions
        
        Usage:
            with db.transaction():
                db.insert(...)
                db.update(...)
        """
        self.begin_transaction()
        try:
            yield
            self.commit()
        except Exception:
            self.rollback()
            raise
    
    @abstractmethod
    def create_table(self, table: str, columns: Dict[str, str], 
                    primary_key: Optional[Union[str, List[str]]] = None,
                    foreign_keys: Optional[List[Dict]] = None) -> None:
        """
        Create a table
        
        Args:
            table: Table name
            columns: Column definitions as dictionary of name: type
            primary_key: Primary key column(s)
            foreign_keys: Foreign key definitions
        """
        pass
    
    @abstractmethod
    def drop_table(self, table: str) -> None:
        """
        Drop a table
        
        Args:
            table: Table name
        """
        pass
    
    @abstractmethod
    def add_column(self, table: str, column: str, column_type: str) -> None:
        """
        Add a column to a table
        
        Args:
            table: Table name
            column: Column name
            column_type: Column type
        """
        pass
    
    @abstractmethod
    def create_index(self, table: str, columns: Union[str, List[str]], 
                    unique: bool = False) -> None:
        """
        Create an index
        
        Args:
            table: Table name
            columns: Column(s) to index
            unique: Whether the index should be unique
        """
        pass
    
    @abstractmethod
    def drop_index(self, table: str, columns: Union[str, List[str]]) -> None:
        """
        Drop an index
        
        Args:
            table: Table name
            columns: Column(s) in the index
        """
        pass
    
    @abstractmethod
    def get_table_info(self, table: str) -> Dict[str, Any]:
        """
        Get information about a table
        
        Args:
            table: Table name
            
        Returns:
            Dictionary with table information
        """
        pass
    
    @abstractmethod
    def get_tables(self) -> List[str]:
        """
        Get list of tables
        
        Returns:
            List of table names
        """
        pass
    
    @abstractmethod
    def transaction(self) -> ContextManager[Session]:
        """
        Get a database transaction context
        
        Returns:
            Context manager for database session
        """
        pass
    
    @abstractmethod
    def initialize(self) -> None:
        """
        Initialize the database (create tables, etc.)
        """
        pass
    
    @abstractmethod
    def close(self) -> None:
        """
        Close the database connection
        """
        pass 