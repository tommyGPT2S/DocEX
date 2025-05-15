"""
DocEX Configuration Management

This module provides configuration management for DocEX.
"""

import os
import json
import yaml
import logging
from typing import Dict, Any, Optional
from pathlib import Path

# Configure logging
logger = logging.getLogger(__name__)

class DocEXConfig:
    """
    Manages system-wide configuration for DocEX
    
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
            
            # Initialize configuration
            self.config: Dict[str, Any] = {}
            
            # Load default configuration from file
            default_config_path = Path(__file__).parent / 'default_config.yaml'
            with open(default_config_path, 'r') as f:
                self.config = yaml.safe_load(f)
            
            # Load configuration from file if it exists
            self.config_file = Path.home() / '.docex' / 'config.yaml'
            if self.config_file.exists():
                self._load_config()
            
            self.initialized = True
    
    @classmethod
    def from_file(cls, config_path: str) -> 'DocEXConfig':
        """Load configuration from file
        
        Args:
            config_path: Path to configuration file
            
        Returns:
            DocEXConfig instance
        """
        instance = cls()
        try:
            with open(config_path) as f:
                instance.config = yaml.safe_load(f)
        except Exception as e:
            instance.logger.error(f"Failed to load configuration from {config_path}: {str(e)}")
            raise
        return instance
    
    @classmethod
    def setup(cls, **kwargs) -> None:
        """
        Set up DocEX configuration
        
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
        
        # Deep update database configuration
        if 'database' in kwargs:
            instance._update_config_recursive(instance.config['database'], kwargs['database'])
        
        # Deep update logging configuration
        if 'logging' in kwargs:
            instance._update_config_recursive(instance.config['logging'], kwargs['logging'])
        
        # Ensure configuration directory exists
        config_dir = instance.config_file.parent
        config_dir.mkdir(parents=True, exist_ok=True)
        
        # Save configuration
        instance._save_config()
        
        instance.logger.info("DocEX configuration updated")
    
    def get(self, key: str, default: Any = None) -> Any:
        """Get configuration value
        
        Args:
            key: Configuration key (dot notation)
            default: Default value if key not found
            
        Returns:
            Configuration value
        """
        try:
            value = self.config
            for k in key.split('.'):
                value = value[k]
            return value
        except (KeyError, TypeError):
            return default
    
    def set(self, key: str, value: Any) -> None:
        """Set configuration value
        
        Args:
            key: Configuration key (dot notation)
            value: Configuration value
        """
        keys = key.split('.')
        config = self.config
        for k in keys[:-1]:
            if k not in config:
                config[k] = {}
            config = config[k]
        config[keys[-1]] = value
    
    def _load_config(self) -> None:
        """Load configuration from file"""
        try:
            if not self.config_file.exists():
                raise RuntimeError(f"Configuration file not found: {self.config_file}")
            
            try:
                with open(self.config_file, 'r') as f:
                    file_config = yaml.safe_load(f)
                    if file_config is None:
                        raise RuntimeError("Configuration file is empty")
                    self._update_config_recursive(self.config, file_config)
                    self.logger.info(f"Configuration loaded from {self.config_file}")
            except yaml.YAMLError as e:
                raise RuntimeError(f"Invalid YAML in configuration file: {str(e)}")
            except Exception as e:
                raise RuntimeError(f"Failed to read configuration file: {str(e)}")
            
            # Validate configuration
            self._validate_config()
            
        except Exception as e:
            self.logger.error(f"Failed to load configuration: {str(e)}")
            raise
    
    def _validate_config(self) -> None:
        """Validate configuration structure and values"""
        if not isinstance(self.config, dict):
            raise RuntimeError("Configuration must be a dictionary")
        
        # Validate required sections
        required_sections = ['database', 'storage', 'logging']
        for section in required_sections:
            if section not in self.config:
                raise RuntimeError(f"Missing required configuration section: {section}")
        
        # Validate database configuration
        db_config = self.config['database']
        if 'type' not in db_config:
            raise RuntimeError("Database type not specified")
        
        db_type = db_config['type']
        if db_type not in ['sqlite', 'postgresql']:
            raise RuntimeError(f"Unsupported database type: {db_type}")
        
        if db_type == 'sqlite':
            if 'path' not in db_config:
                raise RuntimeError("SQLite database path not specified")
        elif db_type == 'postgresql':
            required_fields = ['host', 'port', 'database', 'user', 'password']
            for field in required_fields:
                if field not in db_config:
                    raise RuntimeError(f"PostgreSQL {field} not specified")
    
    def _save_config(self) -> None:
        """Save configuration to file"""
        try:
            with open(self.config_file, 'w') as f:
                yaml.dump(self.config, f)
            self.logger.info(f"Configuration saved to {self.config_file}")
        except Exception as e:
            self.logger.error(f"Failed to save configuration: {str(e)}")
            raise
    
    def _update_config_recursive(self, base: Dict[str, Any], update: Dict[str, Any]) -> None:
        """Update configuration recursively"""
        for key, value in update.items():
            if isinstance(value, dict) and key in base and isinstance(base[key], dict):
                self._update_config_recursive(base[key], value)
            else:
                base[key] = value
    
    def get_database_config(self) -> Dict[str, Any]:
        """Get database configuration"""
        return self.config.get('database', {})
    
    def get_logging_config(self) -> Dict[str, Any]:
        """Get logging configuration"""
        return self.config.get('logging', {})
    
    def validate(self) -> bool:
        """Validate configuration"""
        try:
            self._validate_config()
            return True
        except Exception as e:
            self.logger.error(f"Configuration validation failed: {str(e)}")
            return False
    
    def get_all(self) -> Dict[str, Any]:
        """Get all configuration"""
        return self.config.copy()
    
    def update(self, config: Dict[str, Any]) -> None:
        """Update configuration
        
        Args:
            config: New configuration values
        """
        def deep_update(d: Dict[str, Any], u: Dict[str, Any]) -> Dict[str, Any]:
            for k, v in u.items():
                if isinstance(v, dict) and k in d and isinstance(d[k], dict):
                    d[k] = deep_update(d[k], v)
                else:
                    d[k] = v
            return d
        
        self.config = deep_update(self.config, config)
        self._save_config() 