"""
Claude (Anthropic) Adapter for DocEX

Claude-powered processor that integrates with DocEX's processor architecture.
"""

import os
import json
import logging
from typing import Dict, Any
from datetime import datetime

from docex.processors.base import ProcessingResult
from docex.document import Document
from docex.processors.llm.base_llm_processor import BaseLLMProcessor

logger = logging.getLogger(__name__)

try:
    from docex.processors.llm.claude_service import ClaudeLLMService
except ImportError:
    raise ImportError(
        "Claude adapter requires the 'anthropic' package. "
        "Install it with: pip install anthropic>=0.34.0"
    )


class ClaudeAdapter(BaseLLMProcessor):
    """Claude (Anthropic) powered DocEX processor"""
    
    def _initialize_llm_service(self, config: Dict[str, Any]) -> ClaudeLLMService:
        """
        Initialize Claude LLM service
        
        Args:
            config: Configuration dictionary
            
        Returns:
            Initialized ClaudeLLMService instance
        """
        api_key = config.get('api_key') or os.getenv('ANTHROPIC_API_KEY')
        if not api_key:
            raise ValueError("Anthropic API key is required. Set 'api_key' in config or ANTHROPIC_API_KEY environment variable.")
        
        model = config.get('model', 'claude-3-5-sonnet-20241022')
        return ClaudeLLMService(api_key=api_key, model=model)
    
    async def _process_with_llm(self, document: Document, text: str) -> ProcessingResult:
        """
        Process document with Claude
        
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
            
            # Extract structured data using Claude
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
            
            # Note: Claude doesn't support embeddings, so we skip embedding generation
            if self.config.get('generate_embedding', False):
                logger.warning("Claude doesn't support embedding generation. Skipping embedding.")
            
            # Prepare metadata for DocEX
            metadata = {
                'llm_provider': 'anthropic',
                'llm_model': result['model'],
                'llm_prompt_name': prompt_name,
                'llm_processed_at': datetime.now().isoformat(),
                **extracted_data
            }
            
            if summary:
                metadata['llm_summary'] = summary
            
            if raw_response:
                metadata['llm_raw_response'] = json.dumps(raw_response)
            
            return ProcessingResult(
                success=True,
                content=extracted_data,
                metadata=metadata
            )
            
        except Exception as e:
            logger.error(f"❌ Claude processing failed: {str(e)}")
            return ProcessingResult(
                success=False,
                error=f"Claude processing failed: {str(e)}"
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