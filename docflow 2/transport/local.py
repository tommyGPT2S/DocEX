import os
import shutil
from pathlib import Path
from typing import List

from .base import BaseTransporter, TransportResult
from .config import LocalTransportConfig, TransportType

class LocalTransport(BaseTransporter):
    """Local filesystem transport implementation"""
    
    def __init__(self, config: LocalTransportConfig):
        """Initialize local transport
        
        Args:
            config: Local transport configuration
        """
        if config.type != TransportType.LOCAL:
            raise ValueError("LocalTransport requires LOCAL transport type")
            
        super().__init__(config)
        self.config = config
        
        # Create base path directory if it doesn't exist
        if self.config.create_dirs:
            os.makedirs(self.config.base_path, exist_ok=True)
            
    async def upload(self, file_path: Path, destination_path: str) -> TransportResult:
        """Upload a file to local storage
        
        Args:
            file_path: Path to local file to upload
            destination_path: Destination path relative to base_path
            
        Returns:
            TransportResult indicating success/failure
        """
        if not file_path.exists():
            return TransportResult(
                success=False,
                message=f"Source file not found: {file_path}",
                error=FileNotFoundError(f"Source file not found: {file_path}")
            )
            
        full_dest_path = Path(self.config.base_path) / destination_path
        full_dest_path.parent.mkdir(parents=True, exist_ok=True)
        
        try:
            shutil.copy2(file_path, full_dest_path)
            return TransportResult(
                success=True,
                message=f"File uploaded to {full_dest_path}",
                details={"path": str(full_dest_path)}
            )
        except OSError as e:
            return TransportResult(
                success=False,
                message=f"Failed to upload file: {e}",
                error=e
            )
            
    async def download(self, file_path: str, destination_path: Path) -> TransportResult:
        """Download a file from local storage
        
        Args:
            file_path: Path to file in storage
            destination_path: Local path to save file to
            
        Returns:
            TransportResult indicating success/failure
        """
        source_path = Path(self.config.base_path) / file_path
        
        if not source_path.exists():
            return TransportResult(
                success=False,
                message=f"File not found: {source_path}",
                error=FileNotFoundError(f"File not found: {source_path}")
            )
            
        try:
            destination_path.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source_path, destination_path)
            return TransportResult(
                success=True,
                message=f"File downloaded to {destination_path}",
                details={"path": str(destination_path)}
            )
        except OSError as e:
            return TransportResult(
                success=False,
                message=f"Failed to download file: {e}",
                error=e
            )
            
    async def list_files(self, path: str = "") -> TransportResult:
        """List files in local storage
        
        Args:
            path: Path to list files from
            
        Returns:
            TransportResult containing list of files
        """
        try:
            full_path = Path(self.config.base_path) / path
            if not full_path.exists():
                return TransportResult(
                    success=False,
                    message=f"Path not found: {full_path}",
                    error=FileNotFoundError(f"Path not found: {full_path}")
                )
                
            files = []
            for item in full_path.iterdir():
                files.append({
                    "name": item.name,
                    "path": str(item.relative_to(self.config.base_path)),
                    "is_dir": item.is_dir(),
                    "size": item.stat().st_size if item.is_file() else 0
                })
                
            return TransportResult(
                success=True,
                message=f"Found {len(files)} items in {path}",
                details={"files": files}
            )
        except OSError as e:
            return TransportResult(
                success=False,
                message=f"Failed to list files: {e}",
                error=e
            )
            
    async def delete(self, file_path: str) -> TransportResult:
        """Delete a file from local storage
        
        Args:
            file_path: Path to file in storage
            
        Returns:
            TransportResult indicating success/failure
        """
        full_path = Path(self.config.base_path) / file_path
        
        if not full_path.exists():
            return TransportResult(
                success=False,
                message=f"File not found: {full_path}",
                error=FileNotFoundError(f"File not found: {full_path}")
            )
            
        try:
            if full_path.is_file():
                full_path.unlink()
            else:
                shutil.rmtree(full_path)
                
            return TransportResult(
                success=True,
                message=f"Deleted {file_path}"
            )
        except OSError as e:
            return TransportResult(
                success=False,
                message=f"Failed to delete file: {e}",
                error=e
            )
            
    async def validate_connection(self) -> TransportResult:
        """Validate local storage connection
        
        Returns:
            TransportResult indicating if connection is valid
        """
        try:
            if not os.path.exists(self.config.base_path):
                if self.config.create_dirs:
                    os.makedirs(self.config.base_path, exist_ok=True)
                else:
                    return TransportResult(
                        success=False,
                        message=f"Base path does not exist: {self.config.base_path}",
                        error=FileNotFoundError(f"Base path does not exist: {self.config.base_path}")
                    )
                    
            # Test write access
            test_file = Path(self.config.base_path) / ".test"
            test_file.touch()
            test_file.unlink()
            
            return TransportResult(
                success=True,
                message="Local storage connection validated successfully"
            )
        except OSError as e:
            return TransportResult(
                success=False,
                message=f"Failed to validate local storage: {e}",
                error=e
            ) 