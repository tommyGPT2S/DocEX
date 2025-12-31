"""
Local LLM Adapter for DocEX

Local LLM-powered processor that integrates with DocEX's processor architecture.
Uses Ollama for local model hosting.
"""

import json
import logging
from typing import Dict, Any
from datetime import datetime

from docex.processors.base import ProcessingResult
from docex.document import Document
from docex.processors.llm.base_llm_processor import BaseLLMProcessor
from docex.processors.llm.local_llm_service import LocalLLMService

logger = logging.getLogger(__name__)


class LocalLLMAdapter(BaseLLMProcessor):
    """Local LLM powered DocEX processor using Ollama"""
    
    def _initialize_llm_service(self, config: Dict[str, Any]) -> LocalLLMService:
        """
        Initialize Local LLM service
        
        Args:
            config: Configuration dictionary
            
        Returns:
            Initialized LocalLLMService instance
        """
        base_url = config.get('base_url', 'http://localhost:11434')
        model = config.get('model', 'llama3.2')
        
        return LocalLLMService(base_url=base_url, model=model)
    
    async def _process_with_llm(self, document: Document, text: str) -> ProcessingResult:
        """
        Process document with Local LLM
        
        Args:
            document: DocEX document
            text: Document text content
            
        Returns:
            ProcessingResult with processing results
        """
        try:
            # Check if model is available
            if not await self.llm_service.check_model_availability():
                logger.info(f"Model {self.llm_service.model} not available, attempting to pull...")
                if not await self.llm_service.pull_model():
                    raise Exception(f"Model {self.llm_service.model} is not available and could not be pulled")
            
            # Get prompt name from config or use default
            prompt_name = self.config.get('prompt_name', 'generic_extraction')
            
            # Load prompts from external file
            system_prompt = self.get_system_prompt(prompt_name)
            user_prompt = self.get_user_prompt(prompt_name, content=text)
            
            # Extract structured data using Local LLM
            result = await self.llm_service.extract_structured_data(
                text=text,
                system_prompt=system_prompt,
                user_prompt=user_prompt,
                return_raw_response=self.config.get('return_raw_response', True)
            )
            
            extracted_data = result['extracted_data']
            raw_response = result.get('raw_response', {})
            
            # Optional: Generate summary
            summary = None
            if self.config.get('generate_summary', False):
                try:
                    summary = await self.llm_service.generate_summary(text)
                except Exception as e:
                    logger.warning(f"Summary generation failed: {str(e)}")
            
            # Optional: Generate embedding (if supported)
            embedding = None
            if self.config.get('generate_embedding', False):
                try:
                    embedding = await self.llm_service.generate_embedding(text)
                    if embedding is None:
                        logger.warning("Embedding generation not supported by local model")
                except Exception as e:
                    logger.warning(f"Embedding generation failed: {str(e)}")
            
            # Prepare metadata for DocEX
            metadata = {
                'llm_provider': 'local_llm',
                'llm_model': result['model'],
                'llm_prompt_name': prompt_name,
                'llm_processed_at': datetime.now().isoformat(),
                **extracted_data
            }
            
            if summary:
                metadata['llm_summary'] = summary
            
            if embedding:
                metadata['llm_embedding'] = json.dumps(embedding)  # Store as JSON string
            
            if raw_response:
                metadata['llm_raw_response'] = json.dumps(raw_response)
            
            return ProcessingResult(
                success=True,
                content=extracted_data,
                metadata=metadata
            )
            
        except Exception as e:
            logger.error(f"❌ Local LLM processing failed: {str(e)}")
            return ProcessingResult(
                success=False,
                error=f"Local LLM processing failed: {str(e)}"
            )
    
    def can_process(self, document: Document) -> bool:
        """
        Determine if this processor can handle the document
        
        Args:
            document: DocEX document
            
        Returns:
            True if processor can handle the document
        """
        # Default: can process all documents
        # Subclasses can override for specific document types
        return True