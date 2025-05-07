from docflow.db.connection import Database
from docflow.db.models import DocBasket
from docflow.processors.pdf_to_text import MatchingInvoiceToPOProcessor

class ProcessorMapper:
    def __init__(self):
        self.rules = [self.invoice_pdf_rule]

    def invoice_pdf_rule(self, document):
        basket_name = None
        if document.model and hasattr(document.model, 'basket_id'):
            db = Database()
            with db.session() as session:
                basket = session.query(DocBasket).filter_by(id=document.model.basket_id).first()
                if basket:
                    basket_name = basket.name
        file_type = document.name.split('.')[-1].lower()
        if basket_name == 'invoice' and file_type == 'pdf':
            return MatchingInvoiceToPOProcessor
        return None

    def get_processor(self, document):
        for rule in self.rules:
            processor = rule(document)
            if processor:
                return processor
        return None 