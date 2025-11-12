"""
Test LLM Adapter with Real OpenAI API Key

This script demonstrates how to use the LLM adapter with a real OpenAI API key.
"""

import asyncio
import os
import logging
from pathlib import Path
import tempfile
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


async def test_with_real_openai():
    """Test LLM adapter with real OpenAI API key"""
    
    # Check for API key
    api_key = os.getenv('OPENAI_API_KEY')
    if not api_key:
        logger.error("❌ OPENAI_API_KEY environment variable not set!")
        logger.info("\nTo set it, run:")
        logger.info("  export OPENAI_API_KEY='your-api-key-here'")
        logger.info("\nOr create a .env file with:")
        logger.info("  OPENAI_API_KEY=your-api-key-here")
        return
    
    logger.info("=" * 60)
    logger.info("Testing LLM Adapter with Real OpenAI API")
    logger.info("=" * 60)
    
    # Initialize DocEX with filesystem storage for testing
    docEX = DocEX()
    
    # Get or create basket with filesystem storage (simpler for testing)
    import uuid
    basket_name = f'test_llm_{uuid.uuid4().hex[:8]}'  # Unique name to avoid conflicts
    basket = docEX.create_basket(
        basket_name,
        storage_config={
            'type': 'filesystem',
            'path': f'storage/{basket_name}'
        }
    )
    
    # Create a test document
    test_text = """
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
    
    # Create temporary file
    temp_file = Path(tempfile.gettempdir()) / "test_invoice.txt"
    temp_file.write_text(test_text)
    
    try:
        logger.info("📄 Adding test document to basket...")
        document = basket.add(
            str(temp_file),
            metadata={
                'biz_doc_type': 'invoice',
                'processing_status': 'pending'
            }
        )
        logger.info(f"✅ Document added with ID: {document.id}")
        
        # Initialize OpenAI adapter with invoice extraction prompt
        logger.info("\n🤖 Initializing OpenAI adapter...")
        adapter = OpenAIAdapter({
            'api_key': api_key,  # Use real API key
            'model': 'gpt-4o',   # or 'gpt-4', 'gpt-3.5-turbo', etc.
            'prompt_name': 'invoice_extraction',  # Uses docex/prompts/invoice_extraction.yaml
            'generate_summary': False,
            'generate_embedding': False,
            'return_raw_response': True
        })
        logger.info("✅ Adapter initialized")
        
        # Process document
        logger.info("\n⚙️  Processing document with OpenAI...")
        result = await adapter.process(document)
        
        if result.success:
            logger.info("✅ Processing successful!")
            logger.info("\n📊 Extracted Data:")
            logger.info(f"  {result.content}")
            
            # Check metadata
            metadata = document.get_metadata()
            logger.info("\n📋 Document Metadata:")
            logger.info(f"  Invoice Number: {metadata.get('invoice_number')}")
            logger.info(f"  Customer ID: {metadata.get('customer_id')}")
            logger.info(f"  Supplier ID: {metadata.get('supplier_id')}")
            logger.info(f"  PO Number: {metadata.get('purchase_order_number')}")
            logger.info(f"  Total Amount: ${metadata.get('total_amount')}")
            logger.info(f"  Currency: {metadata.get('currency')}")
            logger.info(f"  LLM Provider: {metadata.get('llm_provider')}")
            logger.info(f"  LLM Model: {metadata.get('llm_model')}")
            logger.info(f"  LLM Prompt: {metadata.get('llm_prompt_name')}")
        else:
            logger.error(f"❌ Processing failed: {result.error}")
    
    except Exception as e:
        logger.error(f"❌ Error: {str(e)}")
        import traceback
        traceback.print_exc()
    
    finally:
        # Cleanup
        if temp_file.exists():
            temp_file.unlink()
            logger.info("\n🧹 Cleaned up temporary file")


async def test_with_summary_and_embedding():
    """Test with summary and embedding generation"""
    
    api_key = os.getenv('OPENAI_API_KEY')
    if not api_key:
        logger.error("❌ OPENAI_API_KEY not set!")
        return
    
    logger.info("\n" + "=" * 60)
    logger.info("Testing with Summary and Embedding Generation")
    logger.info("=" * 60)
    
    docEX = DocEX()
    
    # Create basket with filesystem storage (unique name)
    import uuid
    basket_name = f'test_llm_summary_{uuid.uuid4().hex[:8]}'
    basket = docEX.create_basket(
        basket_name,
        storage_config={
            'type': 'filesystem',
            'path': f'storage/{basket_name}'
        }
    )
    
    test_text = """
    This is a sample document about artificial intelligence and machine learning.
    It discusses various topics including neural networks, deep learning, and
    natural language processing. The document provides an overview of current
    trends and future directions in AI research.
    """
    
    temp_file = Path(tempfile.gettempdir()) / "test_document.txt"
    temp_file.write_text(test_text)
    
    try:
        document = basket.add(
            str(temp_file),
            metadata={'biz_doc_type': 'document'}
        )
        
        # Initialize adapter with summary and embedding
        adapter = OpenAIAdapter({
            'api_key': api_key,
            'model': 'gpt-4o',
            'prompt_name': 'generic_extraction',
            'summary_prompt_name': 'document_summary',
            'generate_summary': True,      # Generate summary
            'generate_embedding': True,    # Generate embedding
            'return_raw_response': False
        })
        
        logger.info("⚙️  Processing with summary and embedding...")
        result = await adapter.process(document)
        
        if result.success:
            logger.info("✅ Processing successful!")
            metadata = document.get_metadata()
            logger.info(f"\n📝 Summary: {metadata.get('llm_summary')}")
            logger.info(f"🔢 Embedding: {len(metadata.get('llm_embedding', ''))} characters")
            logger.info(f"🤖 Provider: {metadata.get('llm_provider')}")
            logger.info(f"🤖 Model: {metadata.get('llm_model')}")
    
    finally:
        if temp_file.exists():
            temp_file.unlink()


def main():
    """Main entry point"""
    
    logger.info("🚀 LLM Adapter Real API Test")
    logger.info("=" * 60)
    
    # Check for API key
    if not os.getenv('OPENAI_API_KEY'):
        logger.error("❌ OPENAI_API_KEY environment variable not set!")
        logger.info("\n📝 How to set your OpenAI API key:")
        logger.info("\n1. Get your API key from: https://platform.openai.com/api-keys")
        logger.info("\n2. Set it as an environment variable:")
        logger.info("   export OPENAI_API_KEY='sk-...'")
        logger.info("\n3. Or create a .env file in the project root:")
        logger.info("   echo 'OPENAI_API_KEY=sk-...' > .env")
        logger.info("\n4. Then run this script again")
        return
    
    try:
        # Run tests
        asyncio.run(test_with_real_openai())
        asyncio.run(test_with_summary_and_embedding())
        
        logger.info("\n" + "=" * 60)
        logger.info("🎉 All tests completed!")
        logger.info("=" * 60)
    
    except KeyboardInterrupt:
        logger.info("\n⚠️  Test interrupted by user")
    except Exception as e:
        logger.error(f"❌ Test failed: {str(e)}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()

