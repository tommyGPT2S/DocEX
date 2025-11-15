from typing import Optional
from docex.db.connection import Database
from docex.db.models import DocBasket
from docex.processors.pdf_invoice import PDFInvoiceProcessor

class ProcessorMapper:
    def __init__(self):
        self.rules = [self.invoice_pdf_rule]

    def invoice_pdf_rule(self, document, db: Optional[Database] = None):
        """
        Rule for mapping invoice PDF documents to the PDFInvoiceProcessor
        Returns the processor class if conditions are met, None otherwise
        
        Args:
            document: Document to check
            db: Optional tenant-aware database instance (for multi-tenancy support)
        """
        basket_name = None
        if document.model and hasattr(document.model, 'basket_id'):
            # Use tenant-aware database if provided, otherwise create new one
            rule_db = db or Database()
            with rule_db.session() as session:
                basket = session.query(DocBasket).filter_by(id=document.model.basket_id).first()
                if basket:
                    basket_name = basket.name
        
        # Check if document is a PDF in the invoice basket
        file_type = document.name.split('.')[-1].lower()
        if basket_name == 'invoice' and file_type == 'pdf':
            return PDFInvoiceProcessor
        return None

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