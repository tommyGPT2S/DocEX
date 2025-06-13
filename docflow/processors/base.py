from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, Union
from datetime import datetime, UTC
from uuid import uuid4

from docflow.document import Document
from docflow.db.connection import Database
from docflow.db.models import ProcessingOperation

class ProcessingResult:
    """Result of a document processing operation"""
    
    def __init__(
        self,
        success: bool,
        content: Optional[Any] = None,
        metadata: Optional[Dict[str, Any]] = None,
        error: Optional[str] = None
    ):
        self.success = success
        self.content = content
        self.metadata = metadata or {}
        self.error = error
        self.timestamp = datetime.now(UTC)

class BaseProcessor(ABC):
    """Base class for document processors"""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.db = Database()
    
    @abstractmethod
    async def process(self, document: Document) -> ProcessingResult:
        """Process a document
        
        Args:
            document: Document to process
            
        Returns:
            ProcessingResult containing processing results
        """
        pass
    
    @abstractmethod
    def can_process(self, document: Document) -> bool:
        """Check if this processor can handle the given document
        
        Args:
            document: Document to check
            
        Returns:
            True if processor can handle the document
        """
        pass
    
    def get_document_content(self, document: Document, mode: str = 'text') -> Union[bytes, str, Dict[str, Any]]:
        """
        Get document content in the specified mode
        
        Args:
            document: Document to get content from
            mode: Content mode ('bytes', 'text', or 'json')
            
        Returns:
            Document content in the requested format
            
        Raises:
            ValueError: If mode is invalid
            FileNotFoundError: If document content cannot be found
            json.JSONDecodeError: If mode is 'json' but content is not valid JSON
        """
        return Document.get_content(document, mode)
    
    def get_document_bytes(self, document: Document) -> bytes:
        """Get document content as bytes"""
        return Document.get_content(document, mode='bytes')
    
    def get_document_text(self, document: Document) -> str:
        """Get document content as text"""
        return Document.get_content(document, mode='text')
    
    def get_document_json(self, document: Document) -> Dict[str, Any]:
        """Get document content as JSON"""
        return Document.get_content(document, mode='json')
    
    def _record_operation(
        self,
        document: Document,
        status: str,
        input_metadata: Optional[Dict[str, Any]] = None,
        output_metadata: Optional[Dict[str, Any]] = None,
        error: Optional[str] = None
    ) -> ProcessingOperation:
        """Record a processing operation
        
        Args:
            document: Document being processed
            status: Operation status
            input_metadata: Input metadata
            output_metadata: Output metadata
            error: Error message if any
            
        Returns:
            Created processing operation
        """
        operation = ProcessingOperation(
            id=f"pop_{uuid4().hex}",
            document_id=document.id,
            processor_id=self.__class__.__name__,
            status=status,
            input_metadata=input_metadata,
            output_metadata=output_metadata,
            error=error
        )
        
        with self.db.session() as session:
            session.add(operation)
            session.commit()
            session.refresh(operation)
            
        return operation 