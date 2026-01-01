"""
Document Manager for DocBasket

This module provides document CRUD operations for DocBasket.
All document-related operations are centralized here for better maintainability.
"""

from typing import Optional, Dict, Any, Union, List, TYPE_CHECKING
from pathlib import Path
from datetime import datetime, timezone
import hashlib
import json
import logging

from sqlalchemy import select, and_, func

from docex.db.models import Document as DocumentModel, DocEvent, Operation, DocumentMetadata
from docex.utils.file_utils import is_binary_file
from docex.models.metadata_keys import MetadataKey
from docex.models.document_metadata import DocumentMetadata as MetaModel

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
    
    def __init__(self, basket: 'DocBasket'):
        """
        Initialize document manager with reference to parent basket.
        
        Args:
            basket: DocBasket instance that owns this manager
        """
        self.basket = basket
    
    def add(
        self, 
        file_path: str, 
        document_type: str = 'file', 
        metadata: Optional[Dict[str, Any]] = None
    ) -> 'Document':
        """
        Add a document to the basket.
        
        Args:
            file_path: Path to the document
            document_type: Type of document (file, url, etc.)
            metadata: Optional metadata
            
        Returns:
            Document instance
        """
        # Import Document class lazily to avoid circular imports
        Document = _get_document_class()
        
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
            file_name = file_path.name if hasattr(file_path, 'name') else str(file_path)
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
                    storage_service=self.basket.storage_service,
                    db=self.basket.db  # Pass tenant-aware database to document
                )
            
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
            
            # Build full path from IDs using path helper
            # All operations center around basket_id and document_id - paths are built internally
            full_path = self.basket.path_helper.build_document_path(document, str(file_path), metadata)
            
            # Update document name to reflect the correct readable name
            # This ensures the document record shows the right filename
            readable_name = self.basket.path_helper.get_readable_document_name(document, str(file_path), metadata)
            document.name = f"{readable_name}{Path(str(file_path)).suffix}"
            
            # Store document using full path (built from IDs)
            # StorageService now expects full paths, not IDs
            stored_path = self.basket.storage_service.store_document(str(file_path), full_path)
            document.path = stored_path

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
                storage_service=self.basket.storage_service,
                db=self.basket.db  # Pass tenant-aware database to document
            )
    
    def list_documents(
        self,
        limit: Optional[int] = None,
        offset: Optional[int] = None,
        order_by: Optional[str] = None,
        order_desc: bool = False,
        status: Optional[str] = None,
        document_type: Optional[str] = None
    ) -> List['Document']:
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
        # Import Document class lazily to avoid circular imports
        Document = _get_document_class()
        
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
                storage_service=self.basket.storage_service,
                db=self.basket.db  # Pass tenant-aware database to document
            ) for doc in documents]
    
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
        with self.basket.db.transaction() as session:
            # Start with documents in this basket
            query = select(DocumentModel).where(DocumentModel.basket_id == self.basket.id)
            
            if isinstance(metadata, dict):
                # Handle dictionary input - multiple key-value pairs (AND logic)
                metadata_filters = []
                for key, value in metadata.items():
                    if isinstance(value, MetaModel):
                        value = value.to_dict()
                    if isinstance(value, dict) and 'extra' in value:
                        value = value['extra'].get('value', None)
                    
                    # Metadata values are stored as JSON strings, so we need to JSON-encode the search value
                    try:
                        value_json = json.dumps(value, default=str)
                    except (TypeError, ValueError):
                        value_json = json.dumps(str(value))
                    
                    # Create subquery for each metadata key-value pair
                    subquery = select(DocumentMetadata.document_id).where(
                        and_(
                            DocumentMetadata.key == key,
                            DocumentMetadata.value == value_json,
                            DocumentMetadata.document_id.in_(
                                select(DocumentModel.id).where(DocumentModel.basket_id == self.basket.id)
                            )
                        )
                    )
                    metadata_filters.append(subquery)
                
                # Intersect all subqueries to get documents matching ALL metadata criteria
                if metadata_filters:
                    base_subquery = metadata_filters[0]
                    for subquery in metadata_filters[1:]:
                        base_subquery = base_subquery.intersect(subquery)
                    query = query.where(DocumentModel.id.in_(base_subquery))
                else:
                    return 0
            elif isinstance(metadata, str):
                # Handle string input (search across all metadata values)
                # Metadata values are stored as JSON strings
                search_value_json = json.dumps(metadata)
                query = query.join(DocumentMetadata, DocumentMetadata.document_id == DocumentModel.id)
                query = query.where(DocumentMetadata.value == search_value_json)
            else:
                raise ValueError("Metadata must be a dictionary or a string.")
            
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
    ) -> List['Document']:
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
        # Import Document class lazily to avoid circular imports
        Document = _get_document_class()
        
        with self.basket.db.transaction() as session:
            # Start with documents in this basket - CRITICAL for performance
            query = select(DocumentModel).where(DocumentModel.basket_id == self.basket.id)
            
            if isinstance(metadata, dict):
                # Handle dictionary input - multiple key-value pairs (AND logic)
                # For AND logic with multiple metadata filters, we need to ensure
                # the document has ALL specified key-value pairs
                metadata_filters = []
                for key, value in metadata.items():
                    if isinstance(value, MetaModel):
                        value = value.to_dict()
                    if isinstance(value, dict) and 'extra' in value:
                        value = value['extra'].get('value', None)
                    
                    # Metadata values are stored as JSON strings, so we need to JSON-encode the search value
                    try:
                        # Try to encode as JSON to match how it's stored
                        value_json = json.dumps(value, default=str)
                    except (TypeError, ValueError):
                        # Fallback to string if JSON encoding fails
                        value_json = json.dumps(str(value))
                    
                    # Create subquery for each metadata key-value pair
                    # This ensures AND logic: document must match ALL filters
                    subquery = select(DocumentMetadata.document_id).where(
                        and_(
                            DocumentMetadata.key == key,
                            DocumentMetadata.value == value_json,
                            DocumentMetadata.document_id.in_(
                                select(DocumentModel.id).where(DocumentModel.basket_id == self.basket.id)
                            )
                        )
                    )
                    metadata_filters.append(subquery)
                
                # Intersect all subqueries to get documents matching ALL metadata criteria
                if metadata_filters:
                    # Start with first filter
                    base_subquery = metadata_filters[0]
                    # Intersect with remaining filters
                    for subquery in metadata_filters[1:]:
                        base_subquery = base_subquery.intersect(subquery)
                    
                    # Filter documents by IDs from intersected subqueries
                    query = query.where(DocumentModel.id.in_(base_subquery))
                else:
                    # No valid metadata filters, return empty
                    return []
            elif isinstance(metadata, str):
                # Handle string input (search across all metadata values)
                # Join with metadata table for string search
                # Metadata values are stored as JSON strings, so we need to search for JSON-encoded value
                search_value_json = json.dumps(metadata)
                query = query.join(DocumentMetadata, DocumentMetadata.document_id == DocumentModel.id)
                query = query.where(DocumentMetadata.value == search_value_json)
            else:
                raise ValueError("Metadata must be a dictionary or a string.")
            
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
            
            # Execute query - use distinct() to avoid duplicates from joins (if any)
            if isinstance(metadata, str):
                query = query.distinct()
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
                storage_service=self.basket.storage_service,
                db=self.basket.db  # Pass tenant-aware database to document
            ) for doc in documents]
    
    def get_document(self, document_id: int) -> Optional['Document']:
        """
        Get a document by document_id.
        
        All operations center around document_id - path is retrieved from DB
        but can be rebuilt from IDs if needed for consistency.
        
        Args:
            document_id: Document ID
            
        Returns:
            Document or None if not found
        """
        # Import Document class lazily to avoid circular imports
        Document = _get_document_class()
        
        with self.basket.db.transaction() as session:
            document = session.get(DocumentModel, document_id)
            if document is None:
                return None
            
            # Path is stored in DB, but we can verify/rebuild it from IDs if needed
            # For now, use stored path (it was built from IDs when document was added)
            stored_path = document.path
            
            # Rebuild path from IDs to ensure consistency
            # This ensures path matches current configuration even if config changed
            # Pass document.name as file_path so path_helper can extract the extension
            full_path = self.basket.path_helper.build_document_path(
                document, 
                document.name if document.name else None, 
                None
            )
            
            # Use the path built from IDs (ensures consistency)
            # This ensures all operations use paths built from IDs, not stored paths
            return Document(
                id=document.id,
                name=document.name,
                path=full_path,  # Use path built from IDs, not stored path
                content_type=document.content_type,
                document_type=document.document_type,
                size=document.size,
                checksum=document.checksum,
                status=document.status,
                created_at=document.created_at,
                updated_at=document.updated_at,
                model=document,
                storage_service=self.basket.storage_service,
                db=self.basket.db  # Pass tenant-aware database to document
            )
    
    def update_document(self, document_id: int, file_path: str) -> 'Document':
        """
        Update a document.
        
        Args:
            document_id: Document ID
            file_path: Path to the new document file
            
        Returns:
            Updated document
        """
        # Import Document class lazily to avoid circular imports
        Document = _get_document_class()
        
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
                storage_service=self.basket.storage_service,
                db=self.basket.db  # Pass tenant-aware database to document
            )
    
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
            tenant_id = self.basket.path_helper.extract_tenant_id()
            document_name = self.basket.path_helper.get_readable_document_name(document, None, None)
            file_ext = Path(document.name).suffix if document.name else ''
            
            # Build full path using path helper
            # Check if storage_config has existing prefix to avoid duplication
            existing_prefix = None
            # Use property to get storage type (validates it exists and is valid)
            storage_type = self.basket.storage_type
            if storage_type == 's3':
                existing_prefix = self.basket.storage_config.get('s3', {}).get('prefix', '')
                if existing_prefix:
                    # Check if prefix already includes the basket path
                    from docex.utils.s3_prefix_builder import sanitize_basket_name
                    basket_id_suffix = self.basket.id.replace('bas_', '')[-4:] if self.basket.id.startswith('bas_') else self.basket.id[-4:]
                    sanitized_name = sanitize_basket_name(self.basket.name)
                    expected_basket_path = f"{sanitized_name}_{basket_id_suffix}"
                    if expected_basket_path not in existing_prefix:
                        existing_prefix = None
            
            # Use path helper to build full path from document
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

