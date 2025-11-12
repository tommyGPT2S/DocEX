"""
Simple LLM Adapter Test - Direct API Test

This script tests the LLM adapter directly without full DocEX integration.
"""

import asyncio
import os
import logging
from dotenv import load_dotenv

# Load .env file
load_dotenv()

from docex.processors.llm import OpenAILLMService, PromptManager

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


async def test_openai_service():
    """Test OpenAI service directly"""
    
    api_key = os.getenv('OPENAI_API_KEY')
    if not api_key:
        logger.error("❌ OPENAI_API_KEY not set in .env file!")
        return
    
    logger.info("=" * 60)
    logger.info("Testing OpenAI LLM Service")
    logger.info("=" * 60)
    
    # Initialize service
    service = OpenAILLMService(api_key=api_key, model='gpt-4o')
    logger.info("✅ Service initialized")
    
    # Test 1: Generate completion
    logger.info("\n📝 Test 1: Text Completion")
    try:
        result = await service.generate_completion(
            prompt="What is 2+2? Answer in one sentence.",
            system_prompt="You are a helpful assistant."
        )
        logger.info(f"✅ Completion: {result}")
    except Exception as e:
        logger.error(f"❌ Error: {e}")
    
    # Test 2: Generate embedding
    logger.info("\n🔢 Test 2: Embedding Generation")
    try:
        embedding = await service.generate_embedding("This is a test document")
        logger.info(f"✅ Embedding generated: {len(embedding)} dimensions")
        logger.info(f"   First 5 values: {embedding[:5]}")
    except Exception as e:
        logger.error(f"❌ Error: {e}")
    
    # Test 3: Extract structured data
    logger.info("\n📊 Test 3: Structured Data Extraction")
    invoice_text = """
    INVOICE
    Invoice Number: INV-001
    Date: 2024-01-15
    Total: $100.00
    """
    
    system_prompt = """
    Extract invoice data and return JSON with:
    - invoice_number
    - date
    - total_amount
    """
    
    try:
        result = await service.extract_structured_data(
            text=invoice_text,
            system_prompt=system_prompt,
            return_raw_response=False
        )
        logger.info(f"✅ Extracted data: {result['extracted_data']}")
    except Exception as e:
        logger.error(f"❌ Error: {e}")


async def test_prompt_manager():
    """Test prompt manager"""
    
    logger.info("\n" + "=" * 60)
    logger.info("Testing Prompt Manager")
    logger.info("=" * 60)
    
    manager = PromptManager()
    
    # Test loading prompts
    logger.info("\n📄 Test: Loading Prompts")
    prompts = manager.list_prompts()
    logger.info(f"✅ Found {len(prompts)} prompts: {prompts}")
    
    # Test loading invoice extraction prompt
    logger.info("\n📄 Test: Invoice Extraction Prompt")
    try:
        system_prompt = manager.get_system_prompt('invoice_extraction')
        logger.info(f"✅ System prompt loaded ({len(system_prompt)} chars)")
        logger.info(f"   Preview: {system_prompt[:100]}...")
        
        user_prompt = manager.get_user_prompt('invoice_extraction', content="Test invoice text")
        logger.info(f"✅ User prompt generated ({len(user_prompt)} chars)")
        logger.info(f"   Preview: {user_prompt[:100]}...")
    except Exception as e:
        logger.error(f"❌ Error: {e}")


async def test_full_extraction():
    """Test full extraction with prompt"""
    
    api_key = os.getenv('OPENAI_API_KEY')
    if not api_key:
        return
    
    logger.info("\n" + "=" * 60)
    logger.info("Testing Full Extraction with External Prompt")
    logger.info("=" * 60)
    
    # Initialize service and prompt manager
    service = OpenAILLMService(api_key=api_key, model='gpt-4o')
    manager = PromptManager()
    
    # Load invoice extraction prompt
    system_prompt = manager.get_system_prompt('invoice_extraction')
    
    # Test invoice text
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
    
    user_prompt = manager.get_user_prompt('invoice_extraction', content=invoice_text)
    
    logger.info("🤖 Calling OpenAI API...")
    try:
        result = await service.extract_structured_data(
            text=invoice_text,
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            return_raw_response=True
        )
        
        logger.info("✅ Extraction successful!")
        logger.info("\n📊 Extracted Data:")
        extracted = result['extracted_data']
        for key, value in extracted.items():
            logger.info(f"  {key}: {value}")
        
        logger.info(f"\n📈 Raw Response Info:")
        raw = result.get('raw_response', {})
        logger.info(f"  Model: {raw.get('model')}")
        logger.info(f"  Finish Reason: {raw.get('finish_reason')}")
        if raw.get('usage'):
            logger.info(f"  Tokens Used: {raw['usage']}")
        
    except Exception as e:
        logger.error(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()


async def main():
    """Run all tests"""
    
    logger.info("🚀 Simple LLM Adapter Test")
    logger.info("=" * 60)
    
    # Check API key
    if not os.getenv('OPENAI_API_KEY'):
        logger.error("❌ OPENAI_API_KEY not set!")
        logger.info("\nPlease add it to your .env file:")
        logger.info("  OPENAI_API_KEY=sk-your-key-here")
        return
    
    try:
        # Run tests
        await test_prompt_manager()
        await test_openai_service()
        await test_full_extraction()
        
        logger.info("\n" + "=" * 60)
        logger.info("🎉 All tests completed!")
        logger.info("=" * 60)
    
    except KeyboardInterrupt:
        logger.info("\n⚠️  Test interrupted")
    except Exception as e:
        logger.error(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())

