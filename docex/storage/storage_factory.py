from typing import Dict, Optional, Any
import importlib
from pathlib import Path

from .abstract_storage import AbstractStorage
from .filesystem_storage import FileSystemStorage

# Optional S3 storage - only available if boto3 is installed
try:
    from .s3_storage import S3Storage
    HAS_S3 = True
except ImportError:
    S3Storage = None
    HAS_S3 = False

class StorageFactory:
    """
    Factory for creating storage backends
    
    Creates and configures the appropriate storage backend based on configuration.
    """
    
    _storage_classes = {
        'filesystem': FileSystemStorage,
    }
    
    # Register S3 storage if available (at class level)
    if HAS_S3 and S3Storage:
        _storage_classes['s3'] = S3Storage
    
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
            
        Raises:
            ValueError: If storage type is unknown or required dependencies are missing
        """
        storage_type = config.get('type', 'filesystem')
        
        # Register S3 if available (check at runtime)
        if storage_type == 's3' and not HAS_S3:
            raise ValueError(
                "S3 storage requires 'boto3' package. "
                "Install it with: pip install docex[storage-s3]"
            )
        
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