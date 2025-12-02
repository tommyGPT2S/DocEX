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
        Get full path for a storage key with path traversal protection
        
        Args:
            key: Storage key
            
        Returns:
            Full path
            
        Raises:
            ValueError: If path traversal is detected or key is invalid
        """
        if not key:
            raise ValueError("Storage key cannot be empty")
        
        # Prevent path traversal attacks before normalization
        # Check for .. sequences in the original key
        if '..' in key or os.path.isabs(key):
            raise ValueError(f"Invalid storage key: {key} - path traversal detected")
        
        # Normalize the path to resolve any relative components
        normalized_key = os.path.normpath(key)
        
        # Double-check after normalization (in case normalization changed something)
        if normalized_key.startswith('..') or os.path.isabs(normalized_key):
            raise ValueError(f"Invalid storage key: {key} - path traversal detected")
        
        # Build the full path
        full_path = (self.base_path / normalized_key).resolve()
        
        # Ensure the resolved path is still within base_path to prevent directory traversal
        try:
            full_path.relative_to(self.base_path.resolve())
        except ValueError:
            raise ValueError(f"Invalid storage key: {key} - path outside storage directory")
        
        return full_path
    
    def save(self, key: str, content: BinaryIO) -> None:
        """
        Save content to storage
        
        Args:
            key: Storage key
            content: Content to save
            
        Raises:
            ValueError: If path traversal is detected or key is invalid
        """
        # get_path() now includes path traversal protection
        path = self.get_path(key)
        
        # Check for symlinks in the path and parent directories to prevent symlink attacks
        current_path = path
        while current_path != self.base_path and current_path != current_path.parent:
            if current_path.exists() and current_path.is_symlink():
                raise ValueError(f"Invalid storage key: {key} - symlinks not allowed in path")
            current_path = current_path.parent
        
        path.parent.mkdir(parents=True, exist_ok=True)
        
        # Check if final path is a symlink
        if path.exists() and path.is_symlink():
            raise ValueError(f"Invalid storage key: {key} - symlinks not allowed")
        
        # Use atomic write to prevent race conditions
        temp_path = path.with_suffix(path.suffix + '.tmp')
        try:
            with temp_path.open('wb') as f:
                f.write(content.read())
            # Atomic move operation
            temp_path.replace(path)
        except Exception as e:
            # Clean up temp file on error
            if temp_path.exists():
                temp_path.unlink()
            raise
    
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
        Get the full path for a given relative path with path traversal protection
        
        Args:
            path: Relative path
            
        Returns:
            Full path as Path object
            
        Raises:
            ValueError: If path traversal is detected or path is invalid
        """
        if not path:
            raise ValueError("Path cannot be empty")
        
        # Prevent path traversal attacks before normalization
        # Check for .. sequences in the original path
        if '..' in path or os.path.isabs(path):
            raise ValueError(f"Invalid path: {path} - path traversal detected")
        
        # Normalize the path to resolve any relative components
        normalized_path = os.path.normpath(path)
        
        # Double-check after normalization
        if normalized_path.startswith('..') or os.path.isabs(normalized_path):
            raise ValueError(f"Invalid path: {path} - path traversal detected")
        
        # Build the full path
        full_path = (self.base_path / normalized_path).resolve()
        
        # Ensure the resolved path is still within base_path to prevent directory traversal
        try:
            full_path.relative_to(self.base_path.resolve())
        except ValueError:
            raise ValueError(f"Invalid path: {path} - path outside storage directory")
        
        return full_path
    
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
            
        Raises:
            ValueError: If path traversal is detected or path is invalid
        """
        source_path = Path(source_path)
        
        # Validate source path exists and is a file
        if not source_path.exists():
            raise FileNotFoundError(f"Source file not found: {source_path}")
        if not source_path.is_file():
            raise ValueError(f"Source path is not a file: {source_path}")
        
        # Use _get_full_path() which includes path traversal protection
        dest_path = self._get_full_path(document_path)
        
        # Check for symlinks in the destination path and parent directories
        current_path = dest_path
        while current_path != self.base_path and current_path != current_path.parent:
            if current_path.exists() and current_path.is_symlink():
                raise ValueError(f"Invalid document_path: {document_path} - symlinks not allowed in path")
            current_path = current_path.parent
        
        # Check if final destination path is a symlink
        if dest_path.exists() and dest_path.is_symlink():
            raise ValueError(f"Invalid document_path: {document_path} - symlinks not allowed")
        
        # Ensure source and destination are different files
        if source_path.resolve() == dest_path.resolve():
            raise ValueError(f"Source and destination paths are the same: {source_path}")
        
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