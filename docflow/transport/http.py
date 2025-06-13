import os
import aiohttp
from pathlib import Path
from typing import Dict, Any, Optional
from urllib.parse import urljoin

from .base import BaseTransporter, TransportResult
from .config import HTTPTransportConfig, TransportType

class HTTPTransport(BaseTransporter):
    """HTTP transport implementation"""
    
    def __init__(self, config: HTTPTransportConfig):
        """Initialize HTTP transport
        
        Args:
            config: HTTP transport configuration
        """
        if config.type != TransportType.HTTP:
            raise ValueError("HTTPTransport requires HTTP transport type")
            
        super().__init__(config)
        self.config = config
        self._session: Optional[aiohttp.ClientSession] = None
        
    async def _get_session(self) -> aiohttp.ClientSession:
        """Get or create HTTP session
        
        Returns:
            Active HTTP session
        """
        if not self._session or self._session.closed:
            # Create session with auth if configured
            auth = None
            if self.config.auth:
                auth = aiohttp.BasicAuth(
                    self.config.auth.get("username", ""),
                    self.config.auth.get("password", "")
                )
                
            self._session = aiohttp.ClientSession(
                auth=auth,
                headers=self.config.headers,
                verify_ssl=self.config.verify_ssl
            )
            
        return self._session
        
    async def _close_session(self) -> None:
        """Close HTTP session"""
        if self._session and not self._session.closed:
            await self._session.close()
        self._session = None
        
    async def upload(self, file_path: Path, destination_path: str) -> TransportResult:
        """Upload a file via HTTP
        
        Args:
            file_path: Path to local file to upload
            destination_path: Destination path relative to endpoint
            
        Returns:
            TransportResult indicating success/failure
        """
        if not file_path.exists():
            return TransportResult(
                success=False,
                message=f"Source file not found: {file_path}",
                error=FileNotFoundError(f"Source file not found: {file_path}")
            )
            
        try:
            session = await self._get_session()
            url = urljoin(self.config.endpoint, destination_path)
            
            # Prepare multipart form data
            data = aiohttp.FormData()
            data.add_field(
                'file',
                open(file_path, 'rb'),
                filename=file_path.name,
                content_type='application/octet-stream'
            )
            
            # Upload file
            async with session.post(url, data=data) as response:
                if response.status >= 400:
                    return TransportResult(
                        success=False,
                        message=f"HTTP error {response.status}: {await response.text()}",
                        error=Exception(f"HTTP error {response.status}")
                    )
                    
                return TransportResult(
                    success=True,
                    message=f"File uploaded to {url}",
                    details={"url": url, "status": response.status}
                )
                
        except Exception as e:
            return TransportResult(
                success=False,
                message=f"Failed to upload file: {e}",
                error=e
            )
            
    async def download(self, file_path: str, destination_path: Path) -> TransportResult:
        """Download a file via HTTP
        
        Args:
            file_path: Path to file in storage
            destination_path: Local path to save file to
            
        Returns:
            TransportResult indicating success/failure
        """
        try:
            session = await self._get_session()
            url = urljoin(self.config.endpoint, file_path)
            
            # Download file
            async with session.get(url) as response:
                if response.status >= 400:
                    return TransportResult(
                        success=False,
                        message=f"HTTP error {response.status}: {await response.text()}",
                        error=Exception(f"HTTP error {response.status}")
                    )
                    
                # Ensure local directory exists
                destination_path.parent.mkdir(parents=True, exist_ok=True)
                
                # Save file
                with open(destination_path, 'wb') as f:
                    f.write(await response.read())
                    
                return TransportResult(
                    success=True,
                    message=f"File downloaded to {destination_path}",
                    details={"path": str(destination_path), "status": response.status}
                )
                
        except Exception as e:
            return TransportResult(
                success=False,
                message=f"Failed to download file: {e}",
                error=e
            )
            
    async def list_files(self, path: str = "") -> TransportResult:
        """List files in HTTP storage
        
        Args:
            path: Path to list files from
            
        Returns:
            TransportResult containing list of files
        """
        try:
            session = await self._get_session()
            url = urljoin(self.config.endpoint, path)
            
            # List files (assuming API returns JSON list)
            async with session.get(url) as response:
                if response.status >= 400:
                    return TransportResult(
                        success=False,
                        message=f"HTTP error {response.status}: {await response.text()}",
                        error=Exception(f"HTTP error {response.status}")
                    )
                    
                files = await response.json()
                
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
        """Delete a file from HTTP storage
        
        Args:
            file_path: Path to file in storage
            
        Returns:
            TransportResult indicating success/failure
        """
        try:
            session = await self._get_session()
            url = urljoin(self.config.endpoint, file_path)
            
            # Delete file
            async with session.delete(url) as response:
                if response.status >= 400:
                    return TransportResult(
                        success=False,
                        message=f"HTTP error {response.status}: {await response.text()}",
                        error=Exception(f"HTTP error {response.status}")
                    )
                    
                return TransportResult(
                    success=True,
                    message=f"Deleted {file_path}",
                    details={"status": response.status}
                )
                
        except Exception as e:
            return TransportResult(
                success=False,
                message=f"Failed to delete file: {e}",
                error=e
            )
            
    async def validate_connection(self) -> TransportResult:
        """Validate HTTP connection
        
        Returns:
            TransportResult indicating if connection is valid
        """
        try:
            session = await self._get_session()
            
            # Try to connect to endpoint
            async with session.get(self.config.endpoint) as response:
                if response.status >= 400:
                    return TransportResult(
                        success=False,
                        message=f"HTTP error {response.status}: {await response.text()}",
                        error=Exception(f"HTTP error {response.status}")
                    )
                    
                return TransportResult(
                    success=True,
                    message="HTTP connection validated successfully",
                    details={"status": response.status}
                )
                
        except Exception as e:
            return TransportResult(
                success=False,
                message=f"Failed to validate HTTP connection: {e}",
                error=e
            )
            
    def __del__(self):
        """Clean up session when object is destroyed"""
        if self._session and not self._session.closed:
            self._close_session() 