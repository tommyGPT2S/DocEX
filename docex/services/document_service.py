from typing import Optional, List, Dict, Any, Union
from datetime import datetime, timedelta, UTC
import hashlib
import json
from uuid import uuid4
from sqlalchemy import select
from pathlib import Path

from docex.db.connection import Database
from docex.db.models import Document as DocumentModel, DocBasket as DocBasketModel, FileHistory, Operation, DocumentMetadata, DocEvent
from docex.models.metadata_keys import MetadataKey

class DocumentService:
    """Service for managing documents and their operations"""
    
    def __init__(self, db: Database, basket_id: str):
        """
        Initialize the document service
        
        Args:
            db: Database instance
            basket_id: ID of the basket this service is operating on
        """
        self.db = db
        self.basket_id = basket_id
    
    def check_for_duplicates(self, source: str, checksum: str) -> Dict[str, Any]:
        """
        Check if a document with the same source and checksum already exists
        
        Args:
            source: Source of the document
            checksum: Checksum of the document
            
        Returns:
            Dictionary containing duplicate information
        """
        with self.db.transaction() as session:
            # Find documents with the same source and checksum
            document = session.execute(
                select(DocumentModel).where(
                    DocumentModel.source == source,
                    DocumentModel.checksum == checksum,
                    DocumentModel.status != 'DUPLICATE',
                    DocumentModel.basket_id == self.basket_id
                ).order_by(DocumentModel.created_at.desc()).limit(1)
            ).scalar_one_or_none()
            
            return {
                'is_duplicate': document is not None,
                'original_document_id': document.id if document else None,
                'original_document': document
            }
    
    def mark_as_duplicate(self, document_id: str, original_document_id: str) -> DocumentModel:
        """
        Mark a document as a duplicate of another document
        
        Args:
            document_id: ID of the document to mark as duplicate
            original_document_id: ID of the original document
            
        Returns:
            Updated Document instance
        """
        with self.db.transaction() as session:
            document = session.get(DocumentModel, document_id)
            if document:
                document.status = 'DUPLICATE'
                event = DocEvent(
                    basket_id=document.basket_id,
                    document_id=document_id,
                    event_type='DUPLICATE_DETECTED',
                    data={
                        'original_document_id': original_document_id
                    }
                )
                session.add(event)
                session.commit()
            return document
    
    def create_document(self, basket_id: str, document_type: str, source: str,
                       content: Dict[str, Any], raw_content: str, checksum: str,
                       metadata: Optional[Dict[str, Any]] = None) -> DocumentModel:
        """
        Create a new document
        
        Args:
            basket_id: Parent basket ID
            document_type: Document type
            source: Source file path
            content: Document content
            raw_content: Raw document content
            checksum: Document checksum
            metadata: Optional document metadata
            
        Returns:
            Created document instance
        """
        with self.db.transaction() as session:
            # Create document instance
            document = DocumentModel(
                basket_id=basket_id,
                document_type=document_type,
                source=source,
                content=content,
                raw_content=raw_content,
                checksum=checksum,
                status='RECEIVED',
                processing_attempts=0,
                created_at=datetime.now(UTC),
                updated_at=datetime.now(UTC)
            )
            
            session.add(document)
            session.flush()  # Ensure the document is in the session
            
            # Store document ID before committing
            doc_id = document.id
            
            session.commit()
            
            # Create a new document instance with the stored ID
            return DocumentModel(
                id=doc_id,
                basket_id=basket_id,
                document_type=document_type,
                source=source,
                content=content,
                raw_content=raw_content,
                checksum=checksum,
                status='RECEIVED',
                processing_attempts=0,
                created_at=datetime.now(UTC),
                updated_at=datetime.now(UTC)
            )
    
    def get_document(self, document_id: str) -> Optional[DocumentModel]:
        """
        Get a document by ID
        
        Args:
            document_id: Document ID
            
        Returns:
            Document instance or None if not found
        """
        with self.db.transaction() as session:
            return session.get(DocumentModel, document_id)
    
    def update_document(self, document_id: str, **kwargs) -> Optional[DocumentModel]:
        """
        Update document properties
        
        Args:
            document_id: Document ID
            **kwargs: Properties to update
            
        Returns:
            Updated document instance or None if not found
        """
        with self.db.transaction() as session:
            document = session.get(DocumentModel, document_id)
            if document:
                for key, value in kwargs.items():
                    setattr(document, key, value)
                document.updated_at = datetime.now(UTC)
                session.commit()
            return document
    
    def delete_document(self, document_id: str) -> bool:
        """
        Delete a document
        
        Args:
            document_id: Document ID
            
        Returns:
            True if deleted, False if not found
        """
        with self.db.transaction() as session:
            document = session.get(DocumentModel, document_id)
            if document:
                session.delete(document)
                session.commit()
                return True
            return False
    
    def list_documents(self, basket_id: str, status: Optional[str] = None) -> List[DocumentModel]:
        """
        List documents in a basket
        
        Args:
            basket_id: Parent basket ID
            status: Optional status filter
            
        Returns:
            List of document instances
        """
        with self.db.transaction() as session:
            query = select(DocumentModel).where(DocumentModel.basket_id == basket_id)
            if status:
                query = query.where(DocumentModel.status == status)
            return session.execute(query).scalars().all()
    
    def add_file_history(self, document_id: str, original_path: str, internal_path: str) -> FileHistory:
        """
        Add file history entry
        
        Args:
            document_id: Document ID
            original_path: Original file path
            internal_path: Internal storage path
            
        Returns:
            Created file history instance
        """
        with self.db.transaction() as session:
            history = FileHistory(
                document_id=document_id,
                original_path=original_path,
                internal_path=internal_path,
                created_at=datetime.now(UTC)
            )
            session.add(history)
            session.commit()
            return history
    
    def get_file_history(self, document_id: str) -> List[FileHistory]:
        """
        Get file history for a document
        
        Args:
            document_id: Document ID
            
        Returns:
            List of file history instances
        """
        with self.db.transaction() as session:
            query = select(FileHistory).where(FileHistory.document_id == document_id)
            return session.execute(query).scalars().all()
    
    def create_operation(self, document_id: str, operation_type: str,
                        status: str, details: Optional[Dict] = None) -> Operation:
        """
        Create a document operation
        
        Args:
            document_id: Document ID
            operation_type: Type of operation
            status: Operation status
            details: Optional operation details
            
        Returns:
            Created Operation instance
        """
        with self.db.transaction() as session:
            operation = Operation(
                id=f"id_{uuid4().hex}",
                document_id=document_id,
                operation_type=operation_type,
                status=status,
                details=details or {},
                created_at=datetime.now(UTC),
                completed_at=datetime.now(UTC)
            )
            session.add(operation)
            session.commit()
            return operation
    
    def set_document_metadata(self, document_id: str, key: Union[str, MetadataKey], value: Any,
                            metadata_type: str = 'custom') -> DocumentMetadata:
        """
        Set document metadata
        
        Args:
            document_id: Document ID
            key: Metadata key (string or MetadataKey enum)
            value: Metadata value
            metadata_type: Metadata type (default: 'custom')
            
        Returns:
            Created or updated DocumentMetadata instance
        """
        with self.db.transaction() as session:
            # Convert MetadataKey enum to string if needed
            if isinstance(key, MetadataKey):
                key = key.value
            
            # Check if metadata already exists
            existing = session.execute(
                select(DocumentMetadata).where(
                    DocumentMetadata.document_id == document_id,
                    DocumentMetadata.key == key
                )
            ).scalar_one_or_none()
            
            if existing:
                existing.value = value
                existing.metadata_type = metadata_type
                existing.updated_at = datetime.now(UTC)
                session.commit()
                return existing
            
            # Create new metadata
            metadata = DocumentMetadata(
                id=f"id_{uuid4().hex}",
                document_id=document_id,
                key=key,
                value=value,
                metadata_type=metadata_type,
                created_at=datetime.now(UTC),
                updated_at=datetime.now(UTC)
            )
            session.add(metadata)
            session.commit()
            return metadata
    
    def add_document(self, basket_model: DocBasketModel, file_path: str, metadata: Optional[Dict[str, Any]] = None) -> DocumentModel:
        """
        Add a document to a basket
        
        Args:
            basket_model: Parent basket model
            file_path: Path to the document file
            metadata: Optional document metadata
            
        Returns:
            Created document instance
        """
        # Read file content
        with open(file_path, 'rb') as f:
            content = f.read()
        
        # Calculate checksum
        checksum = hashlib.sha256(content).hexdigest()
        
        # Check for duplicates
        duplicate_info = self.check_for_duplicates(file_path, checksum)
        if duplicate_info['is_duplicate']:
            return duplicate_info['original_document']
        
        # Create document
        document = self.create_document(
            basket_id=basket_model.id,
            document_type='file',
            source=file_path,
            content={'path': file_path},
            raw_content=content.decode('utf-8'),
            checksum=checksum,
            metadata=metadata
        )
        
        # Add file history
        self.add_file_history(document.id, file_path, file_path)
        
        return document 