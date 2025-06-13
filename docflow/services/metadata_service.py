from typing import Dict, Any, Optional, List
from docflow.db.connection import Database
from docflow.db.models import Document, DocumentMetadata
from sqlalchemy import select

class MetadataService:
    """Service for handling document metadata operations"""
    
    def __init__(self, db: Database):
        """
        Initialize the metadata service
        
        Args:
            db: Database instance
        """
        self.db = db
    
    def get_metadata(self, document_id: str) -> Dict[str, Any]:
        """
        Get metadata for a document
        
        Args:
            document_id: ID of the document
            
        Returns:
            Dictionary containing document metadata
        """
        with self.db.transaction() as session:
            metadata_records = session.execute(
                select(DocumentMetadata).where(DocumentMetadata.document_id == document_id)
            ).scalars().all()
            
            metadata = {}
            for record in metadata_records:
                metadata[record.key] = record.value
            
            return metadata
    
    def update_metadata(self, document_id: str, metadata: Dict[str, Any]) -> None:
        """
        Update metadata for a document
        
        Args:
            document_id: ID of the document
            metadata: Dictionary containing metadata to update
        """
        with self.db.transaction() as session:
            for key, value in metadata.items():
                # Check if metadata already exists
                existing = session.execute(
                    select(DocumentMetadata).where(
                        DocumentMetadata.document_id == document_id,
                        DocumentMetadata.key == key
                    )
                ).scalar_one_or_none()
                
                if existing:
                    existing.value = value
                else:
                    new_metadata = DocumentMetadata(
                        document_id=document_id,
                        key=key,
                        value=value,
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