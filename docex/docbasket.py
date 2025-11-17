from typing import Optional, Dict, Any, Union, List
from pathlib import Path
from datetime import datetime, timedelta, timezone
import hashlib
from uuid import uuid4
import json
from sqlalchemy import cast, String, select, and_
import logging
import os
import shutil
import asyncio

from docex.db.connection import Database, get_base
from docex.db.models import Document as DocumentModel, DocBasket as DocBasketModel, DocEvent, Operation, DocumentMetadata, FileHistory, generate_id
from docex.services.docbasket_service import DocBasketService
from docex.services.document_service import DocumentService
from docex.storage.storage_factory import StorageFactory
from docex.config.config_manager import ConfigManager
from docex.models.metadata_keys import MetadataKey
from sqlalchemy import func
from docex.services.metadata_service import MetadataService
from docex.db.database_factory import DatabaseFactory
from docex.services.storage_service import StorageService
from docex.config.docex_config import DocEXConfig
from docex.transport.route import Route
from docex.transport.config import RouteConfig
from docex.transport.transport_result import TransportResult
from docex.document import Document
from docex.utils.file_utils import is_binary_file, get_content_type
from docex.models.document_metadata import DocumentMetadata as MetaModel

# Configure logging
logger = logging.getLogger(__name__)

class DocBasket:
    """
    Document basket for managing collections of documents
    
    A document basket is a container for related documents with its own storage configuration.
    The basket's storage configuration is stored in the database and cannot be changed after creation.
    Database connection is managed at the DocEX level and cannot be changed.
    """
    
    def __init__(
        self,
        id: int,
        name: str,
        description: Optional[str] = None,
        storage_config: Optional[Dict[str, Any]] = None,
        created_at: Optional[datetime] = None,
        updated_at: Optional[datetime] = None,
        model: Any = None,  # Reference to database model
        db: Optional[Database] = None  # Optional tenant-aware database instance
    ):
        """
        Initialize document basket
        
        Args:
            id: Basket ID
            name: Basket name
            description: Optional basket description
            storage_config: Optional storage configuration
            created_at: Creation timestamp
            updated_at: Last update timestamp
            model: Reference to database model
            db: Optional tenant-aware database instance (for multi-tenancy support)
        """
        self.id = id
        self.name = name
        self.description = description
        self.storage_config = storage_config or {}
        self.created_at = created_at
        self.updated_at = updated_at
        self.model = model
        
        # Initialize database connection - use provided db or create new one
        # If db is provided, it should be tenant-aware (from DocEX instance)
        self.db = db or Database()
        
        # Initialize storage service
        # Note: S3 storage initialization may fail if credentials are not available
        # This is acceptable when just listing baskets - storage will be initialized when actually used
        try:
            self.storage_service = StorageService(self.storage_config)
            self.storage_service.ensure_storage_exists()
        except Exception as e:
            # If storage initialization fails (e.g., S3 without credentials), log warning but continue
            # Storage will be re-initialized when actually needed
            logger.warning(f"Storage initialization failed for basket {self.name} (this is OK if just listing): {e}")
            # Create a minimal storage service that will fail gracefully when used
            self.storage_service = None
        
        # Initialize metadata service
        self.metadata_service = MetadataService(self.db)
    
    def get_basket_path(self) -> str:
        """
        Get the storage path for this basket
        
        Returns:
            Path where basket files are stored
        """
        # Get path from storage config
        return self.storage_config.get('path', '')
    
    @classmethod
    def create(cls, name: str, description: Optional[str] = None, storage_config: Optional[Dict[str, Any]] = None, db: Optional[Database] = None) -> 'DocBasket':
        """
        Create a new document basket
        
        Args:
            name: Basket name
            description: Optional basket description
            storage_config: Optional storage configuration
            
        Returns:
            Created basket
            
        Raises:
            ValueError: If a basket with the same name already exists
        """
        # Get config instance
        config = DocEXConfig()
        
        # Use default storage config if none provided
        if storage_config is None:
            storage_config = config.get('storage', {})
        
        # Ensure storage type is set
        if 'type' not in storage_config:
            storage_config['type'] = 'filesystem'
        
        # Create basket in database first to get the ID
        # Use provided db (tenant-aware) or create new one
        basket_db = db or Database()
        try:
            with basket_db.transaction() as session:
                # Check if basket with same name exists
                existing = session.execute(
                    select(DocBasketModel).where(DocBasketModel.name == name)
                ).scalars().first()
                
                if existing:
                    raise ValueError(f"A basket with name '{name}' already exists")
                
                # Create basket model with initial storage config
                basket_model = DocBasketModel(
                    name=name,
                    description=description,
                    storage_config='{}',  # Temporary empty config
                    status='active',
                    created_at=datetime.now(timezone.utc),
                    updated_at=datetime.now(timezone.utc)
                )
                session.add(basket_model)
                session.flush()  # Get the ID without committing
                
                # Now that we have the ID, set up the storage path/configuration
                if storage_config['type'] == 'filesystem':
                    if 'path' not in storage_config:
                        # Create basket-specific path under the default storage path using ID
                        base_path = config.get('storage.filesystem.path', 'storage/docex')
                        storage_config['path'] = str(Path(base_path) / f"basket_{basket_model.id}")
                elif storage_config['type'] == 's3':
                    # For S3, ensure s3 config is properly nested
                    if 's3' not in storage_config:
                        # If s3 config is at top level, move it under 's3' key
                        s3_config = {k: v for k, v in storage_config.items() if k != 'type'}
                        storage_config = {
                            'type': 's3',
                            's3': s3_config
                        }
                    # Add prefix for basket organization if not present
                    if 'prefix' not in storage_config.get('s3', {}):
                        storage_config['s3']['prefix'] = f"baskets/{basket_model.id}/"
                
                # Update the storage config
                basket_model.storage_config = json.dumps(storage_config)
                session.commit()  # Commit the transaction to ensure ID is persisted
                
                # Create storage service and ensure storage exists
                storage_service = StorageService(storage_config)
                storage_service.ensure_storage_exists()
                
                # Create the basket directory (only for filesystem)
                if storage_config['type'] == 'filesystem':
                    basket_path = Path(storage_config['path'])
                    basket_path.mkdir(parents=True, exist_ok=True)
                
                return cls(
                    id=basket_model.id,
                    name=basket_model.name,
                    description=basket_model.description,
                    storage_config=json.loads(basket_model.storage_config),
                    created_at=basket_model.created_at,
                    updated_at=basket_model.updated_at,
                    model=basket_model,
                    db=basket_db  # Pass tenant-aware database to basket instance
                )
        except Exception as e:
            # If any error occurs, rollback the transaction
            session.rollback()
            raise ValueError(f"Failed to create basket: {str(e)}")
    
    @classmethod
    def get(cls, basket_id: int, db: Optional[Database] = None) -> Optional['DocBasket']:
        """
        Get a document basket by ID
        
        Args:
            basket_id: Basket ID
            db: Optional tenant-aware database instance (for multi-tenancy support)
            
        Returns:
            Document basket or None if not found
        """
        basket_db = db or Database()
        with basket_db.session() as session:
            basket = session.get(DocBasketModel, basket_id)
            if basket is None:
                return None
            return cls(
                id=basket.id,
                name=basket.name,
                description=basket.description,
                storage_config=json.loads(basket.storage_config),
                created_at=basket.created_at,
                updated_at=basket.updated_at,
                model=basket,
                db=basket_db  # Pass tenant-aware database to basket instance
            )
    
    @classmethod
    def find_by_name(cls, name: str, db: Optional[Database] = None) -> Optional['DocBasket']:
        """
        Find a basket by name
        
        Args:
            name: Basket name
            db: Optional tenant-aware database instance (for multi-tenancy support)
            
        Returns:
            DocBasket instance or None if not found
        """
        basket_db = db or Database()
        with basket_db.session() as session:
            basket = session.execute(
                select(DocBasketModel).where(DocBasketModel.name == name)
            ).scalar_one_or_none()
            if basket is None:
                return None
            return cls(
                id=basket.id,
                name=basket.name,
                description=basket.description,
                storage_config=json.loads(basket.storage_config),
                created_at=basket.created_at,
                updated_at=basket.updated_at,
                model=basket,
                db=basket_db  # Pass tenant-aware database to basket instance
            )
    
    def find_documents_by_metadata(self, metadata: Union[Dict[str, Any], str]) -> List[Document]:
        """
        Find documents by metadata. Accepts either a dictionary of key-value pairs or a single string value.
        """
        with self.db.transaction() as session:
            query = select(DocumentModel).join(DocumentMetadata)
            
            if isinstance(metadata, dict):
                # Handle dictionary input
                for key, value in metadata.items():
                    if isinstance(value, MetaModel):
                        value = value.to_dict()
                    if isinstance(value, dict) and 'extra' in value:
                        value = value['extra'].get('value', None)
                    query = query.where(
                        DocumentMetadata.key == key,
                        DocumentMetadata.value == str(value)
                    )
            elif isinstance(metadata, str):
                # Handle string input (search across all metadata values)
                query = query.where(DocumentMetadata.value == metadata)
            else:
                raise ValueError("Metadata must be a dictionary or a string.")
            
            # Execute query
            documents = session.execute(query).scalars().all()
            return [Document(
                id=doc.id,
                name=doc.name,
                path=doc.path,
                content_type=doc.content_type,
                document_type=doc.document_type,
                size=doc.size,
                checksum=doc.checksum,
                status=doc.status,
                created_at=doc.created_at,
                updated_at=doc.updated_at,
                model=doc,
                storage_service=self.storage_service,
                db=self.db  # Pass tenant-aware database to document
            ) for doc in documents]
    
    @classmethod  
    def list(cls, db: Optional[Database] = None) -> List['DocBasket']:
        """
        List all document baskets (class method)
        
        Args:
            db: Optional tenant-aware database instance (for multi-tenancy support)
        
        Returns:
            List of document baskets
        """
        return cls._list_all_baskets(db=db)
    
    @classmethod
    def _list_all_baskets(cls, db: Optional[Database] = None) -> List['DocBasket']:
        """
        Internal method to list all document baskets (class method)
        This is separated to avoid name conflict with instance method list()
        
        Args:
            db: Optional tenant-aware database instance (for multi-tenancy support)
        
        Returns:
            List of document baskets
        """
        basket_db = db or Database()
        with basket_db.session() as session:
            baskets = session.execute(select(DocBasketModel)).scalars().all()
            return [cls(
                id=basket.id,
                name=basket.name,
                description=basket.description,
                storage_config=json.loads(basket.storage_config),
                created_at=basket.created_at,
                updated_at=basket.updated_at,
                model=basket,
                db=basket_db  # Pass tenant-aware database to basket instance
            ) for basket in baskets]
    
    def _get_content_type(self, file_path: Path) -> str:
        return get_content_type(file_path)

    def add(self, file_path: str, document_type: str = 'file', metadata: Optional[Dict[str, Any]] = None) -> Document:
        """
        Add a document to the basket
        
        Args:
            file_path: Path to the document
            document_type: Type of document (file, url, etc.)
            metadata: Optional metadata
            
        Returns:
            Document instance
        """
        # Use tenant-aware database from basket instance
        with self.db.session() as session:
            file_path = Path(file_path)
            if is_binary_file(file_path):
                content = file_path.read_bytes()
                checksum = hashlib.sha256(content).hexdigest()
                size = len(content)
                raw_content = content
            else:
                content = file_path.read_text()
                checksum = hashlib.sha256(content.encode()).hexdigest()
                size = len(content.encode())
                raw_content = content
            # Check for duplicates: same checksum AND same source/filename
            # This allows same file content with different names to be treated as different documents
            file_name = file_path.name if hasattr(file_path, 'name') else str(file_path)
            existing = session.execute(
                select(DocumentModel).where(
                    and_(
                        DocumentModel.basket_id == self.id,
                        DocumentModel.checksum == checksum,
                        DocumentModel.source == str(file_path)  # Also check source/filename
                    )
                )
            ).scalar_one_or_none()
            if existing:
                event = DocEvent(
                    basket_id=self.id,
                    document_id=existing.id,
                    event_type='DUPLICATE',
                    data={'source': str(file_path)}
                )
                session.add(event)
                session.commit()
                return Document(
                    id=existing.id,
                    name=existing.name,
                    path=existing.path,
                    content_type=existing.content_type,
                    document_type=existing.document_type,
                    size=existing.size,
                    checksum=existing.checksum,
                    status=existing.status,
                    created_at=existing.created_at,
                    updated_at=existing.updated_at,
                    model=existing,
                    storage_service=self.storage_service,
                    db=self.db  # Pass tenant-aware database to document
                )
            document = DocumentModel(
                basket_id=self.id,
                name=file_path.name,
                source=str(file_path),
                path='',
                document_type=document_type,
                content={'content': content if isinstance(content, str) else None},
                raw_content=raw_content if isinstance(raw_content, str) else None,
                content_type=self._get_content_type(file_path),
                size=size,
                checksum=checksum,
                status='RECEIVED'
            )
            session.add(document)
            session.flush()
            document_path = f"docex/basket_{self.id}/{document.id}"
            stored_path = self.storage_service.store_document(str(file_path), document_path)
            document.path = stored_path
            if metadata:
                # Store metadata in same session - serialize values to JSON
                import json
                for key, value in metadata.items():
                    # Serialize value to JSON string
                    try:
                        value_json = json.dumps(value, default=str)
                    except (TypeError, ValueError):
                        value_json = json.dumps(str(value))
                    meta = DocumentMetadata(
                        document_id=document.id,
                        key=key,
                        value=value_json,
                        created_at=datetime.now(timezone.utc),
                        updated_at=datetime.now(timezone.utc)
                    )
                    session.add(meta)
            operation = Operation(
                document_id=document.id,
                operation_type='ADD',
                status='success',
                details={
                    'source': str(file_path),
                    'stored_path': stored_path,
                    'document_type': document_type,
                    'size': size,
                    'checksum': checksum
                },
                created_at=datetime.now(timezone.utc),
                completed_at=datetime.now(timezone.utc)
            )
            session.add(operation)
            session.commit()
            return Document(
                id=document.id,
                name=document.name,
                path=document.path,
                content_type=document.content_type,
                document_type=document.document_type,
                size=document.size,
                checksum=document.checksum,
                status=document.status,
                created_at=document.created_at,
                updated_at=document.updated_at,
                model=document,
                storage_service=self.storage_service,
                db=self.db  # Pass tenant-aware database to document
            )
    
    def list_documents(self) -> List[Document]:
        """
        List all documents in this basket
        
        Returns:
            List of Document instances
        """
        with self.db.session() as session:
            documents = session.execute(
                select(DocumentModel).where(DocumentModel.basket_id == self.id)
            ).scalars().all()
            return [Document(
                id=doc.id,
                name=doc.name,
                path=doc.path,
                content_type=doc.content_type,
                document_type=doc.document_type,
                size=doc.size,
                checksum=doc.checksum,
                status=doc.status,
                created_at=doc.created_at,
                updated_at=doc.updated_at,
                model=doc,
                storage_service=self.storage_service,
                db=self.db  # Pass tenant-aware database to document
            ) for doc in documents]
    
    def list_documents(self) -> List[Document]:
        """
        List all documents in this basket
        
        Returns:
            List of Document instances
        """
        with self.db.session() as session:
            documents = session.execute(
                select(DocumentModel).where(DocumentModel.basket_id == self.id)
            ).scalars().all()
            return [Document(
                id=doc.id,
                name=doc.name,
                path=doc.path,
                content_type=doc.content_type,
                document_type=doc.document_type,
                size=doc.size,
                checksum=doc.checksum,
                status=doc.status,
                created_at=doc.created_at,
                updated_at=doc.updated_at,
                model=doc,
                storage_service=self.storage_service,
                db=self.db  # Pass tenant-aware database to document
            ) for doc in documents]
    
    # Instance method list() for listing documents - this shadows the classmethod
    # but Python's method resolution will use the classmethod when called on the class
    # and the instance method when called on an instance
    def list(self) -> List[Document]:
        """
        List all documents in this basket (alias for list_documents for backward compatibility)
        
        Note: This instance method shadows the classmethod list() that lists all baskets.
        When called on an instance (basket.list()), it lists documents.
        When called on the class (DocBasket.list()), it lists baskets.
        
        Returns:
            List of Document instances
        """
        return self.list_documents()
    
    def get_document(self, document_id: int) -> Optional[Document]:
        """
        Get a document by ID
        
        Args:
            document_id: Document ID
            
        Returns:
            Document or None if not found
        """
        with self.db.transaction() as session:
            document = session.get(DocumentModel, document_id)
            if document is None:
                return None
            return Document(
                id=document.id,
                name=document.name,
                path=document.path,
                content_type=document.content_type,
                document_type=document.document_type,
                size=document.size,
                checksum=document.checksum,
                status=document.status,
                created_at=document.created_at,
                updated_at=document.updated_at,
                model=document,
                storage_service=self.storage_service,
                db=self.db  # Pass tenant-aware database to document
            )
    
    def update_document(self, document_id: int, file_path: str) -> Document:
        """
        Update a document
        
        Args:
            document_id: Document ID
            file_path: Path to the new document file
            
        Returns:
            Updated document
        """
        with open(file_path, 'r') as f:
            raw_content = f.read()
            try:
                content = json.loads(raw_content)
            except json.JSONDecodeError:
                content = {"content": raw_content}
        checksum = hashlib.sha256(raw_content.encode()).hexdigest()
        with self.db.transaction() as session:
            document = session.get(DocumentModel, document_id)
            if document is None:
                raise ValueError(f"Document with ID {document_id} not found")
            document.name = Path(file_path).name
            document.source = str(file_path)
            document.content = content
            document.raw_content = raw_content
            document.checksum = checksum
            document.updated_at = datetime.now(timezone.utc)
            path = Path(file_path)
            metadata = {
                MetadataKey.ORIGINAL_PATH.value: str(file_path),
                MetadataKey.FILE_TYPE.value: path.suffix[1:] if path.suffix else "UNKNOWN",
                MetadataKey.FILE_SIZE.value: len(raw_content),
                MetadataKey.FILE_EXTENSION.value: path.suffix,
                MetadataKey.ORIGINAL_FILE_TIMESTAMP.value: datetime.fromtimestamp(path.stat().st_mtime).isoformat(),
                MetadataKey.CONTENT_CHECKSUM.value: checksum,
                MetadataKey.CONTENT_LENGTH.value: len(raw_content),
                MetadataKey.CONTENT_TYPE.value: self._get_content_type(path)
            }
            for key, value in metadata.items():
                doc_metadata = session.execute(
                    select(DocumentMetadata)
                    .where(
                        DocumentMetadata.document_id == document_id,
                        DocumentMetadata.key == key
                    )
                ).scalar_one_or_none()
                if doc_metadata:
                    doc_metadata.value = value
                    doc_metadata.updated_at = datetime.now(timezone.utc)
                else:
                    doc_metadata = DocumentMetadata(
                        document_id=document_id,
                        key=key,
                        value=value,
                        created_at=datetime.now(timezone.utc),
                        updated_at=datetime.now(timezone.utc)
                    )
                    session.add(doc_metadata)
            session.commit()
            return Document(
                id=document.id,
                name=document.name,
                path=document.path,
                content_type=document.content_type,
                document_type=document.document_type,
                size=document.size,
                checksum=document.checksum,
                status=document.status,
                created_at=document.created_at,
                updated_at=document.updated_at,
                model=document,
                storage_service=self.storage_service,
                db=self.db  # Pass tenant-aware database to document
            )
    
    def delete_document(self, document_id: int) -> None:
        """
        Delete a document
        
        Args:
            document_id: Document ID
        """
        with self.db.transaction() as session:
            document = session.get(DocumentModel, document_id)
            if document is None:
                raise ValueError(f"Document with ID {document_id} not found")
            session.delete(document)
            session.commit()
    
    def delete(self) -> None:
        """Delete the basket and all its documents"""
        # Use tenant-aware database from basket instance
        with self.db.session() as session:
            # Delete all documents
            documents = session.execute(
                select(DocumentModel).where(DocumentModel.basket_id == self.id)
            ).scalars().all()
            
            for doc in documents:
                session.delete(doc)
            
            # Delete basket record
            session.delete(self.model)
            session.commit()
            
            # Clean up storage
            self.storage_service.cleanup()
    
    def get_stats(self) -> Dict[str, Any]:
        """Get basket statistics"""
        db = Database()
        with db.transaction() as session:
            basket = session.get(DocBasketModel, self.id)
            if not basket:
                raise ValueError(f"Basket with ID {self.id} not found")
            
            # Get document counts by status and type
            doc_counts = session.execute(
                select(
                    DocumentModel.status,
                    DocumentModel.document_type,
                    func.count(DocumentModel.id)
                )
                .where(DocumentModel.basket_id == self.id)
                .group_by(DocumentModel.status, DocumentModel.document_type)
            ).all()
            
            # Organize counts
            status_counts = {}
            type_counts = {}
            for status, doc_type, count in doc_counts:
                status_counts[status] = status_counts.get(status, 0) + count
                type_counts[doc_type] = type_counts.get(doc_type, 0) + count
            
            return {
                'id': self.id,
                'name': self.name,
                'description': self.description,
                'status': basket.status,
                'document_counts': status_counts,
                'type_counts': type_counts,
                'created_at': basket.created_at,
                'updated_at': basket.updated_at
            }