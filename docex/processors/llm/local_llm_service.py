"""
Local LLM Service (Ollama)

Local LLM service for DocEX processors using Ollama.
"""

import json
import logging
from typing import Dict, Any, List, Optional
import aiohttp
from datetime import datetime

logger = logging.getLogger(__name__)


def clean_json_response(content: str) -> str:
    """
    Remove markdown code blocks and extract pure JSON from local LLM response
    
    Local LLMs (especially instruction-tuned models) often wrap JSON in markdown 
    code blocks or add explanatory text. This function intelligently extracts 
    just the JSON portion for reliable parsing.
    
    Args:
        content: Raw response content from local LLM
        
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


class LocalLLMService:
    """Local LLM service for DocEX processors using Ollama"""
    
    def __init__(self, base_url: str = "http://localhost:11434", model: str = "llama3.2"):
        """
        Initialize Local LLM service
        
        Args:
            base_url: Ollama server URL (default: http://localhost:11434)
            model: Model to use (default: llama3.2)
        """
        self.base_url = base_url.rstrip('/')
        self.model = model
    
    async def _make_request(self, endpoint: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """Make HTTP request to Ollama API"""
        async with aiohttp.ClientSession() as session:
            url = f"{self.base_url}/{endpoint}"
            async with session.post(url, json=data) as response:
                if response.status != 200:
                    raise Exception(f"Ollama API error: {response.status} {await response.text()}")
                return await response.json()
    
    async def generate_completion(
        self, 
        prompt: str, 
        system_prompt: Optional[str] = None,
        temperature: float = 0.1,
        max_tokens: Optional[int] = None,
        **kwargs
    ) -> str:
        """
        Generate text completion using local LLM
        
        Args:
            prompt: User prompt
            system_prompt: Optional system prompt
            temperature: Sampling temperature (0.0 to 1.0)
            max_tokens: Maximum tokens to generate (not supported by Ollama)
            **kwargs: Additional parameters
            
        Returns:
            Generated text completion
        """
        try:
            # Prepare the full prompt
            full_prompt = prompt
            if system_prompt:
                full_prompt = f"{system_prompt}\n\n{prompt}"
            
            data = {
                "model": self.model,
                "prompt": full_prompt,
                "stream": False,
                "options": {
                    "temperature": temperature,
                }
            }
            
            response = await self._make_request("api/generate", data)
            return response.get("response", "")
            
        except Exception as e:
            logger.error(f"Local LLM completion error: {str(e)}")
            raise
    
    async def generate_embedding(self, text: str, model: str = None) -> List[float]:
        """
        Generate embedding for text using local embedding model
        
        Args:
            text: Text to embed
            model: Embedding model name (default: uses configured model)
            
        Returns:
            List of embedding values
        """
        try:
            # Use a dedicated embedding model if available
            embedding_model = model or "nomic-embed-text"
            
            data = {
                "model": embedding_model,
                "prompt": text
            }
            
            response = await self._make_request("api/embeddings", data)
            return response.get("embedding", [])
            
        except Exception as e:
            logger.warning(f"Local LLM embedding error: {str(e)}")
            # Return None if embeddings are not available
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
        Extract structured data from text using local LLM
        
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
                "provider": "local_llm",
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
            logger.error(f"Local LLM structured data extraction error: {str(e)}")
            raise
    
    async def generate_summary(
        self,
        text: str,
        max_length: int = 200,
        **kwargs
    ) -> str:
        """
        Generate a summary of the text using local LLM
        
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
            logger.error(f"Local LLM summary generation error: {str(e)}")
            raise
    
    async def check_model_availability(self) -> bool:
        """
        Check if the model is available on the Ollama server
        
        Returns:
            True if model is available, False otherwise
        """
        try:
            async with aiohttp.ClientSession() as session:
                url = f"{self.base_url}/api/tags"
                async with session.get(url) as response:
                    if response.status != 200:
                        return False
                    
                    data = await response.json()
                    models = [model["name"] for model in data.get("models", [])]
                    return self.model in models
                    
        except Exception as e:
            logger.warning(f"Failed to check model availability: {str(e)}")
            return False
    
    async def pull_model(self) -> bool:
        """
        Pull the model if it's not available
        
        Returns:
            True if model was pulled successfully, False otherwise
        """
        try:
            data = {
                "name": self.model,
                "stream": False
            }
            
            await self._make_request("api/pull", data)
            return True
            
        except Exception as e:
            logger.error(f"Failed to pull model {self.model}: {str(e)}")
            return False