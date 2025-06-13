from typing import Type, TypeVar, Generic, Optional, List, Dict, Any
from datetime import datetime, timedelta
from uuid import uuid4
from sqlalchemy.orm import Session
from sqlalchemy import desc, asc, and_, or_, select, update, delete

from .models import (
    DocBasket, Document, FileHistory, Operation,
    OperationDependency, DocEvent, DocumentMetadata
)
from .connection import Database, Base

T = TypeVar('T', bound=Base)

class BaseRepository(Generic[T]):
    """Base repository class for common database operations"""
    
    def __init__(self, model_class: Type[T], db: Database):
        self.model_class = model_class
        self.db = db
    
    def create(self, data: Dict[str, Any]) -> T:
        """Create a new record"""
        with self.db.session() as session:
            instance = self.model_class(**data)
            session.add(instance)
            session.commit()
            session.refresh(instance)
            return instance
    
    def get(self, id: str) -> Optional[T]:
        """Get a record by ID"""
        with self.db.session() as session:
            return session.get(self.model_class, id)
    
    def update(self, id: str, data: Dict[str, Any]) -> Optional[T]:
        """Update a record"""
        with self.db.session() as session:
            instance = session.get(self.model_class, id)
            if instance:
                for key, value in data.items():
                    setattr(instance, key, value)
                session.commit()
                session.refresh(instance)
            return instance
    
    def delete(self, id: str) -> bool:
        """Delete a record"""
        with self.db.session() as session:
            instance = session.get(self.model_class, id)
            if instance:
                session.delete(instance)
                session.commit()
                return True
            return False
    
    def list(self, **filters) -> List[T]:
        """List records with optional filters"""
        with self.db.session() as session:
            query = select(self.model_class)
            for key, value in filters.items():
                query = query.where(getattr(self.model_class, key) == value)
            return list(session.execute(query).scalars())

class DocBasketRepository(BaseRepository[DocBasket]):
    """Repository for docbasket operations"""
    
    def __init__(self, db: Database):
        super().__init__(DocBasket, db)
    
    def get_by_name(self, name: str) -> Optional[DocBasket]:
        """Get a docbasket by name"""
        with self.db.session() as session:
            query = select(DocBasket).where(DocBasket.name == name)
            return session.execute(query).scalar_one_or_none()
    
    def get_active_baskets(self) -> List[DocBasket]:
        """Get all active docbaskets"""
        return self.list(status='active')

class DocumentRepository(BaseRepository[Document]):
    """Repository for document operations"""
    
    def __init__(self, db: Database):
        super().__init__(Document, db)
    
    def get_by_basket(self, basket_id: str) -> List[Document]:
        """Get all documents in a basket"""
        return self.list(basket_id=basket_id)
    
    def get_by_type(self, basket_id: str, document_type: str) -> List[Document]:
        """Get documents by type in a basket"""
        return self.list(basket_id=basket_id, document_type=document_type)
    
    def get_by_status(self, basket_id: str, status: str) -> List[Document]:
        """Get documents by status in a basket"""
        return self.list(basket_id=basket_id, status=status)
    
    def get_by_po(self, basket_id: str, po_number: str) -> List[Document]:
        """Get documents by PO number in a basket"""
        return self.list(basket_id=basket_id, related_po=po_number)

class FileHistoryRepository(BaseRepository[FileHistory]):
    """Repository for file history operations"""
    
    def __init__(self, db: Database):
        super().__init__(FileHistory, db)
    
    def get_by_document(self, document_id: str) -> List[FileHistory]:
        """Get file history for a document"""
        return self.list(document_id=document_id)

class OperationRepository(BaseRepository[Operation]):
    """Repository for operation operations"""
    
    def __init__(self, db: Database):
        super().__init__(Operation, db)
    
    def get_by_document(self, document_id: str) -> List[Operation]:
        """Get operations for a document"""
        return self.list(document_id=document_id)
    
    def get_latest_operation(self, document_id: str) -> Optional[Operation]:
        """Get the latest operation for a document"""
        with self.db.session() as session:
            query = (
                select(Operation)
                .where(Operation.document_id == document_id)
                .order_by(Operation.created_at.desc())
                .limit(1)
            )
            return session.execute(query).scalar_one_or_none()

class OperationDependencyRepository(BaseRepository[OperationDependency]):
    """Repository for operation dependency operations"""
    
    def __init__(self, db: Database):
        super().__init__(OperationDependency, db)
    
    def get_dependencies(self, operation_id: str) -> List[OperationDependency]:
        """Get dependencies for an operation"""
        return self.list(operation_id=operation_id)
    
    def get_dependents(self, operation_id: str) -> List[OperationDependency]:
        """Get operations that depend on this operation"""
        return self.list(depends_on=operation_id)

class DocumentMetadataRepository(BaseRepository[DocumentMetadata]):
    """Repository for document metadata operations"""
    
    def __init__(self, db: Database):
        super().__init__(DocumentMetadata, db)
    
    def get_by_document(self, document_id: str) -> List[DocumentMetadata]:
        """Get all metadata for a document"""
        return self.list(document_id=document_id)
    
    def get_by_key(self, document_id: str, key: str) -> Optional[DocumentMetadata]:
        """Get metadata by key for a document"""
        with self.db.session() as session:
            query = (
                select(DocumentMetadata)
                .where(
                    DocumentMetadata.document_id == document_id,
                    DocumentMetadata.key == key
                )
            )
            return session.execute(query).scalar_one_or_none()
    
    def get_by_type(self, document_id: str, metadata_type: str) -> List[DocumentMetadata]:
        """Get metadata by type for a document"""
        return self.list(document_id=document_id, metadata_type=metadata_type)

class DocEventRepository(BaseRepository[DocEvent]):
    """Repository for document event operations"""
    
    def __init__(self, db: Database):
        super().__init__(DocEvent, db)
    
    def get_pending_events(self, basket_id: str, batch_size: int = 50) -> List[DocEvent]:
        """Get pending events for a basket"""
        with self.db.session() as session:
            query = (
                select(DocEvent)
                .where(
                    DocEvent.basket_id == basket_id,
                    DocEvent.status == 'PENDING'
                )
                .order_by(DocEvent.event_timestamp.asc())
                .limit(batch_size)
            )
            return list(session.execute(query).scalars())
    
    def mark_processed(self, event_id: str) -> bool:
        """Mark an event as processed"""
        with self.db.session() as session:
            event = session.get(DocEvent, event_id)
            if event:
                event.status = 'PROCESSED'
                session.commit()
                return True
            return False
    
    def mark_failed(self, event_id: str, error_message: str) -> bool:
        """Mark an event as failed"""
        with self.db.session() as session:
            event = session.get(DocEvent, event_id)
            if event:
                event.status = 'FAILED'
                event.error_message = error_message
                session.commit()
                return True
            return False 