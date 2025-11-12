"""
OpenAI Adapter for DocEX

OpenAI-powered processor that integrates with DocEX's processor architecture.
Extracted and generalized from the invoice processing system.
"""

import os
import json
import logging
from typing import Dict, Any, Optional
from datetime import datetime

from docex.processors.base import ProcessingResult
from docex.document import Document
from docex.processors.llm.base_llm_processor import BaseLLMProcessor
from docex.processors.llm.openai_service import OpenAILLMService

logger = logging.getLogger(__name__)


class OpenAIAdapter(BaseLLMProcessor):
    """OpenAI-powered DocEX processor"""
    
    def _initialize_llm_service(self, config: Dict[str, Any]) -> OpenAILLMService:
        """
        Initialize OpenAI LLM service
        
        Args:
            config: Configuration dictionary
            
        Returns:
            Initialized OpenAILLMService instance
        """
        api_key = config.get('api_key') or os.getenv('OPENAI_API_KEY')
        if not api_key:
            raise ValueError("OpenAI API key is required. Set 'api_key' in config or OPENAI_API_KEY environment variable.")
        
        model = config.get('model', 'gpt-4o')
        return OpenAILLMService(api_key=api_key, model=model)
    
    async def _process_with_llm(self, document: Document, text: str) -> ProcessingResult:
        """
        Process document with OpenAI
        
        Args:
            document: DocEX document
            text: Document text content
            
        Returns:
            ProcessingResult with processing results
        """
        try:
            # Get prompt name from config or use default
            prompt_name = self.config.get('prompt_name', 'generic_extraction')
            
            # Load prompts from external file
            system_prompt = self.get_system_prompt(prompt_name)
            user_prompt = self.get_user_prompt(prompt_name, content=text)
            
            # Extract structured data using OpenAI
            result = await self.llm_service.extract_structured_data(
                text=text,
                system_prompt=system_prompt,
                user_prompt=user_prompt,
                return_raw_response=self.config.get('return_raw_response', True)
            )
            
            extracted_data = result['extracted_data']
            raw_response = result.get('raw_response', {})
            
            # Generate summary if requested
            summary = None
            if self.config.get('generate_summary', False):
                summary_prompt_name = self.config.get('summary_prompt_name', 'document_summary')
                summary_system = self.get_system_prompt(summary_prompt_name)
                summary_user = self.get_user_prompt(summary_prompt_name, content=text[:2000])
                summary = await self.llm_service.generate_completion(
                    prompt=summary_user,
                    system_prompt=summary_system,
                    max_tokens=500
                )
            
            # Generate embedding if requested
            embedding = None
            if self.config.get('generate_embedding', False):
                embedding = await self.llm_service.generate_embedding(text)
            
            # Build metadata
            metadata = {
                'llm_provider': 'openai',
                'llm_model': self.llm_service.model,
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
            logger.error(f"❌ OpenAI processing failed: {str(e)}")
            return ProcessingResult(
                success=False,
                error=f"OpenAI processing failed: {str(e)}"
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

