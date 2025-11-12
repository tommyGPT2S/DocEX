"""
Test LLM Adapter with Full DocEX Integration

This script tests the LLM adapter with a complete DocEX setup:
- SQLite database
- Filesystem storage
- Full document lifecycle
- Metadata management
- Operation tracking
"""

import asyncio
import os
import logging
import tempfile
from pathlib import Path
from dotenv import load_dotenv

# Load .env file
load_dotenv()

from docex import DocEX
from docex.processors.llm import OpenAIAdapter

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


async def test_invoice_processing():
    """Test invoice processing with full DocEX integration"""
    
    api_key = os.getenv('OPENAI_API_KEY')
    if not api_key:
        logger.error("❌ OPENAI_API_KEY not set in .env file!")
        return
    
    logger.info("=" * 60)
    logger.info("Test 1: Invoice Processing with DocEX")
    logger.info("=" * 60)
    
    # Initialize DocEX with SQLite (default)
    docEX = DocEX()
    
    # Create basket with filesystem storage
    import uuid
    basket_name = f'invoice_test_{uuid.uuid4().hex[:8]}'
    
    logger.info(f"📁 Creating basket: {basket_name}")
    basket = docEX.create_basket(
        basket_name,
        description="Test basket for invoice processing",
        storage_config={
            'type': 'filesystem',
            'path': f'storage/{basket_name}'
        }
    )
    logger.info(f"✅ Basket created with ID: {basket.id}")
    
    # Create test invoice file
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
    
    temp_file = Path(tempfile.gettempdir()) / f"invoice_{uuid.uuid4().hex[:8]}.txt"
    temp_file.write_text(invoice_text)
    
    try:
        # Add document to basket
        logger.info(f"📄 Adding invoice document to basket...")
        document = basket.add(
            str(temp_file),
            metadata={
                'biz_doc_type': 'invoice',
                'processing_status': 'pending',
                'source': 'test_script'
            }
        )
        logger.info(f"✅ Document added with ID: {document.id}")
        logger.info(f"   Name: {document.name}")
        logger.info(f"   Path: {document.path}")
        
        # Initialize LLM adapter
        logger.info("\n🤖 Initializing OpenAI adapter...")
        adapter = OpenAIAdapter({
            'api_key': api_key,
            'model': 'gpt-4o',
            'prompt_name': 'invoice_extraction',
            'generate_summary': False,
            'generate_embedding': False,
            'return_raw_response': True
        })
        logger.info("✅ Adapter initialized")
        
        # Process document with LLM
        logger.info("\n⚙️  Processing document with LLM adapter...")
        result = await adapter.process(document)
        
        if result.success:
            logger.info("✅ Processing successful!")
            
            # Refresh document to get updated metadata
            document = basket.get_document(document.id)
            metadata_dict = document.get_metadata_dict()  # Use get_metadata_dict() for plain dict
            
            # Helper function to extract actual value from metadata dict
            def get_meta_value(key):
                value = metadata_dict.get(key)
                if isinstance(value, dict) and 'extra' in value:
                    return value['extra'].get('value', value)
                return value
            
            logger.info("\n📊 Extracted Invoice Data:")
            logger.info(f"  Invoice Number: {get_meta_value('invoice_number')}")
            logger.info(f"  Customer ID: {get_meta_value('customer_id')}")
            logger.info(f"  Supplier ID: {get_meta_value('supplier_id')}")
            logger.info(f"  PO Number: {get_meta_value('purchase_order_number')}")
            logger.info(f"  Total Amount: ${get_meta_value('total_amount')}")
            logger.info(f"  Currency: {get_meta_value('currency')}")
            logger.info(f"  Invoice Date: {get_meta_value('invoice_date')}")
            logger.info(f"  Due Date: {get_meta_value('due_date')}")
            
            logger.info("\n📋 LLM Processing Metadata:")
            logger.info(f"  LLM Provider: {get_meta_value('llm_provider')}")
            logger.info(f"  LLM Model: {get_meta_value('llm_model')}")
            logger.info(f"  LLM Prompt: {get_meta_value('llm_prompt_name')}")
            logger.info(f"  Processed At: {get_meta_value('llm_processed_at')}")
            
            # Check line items
            line_items = get_meta_value('line_items')
            if line_items:
                import json
                if isinstance(line_items, str):
                    line_items = json.loads(line_items)
                if isinstance(line_items, list):
                    logger.info(f"\n📦 Line Items ({len(line_items)} items):")
                    for i, item in enumerate(line_items, 1):
                        if isinstance(item, dict):
                            logger.info(f"  {i}. {item.get('description')}: {item.get('quantity')} x ${item.get('unit_price')} = ${item.get('total')}")
            
            # Check operations
            logger.info("\n📝 Processing Operations:")
            operations = document.get_operations()
            for op in operations:
                logger.info(f"  - {op.operation_type}: {op.status}")
                if op.error:
                    logger.info(f"    Error: {op.error}")
            
            logger.info("\n✅ Full DocEX integration test completed successfully!")
        else:
            logger.error(f"❌ Processing failed: {result.error}")
    
    except Exception as e:
        logger.error(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
    
    finally:
        # Cleanup
        if temp_file.exists():
            temp_file.unlink()


async def test_with_summary_and_embedding():
    """Test with summary and embedding generation"""
    
    api_key = os.getenv('OPENAI_API_KEY')
    if not api_key:
        return
    
    logger.info("\n" + "=" * 60)
    logger.info("Test 2: Summary and Embedding Generation")
    logger.info("=" * 60)
    
    docEX = DocEX()
    
    import uuid
    basket_name = f'summary_test_{uuid.uuid4().hex[:8]}'
    
    basket = docEX.create_basket(
        basket_name,
        storage_config={
            'type': 'filesystem',
            'path': f'storage/{basket_name}'
        }
    )
    
    # Create test document
    document_text = """
    Artificial Intelligence and Machine Learning
    
    This document provides a comprehensive overview of artificial intelligence (AI) 
    and machine learning (ML) technologies. AI refers to the simulation of human 
    intelligence in machines, while ML is a subset of AI that enables systems to 
    learn and improve from experience without being explicitly programmed.
    
    Key topics covered include:
    - Neural networks and deep learning architectures
    - Natural language processing and understanding
    - Computer vision and image recognition
    - Reinforcement learning algorithms
    - Current trends and future directions in AI research
    
    The field is rapidly evolving with new breakthroughs in transformer models,
    large language models, and multimodal AI systems that can process text, images,
    and audio simultaneously.
    """
    
    temp_file = Path(tempfile.gettempdir()) / f"document_{uuid.uuid4().hex[:8]}.txt"
    temp_file.write_text(document_text)
    
    try:
        document = basket.add(
            str(temp_file),
            metadata={
                'biz_doc_type': 'document',
                'category': 'technical',
                'processing_status': 'pending'
            }
        )
        
        logger.info(f"✅ Document added: {document.id}")
        
        # Initialize adapter with summary and embedding
        adapter = OpenAIAdapter({
            'api_key': api_key,
            'model': 'gpt-4o',
            'prompt_name': 'generic_extraction',
            'summary_prompt_name': 'document_summary',
            'generate_summary': True,
            'generate_embedding': True,
            'return_raw_response': False
        })
        
        logger.info("⚙️  Processing with summary and embedding...")
        result = await adapter.process(document)
        
        if result.success:
            logger.info("✅ Processing successful!")
            
            document = basket.get_document(document.id)
            metadata_dict = document.get_metadata_dict()  # Use get_metadata_dict() for plain dict
            
            # Helper function to extract actual value from metadata dict
            def get_meta_value(key):
                value = metadata_dict.get(key)
                if isinstance(value, dict) and 'extra' in value:
                    return value['extra'].get('value', value)
                return value
            
            logger.info("\n📝 Summary:")
            summary = get_meta_value('llm_summary')
            if summary:
                logger.info(f"  {summary}")
            
            logger.info("\n🔢 Embedding:")
            embedding = get_meta_value('llm_embedding')
            if embedding:
                import json
                if isinstance(embedding, str):
                    embedding = json.loads(embedding)
                if isinstance(embedding, list):
                    logger.info(f"  Dimensions: {len(embedding)}")
                    logger.info(f"  First 5 values: {embedding[:5]}")
            
            logger.info("\n📋 Metadata:")
            logger.info(f"  LLM Provider: {get_meta_value('llm_provider')}")
            logger.info(f"  LLM Model: {get_meta_value('llm_model')}")
    
    finally:
        if temp_file.exists():
            temp_file.unlink()


async def test_multiple_documents():
    """Test processing multiple documents"""
    
    api_key = os.getenv('OPENAI_API_KEY')
    if not api_key:
        return
    
    logger.info("\n" + "=" * 60)
    logger.info("Test 3: Processing Multiple Documents")
    logger.info("=" * 60)
    
    docEX = DocEX()
    
    import uuid
    basket_name = f'multi_doc_test_{uuid.uuid4().hex[:8]}'
    
    basket = docEX.create_basket(
        basket_name,
        storage_config={
            'type': 'filesystem',
            'path': f'storage/{basket_name}'
        }
    )
    
    # Create multiple test documents
    documents_data = [
        {
            'name': 'invoice_1.txt',
            'content': """
            INVOICE
            Invoice Number: INV-001
            Date: 2024-01-10
            Total: $500.00
            Customer: CUST-001
            """,
            'type': 'invoice'
        },
        {
            'name': 'invoice_2.txt',
            'content': """
            INVOICE
            Invoice Number: INV-002
            Date: 2024-01-15
            Total: $750.00
            Customer: CUST-002
            """,
            'type': 'invoice'
        },
        {
            'name': 'product_desc.txt',
            'content': 'HERSHEY\'S Favorite Standard Size Variety Pack 18 Candy Bars',
            'type': 'product'
        }
    ]
    
    adapter = OpenAIAdapter({
        'api_key': api_key,
        'model': 'gpt-4o',
        'prompt_name': 'invoice_extraction',
        'generate_summary': False,
        'generate_embedding': False
    })
    
    temp_files = []
    
    try:
        for i, doc_data in enumerate(documents_data, 1):
            logger.info(f"\n📄 Processing document {i}: {doc_data['name']}")
            
            temp_file = Path(tempfile.gettempdir()) / f"{doc_data['name']}_{uuid.uuid4().hex[:8]}"
            temp_file.write_text(doc_data['content'])
            temp_files.append(temp_file)
            
            document = basket.add(
                str(temp_file),
                metadata={
                    'biz_doc_type': doc_data['type'],
                    'processing_status': 'pending'
                }
            )
            
            # Process with appropriate prompt
            if doc_data['type'] == 'product':
                adapter.config['prompt_name'] = 'product_extraction'
            else:
                adapter.config['prompt_name'] = 'invoice_extraction'
            
            result = await adapter.process(document)
            
            if result.success:
                document = basket.get_document(document.id)
                metadata_dict = document.get_metadata_dict()  # Use get_metadata_dict() for plain dict
                # Helper function to extract actual value from metadata dict
                def get_meta_value(key):
                    value = metadata_dict.get(key)
                    if isinstance(value, dict) and 'extra' in value:
                        return value['extra'].get('value', value)
                    return value
                logger.info(f"  ✅ Processed: {get_meta_value('invoice_number') or get_meta_value('product_name') or 'N/A'}")
            else:
                logger.error(f"  ❌ Failed: {result.error}")
        
        # Count documents in basket by querying database directly
        from docex.db.connection import Database
        from docex.db.models import Document as DocumentModel
        from sqlalchemy import select
        
        db = Database()
        with db.session() as session:
            query = select(DocumentModel).where(DocumentModel.basket_id == basket.id)
            documents = session.execute(query).scalars().all()
            logger.info(f"\n📁 Basket contains {len(documents)} documents")
        
        # Query by metadata
        logger.info("\n🔍 Querying documents by metadata...")
        invoices = basket.find_documents_by_metadata({'biz_doc_type': 'invoice'})
        logger.info(f"  Found {len(invoices)} invoices")
        
        products = basket.find_documents_by_metadata({'biz_doc_type': 'product'})
        logger.info(f"  Found {len(products)} products")
    
    finally:
        for temp_file in temp_files:
            if temp_file.exists():
                temp_file.unlink()


async def test_database_persistence():
    """Test that data persists in SQLite database"""
    
    api_key = os.getenv('OPENAI_API_KEY')
    if not api_key:
        return
    
    logger.info("\n" + "=" * 60)
    logger.info("Test 4: Database Persistence")
    logger.info("=" * 60)
    
    docEX = DocEX()
    
    import uuid
    basket_name = f'persistence_test_{uuid.uuid4().hex[:8]}'
    
    basket = docEX.create_basket(
        basket_name,
        storage_config={
            'type': 'filesystem',
            'path': f'storage/{basket_name}'
        }
    )
    
    # Create and process document
    temp_file = Path(tempfile.gettempdir()) / f"test_{uuid.uuid4().hex[:8]}.txt"
    temp_file.write_text("INVOICE\nInvoice Number: INV-PERSIST-001\nTotal: $100.00")
    
    try:
        document = basket.add(
            str(temp_file),
            metadata={'biz_doc_type': 'invoice'}
        )
        
        adapter = OpenAIAdapter({
            'api_key': api_key,
            'model': 'gpt-4o',
            'prompt_name': 'invoice_extraction'
        })
        
        result = await adapter.process(document)
        
        if result.success:
            doc_id = document.id
            logger.info(f"✅ Document processed: {doc_id}")
            
            # Get document again (from database)
            document2 = basket.get_document(doc_id)
            metadata = document2.get_metadata()
            
            logger.info(f"✅ Document retrieved from database: {document2.id}")
            logger.info(f"   Invoice Number: {metadata.get('invoice_number')}")
            logger.info(f"   LLM Provider: {metadata.get('llm_provider')}")
            
            # Check operations persisted
            operations = document2.get_operations()
            logger.info(f"✅ Found {len(operations)} operations in database")
            for op in operations:
                logger.info(f"   - {op.get('type', 'unknown')}: {op.get('status', 'unknown')}")
    
    finally:
        if temp_file.exists():
            temp_file.unlink()


async def main():
    """Run all integration tests"""
    
    logger.info("🚀 LLM Adapter - Full DocEX Integration Test")
    logger.info("=" * 60)
    logger.info("Testing with:")
    logger.info("  - SQLite database")
    logger.info("  - Filesystem storage")
    logger.info("  - Full document lifecycle")
    logger.info("  - Metadata management")
    logger.info("  - Operation tracking")
    logger.info("=" * 60)
    
    if not os.getenv('OPENAI_API_KEY'):
        logger.error("❌ OPENAI_API_KEY not set!")
        logger.info("\nPlease add it to your .env file:")
        logger.info("  OPENAI_API_KEY=sk-your-key-here")
        return
    
    try:
        # Run all tests
        await test_invoice_processing()
        await test_with_summary_and_embedding()
        await test_multiple_documents()
        await test_database_persistence()
        
        logger.info("\n" + "=" * 60)
        logger.info("🎉 All integration tests completed!")
        logger.info("=" * 60)
    
    except KeyboardInterrupt:
        logger.info("\n⚠️  Tests interrupted")
    except Exception as e:
        logger.error(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())

