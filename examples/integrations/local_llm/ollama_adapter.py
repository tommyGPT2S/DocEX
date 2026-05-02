"""
Ollama LLM Adapter for DocEX

This adapter provides integration with Ollama, a local LLM serving platform that enables:
- Privacy-focused AI processing (all data stays local)
- Cost-effective text generation (no API fees)
- Offline capability for air-gapped environments
- Support for various open-source models (llama3.2, mistral, etc.)

Key Features:
- Automatic model detection and initialization
- Configurable timeout and token limits
- Proper error handling and logging
- Async/await support for non-blocking operations

Usage:
    adapter = OllamaAdapter({
        'model': 'llama3.2',
        'base_url': 'http://127.0.0.1:11434',
        'max_tokens': 4000
    })
    await adapter.initialize()
    response = await adapter.generate("Your prompt here")
"""
import logging
import httpx
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)

class OllamaAdapter:
    """
    Ollama LLM Adapter for local language model processing.
    
    This adapter interfaces with Ollama's REST API to provide:
    - Local LLM inference without external API dependencies
    - Support for multiple open-source models
    - Configurable generation parameters
    - Proper timeout and error handling
    
    The adapter maintains DocEX patterns while providing direct access
    to Ollama's generation capabilities.
    """
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.base_url = config.get('base_url', 'http://127.0.0.1:11434')
        self.model = config.get('model', 'llama3.2')
        self.max_tokens = config.get('max_tokens', 4000)
        self.is_initialized = False
    
    async def initialize(self) -> bool:
        """
        Initialize the Ollama adapter by verifying server connectivity.
        
        Returns:
            bool: True if Ollama server is accessible and responding, False otherwise
        """
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(f"{self.base_url}/api/tags")
                if response.status_code == 200:
                    self.is_initialized = True
                    logger.info(f"Ollama adapter initialized with model: {self.model}")
                    return True
                else:
                    logger.error(f"Failed to connect to Ollama: {response.status_code}")
                    return False
        except Exception as e:
            logger.error(f"Failed to initialize Ollama adapter: {e}")
            return False
    
    async def generate(self, prompt: str, **kwargs) -> Optional[str]:
        """
        Generate text using the configured Ollama model.
        
        Args:
            prompt: The input text prompt for generation
            **kwargs: Additional parameters including:
                - temperature: Controls randomness (0.0-1.0)
                - max_tokens: Maximum tokens to generate
        
        Returns:
            Optional[str]: Generated text response, or None if generation fails
        """
        if not self.is_initialized:
            await self.initialize()
        
        try:
            async with httpx.AsyncClient(timeout=120.0) as client:
                response = await client.post(
                    f"{self.base_url}/api/generate",
                    json={
                        "model": self.model,
                        "prompt": prompt,
                        "stream": False,
                        "options": {
                            "num_predict": self.max_tokens,
                            "temperature": kwargs.get('temperature', 0.3)
                        }
                    }
                )
                
                if response.status_code == 200:
                    result = response.json()
                    return result.get("response", "")
                else:
                    logger.error(f"Ollama generation failed: {response.status_code}")
                    return None
                    
        except Exception as e:
            logger.error(f"Ollama generation error: {e}")
            return None
    
    def generate_embeddings(self, texts):
        """Placeholder for embedding generation (handled by EmbeddingService)"""
        pass