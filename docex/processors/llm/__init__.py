"""
LLM Provider Adapters for DocEX

This module provides LLM (Large Language Model) adapters that integrate
seamlessly with DocEX's processor architecture.
"""

from .base_llm_processor import BaseLLMProcessor
from .openai_adapter import OpenAIAdapter
from .openai_service import OpenAILLMService
from .local_llm_adapter import LocalLLMAdapter
from .local_llm_service import LocalLLMService
from .prompt_manager import PromptManager

# Optional adapters that require additional dependencies
try:
    from .claude_adapter import ClaudeAdapter
    from .claude_service import ClaudeLLMService
    CLAUDE_AVAILABLE = True
except ImportError:
    CLAUDE_AVAILABLE = False
    
    # Create placeholder classes for documentation/type hints
    class ClaudeAdapter:
        def __init__(self, *args, **kwargs):
            raise ImportError(
                "Claude adapter requires the 'anthropic' package. "
                "Install it with: pip install anthropic>=0.34.0"
            )
    
    class ClaudeLLMService:
        def __init__(self, *args, **kwargs):
            raise ImportError(
                "Claude service requires the 'anthropic' package. "
                "Install it with: pip install anthropic>=0.34.0"
            )

__all__ = [
    'BaseLLMProcessor',
    'OpenAIAdapter',
    'OpenAILLMService',
    'ClaudeAdapter',
    'ClaudeLLMService',
    'LocalLLMAdapter',
    'LocalLLMService',
    'PromptManager',
]

# Export availability flags for runtime checking
__extras__ = {
    'claude': CLAUDE_AVAILABLE,
}

