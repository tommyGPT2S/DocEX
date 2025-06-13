from dataclasses import dataclass
from typing import Optional, Dict, Any, List, Union
from pathlib import Path
from datetime import datetime, UTC
from uuid import uuid4

from .base import BaseTransporter, TransportResult
from .config import RouteConfig, OtherParty, TransportType, RouteMethod
from docflow.document import Document
from docflow.db.connection import Database
from docflow.transport.models import RouteOperation

@dataclass
class Route:
    """Represents a configured transport route with a specific purpose"""
    
    name: str
    route_id: str
    purpose: str
    protocol: str
    config: Dict[str, Any]
    transporter: BaseTransporter
    route_metadata: Dict[str, Any]
    tags: List[str]
    priority: int
    enabled: bool
    created_at: datetime
    updated_at: datetime
    can_upload: bool = False
    can_download: bool = False
    can_list: bool = False
    can_delete: bool = False
    other_party: Optional[OtherParty] = None  # The business entity this route connects to
    
    @classmethod
    def from_model(cls, model: 'Route') -> 'Route':
        """Create a route from a database model
        
        Args:
            model: Database route model
            
        Returns:
            Route instance with initialized transporter
        """
        from .transporter_factory import TransporterFactory
        from .config import RouteConfig, OtherParty
        
        # Create transport config based on protocol
        if model.protocol == TransportType.LOCAL:
            from .local import LocalTransportConfig
            transport_config = LocalTransportConfig(
                type=model.protocol,
                name=f"{model.name}_transport",
                base_path=model.config.get("base_path"),
                create_dirs=model.config.get("create_dirs", True)
            )
        else:
            transport_config = {
                "type": model.protocol,
                "name": f"{model.name}_transport",
                **model.config
            }
        
        # Create other party if available
        other_party = None
        if model.other_party_id:
            other_party = OtherParty(
                id=model.other_party_id,
                name=model.other_party_name,
                type=model.other_party_type
            )
        
        # Create route config
        route_config = RouteConfig(
            name=model.name,
            purpose=model.purpose,
            protocol=model.protocol,
            config=transport_config,
            can_upload=model.can_upload,
            can_download=model.can_download,
            can_list=model.can_list,
            can_delete=model.can_delete,
            enabled=model.enabled,
            other_party=other_party,
            metadata=model.route_metadata,
            tags=model.tags,
            priority=model.priority
        )
        
        # Create transporter and route instance
        transporter = TransporterFactory.create_transporter(transport_config)
        return cls.from_config(route_config, transporter)
    
    @classmethod
    def from_config(cls, config: RouteConfig, transporter: BaseTransporter) -> 'Route':
        """Create a route from configuration
        
        Args:
            config: Route configuration
            transporter: Configured transporter instance
            
        Returns:
            Route instance
        """
        return cls(
            name=config.name,
            route_id=f"rt_{uuid4().hex}",
            purpose=config.purpose,
            protocol=config.protocol,
            config=config.config.model_dump(),
            transporter=transporter,
            other_party=config.other_party,
            route_metadata=config.metadata,
            tags=config.tags,
            priority=config.priority,
            enabled=config.enabled,
            can_upload=config.can_upload,
            can_download=config.can_download,
            can_list=config.can_list,
            can_delete=config.can_delete,
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC)
        )
    
    async def upload_document(self, document: Document) -> TransportResult:
        """Upload a document via this route
        
        Args:
            document: Document to upload
            
        Returns:
            TransportResult indicating success/failure
        """
        if not self.enabled:
            return TransportResult(
                success=False,
                message=f"Route '{self.name}' is disabled",
                error=ValueError(f"Route '{self.name}' is disabled")
            )
            
        if not self.can_upload:
            return TransportResult(
                success=False,
                message=f"Route '{self.name}' does not allow uploads",
                error=ValueError(f"Route '{self.name}' does not allow uploads")
            )
            
        # Record operation start
        db = Database()
        operation_id = f"op_{uuid4().hex}"
        operation = RouteOperation(
            id=operation_id,
            route_id=self.route_id,
            operation_type=RouteMethod.UPLOAD,
            status="in_progress",
            document_id=document.id,
            details={
                "document_name": document.name,
                "document_source": document.model.source
            }
        )
        with db.session() as session:
            session.add(operation)
            session.commit()
            
        try:
            # Get document content from storage
            content = document.get_content()
            
            # If content is a dictionary with 'content' key, extract the actual content
            if isinstance(content, dict) and 'content' in content:
                content = content['content']
            
            # If content is a string or bytes, use document's source path from model
            if isinstance(content, (str, bytes)):
                content = Path(document.model.source)
            
            # Determine destination based on route configuration and document
            destination = self._get_destination(document)
            
            # Upload content
            result = await self.transporter.upload(content, destination)
            
            # Update operation status and document status
            with db.session() as session:
                # Get operation from database
                operation = session.query(RouteOperation).filter_by(id=operation_id).first()
                
                # Update operation status
                operation.status = "success" if result.success else "failed"
                operation.completed_at = datetime.now(UTC)
                if not result.success:
                    operation.error = str(result.error)
                operation.details.update({
                    "success": result.success,
                    "message": result.message,
                    "destination": destination
                })
                
                # Update document status if successful
                if result.success:
                    document.model.status = "SENT"
                    
                session.commit()
            
            # Record document operation if successful
            if result.success:
                document.create_operation(
                    operation_type="UPLOAD",
                    status="success",
                    details={
                        "route_name": self.name,
                        "destination": destination,
                        "route_operation_id": operation_id
                    }
                )
                
            return result
        except Exception as e:
            # Update operation status on error
            with db.session() as session:
                # Get operation from database
                operation = session.query(RouteOperation).filter_by(id=operation_id).first()
                
                # Update operation status
                operation.status = "failed"
                operation.completed_at = datetime.now(UTC)
                operation.error = str(e)
                session.commit()
                
            # Record document operation for failure
            document.create_operation(
                operation_type="UPLOAD",
                status="failed",
                details={
                    "route_name": self.name,
                    "error": str(e),
                    "route_operation_id": operation_id
                }
            )
            raise
    
    def _get_destination(self, document: Document) -> str:
        """Get destination path for document based on route configuration
        
        Args:
            document: Document to determine destination for
            
        Returns:
            Destination path relative to transporter's base path
        """
        # Just use the document name as the destination
        # The transporter will handle combining it with the base path
        return document.name
    
    async def upload(self, file_path: Union[Path, str], destination_path: str) -> TransportResult:
        """Upload a file via this route"""
        if not self.enabled:
            return TransportResult(
                success=False,
                message=f"Route '{self.name}' is disabled",
                error=ValueError(f"Route '{self.name}' is disabled")
            )
            
        if not self.can_upload:
            return TransportResult(
                success=False,
                message=f"Route '{self.name}' does not allow uploads",
                error=ValueError(f"Route '{self.name}' does not allow uploads")
            )
            
        return await self.transporter.upload(file_path, destination_path)
        
    async def download(self, file_path: str, destination_path: Path) -> TransportResult:
        """Download a file via this route"""
        if not self.enabled:
            return TransportResult(
                success=False,
                message=f"Route '{self.name}' is disabled",
                error=ValueError(f"Route '{self.name}' is disabled")
            )
            
        if not self.can_download:
            return TransportResult(
                success=False,
                message=f"Route '{self.name}' does not allow downloads",
                error=ValueError(f"Route '{self.name}' does not allow downloads")
            )
            
        # Record operation start
        db = Database()
        operation_id = f"op_{uuid4().hex}"
        operation = RouteOperation(
            id=operation_id,
            route_id=self.route_id,
            operation_type=RouteMethod.DOWNLOAD,
            status="in_progress",
            details={"file_path": file_path, "destination": str(destination_path)}
        )
        with db.session() as session:
            session.add(operation)
            session.commit()
            
        try:
            # Perform download
            result = await self.transporter.download(file_path, destination_path)
            
            # Update operation status
            with db.session() as session:
                # Get operation from database
                operation = session.query(RouteOperation).filter_by(id=operation_id).first()
                
                # Update operation status
                operation.status = "success" if result.success else "failed"
                operation.completed_at = datetime.now(UTC)
                if not result.success:
                    operation.error = str(result.error)
                operation.details.update({
                    "success": result.success,
                    "message": result.message
                })
                session.commit()
                
            return result
        except Exception as e:
            # Update operation status on error
            with db.session() as session:
                # Get operation from database
                operation = session.query(RouteOperation).filter_by(id=operation_id).first()
                
                # Update operation status
                operation.status = "failed"
                operation.completed_at = datetime.now(UTC)
                operation.error = str(e)
                session.commit()
            raise
        
    async def list_files(self, path: str = "") -> TransportResult:
        """List files available via this route"""
        if not self.enabled:
            return TransportResult(
                success=False,
                message=f"Route '{self.name}' is disabled",
                error=ValueError(f"Route '{self.name}' is disabled")
            )
            
        if not self.can_list:
            return TransportResult(
                success=False,
                message=f"Route '{self.name}' does not allow listing files",
                error=ValueError(f"Route '{self.name}' does not allow listing files")
            )
            
        return await self.transporter.list_files(path)
        
    async def delete(self, file_path: str) -> TransportResult:
        """Delete a file via this route"""
        if not self.enabled:
            return TransportResult(
                success=False,
                message=f"Route '{self.name}' is disabled",
                error=ValueError(f"Route '{self.name}' is disabled")
            )
            
        if not self.can_delete:
            return TransportResult(
                success=False,
                message=f"Route '{self.name}' does not allow file deletion",
                error=ValueError(f"Route '{self.name}' does not allow file deletion")
            )
            
        return await self.transporter.delete(file_path)
        
    async def validate(self) -> TransportResult:
        """Validate the route connection"""
        if not self.enabled:
            return TransportResult(
                success=False,
                message=f"Route '{self.name}' is disabled",
                error=ValueError(f"Route '{self.name}' is disabled")
            )
        return await self.transporter.validate_connection()
        
    def to_dict(self) -> Dict[str, Any]:
        """Convert route to dictionary"""
        return {
            "name": self.name,
            "route_id": self.route_id,
            "purpose": self.purpose,
            "protocol": self.protocol,
            "config": self.config,
            "other_party": self.other_party.model_dump() if self.other_party else None,
            "route_metadata": self.route_metadata,
            "tags": self.tags,
            "priority": self.priority,
            "enabled": self.enabled,
            "can_upload": self.can_upload,
            "can_download": self.can_download,
            "can_list": self.can_list,
            "can_delete": self.can_delete,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat()
        } 