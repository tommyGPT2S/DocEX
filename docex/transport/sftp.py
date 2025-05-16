import os
import paramiko
from pathlib import Path
from typing import List, Optional
from datetime import datetime

from .base import BaseTransporter, TransportResult
from .config import SFTPTransportConfig, TransportType

class SFTPTransport(BaseTransporter):
    """SFTP transport implementation"""
    
    def __init__(self, config: SFTPTransportConfig):
        """Initialize SFTP transport
        
        Args:
            config: SFTP transport configuration
        """
        if config.type != TransportType.SFTP:
            raise ValueError("SFTPTransport requires SFTP transport type")
            
        super().__init__(config)
        self.config = config
        self._client: Optional[paramiko.SFTPClient] = None
        self._transport: Optional[paramiko.Transport] = None
        
    async def _connect(self) -> TransportResult:
        """Establish SFTP connection
        
        Returns:
            TransportResult indicating success/failure
        """
        try:
            if self._client and self._transport and self._transport.is_active():
                return TransportResult(success=True, message="Already connected")
                
            # Create transport
            self._transport = paramiko.Transport((self.config.host, self.config.port))
            
            # Connect with password or key
            if self.config.key_file:
                key = paramiko.RSAKey.from_private_key_file(self.config.key_file)
                self._transport.connect(username=self.config.username, pkey=key)
            else:
                self._transport.connect(username=self.config.username, password=self.config.password)
                
            # Create SFTP client
            self._client = paramiko.SFTPClient.from_transport(self._transport)
            
            # Ensure remote path exists
            try:
                self._client.stat(self.config.remote_path)
            except FileNotFoundError:
                self._client.mkdir(self.config.remote_path)
                
            return TransportResult(success=True, message="SFTP connection established")
            
        except Exception as e:
            return TransportResult(
                success=False,
                message=f"Failed to establish SFTP connection: {e}",
                error=e
            )
            
    async def _disconnect(self) -> None:
        """Close SFTP connection"""
        if self._client:
            self._client.close()
        if self._transport:
            self._transport.close()
        self._client = None
        self._transport = None
        
    async def upload(self, file_path: Path, destination_path: str) -> TransportResult:
        """Upload a file via SFTP
        
        Args:
            file_path: Path to local file to upload
            destination_path: Destination path relative to remote_path
            
        Returns:
            TransportResult indicating success/failure
        """
        if not file_path.exists():
            return TransportResult(
                success=False,
                message=f"Source file not found: {file_path}",
                error=FileNotFoundError(f"Source file not found: {file_path}")
            )
            
        # Connect if needed
        connect_result = await self._connect()
        if not connect_result.success:
            return connect_result
            
        try:
            # Ensure remote directory exists
            remote_dir = os.path.dirname(os.path.join(self.config.remote_path, destination_path))
            try:
                self._client.stat(remote_dir)
            except FileNotFoundError:
                self._client.mkdir(remote_dir)
                
            # Upload file
            remote_path = os.path.join(self.config.remote_path, destination_path)
            self._client.put(str(file_path), remote_path)
            
            return TransportResult(
                success=True,
                message=f"File uploaded to {remote_path}",
                details={"path": remote_path}
            )
            
        except Exception as e:
            return TransportResult(
                success=False,
                message=f"Failed to upload file: {e}",
                error=e
            )
            
    async def download(self, file_path: str, destination_path: Path) -> TransportResult:
        """Download a file via SFTP
        
        Args:
            file_path: Path to file in storage
            destination_path: Local path to save file to
            
        Returns:
            TransportResult indicating success/failure
        """
        # Connect if needed
        connect_result = await self._connect()
        if not connect_result.success:
            return connect_result
            
        try:
            remote_path = os.path.join(self.config.remote_path, file_path)
            
            # Check if file exists
            try:
                self._client.stat(remote_path)
            except FileNotFoundError:
                return TransportResult(
                    success=False,
                    message=f"File not found: {remote_path}",
                    error=FileNotFoundError(f"File not found: {remote_path}")
                )
                
            # Ensure local directory exists
            destination_path.parent.mkdir(parents=True, exist_ok=True)
            
            # Download file
            self._client.get(remote_path, str(destination_path))
            
            return TransportResult(
                success=True,
                message=f"File downloaded to {destination_path}",
                details={"path": str(destination_path)}
            )
            
        except Exception as e:
            return TransportResult(
                success=False,
                message=f"Failed to download file: {e}",
                error=e
            )
            
    async def list_files(self, path: str = "") -> TransportResult:
        """List files in SFTP storage
        
        Args:
            path: Path to list files from
            
        Returns:
            TransportResult containing list of files
        """
        # Connect if needed
        connect_result = await self._connect()
        if not connect_result.success:
            return connect_result
            
        try:
            remote_path = os.path.join(self.config.remote_path, path)
            
            # Check if path exists
            try:
                self._client.stat(remote_path)
            except FileNotFoundError:
                return TransportResult(
                    success=False,
                    message=f"Path not found: {remote_path}",
                    error=FileNotFoundError(f"Path not found: {remote_path}")
                )
                
            # List files
            files = []
            for item in self._client.listdir_attr(remote_path):
                full_path = os.path.join(remote_path, item.filename)
                relative_path = os.path.relpath(full_path, self.config.remote_path)
                
                files.append({
                    "name": item.filename,
                    "path": relative_path,
                    "is_dir": item.st_mode & 0o40000 != 0,
                    "size": item.st_size,
                    "modified": datetime.fromtimestamp(item.st_mtime)
                })
                
            return TransportResult(
                success=True,
                message=f"Found {len(files)} items in {path}",
                details={"files": files}
            )
            
        except Exception as e:
            return TransportResult(
                success=False,
                message=f"Failed to list files: {e}",
                error=e
            )
            
    async def delete(self, file_path: str) -> TransportResult:
        """Delete a file from SFTP storage
        
        Args:
            file_path: Path to file in storage
            
        Returns:
            TransportResult indicating success/failure
        """
        # Connect if needed
        connect_result = await self._connect()
        if not connect_result.success:
            return connect_result
            
        try:
            remote_path = os.path.join(self.config.remote_path, file_path)
            
            # Check if file exists
            try:
                stat = self._client.stat(remote_path)
            except FileNotFoundError:
                return TransportResult(
                    success=False,
                    message=f"File not found: {remote_path}",
                    error=FileNotFoundError(f"File not found: {remote_path}")
                )
                
            # Delete file or directory
            if stat.st_mode & 0o40000 != 0:  # Directory
                self._client.rmdir(remote_path)
            else:
                self._client.remove(remote_path)
                
            return TransportResult(
                success=True,
                message=f"Deleted {file_path}"
            )
            
        except Exception as e:
            return TransportResult(
                success=False,
                message=f"Failed to delete file: {e}",
                error=e
            )
            
    async def validate_connection(self) -> TransportResult:
        """Validate SFTP connection
        
        Returns:
            TransportResult indicating if connection is valid
        """
        try:
            # Try to connect
            connect_result = await self._connect()
            if not connect_result.success:
                return connect_result
                
            # Try to list root directory
            self._client.listdir(self.config.remote_path)
            
            return TransportResult(
                success=True,
                message="SFTP connection validated successfully"
            )
            
        except Exception as e:
            return TransportResult(
                success=False,
                message=f"Failed to validate SFTP connection: {e}",
                error=e
            )
            
    def __del__(self):
        """Clean up connections when object is destroyed"""
        if self._client or self._transport:
            self._disconnect() 