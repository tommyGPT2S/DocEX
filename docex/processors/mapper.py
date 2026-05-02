from typing import Optional
from docex.db.connection import Database

class ProcessorMapper:
    def __init__(self):
        self.rules = []

    def get_processor(self, document, db: Optional[Database] = None):
        """
        Get the appropriate processor for a document by evaluating all rules
        Returns the processor class if a matching rule is found, None otherwise
        
        Args:
            document: Document to get processor for
            db: Optional tenant-aware database instance (for multi-tenancy support)
        """
        for rule in self.rules:
            processor = rule(document, db=db)
            if processor:
                return processor
        return None 
