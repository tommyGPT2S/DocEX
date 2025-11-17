from typing import Dict, Any, Optional, List
from docex.db.connection import Database
from docex.db.models import Document, DocumentMetadata
from sqlalchemy import select
import json
import logging

logger = logging.getLogger(__name__)

class MetadataService:
    """Service for handling document metadata operations with direct value storage"""
    
    def __init__(self, db: Optional[Database] = None):
        """
        Initialize the metadata service
        
        Args:
            db: Database instance (optional)
        """
        self.db = db or Database()
    
    def get_metadata(self, document_id: str) -> Dict[str, Any]:
        """
        Get metadata for a document as a dict of key -> value (direct access).
        
        Returns:
            Dict[str, Any]: Metadata dictionary with direct values (no wrapping)
        """
        with self.db.transaction() as session:
            metadata_records = session.execute(
                select(DocumentMetadata).where(DocumentMetadata.document_id == document_id)
            ).scalars().all()
            metadata = {}
            for record in metadata_records:
                try:
                    # Parse JSON value - stored directly, no wrapping
                    value = json.loads(record.value)
                    
                    # Recursively unwrap old nested format if present
                    def unwrap_value(v):
                        """Recursively unwrap nested DocumentMetadata format"""
                        if isinstance(v, dict):
                            if 'extra' in v and isinstance(v['extra'], dict):
                                nested = v['extra'].get('value', v)
                                # Recursively unwrap if still nested
                                if isinstance(nested, dict) and nested != v:
                                    return unwrap_value(nested)
                                return nested
                        return v
                    
                    unwrapped_value = unwrap_value(value)
                    metadata[record.key] = unwrapped_value
                    
                    # Migrate to new format on read if unwrapped
                    if unwrapped_value != value:
                        try:
                            value_json = json.dumps(unwrapped_value, default=str)
                            record.value = value_json
                            session.commit()
                        except Exception:
                            pass  # If migration fails, continue with unwrapped value
                except (json.JSONDecodeError, TypeError):
                    # Fallback: treat as plain string if JSON parsing fails
                    metadata[record.key] = record.value
            
            return metadata
    
    def update_metadata(self, document_id: str, metadata: Dict[str, Any]) -> None:
        """
        Update metadata for a document. Stores values directly (no wrapping).
        
        Args:
            document_id: Document ID
            metadata: Dictionary of key -> value pairs (values stored directly)
        """
        with self.db.transaction() as session:
            for key, value in metadata.items():
                # Serialize to JSON (handles dict, list, string, number, etc.)
                try:
                    value_json = json.dumps(value, default=str)
                except (TypeError, ValueError) as e:
                    logger.warning(f"Failed to serialize metadata {key}, storing as string: {e}")
                    value_json = json.dumps(str(value))
                
                # Check if metadata already exists
                existing = session.execute(
                    select(DocumentMetadata).where(
                        DocumentMetadata.document_id == document_id,
                        DocumentMetadata.key == key
                    )
                ).scalar_one_or_none()
                
                if existing:
                    existing.value = value_json
                else:
                    new_metadata = DocumentMetadata(
                        document_id=document_id,
                        key=key,
                        value=value_json,
                        metadata_type='custom'
                    )
                    session.add(new_metadata)
            session.commit()
    
    def delete_metadata(self, document_id: str, keys: List[str]) -> None:
        """
        Delete metadata for a document
        
        Args:
            document_id: ID of the document
            keys: List of metadata keys to delete
        """
        with self.db.transaction() as session:
            session.execute(
                DocumentMetadata.__table__.delete().where(
                    DocumentMetadata.document_id == document_id,
                    DocumentMetadata.key.in_(keys)
                )
            )
            session.commit() 