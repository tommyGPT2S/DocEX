"""
DSPy Adapter for DocEX

Integrates DSPy (Declarative Self-improving Python) framework with DocEX processors.
DSPy allows programming with LMs rather than prompting, with automatic optimization.

Reference: https://dspy.ai/
"""

import logging
from typing import Dict, Any, Optional, List
import json

try:
    import dspy
    from dspy import Signature, ChainOfThought, Predict, Module
    DSPY_AVAILABLE = True
except ImportError:
    DSPY_AVAILABLE = False
    # Create placeholder classes for type hints
    class Signature:
        pass
    class ChainOfThought:
        pass
    class Predict:
        pass
    class Module:
        pass

from docex.processors.base import BaseProcessor, ProcessingResult
from docex.document import Document

logger = logging.getLogger(__name__)


class DSPyAdapter(BaseProcessor):
    """
    DSPy-powered DocEX processor adapter
    
    Uses DSPy modules (Signatures, ChainOfThought, Predict) instead of
    traditional prompts, enabling automatic optimization and better
    structured extraction.
    
    Example:
        ```python
        from docex.processors.llm.dspy_adapter import DSPyAdapter
        
        # Define signature for extraction
        signature = "document_text -> customer_name, address, hin, dea, contract_number"
        
        # Create adapter
        adapter = DSPyAdapter({
            'signature': signature,
            'model': 'openai/gpt-4o-mini',
            'use_chain_of_thought': True
        })
        
        # Process document
        result = await adapter.process(document)
        ```
    """
    
    def __init__(self, config: Dict[str, Any], db=None):
        """
        Initialize DSPy Adapter
        
        Args:
            config: Configuration dictionary with:
                - signature: DSPy signature string (e.g., "text -> field1, field2")
                - model: Model identifier (e.g., 'openai/gpt-4o-mini', 'anthropic/claude-sonnet-4-5-20250929')
                - api_key: Optional API key (uses env vars if not provided)
                - use_chain_of_thought: Use ChainOfThought module (default: True)
                - optimizer: Optional DSPy optimizer config (e.g., {'type': 'MIPROv2', 'metric': ...})
                - training_data: Optional training examples for optimization
            db: Optional tenant-aware database instance
        """
        if not DSPY_AVAILABLE:
            raise ImportError(
                "DSPy is not installed. Install it with: pip install dspy-ai"
            )
        
        super().__init__(config, db=db)
        
        # Initialize DSPy LM
        self.model_name = config.get('model', 'openai/gpt-4o-mini')
        api_key = config.get('api_key')
        
        # Configure DSPy LM based on model name
        if self.model_name.startswith('openai/'):
            model_id = self.model_name.replace('openai/', '')
            if api_key:
                self.lm = dspy.LM(f"openai/{model_id}", api_key=api_key)
            else:
                self.lm = dspy.LM(f"openai/{model_id}")
        elif self.model_name.startswith('anthropic/'):
            model_id = self.model_name.replace('anthropic/', '')
            if api_key:
                self.lm = dspy.LM(f"anthropic/{model_id}", api_key=api_key)
            else:
                self.lm = dspy.LM(f"anthropic/{model_id}")
        elif self.model_name.startswith('ollama/') or self.model_name.startswith('local/'):
            # For Ollama/local models
            base_url = config.get('base_url', 'http://localhost:11434')
            model_id = self.model_name.replace('ollama/', '').replace('local/', '')
            self.lm = dspy.LM(f"ollama/{model_id}", base_url=base_url)
        else:
            # Try as-is
            self.lm = dspy.LM(self.model_name, api_key=api_key)
        
        # Configure DSPy
        dspy.configure(lm=self.lm)
        
        # Parse signature
        signature_str = config.get('signature')
        if not signature_str:
            raise ValueError("'signature' is required in config")
        
        self.signature = Signature(signature_str)
        
        # Create DSPy module
        use_cot = config.get('use_chain_of_thought', True)
        if use_cot:
            self.module = ChainOfThought(self.signature)
        else:
            self.module = Predict(self.signature)
        
        # Set LM on module
        self.module.set_lm(self.lm)
        
        # Optional optimizer
        self.optimizer_config = config.get('optimizer')
        self.training_data = config.get('training_data', [])
        self.optimized_module = None
        
        # Optimize if config provided
        if self.optimizer_config and self.training_data:
            self._optimize_module()
    
    def _optimize_module(self):
        """Optimize DSPy module using configured optimizer"""
        try:
            optimizer_type = self.optimizer_config.get('type', 'BootstrapFewShot')
            metric = self.optimizer_config.get('metric')
            
            if not metric:
                logger.warning("No metric provided for optimizer, skipping optimization")
                return
            
            # Convert training data to DSPy Examples
            examples = [dspy.Example(**ex) for ex in self.training_data]
            
            # Select optimizer
            if optimizer_type == 'MIPROv2':
                optimizer = dspy.MIPROv2(metric=metric)
            elif optimizer_type == 'BootstrapFewShot':
                optimizer = dspy.BootstrapFewShot(metric=metric)
            elif optimizer_type == 'BootstrapFinetune':
                optimizer = dspy.BootstrapFinetune(metric=metric)
            else:
                logger.warning(f"Unknown optimizer type: {optimizer_type}, using BootstrapFewShot")
                optimizer = dspy.BootstrapFewShot(metric=metric)
            
            # Compile (optimize) the module
            logger.info(f"Optimizing DSPy module with {optimizer_type}...")
            self.optimized_module = optimizer.compile(self.module, trainset=examples)
            logger.info("Optimization complete")
            
        except Exception as e:
            logger.error(f"Error optimizing DSPy module: {e}", exc_info=True)
            # Fall back to unoptimized module
            self.optimized_module = None
    
    def can_process(self, document: Document) -> bool:
        """Check if this processor can handle the document"""
        # DSPy adapter can process any document with text content
        try:
            text = self.get_document_text(document)
            return bool(text and text.strip())
        except Exception:
            return False
    
    def get_document_text(self, document: Document) -> str:
        """Get text content from document"""
        try:
            content = document.get_content(mode='text')
            if content:
                return content
        except Exception:
            pass
        
        try:
            content = document.get_content(mode='bytes')
            if content:
                return content.decode('utf-8', errors='ignore')
        except Exception:
            pass
        
        logger.warning(f"Could not extract text from document {document.id}")
        return ""
    
    async def process(self, document: Document) -> ProcessingResult:
        """
        Process document using DSPy module
        
        Args:
            document: DocEX document to process
            
        Returns:
            ProcessingResult with extracted data
        """
        try:
            # Record operation start
            self._record_operation(
                document,
                status='in_progress',
                input_metadata={
                    'document_id': document.id,
                    'document_type': document.document_type,
                    'processor': 'DSPyAdapter',
                    'model': self.model_name
                }
            )
            
            # Get document text
            text_content = self.get_document_text(document)
            
            if not text_content.strip():
                return ProcessingResult(
                    success=False,
                    error="No text content could be extracted from document"
                )
            
            # Use optimized module if available, otherwise use base module
            module = self.optimized_module if self.optimized_module else self.module
            
            # Run DSPy module
            # DSPy modules are synchronous, so we run in executor if needed
            import asyncio
            loop = asyncio.get_event_loop()
            
            # Create input for DSPy module based on signature
            # Extract input field name from signature
            signature_str = str(self.signature)
            input_field = signature_str.split('->')[0].strip()
            
            # Prepare input
            prediction_input = {input_field: text_content}
            
            # Run prediction (DSPy is synchronous)
            prediction = await loop.run_in_executor(
                None,
                lambda: module(**prediction_input)
            )
            
            # Extract results
            # DSPy predictions have fields as attributes
            extracted_data = {}
            for field_name in dir(prediction):
                if not field_name.startswith('_') and field_name != input_field:
                    value = getattr(prediction, field_name, None)
                    if value is not None:
                        extracted_data[field_name] = value
            
            # If using ChainOfThought, also extract reasoning
            if hasattr(prediction, 'reasoning'):
                extracted_data['reasoning'] = prediction.reasoning
            
            # Store as metadata
            if extracted_data:
                from docex.services.metadata_service import MetadataService
                metadata_service = MetadataService(self.db)
                metadata_service.update_metadata(document.id, extracted_data)
            
            # Record success
            self._record_operation(
                document,
                status='success',
                output_metadata={
                    'extracted_fields': list(extracted_data.keys()),
                    'model': self.model_name,
                    'optimized': self.optimized_module is not None
                }
            )
            
            return ProcessingResult(
                success=True,
                metadata=extracted_data,
                content=f"Extracted {len(extracted_data)} fields using DSPy"
            )
            
        except Exception as e:
            logger.error(f"Error processing document {document.id} with DSPy: {str(e)}", exc_info=True)
            
            # Record failure
            self._record_operation(
                document,
                status='failed',
                error=str(e)
            )
            
            return ProcessingResult(
                success=False,
                error=f"DSPy processing failed: {str(e)}"
            )


class DSPySignatureBuilder:
    """
    Helper class to build DSPy signatures from YAML prompt definitions
    """
    
    @staticmethod
    def from_yaml_schema(yaml_schema: Dict[str, Any]) -> str:
        """
        Convert YAML schema to DSPy signature string
        
        Args:
            yaml_schema: Dictionary with 'schema' key containing field definitions
            
        Returns:
            DSPy signature string (e.g., "text -> field1, field2, field3")
        """
        schema = yaml_schema.get('schema', {})
        
        # Input is always document text
        inputs = "document_text"
        
        # Outputs are all schema fields
        outputs = ", ".join(schema.keys())
        
        return f"{inputs} -> {outputs}"
    
    @staticmethod
    def from_field_list(fields: List[str], input_name: str = "document_text") -> str:
        """
        Create DSPy signature from list of field names
        
        Args:
            fields: List of output field names
            input_name: Name of input field (default: "document_text")
            
        Returns:
            DSPy signature string
        """
        outputs = ", ".join(fields)
        return f"{input_name} -> {outputs}"

