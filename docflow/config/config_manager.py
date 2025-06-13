import os
import json
import logging
from typing import Dict, Any, Optional

# Configure logging
logger = logging.getLogger(__name__)

class ConfigManager:
    """
    Manages configuration for document baskets
    
    This class handles basket-specific configuration settings.
    It does not include database connection settings, which are managed by DocFlowConfig.
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        Initialize configuration manager
        
        Args:
            config: Optional initial configuration
        """
        self.config = config if config else {}
        logger.debug("Initialized ConfigManager")
    
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
        Get configuration value
        
        Args:
            key: Configuration key
            default: Default value if key not found
            
        Returns:
            Configuration value
        """
        return self.config.get(key, default)
    
    def set(self, key: str, value: Any) -> None:
        """
        Set configuration value
        
        Args:
            key: Configuration key
            value: Configuration value
        """
        self.config[key] = value
        logger.debug(f"Set configuration {key}={value}")
    
    def update(self, config: Dict[str, Any]) -> None:
        """
        Update configuration with new values
        
        Args:
            config: New configuration values
        """
        self.config.update(config)
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