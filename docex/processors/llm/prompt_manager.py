"""
Prompt Manager for LLM Processors

Manages prompts stored in external files, allowing for easy editing
and versioning without code changes.
"""

import os
import yaml
from pathlib import Path
from typing import Dict, Any, Optional
from jinja2 import Template
import logging

logger = logging.getLogger(__name__)


class PromptManager:
    """Manages prompts loaded from external files"""
    
    def __init__(self, prompts_dir: Optional[str] = None):
        """
        Initialize PromptManager
        
        Args:
            prompts_dir: Directory containing prompt files. If None, uses default location.
        """
        if prompts_dir is None:
            # Default to prompts directory in docex package
            base_dir = Path(__file__).parent.parent.parent
            prompts_dir = base_dir / "prompts"
        
        self.prompts_dir = Path(prompts_dir)
        self._prompts_cache: Dict[str, Dict[str, Any]] = {}
        
        # Ensure prompts directory exists
        self.prompts_dir.mkdir(parents=True, exist_ok=True)
    
    def load_prompt(self, prompt_name: str, use_cache: bool = True) -> Dict[str, Any]:
        """
        Load a prompt from YAML file
        
        Args:
            prompt_name: Name of the prompt (without .yaml extension)
            use_cache: Whether to use cached prompts
            
        Returns:
            Dictionary with 'system_prompt' and 'user_prompt_template' keys
        """
        if use_cache and prompt_name in self._prompts_cache:
            return self._prompts_cache[prompt_name]
        
        prompt_file = self.prompts_dir / f"{prompt_name}.yaml"
        
        if not prompt_file.exists():
            logger.warning(f"Prompt file not found: {prompt_file}")
            # Return default prompt structure
            return {
                'system_prompt': '',
                'user_prompt_template': '{{ content }}'
            }
        
        try:
            with open(prompt_file, 'r', encoding='utf-8') as f:
                prompt_data = yaml.safe_load(f)
            
            if use_cache:
                self._prompts_cache[prompt_name] = prompt_data
            
            return prompt_data
        except Exception as e:
            logger.error(f"Failed to load prompt {prompt_name}: {e}")
            raise
    
    def get_system_prompt(self, prompt_name: str) -> str:
        """Get system prompt for a given prompt name"""
        prompt_data = self.load_prompt(prompt_name)
        return prompt_data.get('system_prompt', '')
    
    def get_user_prompt(self, prompt_name: str, **kwargs) -> str:
        """
        Get user prompt with template variables filled in
        
        Args:
            prompt_name: Name of the prompt
            **kwargs: Variables to fill in the template
            
        Returns:
            Rendered user prompt string
        """
        prompt_data = self.load_prompt(prompt_name)
        template_str = prompt_data.get('user_prompt_template', '{{ content }}')
        
        template = Template(template_str)
        return template.render(**kwargs)
    
    def clear_cache(self):
        """Clear the prompts cache"""
        self._prompts_cache.clear()
    
    def list_prompts(self) -> list:
        """List all available prompt files"""
        if not self.prompts_dir.exists():
            return []
        
        return [
            f.stem for f in self.prompts_dir.glob("*.yaml")
        ]


# Global prompt manager instance
_default_prompt_manager: Optional[PromptManager] = None


def get_prompt_manager(prompts_dir: Optional[str] = None) -> PromptManager:
    """Get the default prompt manager instance"""
    global _default_prompt_manager
    
    if _default_prompt_manager is None:
        _default_prompt_manager = PromptManager(prompts_dir)
    
    return _default_prompt_manager

