"""
Example: Batch ingestion of a folder of documents.

Creates a small inbox folder, files everything in it into a basket in one
call, and prints the report. Run it twice to see duplicate skipping: the
second run adds nothing, so a nightly job can point at the same folder and
only pick up new files.

To also extract fields from each document as it is filed, pass any DocEX
processor:

    ingestor = BatchIngestor(basket, processor=my_processor)

Processors that separate parsing from persistence (read_text /
extract_from_text / save_results) get their parsing parallelized across a
thread pool; database writes always stay on a single thread.

Note: DocEX must be initialized first using the CLI command 'docex init'.
"""

import logging
from pathlib import Path

from docex import DocEX
from docex.batch import BatchIngestor
from docex.context import UserContext

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

SAMPLE_INVOICES = {
    'invoice_april.txt': "Invoice No.: 2024-0104\nTotal Due: $12,500.00\n",
    'invoice_may.txt': "Invoice No.: 2024-0105\nTotal Due: $12,500.00\n",
    'invoice_june.txt': "Invoice No.: 2024-0106\nTotal Due: $13,100.00\n",
}


def main():
    inbox = Path('examples/sample_data/batch_inbox')
    inbox.mkdir(parents=True, exist_ok=True)
    for name, content in SAMPLE_INVOICES.items():
        (inbox / name).write_text(content)

    user_context = UserContext(user_id='batch_example', user_email='example@example.com')
    docEX = DocEX(user_context=user_context)
    basket = docEX.basket('batch_example')

    ingestor = BatchIngestor(basket)

    report = ingestor.ingest_folder(str(inbox), pattern='*.txt')
    logger.info(f"First run:  {report.summary()}")
    for outcome in report.outcomes:
        logger.info(f"  {outcome.status:18} {Path(outcome.path).name}  {outcome.reason or ''}")

    # Second run over the same folder: everything is recognized and skipped.
    report = ingestor.ingest_folder(str(inbox), pattern='*.txt')
    logger.info(f"Second run: {report.summary()}")
    logger.info(f"Documents in basket: {basket.count_documents()}")


if __name__ == '__main__':
    main()
