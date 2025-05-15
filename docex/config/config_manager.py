"""
DocEX Configuration Manager

This module provides configuration management for DocEX baskets and components.
"""

import os
import json
import logging
from typing import Dict, Any, Optional

# Configure logging
logger = logging.getLogger(__name__)

class ConfigManager:
    """
    Manages configuration for DocEX baskets and components
    
    This class handles basket-specific and component-specific configuration settings.
    It does not include database connection settings, which are managed by DocEXConfig.
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        Initialize configuration manager
        
        Args:
            config: Optional initial configuration
        """
        self.config = config if config else {}
        logger.debug("Initialized DocEX ConfigManager")
    
    @classmethod
    def from_dict(cls, config: Optional[Dict[str, Any]] = None) -> 'ConfigManager':
        """
        Create a ConfigManager instance from a dictionary
        
        Args:
            config: Optional configuration dictionary
            
        Returns:
            ConfigManager instance
        """
        return cls(config)
    
    def to_dict(self) -> Dict[str, Any]:
        """
        Convert configuration to dictionary
        
        Returns:
            Configuration dictionary
        """
        return self.config.copy()
    
    def get(self, key: str, default: Any = None) -> Any:
        """
        Get configuration value using dot notation
        
        Args:
            key: Configuration key (e.g., 'storage.type')
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
        """
        Set configuration value using dot notation
        
        Args:
            key: Configuration key (e.g., 'storage.type')
            value: Configuration value
        """
        keys = key.split('.')
        config = self.config
        for k in keys[:-1]:
            if k not in config:
                config[k] = {}
            config = config[k]
        config[keys[-1]] = value
        logger.debug(f"Set configuration {key}={value}")
    
    def update(self, config: Dict[str, Any]) -> None:
        """
        Update configuration with new values
        
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
        logger.debug(f"Updated configuration with {config}")
    
    def get_storage_config(self) -> Dict[str, Any]:
        """
        Get storage configuration
        
        Returns:
            Storage configuration
        """
        return self.config.get('storage', {})
    
    def get_metadata_config(self) -> Dict[str, Any]:
        """
        Get metadata configuration
        
        Returns:
            Metadata configuration
        """
        return self.config.get('metadata', {})
    
    def get_document_config(self) -> Dict[str, Any]:
        """
        Get document configuration
        
        Returns:
            Document configuration
        """
        return self.config.get('document', {})
    
    def validate(self) -> bool:
        """
        Validate configuration
        
        Returns:
            True if configuration is valid
        """
        try:
            # Validate storage configuration
            storage_config = self.get_storage_config()
            if not storage_config:
                logger.warning("No storage configuration found")
                return False
            
            # Validate metadata configuration
            metadata_config = self.get_metadata_config()
            if not metadata_config:
                logger.warning("No metadata configuration found")
                return False
            
            # Validate document configuration
            document_config = self.get_document_config()
            if not document_config:
                logger.warning("No document configuration found")
                return False
            
            return True
        except Exception as e:
            logger.error(f"Configuration validation failed: {str(e)}")
            return False 