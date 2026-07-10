"""
Invoice Processing at Scale Example

Demonstrates the complete invoice processing pipeline:
1. Ingest invoice documents
2. Extract structured data using LLM
3. Validate and normalize data
4. Route based on confidence (human review vs auto-approve)
5. Batch processing with job queue
"""

import asyncio
import logging
import os
import sys
from datetime import datetime
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from docex import DocEX
from docex.docbasket import DocBasket
from docex.document import Document
from docex.services.invoice_service import InvoiceService
from docex.processors.invoice import (
    InvoicePipeline,
    InvoiceExtractor,
    InvoiceValidator,
    InvoiceNormalizer,
    process_invoice
)
from docex.models.invoice import (
    InvoiceData,
    InvoiceStatus,
    InvoiceProcessingConfig
)
from docex.jobs import (
    JobQueue,
    JobPriority,
    Worker,
    WorkerConfig,
    RateLimiter,
    RateLimitConfig,
    CostTracker
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


# Sample invoice text for testing
SAMPLE_INVOICE_TEXT = """
INVOICE

Invoice Number: INV-2024-001234
Date: January 15, 2024
Due Date: February 15, 2024

FROM:
Acme Corporation
123 Business Street
Suite 456
San Francisco, CA 94102
Tax ID: 12-3456789
Email: billing@acmecorp.com

BILL TO:
Widget Industries Inc.
789 Commerce Ave
New York, NY 10001
Customer ID: CUST-5678

ITEMS:
Description                 Qty    Unit Price    Total
----------------------------------------------------
Professional Services       10     $150.00       $1,500.00
Software License           1      $2,500.00     $2,500.00
Support Package (Annual)   1      $500.00       $500.00

                           Subtotal:    $4,500.00
                           Tax (8.5%):  $382.50
                           TOTAL:       $4,882.50

Payment Terms: Net 30
Please make payment to: Acme Corporation
Bank: First National Bank
Account: 1234567890

Thank you for your business!
"""


async def example_single_invoice():
    """Example: Process a single invoice"""
    print("\n" + "="*60)
    print("Example 1: Process Single Invoice")
    print("="*60)
    
    # Initialize DocEX
    docex = DocEX()
    
    # Create a basket for invoices
    basket = docex.create_basket(
        name=f"invoices_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
        storage_config={'base_path': './storage/invoices'}
    )
    
    print(f"[OK] Created basket: {basket.name}")
    
    # Create a test document by writing to a temp file first
    import tempfile
    with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
        f.write(SAMPLE_INVOICE_TEXT)
        temp_path = f.name
    
    doc = basket.add(temp_path)
    
    # Clean up temp file
    import os
    os.unlink(temp_path)
    
    print(f"[OK] Created document: {doc.name}")
    
    # Get LLM adapter (use local Ollama or configure OpenAI)
    llm_adapter = None
    try:
        from docex.processors.llm import LocalLLMAdapter
        llm_adapter = LocalLLMAdapter({
            'model': 'llama3.2',
            'base_url': 'http://localhost:11434'
        })
        print("[OK] Using Ollama LLM adapter")
    except Exception as e:
        print(f"[WARN] Could not initialize LLM adapter: {e}")
        print("      Skipping LLM extraction, using validation only")
    
    # Process using the pipeline
    if llm_adapter:
        pipeline = InvoicePipeline({
            'llm_adapter': llm_adapter,
            'processing_config': {
                'confidence_threshold': 0.8,
                'auto_approve_threshold': 0.95,
                'enable_ocr': False
            }
        }, docex.db)
        
        result = await pipeline.process(doc)
        
        if result.success:
            print(f"[OK] Invoice processed successfully")
            print(f"    Status: {result.metadata.get('status')}")
            print(f"    Needs Review: {result.metadata.get('needs_review')}")
            print(f"    Time: {result.metadata.get('total_time_ms')}ms")
            
            # Show extracted data
            if result.content:
                invoice_data = result.content.get('raw_json', {})
                print(f"\nExtracted Data:")
                print(f"    Invoice Number: {invoice_data.get('invoice_number', 'N/A')}")
                print(f"    Total Amount: {invoice_data.get('total_amount', 'N/A')}")
                print(f"    Confidence: {invoice_data.get('confidence_score', 'N/A')}")
        else:
            print(f"[WARN] Invoice processing failed: {result.error}")
    
    # Demonstrate validation without LLM
    print("\n--- Validation Only Demo ---")
    
    # Create sample extracted data
    sample_data = {
        'invoice_number': 'INV-2024-001234',
        'total_amount': 4882.50,
        'subtotal': 4500.00,
        'tax_amount': 382.50,
        'currency': 'USD',
        'invoice_date': '2024-01-15',
        'due_date': '2024-02-15',
        'confidence_score': 0.92,
        'supplier': {
            'name': 'Acme Corporation',
            'tax_id': '12-3456789',
            'email': 'billing@acmecorp.com'
        },
        'customer': {
            'name': 'Widget Industries Inc.',
            'id': 'CUST-5678'
        },
        'line_items': [
            {'description': 'Professional Services', 'quantity': 10, 'unit_price': 150.00, 'total': 1500.00},
            {'description': 'Software License', 'quantity': 1, 'unit_price': 2500.00, 'total': 2500.00},
            {'description': 'Support Package', 'quantity': 1, 'unit_price': 500.00, 'total': 500.00}
        ]
    }
    
    # Validate using Pydantic model
    try:
        invoice = InvoiceData(**sample_data)
        print(f"[OK] Invoice validated successfully")
        print(f"    Invoice Number: {invoice.invoice_number}")
        print(f"    Total: {invoice.currency.value} {invoice.total_amount}")
        print(f"    Line Items: {len(invoice.line_items)}")
        print(f"    Needs Review: {invoice.needs_review()}")
        
        # Show validation errors
        errors = invoice.get_validation_errors()
        if errors:
            print(f"    Warnings: {len(errors)}")
            for err in errors:
                print(f"      - {err.field}: {err.message}")
    except Exception as e:
        print(f"[WARN] Validation failed: {e}")
    
    # Return doc for use in later examples
    return doc


async def example_invoice_service():
    """Example: Use InvoiceService for batch processing"""
    print("\n" + "="*60)
    print("Example 2: Invoice Service with Batch Processing")
    print("="*60)
    
    # Initialize
    docex = DocEX()
    
    # Get LLM adapter
    llm_adapter = None
    try:
        from docex.processors.llm import LocalLLMAdapter
        llm_adapter = LocalLLMAdapter({
            'model': 'llama3.2',
            'base_url': 'http://localhost:11434'
        })
    except Exception:
        print("[WARN] LLM adapter not available")
    
    # Create invoice service
    config = InvoiceProcessingConfig(
        confidence_threshold=0.8,
        auto_approve_threshold=0.95,
        enable_ocr=True
    )
    
    service = InvoiceService(docex.db, llm_adapter, config)
    print("[OK] InvoiceService initialized")
    
    # Get processing stats
    stats = service.get_processing_stats()
    print(f"\nProcessing Statistics:")
    print(f"    Total Invoices: {stats['total']}")
    print(f"    Needs Review: {stats['needs_review']}")
    print(f"    Approved: {stats['approved']}")
    print(f"    Avg Confidence: {stats['avg_confidence']:.2%}")
    
    return service


async def example_job_queue(doc_id: str = None):
    """Example: Use job queue for async processing"""
    print("\n" + "="*60)
    print("Example 3: Job Queue for Async Processing")
    print("="*60)
    
    # Initialize
    docex = DocEX()
    
    # Create job queue
    queue = JobQueue(docex.db)
    print("[OK] JobQueue initialized")
    
    # If no document ID provided, just show queue stats
    if not doc_id:
        print("[INFO] Skipping job enqueue - no document ID provided")
        stats = queue.get_queue_stats()
        print(f"\nQueue Statistics:")
        print(f"    Total Jobs: {stats['total']}")
        print(f"    By Status: {stats['by_status']}")
        print(f"    By Type: {stats['by_type']}")
        return queue
    
    # Enqueue a job for the actual document
    job_id = queue.enqueue(
        document_id=doc_id,
        operation_type='INVOICE_EXTRACTION',
        priority=JobPriority.NORMAL,
        idempotency_key=f"invoice_job_{doc_id}_{datetime.now().timestamp()}"
    )
    print(f"[OK] Enqueued job: {job_id}")
    
    # Check queue stats
    stats = queue.get_queue_stats()
    print(f"\nQueue Statistics:")
    print(f"    Total Jobs: {stats['total']}")
    print(f"    By Status: {stats['by_status']}")
    print(f"    By Type: {stats['by_type']}")
    
    # Check job status
    status = queue.get_job_status(job_id)
    print(f"\nJob {job_id}:")
    print(f"    Status: {status.get('status')}")
    print(f"    Created: {status.get('created_at')}")
    
    return queue


async def example_rate_limiter():
    """Example: Rate limiting for LLM calls"""
    print("\n" + "="*60)
    print("Example 4: Rate Limiting for LLM Calls")
    print("="*60)
    
    # Create rate limiter
    config = RateLimitConfig(
        requests_per_minute=10,
        requests_per_hour=100,
        tokens_per_day=1000000,
        cost_per_day=10.0
    )
    
    limiter = RateLimiter(config, tenant_id='demo_tenant')
    print("[OK] RateLimiter initialized")
    
    # Create cost tracker
    tracker = CostTracker()
    
    # Simulate some API calls
    print("\nSimulating API calls...")
    for i in range(5):
        await limiter.acquire()
        
        # Simulate token usage
        input_tokens = 500
        output_tokens = 200
        
        limiter.record_usage(tokens=input_tokens + output_tokens)
        cost = tracker.record('gpt-3.5-turbo', input_tokens, output_tokens)
        
        print(f"    Request {i+1}: {input_tokens + output_tokens} tokens, ${cost:.6f}")
    
    # Get usage stats
    usage = limiter.get_usage()
    print(f"\nUsage Statistics:")
    print(f"    Requests (minute): {usage['requests']['minute']}")
    print(f"    Tokens (day): {usage['tokens']['day']}")
    
    # Get cost summary
    costs = tracker.get_summary()
    print(f"\nCost Summary:")
    print(f"    Total Cost: ${costs['total_cost']:.6f}")
    
    return limiter


async def example_normalizer():
    """Example: Invoice data normalization"""
    print("\n" + "="*60)
    print("Example 5: Invoice Data Normalization")
    print("="*60)
    
    # Raw extracted data with various formats
    raw_data = {
        'invoice_number': '  INV-2024-001  ',
        'total_amount': '$4,882.50',
        'subtotal': '4500',
        'tax_amount': 382.5,
        'currency': '$',
        'invoice_date': '01/15/2024',  # US format
        'due_date': 'February 15, 2024',  # Text format
        'supplier': {
            'name': '  Acme Corporation  ',
            'tax_id': '12-345-6789',  # With dashes
            'email': 'BILLING@ACMECORP.COM'  # Uppercase
        },
        'customer': {
            'name': 'Widget Industries',
            'address': {
                'line1': '789 Commerce Ave',
                'city': 'new york',
                'state': 'ny',
                'postal_code': '10001-1234',
                'country': 'USA'
            }
        },
        'line_items': [
            {'description': '  Services  ', 'quantity': '10', 'unit_price': '$150', 'total': '1500'}
        ]
    }
    
    print("Before Normalization:")
    print(f"    Invoice Date: {raw_data['invoice_date']}")
    print(f"    Currency: {raw_data['currency']}")
    print(f"    Supplier Email: {raw_data['supplier']['email']}")
    print(f"    Customer Country: {raw_data['customer']['address']['country']}")
    
    # Normalize
    from docex.processors.invoice.normalizer import normalize_invoice_dict
    
    normalized = normalize_invoice_dict(raw_data)
    
    print("\nAfter Normalization:")
    print(f"    Invoice Date: {normalized.get('invoice_date')}")
    print(f"    Currency: {normalized.get('currency')}")
    print(f"    Supplier Email: {normalized.get('supplier', {}).get('email')}")
    print(f"    Supplier Dedup Key: {normalized.get('supplier', {}).get('normalized_key')}")
    print(f"    Customer Country: {normalized.get('customer', {}).get('address', {}).get('country')}")
    print(f"    Total Amount: {normalized.get('total_amount')}")
    
    return normalized


async def main():
    """Run all examples"""
    print("\n" + "#"*60)
    print("# Invoice Processing at Scale - Examples")
    print("#"*60)
    
    try:
        # Run examples and capture document ID for later use
        doc = await example_single_invoice()
        doc_id = doc.id if doc and hasattr(doc, 'id') else None
        
        await example_invoice_service()
        await example_job_queue(doc_id)
        await example_rate_limiter()
        await example_normalizer()
        
        print("\n" + "="*60)
        print("[OK] All examples completed successfully!")
        print("="*60)
        
    except Exception as e:
        logger.exception(f"Example failed: {e}")
        raise


if __name__ == "__main__":
    asyncio.run(main())

