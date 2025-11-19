"""
Claude (Anthropic) LLM Adapter Example

This example demonstrates how to use the Claude adapter with DocEX.
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
from docex.processors.llm import ClaudeAdapter

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


async def test_claude_basic():
    """Test Claude adapter with basic document processing"""
    
    # Check if API key is available
    api_key = os.getenv('ANTHROPIC_API_KEY')
    if not api_key:
        logger.error("❌ ANTHROPIC_API_KEY not found in environment variables")
        logger.info("Please set your Anthropic API key:")
        logger.info("export ANTHROPIC_API_KEY='your-api-key-here'")
        return
    
    try:
        # Initialize DocEX
        logger.info("🚀 Initializing DocEX...")
        docex = DocEX()
        basket = docex.basket('claude_test')
        
        # Create a sample document
        sample_text = """
        Invoice #INV-2024-001
        Date: November 18, 2024
        From: Tech Solutions Inc.
        To: ABC Corporation
        
        Items:
        - Software License: $500.00
        - Support Contract: $200.00
        - Training: $300.00
        
        Total: $1,000.00
        Payment Due: December 18, 2024
        """
        
        # Create temporary file
        temp_file = Path(tempfile.mktemp(suffix='.txt'))
        temp_file.write_text(sample_text)
        
        logger.info(f"📄 Created sample document at: {temp_file}")
        
        # Add document to basket
        document = basket.add(str(temp_file))
        logger.info(f"📋 Added document to basket: {document.id}")
        
        # Initialize Claude adapter
        logger.info("🧠 Initializing Claude adapter...")
        adapter = ClaudeAdapter({
            'api_key': api_key,
            'model': 'claude-3-5-sonnet-20241022',
            'prompt_name': 'invoice_extraction',  # Uses external YAML file
            'generate_summary': True,
            'return_raw_response': True
        })
        logger.info("✅ Adapter initialized")
        
        # Process document
        logger.info("\n⚙️  Processing document with Claude...")
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
            logger.info(f"  Total Amount: ${metadata.get('total_amount')}")
            logger.info(f"  Currency: {metadata.get('currency')}")
            logger.info(f"  LLM Provider: {metadata.get('llm_provider')}")
            logger.info(f"  LLM Model: {metadata.get('llm_model')}")
            logger.info(f"  LLM Prompt: {metadata.get('llm_prompt_name')}")
            
            if metadata.get('llm_summary'):
                logger.info(f"  Summary: {metadata.get('llm_summary')}")
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


async def test_claude_with_custom_prompt():
    """Test Claude with a custom prompt"""
    
    api_key = os.getenv('ANTHROPIC_API_KEY')
    if not api_key:
        logger.error("❌ ANTHROPIC_API_KEY not found")
        return
    
    try:
        # Initialize DocEX
        docex = DocEX()
        basket = docex.basket('claude_custom_test')
        
        # Create a product description document
        sample_text = """
        Product: Smart Home Security System
        Model: SecureHome Pro 3000
        Price: $299.99
        
        Features:
        - 24/7 monitoring with AI detection
        - Mobile app with real-time alerts
        - Cloud storage for 30 days
        - Easy installation with wireless sensors
        - Compatible with Alexa and Google Home
        
        Customer Reviews:
        "Great product, easy to install and very reliable!" - 5 stars
        "Works perfectly with my smart home setup" - 4 stars
        "Good value for money" - 4 stars
        """
        
        temp_file = Path(tempfile.mktemp(suffix='.txt'))
        temp_file.write_text(sample_text)
        
        document = basket.add(str(temp_file))
        
        # Use product extraction prompt
        adapter = ClaudeAdapter({
            'api_key': api_key,
            'model': 'claude-3-5-sonnet-20241022',
            'prompt_name': 'product_extraction',  # Different prompt
            'generate_summary': True
        })
        
        logger.info("\n⚙️  Processing product document with Claude...")
        result = await adapter.process(document)
        
        if result.success:
            logger.info("✅ Product processing successful!")
            logger.info("\n📊 Extracted Product Data:")
            for key, value in result.content.items():
                logger.info(f"  {key}: {value}")
        else:
            logger.error(f"❌ Processing failed: {result.error}")
    
    except Exception as e:
        logger.error(f"❌ Error: {str(e)}")
    
    finally:
        if temp_file.exists():
            temp_file.unlink()


def main():
    """Main entry point"""
    logger.info("🎯 Claude LLM Adapter Example")
    logger.info("=" * 50)
    
    # Test basic functionality
    asyncio.run(test_claude_basic())
    
    logger.info("\n" + "=" * 50)
    
    # Test custom prompt
    asyncio.run(test_claude_with_custom_prompt())
    
    logger.info("\n🎉 Claude adapter examples completed!")


if __name__ == "__main__":
    main()