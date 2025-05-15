from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Optional, Dict, Any, BinaryIO
from pathlib import Path

from .config import TransportConfig

@dataclass
class TransportResult:
    """Result of a DocEX transport operation"""
    success: bool
    message: str
    details: Optional[Dict[str, Any]] = None
    error: Optional[Exception] = None

class BaseTransporter(ABC):
    """Base class for all DocEX transport implementations"""
    
    def __init__(self, config: TransportConfig):
        """Initialize transport with configuration"""
        self.config = config
        
    @abstractmethod
    async def upload(self, file_path: Path, destination_path: str) -> TransportResult:
        """Upload a file to storage
        
        Args:
            file_path: Path to local file to upload
            destination_path: Destination path in storage
            
        Returns:
            TransportResult indicating success/failure
        """
        pass
        
    @abstractmethod
    async def download(self, file_path: str, destination_path: Path) -> TransportResult:
        """Download a file from storage
        
        Args:
            file_path: Path to file in storage
            destination_path: Local path to save file to
            
        Returns:
            TransportResult indicating success/failure
        """
        pass
        
    @abstractmethod
    async def list_files(self, path: str = "") -> TransportResult:
        """List files in storage
        
        Args:
            path: Path to list files from
            
        Returns:
            TransportResult containing list of files
        """
        pass
        
    @abstractmethod
    async def delete(self, file_path: str) -> TransportResult:
        """Delete a file from storage
        
        Args:
            file_path: Path to file in storage
            
        Returns:
            TransportResult indicating success/failure
        """
        pass
        
    @abstractmethod
    async def validate_connection(self) -> TransportResult:
        """Validate the transport connection
        
        Returns:
            TransportResult indicating if connection is valid
        """
        pass 