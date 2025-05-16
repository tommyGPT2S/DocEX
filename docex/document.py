from typing import Dict, Any, Optional, Union, List
from pathlib import Path
from datetime import datetime, UTC
import json

from docex.services.storage_service import StorageService
from docex.config.config_manager import ConfigManager
from docex.services.metadata_service import MetadataService
from docex.db.connection import Database
from docex.db.models import Operation
from docex.transport.models import RouteOperation
from sqlalchemy import text
from docex.models.document_metadata import DocumentMetadata as MetaModel

class Document:
    """Represents a document in DocFlow"""
    
    def __init__(
        self,
        id: int,
        name: str,
        path: str,
        content_type: str,
        document_type: str,
        size: int,
        checksum: str,
        status: str,
        created_at: datetime,
        updated_at: datetime,
        model: Any = None,  # Reference to database model
        storage_service: Optional[StorageService] = None  # Allow passing storage service directly
    ):
        self.id = id
        self.name = name
        self.path = path
        self.content_type = content_type
        self.document_type = document_type
        self.size = size
        self.checksum = checksum
        self.status = status
        self.created_at = created_at
        self.updated_at = updated_at
        self.model = model
        
        # Initialize storage service
        if storage_service:
            self.storage_service = storage_service
        elif model and model.basket:
            self.storage_service = StorageService(json.loads(model.basket.storage_config))
        else:
            # Fallback to default storage config
            config_manager = ConfigManager()
            self.storage_service = StorageService(config_manager.get_storage_config())
    
    @staticmethod
    def _get_content_static(document: 'Document', mode: str = 'bytes') -> Union[bytes, str, Dict[str, Any]]:
        """
        Get document content from storage
        
        Args:
            document: Document instance to get content from
            mode: Content mode ('bytes', 'text', or 'json')
                - 'bytes': Return raw bytes
                - 'text': Return decoded text
                - 'json': Return parsed JSON (if content is JSON)
        
        Returns:
            Document content in the requested format
        
        Raises:
            ValueError: If mode is invalid
            FileNotFoundError: If document content cannot be found
            json.JSONDecodeError: If mode is 'json' but content is not valid JSON
        """
        content = document.storage_service.retrieve_document(document.path)
        if content is None:
            raise FileNotFoundError(f"Document content not found at path: {document.path}")
        # If content is a file-like object, read it
        if hasattr(content, 'read'):
            content = content.read()
        if mode == 'bytes':
            if isinstance(content, bytes):
                return content
            return content.encode('utf-8')
        elif mode == 'text':
            if isinstance(content, str):
                return content
            return content.decode('utf-8')
        elif mode == 'json':
            if isinstance(content, dict):
                return content
            if isinstance(content, str):
                return json.loads(content)
            return json.loads(content.decode('utf-8'))
        else:
            raise ValueError(f"Invalid mode: {mode}. Must be one of: bytes, text, json")
    
    def get_content(self, mode: str = 'bytes') -> Union[bytes, str, Dict[str, Any]]:
        """Instance method version of get_content for compatibility."""
        return Document._get_content_static(self, mode)
    
    def get_details(self) -> Dict[str, Any]:
        """Get document details"""
        return {
            "id": self.id,
            "name": self.name,
            "path": self.path,
            "content_type": self.content_type,
            "document_type": self.document_type,
            "size": self.size,
            "checksum": self.checksum,
            "status": self.status,
            "created_at": self.created_at,
            "updated_at": self.updated_at
        }

    def get_metadata(self) -> Dict[str, MetaModel]:
        """Get all metadata for this document from the database as DocumentMetadata models."""
        db = Database()
        service = MetadataService(db)
        return service.get_metadata(self.id)

    def get_metadata_dict(self) -> Dict[str, Any]:
        """Get all metadata as a plain dict (for backward compatibility)."""
        meta = self.get_metadata()
        return {k: v.to_dict() for k, v in meta.items()}

    def create_operation(self, operation_type: str, status: str, details: Optional[Dict] = None) -> Any:
        """Create an operation record for this document."""
        db = Database()
        with db.transaction() as session:
            operation = Operation(
                document_id=self.id,
                operation_type=operation_type,
                status=status,
                details=details or {},
                created_at=datetime.now(UTC),
                completed_at=datetime.now(UTC)
            )
            session.add(operation)
            session.commit()
            session.refresh(operation)
            return operation

    def remove_from_basket(self) -> None:
        """Remove this document from its basket. This deletes the document from the database and cleans up its storage."""
        db = Database()
        with db.transaction() as session:
            if self.model:
                session.delete(self.model)
            else:
                session.execute(text("DELETE FROM document WHERE id = :id"), {"id": self.id})
            session.commit()
        # Optionally clean up storage if needed
        if hasattr(self, 'storage_service'):
            self.storage_service.delete_document(self.path)

    def get_operations(self) -> List[Dict[str, Any]]:
        """Retrieve all operations associated with this document from the database."""
        db = Database()
        with db.session() as session:
            operations = session.query(Operation).filter(Operation.document_id == self.id).all()
            return [{"type": op.operation_type, "status": op.status, "created_at": op.created_at, "completed_at": op.completed_at, "error": op.error, "details": op.details} for op in operations]

    def get_route_operations(self) -> List[Dict[str, Any]]:
        """Retrieve all route operations associated with this document from the database."""
        db = Database()
        with db.session() as session:
            route_operations = session.query(RouteOperation).filter(RouteOperation.document_id == self.id).all()
            return [{"type": op.operation_type, "status": op.status, "created_at": op.created_at, "completed_at": op.completed_at, "error": op.error, "details": op.details} for op in route_operations] 