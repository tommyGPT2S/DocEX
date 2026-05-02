"""
OpenAI LLM Service

Reusable OpenAI service for DocEX processors, extracted and generalized
from the invoice processing system.
"""

import json
import logging
from typing import Dict, Any, List, Optional
from openai import AsyncOpenAI
from datetime import datetime

logger = logging.getLogger(__name__)


def clean_json_response(content: str) -> str:
    """Remove markdown code blocks from OpenAI response"""
    content = content.strip()
    if content.startswith('```json'):
        content = content[7:]
    if content.startswith('```'):
        content = content[3:]
    if content.endswith('```'):
        content = content[:-3]
    return content.strip()


class OpenAILLMService:
    """Reusable OpenAI LLM service for DocEX processors"""
    
    def __init__(self, api_key: str, model: str = "gpt-4o"):
        """
        Initialize OpenAI LLM service
        
        Args:
            api_key: OpenAI API key
            model: Model to use (default: gpt-4o)
        """
        self.client = AsyncOpenAI(api_key=api_key)
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
        Generate text completion using OpenAI
        
        Args:
            prompt: User prompt
            system_prompt: Optional system prompt
            temperature: Sampling temperature (default: 0.1)
            max_tokens: Maximum tokens to generate
            **kwargs: Additional parameters for OpenAI API
            
        Returns:
            Generated text completion
        """
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})
        
        response = await self.client.chat.completions.create(
            model=self.model,
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens,
            **kwargs
        )
        
        return response.choices[0].message.content
    
    async def generate_embedding(
        self, 
        text: str, 
        model: str = "text-embedding-3-large"
    ) -> List[float]:
        """
        Generate embedding using OpenAI
        
        Args:
            text: Text to embed
            model: Embedding model to use (default: text-embedding-3-large)
            
        Returns:
            Embedding vector as list of floats
        """
        response = await self.client.embeddings.create(
            model=model,
            input=text
        )
        return response.data[0].embedding
    
    async def extract_structured_data(
        self,
        text: str,
        system_prompt: str,
        user_prompt: Optional[str] = None,
        return_raw_response: bool = False
    ) -> Dict[str, Any]:
        """
        Extract structured data from text using OpenAI
        
        Args:
            text: Text to extract data from
            system_prompt: System prompt defining extraction schema
            user_prompt: Optional user prompt (if None, uses default)
            return_raw_response: Whether to include raw API response
            
        Returns:
            Dictionary with 'extracted_data' and optionally 'raw_response'
        """
        if user_prompt is None:
            user_prompt = f"""
Please extract the data from this text:

{text}

Return the data as a JSON object with the exact structure specified in the system prompt.
"""
        
        try:
            logger.info("🤖 Calling OpenAI API for data extraction...")
            
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=0.1,
                max_tokens=2000
            )
            
            content = response.choices[0].message.content.strip()
            content = clean_json_response(content)
            extracted_data = json.loads(content)
            
            result = {
                'extracted_data': extracted_data
            }
            
            if return_raw_response:
                result['raw_response'] = {
                    'model': self.model,
                    'usage': response.usage.model_dump() if response.usage else None,
                    'raw_content': response.choices[0].message.content,
                    'finish_reason': response.choices[0].finish_reason,
                    'system_prompt': system_prompt,
                    'user_prompt': user_prompt,
                    'api_timestamp': datetime.utcnow().isoformat()
                }
            
            logger.info("✅ OpenAI extraction successful")
            return result
            
        except json.JSONDecodeError as e:
            logger.error(f"❌ Failed to parse OpenAI JSON response: {str(e)}")
            logger.error(f"Raw response: {content}")
            raise
        except Exception as e:
            logger.error(f"❌ OpenAI API call failed: {str(e)}")
            raise

