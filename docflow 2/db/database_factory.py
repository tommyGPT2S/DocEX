from typing import Optional
from docflow.db.abstract_database import AbstractDatabase
from docflow.db.postgres_database import PostgresDatabase
from docflow.db.sqlite_database import SQLiteDatabase
from docflow.config.config_manager import ConfigManager

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
        """
        if config is None:
            config = ConfigManager()
        
        db_type = config.get('database.type', 'postgres')
        
        if db_type.lower() == 'sqlite':
            return SQLiteDatabase(config)
        elif db_type.lower() == 'postgres':
            return PostgresDatabase(config)
        else:
            raise ValueError(f"Unsupported database type: {db_type}") 