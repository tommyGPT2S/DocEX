import os
import json
import shutil
from typing import Dict, Any, Optional, Union, BinaryIO, List
from pathlib import Path
from datetime import datetime

from .abstract_storage import AbstractStorage

class FileSystemStorage(AbstractStorage):
    """
    File system implementation of the storage backend
    
    Stores document content in the local file system.
    """
    
    def __init__(self, config: Dict[str, Any]):
        """
        Initialize filesystem storage
        
        Args:
            config: Storage configuration dictionary with at least:
                   - path: Base path for storage
        """
        self.config = config
        self.base_path = Path(config.get('path', 'storage'))
        self.ensure_storage_exists()
    
    def ensure_storage_exists(self) -> None:
        """Ensure storage directory exists"""
        self.base_path.mkdir(parents=True, exist_ok=True)
    
    def get_path(self, key: str) -> Path:
        """
        Get full path for a storage key
        
        Args:
            key: Storage key
            
        Returns:
            Full path
        """
        return self.base_path / key
    
    def save(self, key: str, content: BinaryIO) -> None:
        """
        Save content to storage
        
        Args:
            key: Storage key
            content: Content to save
        """
        path = self.get_path(key)
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open('wb') as f:
            f.write(content.read())
    
    def load(self, key: str) -> Optional[BinaryIO]:
        """
        Load content from storage
        
        Args:
            key: Storage key
            
        Returns:
            Content as binary stream or None if not found
        """
        path = self.get_path(key)
        if not path.exists():
            return None
        return path.open('rb')
    
    def delete(self, key: str) -> None:
        """
        Delete content from storage
        
        Args:
            key: Storage key
        """
        path = self.get_path(key)
        if path.exists():
            path.unlink()
    
    def cleanup(self) -> None:
        """Clean up storage"""
        if self.base_path.exists():
            import shutil
            shutil.rmtree(self.base_path)
    
    def _get_full_path(self, path: str) -> Path:
        """
        Get the full path for a given relative path
        
        Args:
            path: Relative path
            
        Returns:
            Full path as Path object
        """
        return self.base_path / path
    
    def exists(self, path: str) -> bool:
        """
        Check if content exists at the specified path
        
        Args:
            path: Path to check
            
        Returns:
            True if content exists, False otherwise
        """
        return self._get_full_path(path).exists()
    
    def create_directory(self, path: str) -> bool:
        """
        Create a directory at the specified path
        
        Args:
            path: Path to create the directory at
            
        Returns:
            True if successful, False otherwise
        """
        try:
            self._get_full_path(path).mkdir(parents=True, exist_ok=True)
            return True
        except Exception:
            return False
    
    def list_directory(self, path: str) -> List[str]:
        """
        List contents of a directory
        
        Args:
            path: Path to list contents of
            
        Returns:
            List of paths in the directory
        """
        full_path = self._get_full_path(path)
        
        if not full_path.exists() or not full_path.is_dir():
            return []
        
        return [str(p.relative_to(self.base_path)) for p in full_path.iterdir()]
    
    def get_metadata(self, path: str) -> Dict[str, Any]:
        """
        Get metadata for a file
        
        Args:
            path: Path to get metadata for
            
        Returns:
            Dictionary of metadata
        """
        full_path = self._get_full_path(path)
        
        if not full_path.exists():
            raise FileNotFoundError(f"File not found: {path}")
        
        stat = full_path.stat()
        return {
            'size': stat.st_size,
            'created_at': datetime.fromtimestamp(stat.st_ctime),
            'modified_at': datetime.fromtimestamp(stat.st_mtime),
            'is_file': full_path.is_file(),
            'is_dir': full_path.is_dir()
        }
    
    def get_url(self, path: str, expires_in: Optional[int] = None) -> str:
        """
        Get a URL for accessing the file
        
        Args:
            path: Path to get URL for
            expires_in: Optional expiration time in seconds (ignored for filesystem)
            
        Returns:
            URL for accessing the file
        """
        return f"file://{self._get_full_path(path)}"
    
    def copy(self, source_path: str, dest_path: str) -> bool:
        """
        Copy a file from source to destination
        
        Args:
            source_path: Source path
            dest_path: Destination path
            
        Returns:
            True if successful, False otherwise
        """
        try:
            source = self._get_full_path(source_path)
            dest = self._get_full_path(dest_path)
            
            if source.is_file():
                shutil.copy2(source, dest)
            else:
                shutil.copytree(source, dest)
            return True
        except Exception:
            return False
    
    def move(self, source_path: str, dest_path: str) -> bool:
        """
        Move a file from source to destination
        
        Args:
            source_path: Source path
            dest_path: Destination path
            
        Returns:
            True if successful, False otherwise
        """
        try:
            source = self._get_full_path(source_path)
            dest = self._get_full_path(dest_path)
            
            shutil.move(source, dest)
            return True
        except Exception:
            return False

    def store(self, source_path: str, document_path: str) -> str:
        """
        Store a document
        
        Args:
            source_path: Path to source document
            document_path: Path relative to storage root (self.base_path)
        
        Returns:
            Path where document was stored (relative to self.base_path)
        """
        source_path = Path(source_path)
        dest_path = self.base_path / document_path  # Store under self.base_path
        dest_path.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source_path, dest_path)
        return str(dest_path.relative_to(self.base_path))
    
    def retrieve(self, path: str) -> Optional[Union[str, bytes]]:
        """
        Retrieve content from the specified path
        
        Args:
            path: Path to retrieve content from
            
        Returns:
            Content as string or bytes, or None if not found
        """
        try:
            return self.load(path)
        except FileNotFoundError:
            return None
    
    def set_metadata(self, path: str, metadata: Dict[str, Any]) -> bool:
        """
        Set metadata for content at the specified path
        
        Args:
            path: Path to set metadata for
            metadata: Dictionary of metadata to set
            
        Returns:
            True if successful, False otherwise
        """
        try:
            full_path = self._get_full_path(path)
            metadata_path = full_path.with_suffix(full_path.suffix + '.meta')
            
            with open(metadata_path, 'w') as f:
                json.dump(metadata, f, indent=2)
            return True
        except Exception:
            return False 