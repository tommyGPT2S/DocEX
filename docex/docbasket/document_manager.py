"""
Document Manager for DocBasket

This module provides document CRUD operations for DocBasket.
All document-related operations are centralized here for better maintainability.
"""

from __future__ import annotations

import hashlib
import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import TYPE_CHECKING, Any, Dict, List, Optional, Union

from sqlalchemy import and_, func, select

from docex.db.models import (
    DocEvent,
    DocumentMetadata,
    Operation,
)
from docex.db.models import (
    Document as DocumentModel,
)
from docex.models.document_metadata import DocumentMetadata as MetaModel
from docex.models.metadata_keys import MetadataKey
from docex.utils.file_utils import is_binary_file

if TYPE_CHECKING:
    from docex.docbasket import DocBasket
    from docex.document import Document

# Avoid circular import - import Document lazily when needed
def _get_document_class():
    """Lazy import of Document to avoid circular imports"""
    from docex.document import Document
    return Document

logger = logging.getLogger(__name__)


class DocBasketDocumentManager:
    """
    Manager class for document operations in DocBasket.
    
    This class encapsulates all document CRUD operations to keep the main
    DocBasket class focused on basket-level operations.
    """
    
    def __init__(self, basket: DocBasket):
        """
        Initialize document manager with reference to parent basket.
        
        Args:
            basket: DocBasket instance that owns this manager
        """
        self.basket = basket

    def _document_instance(self, document: DocumentModel) -> Document:
        """Build a runtime Document with lazy storage initialization."""
        Document = _get_document_class()
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
            storage_config=self.basket.storage_config,
            db=self.basket.db,
        )

    def _serialize_metadata_value(self, value: Any) -> str:
        """Serialize metadata values the same way the write path stores them."""
        if isinstance(value, MetaModel):
            value = value.to_dict()
        if isinstance(value, dict) and 'extra' in value:
            value = value['extra'].get('value', None)
        try:
            return json.dumps(value, default=str)
        except (TypeError, ValueError):
            return json.dumps(str(value))

    def _apply_metadata_filter(
        self,
        query: Any,
        metadata: Union[Dict[str, Any], str],
    ) -> Any:
        """Apply metadata filtering to a base document query."""
        if isinstance(metadata, dict):
            metadata_filters = []
            for key, value in metadata.items():
                value_json = self._serialize_metadata_value(value)
                subquery = select(DocumentMetadata.document_id).where(
                    and_(
                        DocumentMetadata.key == key,
                        DocumentMetadata.value == value_json,
                        DocumentMetadata.document_id.in_(
                            select(DocumentModel.id).where(
                                DocumentModel.basket_id == self.basket.id
                            )
                        ),
                    )
                )
                metadata_filters.append(subquery)
            if not metadata_filters:
                return None

            base_subquery = metadata_filters[0]
            for subquery in metadata_filters[1:]:
                base_subquery = base_subquery.intersect(subquery)
            return query.where(DocumentModel.id.in_(base_subquery))

        if isinstance(metadata, str):
            search_value_json = json.dumps(metadata)
            query = query.join(
                DocumentMetadata,
                DocumentMetadata.document_id == DocumentModel.id,
            )
            return query.where(DocumentMetadata.value == search_value_json).distinct()

        raise ValueError("Metadata must be a dictionary or a string.")
    
    
    def add(
        self, 
        file_path: str, 
        document_type: str = 'file', 
        metadata: Optional[Dict[str, Any]] = None
    ) -> Document:
        """
        Add a document to the basket.
        
        Args:
            file_path: Path to the document
            document_type: Type of document (file, url, etc.)
            metadata: Optional metadata
            
        Returns:
            Document instance
        """
        # Use tenant-aware database from basket instance
        with self.basket.db.session() as session:
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
            existing = session.execute(
                select(DocumentModel).where(
                    and_(
                        DocumentModel.basket_id == self.basket.id,
                        DocumentModel.checksum == checksum,
                        DocumentModel.source == str(file_path)  # Also check source/filename
                    )
                )
            ).scalar_one_or_none()
            
            if existing:
                event = DocEvent(
                    basket_id=self.basket.id,
                    document_id=existing.id,
                    event_type='DUPLICATE',
                    data={'source': str(file_path)}
                )
                session.add(event)
                session.commit()
                return self._document_instance(existing)
            
            # Generate the correct readable name using path helper
            readable_name = self.basket.path_helper.get_readable_document_name(
                document=None, 
                file_path=str(file_path), 
                metadata=metadata
            )
            document_filename = f"{readable_name}{Path(str(file_path)).suffix}"

            document = DocumentModel(
                basket_id=self.basket.id,
                name=document_filename,  # Use the correct readable filename
                source=str(file_path),
                path='',
                document_type=document_type,
                content={'content': content if isinstance(content, str) else None},
                raw_content=raw_content if isinstance(raw_content, str) else None,
                content_type=self.basket.path_helper.get_content_type(Path(file_path)),
                size=size,
                checksum=checksum,
                status='RECEIVED'
            )
            session.add(document)
            session.flush()
            
            # Build full path from IDs using path helper (for storage operations)
            # Full path = Part A (config) + Part B (basket) + Part C (document)
            full_path = self.basket.path_helper.build_document_path(document, str(file_path), metadata)
            
            # Update document name to reflect the correct readable name
            # This ensures the document record shows the right filename
            readable_name = self.basket.path_helper.get_readable_document_name(document, str(file_path), metadata)
            document.name = f"{readable_name}{Path(str(file_path)).suffix}"
            
            # Store document using full path (built from IDs)
            # StorageService expects full paths for storage operations
            stored_path = self.basket.storage_service.store_document(str(file_path), full_path)
            
            # Store full path in document.path for consistency and simplicity
            # For S3: Full path = Part A (config) + Part B (basket) + Part C (document)
            # For filesystem: Full relative path = Part B (basket) + Part C (document)
            # This avoids reconstruction logic and ensures consistency
            document.path = stored_path
            
            logger.debug(f"DocBasketDocumentManager.add: Stored full path in document.path: '{stored_path}'")

            # Update document name to reflect the correct readable name
            # This ensures the document record shows the right filename
            readable_name = self.basket.path_helper.get_readable_document_name(document, str(file_path), metadata)
            document.name = f"{readable_name}{Path(str(file_path)).suffix}"

            # Prepare metadata with original filename
            if metadata is None:
                metadata = {}
            # Store the original filename for future reference
            # If not provided in metadata, use the file_path name
            if 'original_filename' not in metadata:
                original_filename = file_path.name if hasattr(file_path, 'name') else str(file_path)
                metadata['original_filename'] = original_filename

            if metadata:
                # Store metadata in same session - serialize values to JSON
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
            
            return self._document_instance(document)
    
    def list_documents(
        self,
        limit: Optional[int] = None,
        offset: Optional[int] = None,
        order_by: Optional[str] = None,
        order_desc: bool = False,
        status: Optional[str] = None,
        document_type: Optional[str] = None
    ) -> List[Document]:
        """
        List documents in this basket with pagination, sorting, and filtering.
        Optimized for large datasets using indexed queries.
        
        Args:
            limit: Maximum number of results to return (for pagination)
            offset: Number of results to skip (for pagination)
            order_by: Field to sort by ('created_at', 'updated_at', 'name', 'size', 'status')
            order_desc: If True, sort in descending order
            status: Optional filter by document status
            document_type: Optional filter by document type
            
        Returns:
            List of Document instances
        """
        with self.basket.db.session() as session:
            query = select(DocumentModel).where(DocumentModel.basket_id == self.basket.id)
            
            # Add filters
            if status:
                query = query.where(DocumentModel.status == status)
            if document_type:
                query = query.where(DocumentModel.document_type == document_type)
            
            # Add sorting
            if order_by:
                order_field = getattr(DocumentModel, order_by, None)
                if order_field is not None:
                    if order_desc:
                        query = query.order_by(order_field.desc())
                    else:
                        query = query.order_by(order_field.asc())
                else:
                    logger.warning(f"Invalid order_by field: {order_by}, using default")
                    query = query.order_by(DocumentModel.created_at.desc())
            else:
                # Default sorting by creation date (newest first)
                query = query.order_by(DocumentModel.created_at.desc())
            
            # Add pagination
            if limit is not None:
                query = query.limit(limit)
            if offset is not None:
                query = query.offset(offset)
            
            documents = session.execute(query).scalars().all()
            
            # document.path already contains the full path (no reconstruction needed)
            return [self._document_instance(doc) for doc in documents]
    
    def list_documents_with_metadata(
        self,
        columns: Optional[List[str]] = None,
        filters: Optional[Dict[str, Any]] = None,
        limit: Optional[int] = None,
        offset: Optional[int] = None,
        order_by: Optional[str] = None,
        order_desc: bool = False
    ) -> List[Dict[str, Any]]:
        """
        Efficiently list documents with selected metadata columns.
        
        This method returns lightweight dictionaries instead of full Document instances,
        avoiding N+1 queries and object instantiation overhead.
        
        Args:
            columns: List of column names to include in results. 
                    Default: ['id', 'name', 'document_type', 'status', 'size', 'created_at']
                    Available: 'id', 'name', 'path', 'document_type', 'content_type', 
                              'size', 'checksum', 'status', 'created_at', 'updated_at'
            filters: Optional dictionary of filters (e.g., {'document_type': 'invoice', 'status': 'RECEIVED'})
            limit: Maximum number of results to return (for pagination)
            offset: Number of results to skip (for pagination)
            order_by: Field to sort by ('created_at', 'updated_at', 'name', 'size', 'status')
            order_desc: If True, sort in descending order
            
        Returns:
            List of dictionaries containing selected document fields
            
        Example:
            >>> documents = basket.list_documents_with_metadata(
            ...     columns=['id', 'name', 'document_type', 'created_at'],
            ...     filters={'document_type': 'invoice'},
            ...     limit=100
            ... )
            >>> # Returns:
            >>> # [
            >>> #     {'id': 'doc_123', 'name': 'invoice_001.pdf', 'document_type': 'invoice', 'created_at': datetime(...)},
            >>> #     ...
            >>> # ]
        """
        # Default columns if not specified
        if columns is None:
            columns = ['id', 'name', 'document_type', 'status', 'size', 'created_at']
        
        # Map column names to model attributes
        column_map = {
            'id': DocumentModel.id,
            'name': DocumentModel.name,
            'path': DocumentModel.path,
            'document_type': DocumentModel.document_type,
            'content_type': DocumentModel.content_type,
            'size': DocumentModel.size,
            'checksum': DocumentModel.checksum,
            'status': DocumentModel.status,
            'created_at': DocumentModel.created_at,
            'updated_at': DocumentModel.updated_at,
        }
        
        # Build select statement with only requested columns
        selected_columns = []
        for col in columns:
            if col in column_map:
                selected_columns.append(column_map[col])
            else:
                logger.warning(f"Unknown column '{col}' requested, skipping")
        
        if not selected_columns:
            raise ValueError("No valid columns specified")
        
        with self.basket.db.session() as session:
            # Build query with selected columns
            query = select(*selected_columns).where(DocumentModel.basket_id == self.basket.id)
            
            # Add filters
            if filters:
                for key, value in filters.items():
                    if key in column_map:
                        query = query.where(column_map[key] == value)
                    else:
                        logger.warning(f"Unknown filter key '{key}', skipping")
            
            # Add sorting
            if order_by:
                order_field = column_map.get(order_by)
                if order_field is not None:
                    if order_desc:
                        query = query.order_by(order_field.desc())
                    else:
                        query = query.order_by(order_field.asc())
                else:
                    logger.warning(f"Invalid order_by field: {order_by}, using default")
                    query = query.order_by(DocumentModel.created_at.desc())
            else:
                # Default sorting by creation date (newest first)
                query = query.order_by(DocumentModel.created_at.desc())
            
            # Add pagination
            if limit is not None:
                query = query.limit(limit)
            if offset is not None:
                query = query.offset(offset)
            
            # Execute query and convert to dictionaries
            results = session.execute(query).all()
            
            # Convert to list of dictionaries
            documents = []
            for row in results:
                doc_dict = {}
                for i, col in enumerate(columns):
                    if col in column_map:
                        value = row[i]
                        # Convert datetime to ISO format string for JSON serialization
                        if hasattr(value, 'isoformat'):
                            value = value.isoformat()
                        doc_dict[col] = value
                documents.append(doc_dict)
            
            logger.debug(f"Retrieved {len(documents)} documents with metadata (columns: {columns})")
            return documents
    
    def count_documents(
        self,
        status: Optional[str] = None,
        document_type: Optional[str] = None
    ) -> int:
        """
        Count documents in this basket with optional filters.
        Optimized for performance using COUNT query.
        
        Args:
            status: Optional filter by document status
            document_type: Optional filter by document type
            
        Returns:
            Total count of documents matching the criteria
        """
        with self.basket.db.session() as session:
            query = select(func.count(DocumentModel.id)).where(
                DocumentModel.basket_id == self.basket.id
            )
            
            # Add filters
            if status:
                query = query.where(DocumentModel.status == status)
            if document_type:
                query = query.where(DocumentModel.document_type == document_type)
            
            result = session.execute(query).scalar()
            return result or 0
    
    def count_documents_by_metadata(
        self,
        metadata: Union[Dict[str, Any], str]
    ) -> int:
        """
        Count documents matching metadata criteria.
        Optimized for large datasets.
        
        Args:
            metadata: Dictionary of key-value pairs or a single string value
            
        Returns:
            Count of documents matching the metadata criteria
        """
        with self.basket.db.session() as session:
            # Start with documents in this basket
            query = select(DocumentModel).where(DocumentModel.basket_id == self.basket.id)
            query = self._apply_metadata_filter(query, metadata)
            if query is None:
                return 0
            
            # Count distinct documents
            count_query = select(func.count()).select_from(query.subquery())
            result = session.execute(count_query).scalar()
            return result or 0
    
    def find_documents_by_metadata(
        self,
        metadata: Union[Dict[str, Any], str],
        limit: Optional[int] = None,
        offset: Optional[int] = None,
        order_by: Optional[str] = None,
        order_desc: bool = False
    ) -> List[Document]:
        """
        Find documents by metadata with pagination and sorting support.
        Optimized for large datasets with proper basket_id filtering.
        
        Args:
            metadata: Dictionary of key-value pairs or a single string value
            limit: Maximum number of results to return (for pagination)
            offset: Number of results to skip (for pagination)
            order_by: Field to sort by ('created_at', 'updated_at', 'name', 'size')
            order_desc: If True, sort in descending order
            
        Returns:
            List of Document instances matching the metadata criteria
        """
        with self.basket.db.session() as session:
            # Start with documents in this basket - CRITICAL for performance
            query = select(DocumentModel).where(DocumentModel.basket_id == self.basket.id)
            query = self._apply_metadata_filter(query, metadata)
            if query is None:
                return []
            
            # Add sorting
            if order_by:
                order_field = getattr(DocumentModel, order_by, None)
                if order_field is not None:
                    if order_desc:
                        query = query.order_by(order_field.desc())
                    else:
                        query = query.order_by(order_field.asc())
                else:
                    logger.warning(f"Invalid order_by field: {order_by}, using default")
                    query = query.order_by(DocumentModel.created_at.desc())
            else:
                # Default sorting by creation date (newest first)
                query = query.order_by(DocumentModel.created_at.desc())
            
            # Add pagination
            if limit is not None:
                query = query.limit(limit)
            if offset is not None:
                query = query.offset(offset)
            
            documents = session.execute(query).scalars().all()
            return [self._document_instance(doc) for doc in documents]

    def find_documents_by_metadata_with_metadata(
        self,
        metadata: Union[Dict[str, Any], str],
        columns: Optional[List[str]] = None,
        limit: Optional[int] = None,
        offset: Optional[int] = None,
        order_by: Optional[str] = None,
        order_desc: bool = False,
    ) -> List[Dict[str, Any]]:
        """
        Find documents by metadata and return lightweight dictionaries.

        This is the metadata-first alternative to `find_documents_by_metadata()`
        when callers do not need runtime `Document` objects or content access.
        """
        if columns is None:
            columns = ['id', 'name', 'document_type', 'status', 'size', 'created_at']

        column_map = {
            'id': DocumentModel.id,
            'name': DocumentModel.name,
            'path': DocumentModel.path,
            'document_type': DocumentModel.document_type,
            'content_type': DocumentModel.content_type,
            'size': DocumentModel.size,
            'checksum': DocumentModel.checksum,
            'status': DocumentModel.status,
            'created_at': DocumentModel.created_at,
            'updated_at': DocumentModel.updated_at,
        }
        valid_columns = [col for col in columns if col in column_map]
        selected_columns = [column_map[col] for col in valid_columns]
        if not selected_columns:
            raise ValueError("No valid columns specified")

        with self.basket.db.session() as session:
            query = select(*selected_columns).where(
                DocumentModel.basket_id == self.basket.id
            )
            query = self._apply_metadata_filter(query, metadata)
            if query is None:
                return []

            if order_by:
                order_field = column_map.get(order_by)
                if order_field is not None:
                    query = query.order_by(
                        order_field.desc() if order_desc else order_field.asc()
                    )
            else:
                query = query.order_by(DocumentModel.created_at.desc())

            if limit is not None:
                query = query.limit(limit)
            if offset is not None:
                query = query.offset(offset)

            results = session.execute(query).all()
            documents = []
            for row in results:
                doc_dict = {}
                for index, col in enumerate(valid_columns):
                    value = row[index]
                    if hasattr(value, 'isoformat'):
                        value = value.isoformat()
                    doc_dict[col] = value
                documents.append(doc_dict)
            return documents
    
    def get_document(self, document_id: int) -> Optional[Document]:
        """
        Get a document by document_id.
        
        All operations center around document_id - path is retrieved from DB
        but can be rebuilt from IDs if needed for consistency.
        
        Args:
            document_id: Document ID
            
        Returns:
            Document or None if not found
        """
        with self.basket.db.session() as session:
            document = session.execute(
                select(DocumentModel).where(
                    and_(
                        DocumentModel.id == document_id,
                        DocumentModel.basket_id == self.basket.id,
                    )
                )
            ).scalar_one_or_none()
            if document is None:
                return None
            return self._document_instance(document)
    
    def update_document(self, document_id: int, file_path: str) -> Document:
        """
        Update a document.
        
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
        with self.basket.db.transaction() as session:
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
                MetadataKey.CONTENT_TYPE.value: self.basket.path_helper.get_content_type(path)
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
            # document.path already contains the full path (no reconstruction needed)
            return self._document_instance(document)
    
    def delete_document(self, document_id: int) -> None:
        """
        Delete a document by document_id.
        
        All operations center around document_id - path is built from ID.
        
        Args:
            document_id: Document ID
        """
        with self.basket.db.transaction() as session:
            document = session.get(DocumentModel, document_id)
            if document is None:
                raise ValueError(f"Document with ID {document_id} not found")
            
            # Build full path from IDs to ensure we delete the correct file
            # This ensures consistency: all operations use IDs, paths are built internally
            # Build full path using path helper (uses three-part structure)
            # For S3: Part A (config) + Part B (basket) + Part C (document)
            # The path helper will use config_prefix and basket_path from storage_config if available
            full_path = self.basket.path_helper.build_document_path(document, None, None)
            
            # Delete from storage using full path built from IDs
            if self.basket.storage_service:
                try:
                    # Get the underlying storage and delete using full path
                    storage = self.basket.storage_service.storage
                    storage.delete(full_path)
                except Exception as e:
                    logger.warning(f"Failed to delete document from storage at {full_path}: {e}")
            
            # Delete from database
            session.delete(document)
            session.commit()
