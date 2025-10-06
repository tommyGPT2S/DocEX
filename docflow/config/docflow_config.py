import os
import json
import yaml
import logging
from typing import Dict, Any, Optional
from pathlib import Path

# Configure logging
logger = logging.getLogger(__name__)

class DocFlowConfig:
    """
    Manages system-wide configuration for DocFlow
    
    This class follows the singleton pattern to ensure only one configuration instance exists.
    It manages system-wide settings like database connection and logging.
    """
    
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self):
        if not hasattr(self, 'initialized'):
            # Set up logging
            self.logger = logging.getLogger(__name__)
            
            # Load default configuration from file
            default_config_path = Path(__file__).parent / 'default_config.yaml'
            with open(default_config_path, 'r') as f:
                self.config = yaml.safe_load(f)
            
            # Load configuration from file if it exists
            self.config_file = Path.home() / '.docflow' / 'config.yaml'
            if self.config_file.exists():
                self._load_config()
            
            self.initialized = True
    
    @classmethod
    def setup(cls, **kwargs) -> None:
        """
        Set up DocFlow configuration
        
        Args:
            database: Database configuration
                - type: Database type ('sqlite' or 'postgresql')
                - sqlite: SQLite-specific settings
                    - path: Path to SQLite database file
                - postgresql: PostgreSQL-specific settings
                    - host: Database host
                    - port: Database port
                    - database: Database name
                    - user: Database user
                    - password: Database password
                    - schema: Database schema
            logging: Logging configuration
                - level: Logging level
                - file: Path to log file
        """
        instance = cls()
        
        # Update database configuration
        if 'database' in kwargs:
            instance.config['database'].update(kwargs['database'])
        
        # Update logging configuration
        if 'logging' in kwargs:
            instance.config['logging'].update(kwargs['logging'])
        
        # Ensure configuration directory exists
        config_dir = instance.config_file.parent
        config_dir.mkdir(parents=True, exist_ok=True)
        
        # Save configuration
        instance._save_config()
        
        instance.logger.info("DocFlow configuration updated")
    
    def _load_config(self) -> None:
        """Load configuration from file"""
        try:
            with open(self.config_file, 'r') as f:
                file_config = yaml.safe_load(f)
                self._update_config_recursive(self.config, file_config)
                self.logger.info(f"Configuration loaded from {self.config_file}")
        except Exception as e:
            self.logger.warning(f"Failed to load configuration: {str(e)}")
    
    def _save_config(self) -> None:
        """Save configuration to file"""
        try:
            with open(self.config_file, 'w') as f:
                yaml.dump(self.config, f, default_flow_style=False)
                self.logger.info(f"Configuration saved to {self.config_file}")
        except Exception as e:
            self.logger.error(f"Failed to save configuration: {str(e)}")
    
    def _update_config_recursive(self, base: Dict[str, Any], update: Dict[str, Any]) -> None:
        """Update configuration dictionary recursively"""
        for key, value in update.items():
            if key in base and isinstance(base[key], dict) and isinstance(value, dict):
                self._update_config_recursive(base[key], value)
            else:
                base[key] = value
    
    def get_database_config(self) -> Dict[str, Any]:
        """Get database configuration"""
        return self.config['database']
    
    def get_logging_config(self) -> Dict[str, Any]:
        """Get logging configuration"""
        return self.config['logging']
    
    def validate(self) -> bool:
        """
        Validate configuration
        
        Returns:
            True if configuration is valid
        """
        try:
            # Validate database configuration
            db_type = self.get('database.type')
            if db_type not in ['postgres', 'sqlite']:
                return False
            
            if db_type == 'postgres':
                required_fields = ['host', 'port', 'database', 'user', 'password']
                for field in required_fields:
                    if not self.get(f'database.postgresql.{field}'):
                        return False
            
            elif db_type == 'sqlite':
                if not self.get('database.sqlite.path'):
                    return False
            
            # Validate logging configuration
            if not self.get('logging.level') or not self.get('logging.file'):
                return False
            
            return True
        except Exception:
            return False
    
    def get(self, key: str, default: Any = None) -> Any:
        """
        Get configuration value using dot notation
        
        Args:
            key: Configuration key (e.g., 'database.type')
            default: Default value if key not found
            
        Returns:
            Configuration value
        """
        value = self.config
        for k in key.split('.'):
            if isinstance(value, dict):
                value = value.get(k, default)
            else:
                return default
        return value
    
    def get_all(self) -> Dict[str, Any]:
        """
        Get all configuration
        
        Returns:
            Complete configuration dictionary
        """
        return self.config.copy()
    
    def update(self, config: Dict[str, Any]) -> None:
        """
        Update configuration
        
        Args:
            config: Configuration dictionary to update with
        """
        def deep_update(d: Dict[str, Any], u: Dict[str, Any]) -> Dict[str, Any]:
            for k, v in u.items():
                if isinstance(v, dict) and k in d and isinstance(d[k], dict):
                    d[k] = deep_update(d[k], v)
                else:
                    d[k] = v
            return d
        
        self.config = deep_update(self.config, config) 