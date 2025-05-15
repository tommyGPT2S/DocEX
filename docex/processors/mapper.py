from docex.db.connection import Database
from docex.db.models import DocBasket
from docex.processors.pdf_invoice import PDFInvoiceProcessor

class ProcessorMapper:
    """DocEX processor mapper for mapping documents to appropriate processors"""
    
    def __init__(self):
        self.rules = [self.invoice_pdf_rule]

    def invoice_pdf_rule(self, document):
        """
        Rule for mapping invoice PDF documents to the PDFInvoiceProcessor
        Returns the processor class if conditions are met, None otherwise
        """
        basket_name = None
        if document.model and hasattr(document.model, 'basket_id'):
            db = Database()
            with db.session() as session:
                basket = session.query(DocBasket).filter_by(id=document.model.basket_id).first()
                if basket:
                    basket_name = basket.name
        
        # Check if document is a PDF in the invoice basket
        file_type = document.name.split('.')[-1].lower()
        if basket_name == 'invoice' and file_type == 'pdf':
            return PDFInvoiceProcessor
        return None

    def get_processor(self, document):
        """
        Get the appropriate processor for a document by evaluating all rules
        Returns the processor class if a matching rule is found, None otherwise
        """
        for rule in self.rules:
            processor = rule(document)
            if processor:
                return processor
        return None 