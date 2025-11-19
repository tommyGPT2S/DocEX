"""
Claude (Anthropic) LLM Service

Claude service for DocEX processors.
"""

import json
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime

logger = logging.getLogger(__name__)

try:
    import anthropic
except ImportError:
    raise ImportError(
        "Claude service requires the 'anthropic' package. "
        "Install it with: pip install anthropic>=0.34.0"
    )


def clean_json_response(content: str) -> str:
    """
    Remove markdown code blocks and extract pure JSON from Claude response
    
    Claude often wraps JSON responses in markdown code blocks or adds explanatory text.
    This function intelligently extracts just the JSON portion for reliable parsing.
    
    Args:
        content: Raw response content from Claude
        
    Returns:
        Cleaned JSON string ready for parsing
    """
    content = content.strip()
    
    # Handle various markdown code block formats
    if content.startswith('```json'):
        content = content[7:]
    elif content.startswith('```JSON'):
        content = content[7:]
    elif content.startswith('```'):
        content = content[3:]
    
    # Remove trailing code blocks
    if content.endswith('```'):
        content = content[:-3]
    
    # Handle cases where there's text before/after JSON
    lines = content.split('\n')
    json_start = -1
    json_end = -1
    
    # Find the start of JSON (look for opening brace)
    for i, line in enumerate(lines):
        if line.strip().startswith('{'):
            json_start = i
            break
    
    # Find the end of JSON (look for closing brace)
    for i in range(len(lines) - 1, -1, -1):
        if lines[i].strip().endswith('}'):
            json_end = i
            break
    
    # Extract just the JSON portion if found
    if json_start >= 0 and json_end >= 0 and json_end >= json_start:
        content = '\n'.join(lines[json_start:json_end + 1])
    
    return content.strip()


class ClaudeLLMService:
    """Claude (Anthropic) LLM service for DocEX processors"""
    
    def __init__(self, api_key: str, model: str = "claude-3-haiku-20240307"):
        """
        Initialize Claude LLM service
        
        Args:
            api_key: Anthropic API key
            model: Model to use (default: claude-3-haiku-20240307)
        """
        self.client = anthropic.Anthropic(api_key=api_key)
        self.model = model
    
    async def generate_completion(
        self, 
        prompt: str, 
        system_prompt: Optional[str] = None,
        temperature: float = 0.1,
        max_tokens: Optional[int] = None,
        **kwargs
    ) -> str:
        """
        Generate text completion using Claude
        
        Args:
            prompt: User prompt
            system_prompt: Optional system prompt
            temperature: Sampling temperature (0.0 to 1.0)
            max_tokens: Maximum tokens to generate
            **kwargs: Additional parameters
            
        Returns:
            Generated text completion
        """
        try:
            messages = [{"role": "user", "content": prompt}]
            
            request_kwargs = {
                "model": self.model,
                "messages": messages,
                "temperature": temperature,
            }
            
            if system_prompt:
                request_kwargs["system"] = system_prompt
            
            if max_tokens:
                request_kwargs["max_tokens"] = max_tokens
            else:
                request_kwargs["max_tokens"] = 4096
            
            response = self.client.messages.create(**request_kwargs)
            
            return response.content[0].text
            
        except Exception as e:
            logger.error(f"Claude completion error: {str(e)}")
            raise
    
    async def generate_embedding(self, text: str, model: str = "text-embedding-3-large") -> List[float]:
        """
        Generate embedding for text
        
        Note: Anthropic doesn't provide embedding models, so we'll use OpenAI as fallback
        or return None to indicate embeddings are not supported.
        
        Args:
            text: Text to embed
            model: Embedding model name (unused for Claude)
            
        Returns:
            List of embedding values or None if not supported
        """
        logger.warning("Claude doesn't support embeddings. Consider using OpenAI for embeddings.")
        return None
    
    async def extract_structured_data(
        self,
        text: str,
        system_prompt: str,
        user_prompt: str,
        return_raw_response: bool = True,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Extract structured data from text using Claude
        
        Args:
            text: Text to analyze
            system_prompt: System prompt for extraction
            user_prompt: User prompt template
            return_raw_response: Whether to return raw response
            **kwargs: Additional parameters
            
        Returns:
            Dictionary with extracted data
        """
        try:
            # Generate completion
            completion = await self.generate_completion(
                prompt=user_prompt,
                system_prompt=system_prompt,
                **kwargs
            )
            
            # Clean and parse JSON response
            cleaned_response = clean_json_response(completion)
            
            try:
                extracted_data = json.loads(cleaned_response)
            except json.JSONDecodeError as e:
                logger.warning(f"Failed to parse JSON response: {e}")
                # Return structured error response
                extracted_data = {
                    "error": "Failed to parse JSON response",
                    "raw_content": cleaned_response
                }
            
            result = {
                "extracted_data": extracted_data,
                "provider": "anthropic",
                "model": self.model,
                "timestamp": datetime.now().isoformat()
            }
            
            if return_raw_response:
                result["raw_response"] = {
                    "completion": completion,
                    "cleaned": cleaned_response
                }
            
            return result
            
        except Exception as e:
            logger.error(f"Claude structured data extraction error: {str(e)}")
            raise
    
    async def generate_summary(
        self,
        text: str,
        max_length: int = 200,
        **kwargs
    ) -> str:
        """
        Generate a summary of the text using Claude
        
        Args:
            text: Text to summarize
            max_length: Maximum summary length
            **kwargs: Additional parameters
            
        Returns:
            Text summary
        """
        try:
            system_prompt = (
                "You are a helpful assistant that creates concise summaries. "
                f"Summarize the following text in no more than {max_length} characters."
            )
            
            summary = await self.generate_completion(
                prompt=f"Please summarize this text:\n\n{text}",
                system_prompt=system_prompt,
                **kwargs
            )
            
            return summary.strip()
            
        except Exception as e:
            logger.error(f"Claude summary generation error: {str(e)}")
            raise