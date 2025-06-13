import os
import json
from contextlib import contextmanager
from typing import ContextManager, Dict, Any, Optional, List, Union
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker, Session
from docflow.db.abstract_database import AbstractDatabase
from docflow.config.config_manager import ConfigManager
from docflow.db.models import Base

class SQLiteDatabase(AbstractDatabase):
    """SQLite database implementation"""
    
    def __init__(self, config: ConfigManager):
        """
        Initialize SQLite database
        
        Args:
            config: Configuration manager
        """
        super().__init__(config)
        self.db_path = config.get('database.sqlite.path', 'docflow.db')
        self.engine = None
        self.Session = None
        self._current_session = None
    
    def _create_engine(self) -> None:
        """Create SQLite engine"""
        # Ensure directory exists
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        
        # Ensure file has write permissions
        if os.path.exists(self.db_path):
            os.chmod(self.db_path, 0o644)
        
        # Create engine with SQLite specific settings
        self.engine = create_engine(
            f'sqlite:///{self.db_path}',
            connect_args={
                'check_same_thread': False,  # Required for SQLite
                'timeout': 30,  # Add timeout to prevent locking issues
            },
            echo=self.config.get('database.echo', False)
        )
        self.Session = sessionmaker(bind=self.engine)
    
    def connect(self) -> None:
        """Connect to the database"""
        if self.engine is None:
            self._create_engine()
    
    def disconnect(self) -> None:
        """Disconnect from the database"""
        self.close()
    
    def _handle_json_fields(self, data: Dict) -> Dict:
        """Convert JSON fields to/from text for SQLite storage"""
        json_fields = {'config', 'content', 'details', 'data', 'value'}
        result = {}
        for key, value in data.items():
            if key in json_fields and value is not None:
                if isinstance(value, str):
                    try:
                        # Try to parse if it's a JSON string
                        result[key] = json.loads(value)
                    except json.JSONDecodeError:
                        # If not valid JSON, store as is
                        result[key] = value
                else:
                    # Convert to JSON string for storage
                    result[key] = json.dumps(value)
            else:
                result[key] = value
        return result

    def initialize(self) -> None:
        """Initialize the database with schema"""
        self.connect()
        
        # Read and execute unified schema
        schema_path = os.path.join(os.path.dirname(__file__), 'schema.sql')
        with open(schema_path, 'r') as f:
            schema_sql = f.read()
        
        # Process schema SQL, excluding PostgreSQL-specific sections
        in_postgres_section = False
        processed_statements = []
        
        for line in schema_sql.split('\n'):
            line = line.strip()
            
            # Skip empty lines and regular comments
            if not line or (line.startswith('--') and 'POSTGRES-SPECIFIC' not in line):
                continue
            
            # Handle PostgreSQL section markers
            if '-- BEGIN POSTGRES-SPECIFIC' in line:
                in_postgres_section = True
                continue
            elif '-- END POSTGRES-SPECIFIC' in line:
                in_postgres_section = False
                continue
            
            # Skip lines in PostgreSQL sections
            if in_postgres_section:
                continue
            
            # Remove schema prefix from table names and references
            line = line.replace('docflow.', '')
            processed_statements.append(line)
        
        # Join processed statements back into SQL
        processed_sql = '\n'.join(processed_statements)
        
        # Split into individual statements and execute
        statements = processed_sql.split(';')
        with self.transaction() as session:
            for statement in statements:
                statement = statement.strip()
                if statement:
                    try:
                        session.execute(text(statement))
                    except Exception as e:
                        print(f"Error executing statement: {statement}")
                        raise
            session.commit()
    
    def execute(self, query: str, params: Optional[Dict] = None) -> Any:
        """
        Execute a query
        
        Args:
            query: SQL query
            params: Optional query parameters
            
        Returns:
            Query result
        """
        if params:
            params = self._handle_json_fields(params)
            
        if self._current_session is None:
            with self.transaction() as session:
                result = session.execute(text(query), params or {})
                return result
        return self._current_session.execute(text(query), params or {})
    
    def fetch_one(self, query: str, params: Optional[Dict] = None) -> Optional[Dict]:
        """
        Fetch one row from a query
        
        Args:
            query: SQL query
            params: Optional query parameters
            
        Returns:
            Single row as dictionary or None
        """
        result = self.execute(query, params)
        row = result.fetchone()
        if row:
            data = dict(row._mapping)
            return self._handle_json_fields(data)
        return None
    
    def fetch_all(self, query: str, params: Optional[Dict] = None) -> List[Dict]:
        """
        Fetch all rows from a query
        
        Args:
            query: SQL query
            params: Optional query parameters
            
        Returns:
            List of rows as dictionaries
        """
        result = self.execute(query, params)
        return [self._handle_json_fields(dict(row._mapping)) for row in result]
    
    def insert(self, table: str, data: Dict) -> Any:
        """
        Insert a row into a table
        
        Args:
            table: Table name
            data: Row data as dictionary
            
        Returns:
            Inserted row ID
        """
        columns = ', '.join(data.keys())
        placeholders = ', '.join(f':{k}' for k in data.keys())
        query = f'INSERT INTO {table} ({columns}) VALUES ({placeholders})'
        result = self.execute(query, data)
        return result.lastrowid
    
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
        set_clause = ', '.join(f'{k} = :{k}' for k in data.keys())
        where_clause = ' AND '.join(f'{k} = :where_{k}' for k in where.keys())
        query = f'UPDATE {table} SET {set_clause} WHERE {where_clause}'
        
        params = {**data, **{f'where_{k}': v for k, v in where.items()}}
        result = self.execute(query, params)
        return result.rowcount
    
    def delete(self, table: str, where: Dict) -> int:
        """
        Delete rows from a table
        
        Args:
            table: Table name
            where: WHERE clause conditions as dictionary
            
        Returns:
            Number of rows deleted
        """
        where_clause = ' AND '.join(f'{k} = :{k}' for k in where.keys())
        query = f'DELETE FROM {table} WHERE {where_clause}'
        result = self.execute(query, where)
        return result.rowcount
    
    def begin_transaction(self) -> None:
        """Begin a transaction"""
        if self._current_session is None:
            self._current_session = self.Session()
    
    def commit(self) -> None:
        """Commit a transaction"""
        if self._current_session is not None:
            self._current_session.commit()
            self._current_session = None
    
    def rollback(self) -> None:
        """Rollback a transaction"""
        if self._current_session is not None:
            self._current_session.rollback()
            self._current_session = None
    
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
        column_defs = []
        for name, col_type in columns.items():
            column_defs.append(f'{name} {col_type}')
        
        if primary_key:
            if isinstance(primary_key, str):
                column_defs.append(f'PRIMARY KEY ({primary_key})')
            else:
                column_defs.append(f'PRIMARY KEY ({", ".join(primary_key)})')
        
        if foreign_keys:
            for fk in foreign_keys:
                column_defs.append(
                    f'FOREIGN KEY ({fk["column"]}) REFERENCES {fk["references"]}({fk["key"]})'
                )
        
        query = f'CREATE TABLE IF NOT EXISTS {table} ({", ".join(column_defs)})'
        self.execute(query)
    
    def drop_table(self, table: str) -> None:
        """
        Drop a table
        
        Args:
            table: Table name
        """
        self.execute(f'DROP TABLE IF EXISTS {table}')
    
    def add_column(self, table: str, column: str, column_type: str) -> None:
        """
        Add a column to a table
        
        Args:
            table: Table name
            column: Column name
            column_type: Column type
        """
        self.execute(f'ALTER TABLE {table} ADD COLUMN {column} {column_type}')
    
    def create_index(self, table: str, columns: Union[str, List[str]], 
                    unique: bool = False) -> None:
        """
        Create an index
        
        Args:
            table: Table name
            columns: Column(s) to index
            unique: Whether the index should be unique
        """
        if isinstance(columns, str):
            columns = [columns]
        
        index_name = f'idx_{table}_{"_".join(columns)}'
        unique_str = 'UNIQUE ' if unique else ''
        columns_str = ', '.join(columns)
        
        self.execute(f'CREATE {unique_str}INDEX IF NOT EXISTS {index_name} ON {table} ({columns_str})')
    
    def drop_index(self, table: str, columns: Union[str, List[str]]) -> None:
        """
        Drop an index
        
        Args:
            table: Table name
            columns: Column(s) in the index
        """
        if isinstance(columns, str):
            columns = [columns]
        
        index_name = f'idx_{table}_{"_".join(columns)}'
        self.execute(f'DROP INDEX IF EXISTS {index_name}')
    
    def get_table_info(self, table: str) -> Dict[str, Any]:
        """
        Get information about a table
        
        Args:
            table: Table name
            
        Returns:
            Dictionary with table information
        """
        return self.fetch_one(f'SELECT * FROM sqlite_master WHERE type="table" AND name=:table', {'table': table})
    
    def get_tables(self) -> List[str]:
        """
        Get list of tables
        
        Returns:
            List of table names
        """
        result = self.fetch_all("SELECT name FROM sqlite_master WHERE type='table'")
        return [row['name'] for row in result]
    
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
        if self._current_session:
            self._current_session.close()
            self._current_session = None
        
        if self.engine:
            self.engine.dispose()
            self.engine = None
            self.Session = None 