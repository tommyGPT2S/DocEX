from typing import Dict, Optional, Any
import importlib
from pathlib import Path

from .abstract_storage import AbstractStorage
from .filesystem_storage import FileSystemStorage
from .s3_storage import S3Storage

class StorageFactory:
    """
    Factory for creating storage backends
    
    Creates and configures the appropriate storage backend based on configuration.
    """
    
    _storage_classes = {
        'filesystem': FileSystemStorage,
        's3': S3Storage,
        # Add other storage backends here as they are implemented
    }
    
    @classmethod
    def register_storage(cls, name: str, storage_class: type) -> None:
        """
        Register a new storage backend
        
        Args:
            name: Name of the storage backend
            storage_class: Class implementing the storage backend
        """
        if not issubclass(storage_class, AbstractStorage):
            raise ValueError(f"Storage class must inherit from AbstractStorage")
        cls._storage_classes[name.lower()] = storage_class
    
    @classmethod
    def create_storage(cls, config: Dict[str, Any]) -> AbstractStorage:
        """
        Create a storage backend based on configuration
        
        Args:
            config: Storage configuration dictionary with at least:
                   - type: Type of storage backend
                   - Other configuration specific to the storage backend
                   
        Returns:
            Configured storage backend instance
        """
        storage_type = config.get('type', 'filesystem')
        
        if storage_type not in cls._storage_classes:
            raise ValueError(f"Unknown storage type: {storage_type}")
        
        storage_class = cls._storage_classes[storage_type]
        return storage_class(config)
    
    @classmethod
    def get_available_storages(cls) -> Dict[str, type]:
        """
        Get all available storage backends
        
        Returns:
            Dictionary mapping storage type names to their classes
        """
        return cls._storage_classes.copy() 