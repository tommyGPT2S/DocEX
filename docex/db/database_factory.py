from typing import Optional
from docex.db.abstract_database import AbstractDatabase
from docex.db.sqlite_database import SQLiteDatabase
from docex.config.config_manager import ConfigManager

# Optional PostgreSQL support - only available if psycopg2-binary is installed
try:
    from docex.db.postgres_database import PostgresDatabase
    HAS_POSTGRES = True
except ImportError:
    PostgresDatabase = None
    HAS_POSTGRES = False

class DatabaseFactory:
    """Factory for creating database instances based on configuration"""
    
    @staticmethod
    def create_database(config: Optional[ConfigManager] = None) -> AbstractDatabase:
        """
        Create a database instance based on configuration
        
        Args:
            config: Optional configuration manager. If not provided, will use default config.
            
        Returns:
            Database instance
            
        Raises:
            ValueError: If database type is unsupported or required dependencies are missing
        """
        if config is None:
            config = ConfigManager()
        
        db_type = config.get('database.type', 'sqlite')  # Default to SQLite for lightweight install
        
        if db_type.lower() == 'sqlite':
            return SQLiteDatabase(config)
        elif db_type.lower() == 'postgres':
            if not HAS_POSTGRES or not PostgresDatabase:
                raise ValueError(
                    "PostgreSQL support requires 'psycopg2-binary' package. "
                    "Install it with: pip install docex[postgres]"
                )
            return PostgresDatabase(config)
        else:
            raise ValueError(f"Unsupported database type: {db_type}") 