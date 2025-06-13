from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, Union, BinaryIO, List
from pathlib import Path

class AbstractStorage(ABC):
    """
    Abstract base class for storage backends
    
    Defines the interface for document content storage.
    Implementations can use different storage mechanisms (filesystem, S3, etc.).
    """
    
    @abstractmethod
    def save(self, path: str, content: Union[str, Dict, bytes, BinaryIO]) -> None:
        """
        Save content to the specified path
        
        Args:
            path: Path to save the content to
            content: Content to save (string, dict, bytes, or file-like object)
        """
        pass
    
    @abstractmethod
    def load(self, path: str) -> Union[Dict, bytes]:
        """
        Load content from the specified path
        
        Args:
            path: Path to load the content from
            
        Returns:
            Content as a dictionary (for JSON) or bytes (for binary)
        """
        pass
    
    @abstractmethod
    def delete(self, path: str) -> bool:
        """
        Delete content at the specified path
        
        Args:
            path: Path to delete
            
        Returns:
            True if successful, False otherwise
        """
        pass
    
    @abstractmethod
    def exists(self, path: str) -> bool:
        """
        Check if content exists at the specified path
        
        Args:
            path: Path to check
            
        Returns:
            True if content exists, False otherwise
        """
        pass
    
    @abstractmethod
    def create_directory(self, path: str) -> bool:
        """
        Create a directory at the specified path
        
        Args:
            path: Path to create the directory at
            
        Returns:
            True if successful, False otherwise
        """
        pass
    
    @abstractmethod
    def list_directory(self, path: str) -> List[str]:
        """
        List contents of a directory
        
        Args:
            path: Path to list contents of
            
        Returns:
            List of paths in the directory
        """
        pass
    
    @abstractmethod
    def get_metadata(self, path: str) -> Dict[str, Any]:
        """
        Get metadata for a file
        
        Args:
            path: Path to get metadata for
            
        Returns:
            Dictionary of metadata
        """
        pass
    
    @abstractmethod
    def get_url(self, path: str, expires_in: Optional[int] = None) -> str:
        """
        Get a URL for accessing the file
        
        Args:
            path: Path to get URL for
            expires_in: Optional expiration time in seconds
            
        Returns:
            URL for accessing the file
        """
        pass
    
    @abstractmethod
    def copy(self, source_path: str, dest_path: str) -> bool:
        """
        Copy a file from source to destination
        
        Args:
            source_path: Source path
            dest_path: Destination path
            
        Returns:
            True if successful, False otherwise
        """
        pass
    
    @abstractmethod
    def move(self, source_path: str, dest_path: str) -> bool:
        """
        Move a file from source to destination
        
        Args:
            source_path: Source path
            dest_path: Destination path
            
        Returns:
            True if successful, False otherwise
        """
        pass

    @abstractmethod
    def store(self, path: str, content: Union[str, bytes, BinaryIO]) -> bool:
        """Store content at the specified path"""
        pass
    
    @abstractmethod
    def retrieve(self, path: str) -> Optional[Union[str, bytes]]:
        """Retrieve content from the specified path"""
        pass
    
    @abstractmethod
    def set_metadata(self, path: str, metadata: Dict[str, Any]) -> bool:
        """Set metadata for content at the specified path"""
        pass 