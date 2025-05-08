from typing import Dict, Type, Optional
from docflow.processors.base import BaseProcessor
from docflow.db.connection import Database
from docflow.db.models import Processor, DocBasket
from docflow.processors.pdf_invoice import PDFInvoiceProcessor
from docflow.processors.mapper import ProcessorMapper

class ProcessorFactory:
    """Factory for creating and managing processor instances"""
    
    def __init__(self):
        self._processors: Dict[str, Type[BaseProcessor]] = {}
        self._instances: Dict[str, BaseProcessor] = {}
        self.mapper = ProcessorMapper()
    
    def register(self, processor_class: Type[BaseProcessor]) -> None:
        """Register a processor class"""
        if not issubclass(processor_class, BaseProcessor):
            raise ValueError(f"Processor class must inherit from BaseProcessor")
        
        processor_name = processor_class.__name__
        if processor_name in self._processors:
            raise ValueError(f"Processor {processor_name} is already registered")
        
        self._processors[processor_name] = processor_class
    
    def get_processor(self, name: str) -> Optional[BaseProcessor]:
        """Get a processor instance by name"""
        if name in self._instances:
            return self._instances[name]
        
        if name not in self._processors:
            return None
        
        # Get processor configuration from database
        db = Database()
        with db.session() as session:
            processor_model = session.query(Processor).filter_by(name=name).first()
            if not processor_model or not processor_model.enabled:
                return None
            
            # Create processor instance with configuration
            processor_class = self._processors[name]
            processor = processor_class(processor_model.config)
            self._instances[name] = processor
            return processor
    
    def list_processors(self) -> Dict[str, Type[BaseProcessor]]:
        """List all registered processors"""
        return self._processors.copy()
    
    def clear_instances(self) -> None:
        """Clear all processor instances"""
        self._instances.clear()

    def map_document_to_processor(self, document):
        return self.mapper.get_processor(document)

# Global factory instance
factory = ProcessorFactory() 