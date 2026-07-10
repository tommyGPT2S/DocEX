"""
Example: Configurable field extraction with traceable results.

Adds the sample invoice PDF to a basket, extracts the fields defined in a
config (label phrases + type, no regular expressions required), and stores
each found value as document metadata together with how it was found:

    total                12500.00
    total_source         regex        (or: llm)
    total_source_label   Total Due    (the label text that identified it)
    needs_review         true/false   (any field missing or conflicting)

The extraction runs rules-first. To resolve fields whose labels are worded
unexpectedly (abbreviations, synonyms), pass an llm_fn callable:

    def my_llm(prompt: str) -> str:
        return my_provider.complete(prompt)   # returns the model's JSON reply

    processor = FieldExtractionProcessor(llm_fn=my_llm)

Note: DocEX must be initialized first using the CLI command 'docex init'.
Requires the pdf extra for the sample PDF: pip install docex[pdf]
"""

import logging
import sys

from docex import DocEX
from docex.context import UserContext
from docex.extraction import ExtractionConfig, FieldExtractionProcessor

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Fields to extract: plain phrases and a type. Fully user-definable;
# omit this to use the packaged commercial real estate default set.
FIELDS = {
    'invoice_number': {'type': 'text', 'labels': ['Invoice No.', 'Invoice Number']},
    'invoice_date': {'type': 'date', 'labels': ['Invoice Date', 'Date']},
    'po_number': {'type': 'text', 'labels': ['PO number', 'Purchase Order']},
    'total': {'type': 'money', 'labels': ['Total Due', 'Amount Due', 'Total']},
}


def main():
    user_context = UserContext(user_id='extraction_example', user_email='example@example.com')
    docEX = DocEX(user_context=user_context)
    basket = docEX.basket('extraction_example')

    doc = basket.add('examples/sample_data/invoice_2001321.pdf', metadata={'biz_doc_type': 'invoice'})
    logger.info(f"Added document {doc.id}")

    processor = FieldExtractionProcessor(extraction_config=ExtractionConfig.from_dict(FIELDS))
    result = processor.process(doc)
    if not result.success:
        logger.error(f"Extraction failed: {result.error}")
        sys.exit(1)

    logger.info("Stored metadata:")
    for key, value in sorted(doc.get_metadata().items()):
        logger.info(f"  {key} = {value}")

    # The stored fields are immediately searchable.
    flagged = basket.find_documents_by_metadata({'needs_review': 'true'})
    logger.info(f"Documents needing review in this basket: {len(flagged)}")


if __name__ == '__main__':
    main()
