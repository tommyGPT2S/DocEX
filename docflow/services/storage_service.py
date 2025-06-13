import logging
from pathlib import Path
from typing import Dict, Any, Optional
from docflow.storage.storage_factory import StorageFactory
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
        storage_settings = storage_config.get(storage_type, {})
        
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
        
        logger.info(f"Initialized storage service with type: {storage_type}")
        self.storage = StorageFactory.create_storage(config)
    
    def store_document(self, source_path: str, document_id: str) -> str:
        """
        Store a document
        
        Args:
            source_path: Path to source document
            document_id: Document ID
            
        Returns:
            Path where document was stored
        """
        # Store the document in the basket's storage
        stored_path = self.storage.store(source_path, document_id)
        
        # Return the relative path from the basket's storage root
        return stored_path
    
    def retrieve_document(self, document_id: str) -> str:
        """
        Retrieve a document
        
        Args:
            document_id: Document ID
            
        Returns:
            Path to retrieved document
        """
        return self.storage.retrieve(document_id)
    
    def delete_document(self, document_id: str) -> None:
        """
        Delete a document
        
        Args:
            document_id: Document ID
        """
        self.storage.delete(document_id)
    
    def get_storage_path(self) -> str:
        """
        Get storage path
        
        Returns:
            Storage path
        """
        return self.storage.config['path']
    
    def ensure_storage_exists(self) -> None:
        """
        Ensure storage directory exists
        """
        self.storage.ensure_storage_exists()
    
    def cleanup(self) -> None:
        """
        Clean up storage resources
        
        This method should be called when a basket is deleted to clean up any associated storage resources.
        """
        self.storage.cleanup() 