"""
Base LLM Processor for DocEX

Base class for LLM-powered DocEX processors, extracted and generalized
from the invoice processing system.
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, Optional
import logging

from docex.processors.base import BaseProcessor, ProcessingResult
from docex.document import Document
from docex.db.connection import Database
from docex.processors.llm.prompt_manager import PromptManager, get_prompt_manager

logger = logging.getLogger(__name__)


class BaseLLMProcessor(BaseProcessor):
    """Base class for LLM-powered DocEX processors"""
    
    def __init__(self, config: Dict[str, Any], db: Optional[Database] = None):
        """
        Initialize base LLM processor
        
        Args:
            config: Configuration dictionary
            db: Optional tenant-aware database instance (for multi-tenancy support)
        """
        super().__init__(config, db=db)
        self.llm_service = self._initialize_llm_service(config)
        
        # Initialize prompt manager
        prompts_dir = config.get('prompts_dir')
        self.prompt_manager = get_prompt_manager(prompts_dir)
    
    @abstractmethod
    def _initialize_llm_service(self, config: Dict[str, Any]):
        """Initialize LLM service - subclasses must implement"""
        raise NotImplementedError
    
    def get_document_text(self, document: Document) -> str:
        """
        Get text content from document
        
        Args:
            document: DocEX document
            
        Returns:
            Document text content
        """
        try:
            # Try to get text content directly
            content = document.get_content(mode='text')
            if content:
                return content
        except Exception:
            pass
        
        # Fallback: try bytes and decode
        try:
            content = document.get_content(mode='bytes')
            if content:
                return content.decode('utf-8', errors='ignore')
        except Exception:
            pass
        
        # Last resort: return empty string
        logger.warning(f"Could not extract text from document {document.id}")
        return ""
    
    async def process(self, document: Document) -> ProcessingResult:
        """
        Process document using LLM - leverages DocEX infrastructure
        
        Args:
            document: DocEX document to process
            
        Returns:
            ProcessingResult with processing outcome
        """
        try:
            # DocEX tracks operation start
            operation = self._record_operation(
                document,
                status='in_progress',
                input_metadata={'document_id': document.id, 'document_type': document.document_type}
            )
            
            # Get document content (DocEX method)
            text_content = self.get_document_text(document)
            
            if not text_content.strip():
                return ProcessingResult(
                    success=False,
                    error="No text content could be extracted from document"
                )
            
            # Process with LLM (subclass implements)
            result = await self._process_with_llm(document, text_content)
            
            # Store results as DocEX metadata
            # Use tenant-aware database from processor instance
            if result.metadata:
                from docex.services.metadata_service import MetadataService
                metadata_service = MetadataService(self.db)
                metadata_service.update_metadata(document.id, result.metadata)
            
            # DocEX tracks operation success
            # Convert metadata to plain dict for JSON serialization
            output_metadata = {}
            if result.metadata:
                # Convert DocumentMetadata objects to plain dict
                from docex.models.document_metadata import DocumentMetadata as MetaModel
                from datetime import datetime, date
                import json
                
                def serialize_value(value):
                    """Serialize value to JSON-compatible format"""
                    # Handle DocumentMetadata objects
                    if isinstance(value, MetaModel):
                        return serialize_value(value.to_dict())
                    # Handle datetime objects
                    elif isinstance(value, datetime):
                        return value.isoformat()
                    elif isinstance(value, date):
                        return value.isoformat()
                    # Handle dicts (including nested ones)
                    elif isinstance(value, dict):
                        if 'extra' in value:
                            return serialize_value(value['extra'].get('value', value))
                        else:
                            return {k: serialize_value(v) for k, v in value.items()}
                    # Handle lists
                    elif isinstance(value, list):
                        return [serialize_value(item) for item in value]
                    # Handle other types - try JSON serialization test
                    else:
                        try:
                            json.dumps(value)  # Test if already serializable
                            return value
                        except (TypeError, ValueError):
                            # If not serializable, convert to string
                            return str(value)
                
                for key, value in result.metadata.items():
                    try:
                        output_metadata[key] = serialize_value(value)
                    except Exception as e:
                        # If serialization fails, store as string
                        logger.warning(f"Failed to serialize metadata key '{key}': {e}")
                        output_metadata[key] = str(value)
            
            self._record_operation(
                document,
                status='success',
                output_metadata=output_metadata
            )
            
            return result
            
        except Exception as e:
            # DocEX tracks operation failure
            logger.error(f"❌ LLM processing failed for document {document.id}: {str(e)}")
            self._record_operation(
                document,
                status='failed',
                error=str(e)
            )
            return ProcessingResult(success=False, error=str(e))
    
    @abstractmethod
    async def _process_with_llm(self, document: Document, text: str) -> ProcessingResult:
        """
        Process document with LLM - subclasses must implement
        
        Args:
            document: DocEX document
            text: Document text content
            
        Returns:
            ProcessingResult with LLM processing results
        """
        pass
    
    def load_prompt(self, prompt_name: str) -> Dict[str, Any]:
        """
        Load a prompt from external file
        
        Args:
            prompt_name: Name of the prompt (without .yaml extension)
            
        Returns:
            Dictionary with prompt data
        """
        return self.prompt_manager.load_prompt(prompt_name)
    
    def get_system_prompt(self, prompt_name: str) -> str:
        """
        Get system prompt for a given prompt name
        
        Args:
            prompt_name: Name of the prompt
            
        Returns:
            System prompt string
        """
        return self.prompt_manager.get_system_prompt(prompt_name)
    
    def get_user_prompt(self, prompt_name: str, **kwargs) -> str:
        """
        Get user prompt with template variables filled in
        
        Args:
            prompt_name: Name of the prompt
            **kwargs: Variables to fill in the template
            
        Returns:
            Rendered user prompt string
        """
        return self.prompt_manager.get_user_prompt(prompt_name, **kwargs)

