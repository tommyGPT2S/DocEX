from typing import Dict, Any, Optional, List
from docex.db.connection import Database
from docex.db.models import Document, DocumentMetadata
from sqlalchemy import select
import json
from docex.models.document_metadata import DocumentMetadata as MetaModel

class MetadataService:
    """Service for handling document metadata operations"""
    
    def __init__(self, db: Optional[Database] = None):
        """
        Initialize the metadata service
        
        Args:
            db: Database instance (optional)
        """
        self.db = db or Database()
    
    def get_metadata(self, document_id: str) -> Dict[str, MetaModel]:
        """
        Get metadata for a document as a dict of key -> DocumentMetadata model
        """
        with self.db.transaction() as session:
            metadata_records = session.execute(
                select(DocumentMetadata).where(DocumentMetadata.document_id == document_id)
            ).scalars().all()
            metadata = {}
            for record in metadata_records:
                try:
                    value = json.loads(record.value)
                    meta_obj = MetaModel.from_dict(value)
                except Exception:
                    # fallback for legacy or non-JSON values
                    meta_obj = MetaModel(extra={"value": record.value})
                metadata[record.key] = meta_obj
            return metadata
    
    def update_metadata(self, document_id: str, metadata: Dict[str, Any]) -> None:
        """
        Update metadata for a document. Accepts dict of key -> DocumentMetadata or key -> dict/Any.
        """
        with self.db.transaction() as session:
            for key, value in metadata.items():
                # Accept either DocumentMetadata or dict/Any
                if not isinstance(value, MetaModel):
                    value = MetaModel.from_dict(value) if isinstance(value, dict) else MetaModel(extra={"value": value})
                # Check if metadata already exists
                existing = session.execute(
                    select(DocumentMetadata).where(
                        DocumentMetadata.document_id == document_id,
                        DocumentMetadata.key == key
                    )
                ).scalar_one_or_none()
                value_json = json.dumps(value.to_dict(), default=str)
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