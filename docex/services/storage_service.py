import logging
from pathlib import Path
from typing import Dict, Any, Optional
from docex.storage.storage_factory import StorageFactory
import shutil

logger = logging.getLogger(__name__)

class StorageService:
    """
    Service for handling document storage operations
    
    This service manages document storage using the configured storage type
    (e.g., filesystem, S3) for a specific basket.
    """
    
    def __init__(self, storage_config: Dict[str, Any]):
        """
        Initialize storage service
        
        Args:
            storage_config: Storage configuration
        """
        # Extract storage type and settings
        storage_type = storage_config.get('type', 'filesystem')

        # Check if config has flattened params (preferred) or nested format
        flattened_params = {k: v for k, v in storage_config.items()
                          if k not in ['type', storage_type] and v is not None}

        if storage_type in storage_config and isinstance(storage_config[storage_type], dict):
            # Nested format exists, merge with flattened params (flattened takes precedence)
            nested_params = storage_config[storage_type]
            storage_settings = {**nested_params, **flattened_params}
        else:
            # Only flattened format available
            storage_settings = flattened_params
        
        # Create storage config with type and settings
        config = {
            'type': storage_type,
            **storage_settings
        }
        
        # Ensure path is set for filesystem storage
        if storage_type == 'filesystem':
            if 'path' not in config:
                config['path'] = 'storage'
            # Convert path to absolute if relative
            config['path'] = str(Path(config['path']).resolve())
        
        # Validate S3 configuration
        elif storage_type == 's3':
            if 'bucket' not in config:
                raise ValueError("S3 storage requires 'bucket' in configuration")
            # Optional: validate bucket name format
            bucket_name = config['bucket']
            if not bucket_name or len(bucket_name) < 3 or len(bucket_name) > 63:
                raise ValueError(f"Invalid S3 bucket name: {bucket_name}")
        
        logger.info(f"Initialized storage service with type: {storage_type}")
        self.storage = StorageFactory.create_storage(config)
    
    def store_document(self, source_path: str, full_document_path: str) -> str:
        """
        Store a document using full path.
        
        All operations center around document_id and basket_id - full paths
        should be built by DocEXPathBuilder before calling this method.
        
        Args:
            source_path: Path to source document file
            full_document_path: Full storage path (built from basket_id and document_id)
            
        Returns:
            Full path where document was stored (same as full_document_path)
        """
        # Store the document in the basket's storage using full path
        stored_path = self.storage.store(source_path, full_document_path)
        
        # Return the full path (storage backends now receive full paths)
        return stored_path
    
    def retrieve_document(self, full_document_path: str) -> str:
        """
        Retrieve a document using full path.
        
        All operations center around document_id and basket_id - full paths
        should be built by DocEXPathBuilder before calling this method.
        
        Args:
            full_document_path: Full storage path (built from basket_id and document_id)
            
        Returns:
            Retrieved document content
        """
        return self.storage.retrieve(full_document_path)
    
    def delete_document(self, full_document_path: str) -> None:
        """
        Delete a document using full path.
        
        All operations center around document_id and basket_id - full paths
        should be built by DocEXPathBuilder before calling this method.
        
        Args:
            full_document_path: Full storage path (built from basket_id and document_id)
        """
        self.storage.delete(full_document_path)
    
    def get_storage_path(self) -> str:
        """
        Get storage path
        
        Returns:
            Storage path (for filesystem) or bucket name (for S3)
        """
        if hasattr(self.storage, 'config') and 'path' in self.storage.config:
            return self.storage.config['path']
        elif hasattr(self.storage, 'bucket'):
            # For S3 storage, return bucket name
            return self.storage.bucket
        else:
            return ''
    
    def ensure_storage_exists(self) -> None:
        """
        Ensure storage directory exists
        """
        self.storage.ensure_storage_exists()
    
    def cleanup(self, prefix: str) -> None:
        """
        Clean up storage resources using prefix built from IDs.
        
        All operations center around basket_id and document_id - prefix should be
        built by DocEXPathBuilder before calling this method.
        
        Args:
            prefix: Full storage prefix path (built from basket_id using DocEXPathBuilder)
        """
        self.storage.cleanup(prefix) 