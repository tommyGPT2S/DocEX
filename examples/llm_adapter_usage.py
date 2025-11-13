"""
Example: Using LLM Adapter with External Prompts

This example demonstrates how to use the OpenAI adapter with prompts
stored in external YAML files.

Security Best Practices:
- Always use UserContext for audit logging
- UserContext enables operation tracking and multi-tenant support
- For multi-tenant applications, provide tenant_id in UserContext
"""

import asyncio
import os
import logging
from pathlib import Path

from docex import DocEX
from docex.context import UserContext
from docex.processors.llm import OpenAIAdapter

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def example_invoice_extraction():
    """Example: Extract invoice data using external prompt"""
    
    logger.info("=" * 60)
    logger.info("Example: Invoice Data Extraction with External Prompts")
    logger.info("=" * 60)
    
    # Create UserContext for audit logging
    user_context = UserContext(
        user_id="llm_user",
        user_email="llm@example.com",
        tenant_id="example_tenant",  # Optional: for multi-tenant applications
        roles=["user"]
    )
    
    # Initialize DocEX with UserContext (enables audit logging)
    docEX = DocEX(user_context=user_context)
    
    # Create a basket for invoices
    basket = docEX.basket('invoices')
    
    # Initialize OpenAI adapter with invoice extraction prompt
    adapter = OpenAIAdapter({
        'api_key': os.getenv('OPENAI_API_KEY'),
        'model': 'gpt-4o',
        'prompt_name': 'invoice_extraction',  # Uses docex/prompts/invoice_extraction.yaml
        'generate_summary': False,
        'generate_embedding': False,
        'return_raw_response': True
    })
    
    # Example invoice text (in real usage, this would come from a PDF)
    invoice_text = """
    INVOICE
    
    Invoice Number: INV-2024-001
    Date: 2024-02-15
    Due Date: 2024-03-15
    
    Bill To:
    Customer ID: CUST-001
    Store: Main Store
    
    From:
    Supplier ID: SUP-001
    Supplier: ABC Company
    
    Purchase Order: PO-12345
    
    Description          Qty    Unit Price    Total
    Product A            100   $10.00        $1000.00
    Product B            50    $20.00        $1000.00
    
    Total Amount: $2000.00 USD
    """
    
    # Create a temporary text file for the invoice
    temp_file = Path('/tmp/example_invoice.txt')
    temp_file.write_text(invoice_text)
    
    try:
        # Add invoice to basket
        logger.info("📄 Adding invoice to basket...")
        document = basket.add(
            str(temp_file),
            metadata={
                'biz_doc_type': 'invoice',
                'processing_status': 'pending'
            }
        )
        
        logger.info(f"✅ Document added with ID: {document.id}")
        
        # Process document with LLM adapter
        logger.info("🤖 Processing document with OpenAI adapter...")
        result = await adapter.process(document)
        
        if result.success:
            logger.info("✅ Processing successful!")
            logger.info(f"📊 Extracted data: {result.content}")
            
            # Check metadata
            metadata = document.get_metadata()
            logger.info("\n📋 Document Metadata:")
            logger.info(f"  Invoice Number: {metadata.get('invoice_number')}")
            logger.info(f"  Customer ID: {metadata.get('customer_id')}")
            logger.info(f"  Supplier ID: {metadata.get('supplier_id')}")
            logger.info(f"  Total Amount: ${metadata.get('total_amount')}")
            logger.info(f"  LLM Provider: {metadata.get('llm_provider')}")
            logger.info(f"  LLM Model: {metadata.get('llm_model')}")
        else:
            logger.error(f"❌ Processing failed: {result.error}")
    
    finally:
        # Clean up temp file
        if temp_file.exists():
            temp_file.unlink()


async def example_product_extraction():
    """Example: Extract product data using external prompt"""
    
    logger.info("\n" + "=" * 60)
    logger.info("Example: Product Data Extraction with External Prompts")
    logger.info("=" * 60)
    
    # Create UserContext for audit logging
    user_context = UserContext(
        user_id="llm_user",
        user_email="llm@example.com",
        tenant_id="example_tenant",
        roles=["user"]
    )
    
    # Initialize DocEX with UserContext
    docEX = DocEX(user_context=user_context)
    
    # Create a basket for products
    basket = docEX.basket('products')
    
    # Initialize OpenAI adapter with product extraction prompt
    adapter = OpenAIAdapter({
        'api_key': os.getenv('OPENAI_API_KEY'),
        'model': 'gpt-4o',
        'prompt_name': 'product_extraction',  # Uses docex/prompts/product_extraction.yaml
        'generate_summary': False,
        'generate_embedding': False
    })
    
    # Example product descriptions
    product_descriptions = [
        "HERSHEY'S Favorite Standard Size Variety Pack 18 Candy Bars",
        "Coca-Cola Classic 24 Pack 12 oz Cans",
        "Lay's Classic Potato Chips Family Size 15 oz Bag"
    ]
    
    for i, description in enumerate(product_descriptions, 1):
        logger.info(f"\n📦 Processing Product {i}: {description}")
        
        # Create a temporary text file
        temp_file = Path(f'/tmp/product_{i}.txt')
        temp_file.write_text(description)
        
        try:
            # Add product to basket
            document = basket.add(
                str(temp_file),
                metadata={
                    'biz_doc_type': 'product',
                    'processing_status': 'pending'
                }
            )
            
            # Process document with LLM adapter
            result = await adapter.process(document)
            
            if result.success:
                logger.info("✅ Extraction successful!")
                extracted = result.content
                logger.info(f"  Product Name: {extracted.get('product_name')}")
                logger.info(f"  Brand: {extracted.get('brand')}")
                logger.info(f"  Case Pack: {extracted.get('case_pack')}")
                logger.info(f"  Unit Type: {extracted.get('unit_type')}")
                logger.info(f"  Confidence: {extracted.get('confidence_score')}")
            else:
                logger.error(f"❌ Extraction failed: {result.error}")
        
        finally:
            # Clean up temp file
            if temp_file.exists():
                temp_file.unlink()


async def example_with_summary_and_embedding():
    """Example: Generate summary and embedding using external prompts"""
    
    logger.info("\n" + "=" * 60)
    logger.info("Example: Summary and Embedding Generation")
    logger.info("=" * 60)
    
    # Create UserContext for audit logging
    user_context = UserContext(
        user_id="llm_user",
        user_email="llm@example.com",
        tenant_id="example_tenant",
        roles=["user"]
    )
    
    # Initialize DocEX with UserContext
    docEX = DocEX(user_context=user_context)
    
    # Create a basket for documents
    basket = docEX.basket('documents')
    
    # Initialize OpenAI adapter with summary and embedding generation
    adapter = OpenAIAdapter({
        'api_key': os.getenv('OPENAI_API_KEY'),
        'model': 'gpt-4o',
        'prompt_name': 'generic_extraction',
        'summary_prompt_name': 'document_summary',
        'generate_summary': True,  # Generate summary
        'generate_embedding': True,  # Generate embedding
        'return_raw_response': False
    })
    
    # Example document text
    document_text = """
    This is a sample document about artificial intelligence and machine learning.
    It discusses various topics including neural networks, deep learning, and
    natural language processing. The document provides an overview of current
    trends and future directions in AI research.
    """
    
    # Create a temporary text file
    temp_file = Path('/tmp/example_document.txt')
    temp_file.write_text(document_text)
    
    try:
        # Add document to basket
        logger.info("📄 Adding document to basket...")
        document = basket.add(
            str(temp_file),
            metadata={
                'biz_doc_type': 'document',
                'processing_status': 'pending'
            }
        )
        
        # Process document with LLM adapter
        logger.info("🤖 Processing document with OpenAI adapter...")
        result = await adapter.process(document)
        
        if result.success:
            logger.info("✅ Processing successful!")
            
            # Check metadata
            metadata = document.get_metadata()
            logger.info("\n📋 Document Metadata:")
            logger.info(f"  LLM Summary: {metadata.get('llm_summary')}")
            logger.info(f"  Has Embedding: {'llm_embedding' in metadata}")
            logger.info(f"  LLM Provider: {metadata.get('llm_provider')}")
            logger.info(f"  LLM Model: {metadata.get('llm_model')}")
        else:
            logger.error(f"❌ Processing failed: {result.error}")
    
    finally:
        # Clean up temp file
        if temp_file.exists():
            temp_file.unlink()


async def main():
    """Run all examples"""
    
    # Check for OpenAI API key
    if not os.getenv('OPENAI_API_KEY'):
        logger.error("❌ Please set OPENAI_API_KEY environment variable")
        return
    
    try:
        # Run examples
        await example_invoice_extraction()
        await example_product_extraction()
        await example_with_summary_and_embedding()
        
        logger.info("\n" + "=" * 60)
        logger.info("🎉 All examples completed!")
        logger.info("=" * 60)
    
    except Exception as e:
        logger.error(f"❌ Example failed: {str(e)}")
        raise


if __name__ == "__main__":
    asyncio.run(main())

