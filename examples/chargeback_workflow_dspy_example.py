"""
Chargeback Workflow Example with DSPy

Demonstrates using DSPy for structured extraction in the chargeback workflow.
DSPy enables automatic prompt optimization and better extraction quality.

Reference: https://dspy.ai/
"""

import asyncio
import os
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from docex import DocEX
from docex.processors.chargeback import ExtractIdentifiersDSPyProcessor
from docex.docbasket import DocBasket


async def main():
    """Run chargeback workflow with DSPy extraction"""
    
    # Initialize DocEX
    print("🚀 Initializing DocEX...")
    docex = DocEX()
    
    # Get or create basket
    basket_name = 'chargeback_dspy_test'
    try:
        basket = DocBasket.find_by_name(docex.db, basket_name)
        print(f"✅ Using existing basket: {basket_name}")
    except Exception:
        basket = docex.create_basket(basket_name)
        print(f"✅ Created basket: {basket_name}")
    
    # Sample chargeback document text
    chargeback_text = """
    CHARGEBACK INVOICE
    
    Customer: ABC Healthcare Systems
    Address: 123 Medical Center Drive
    City: Boston
    State: MA
    ZIP: 02115
    
    HIN: 123456789
    DEA: AB1234567
    Contract Number: CNT-2024-001
    Contract Type: GPO
    NDC: 12345-6789-01
    Quantity: 100
    Invoice Date: 2024-01-15
    Chargeback Amount: $5,000.00
    Invoice Number: INV-2024-001
    Class of Trade: Hospital
    """
    
    # Create document
    print("\n📄 Creating chargeback document...")
    document = basket.add_document(
        content=chargeback_text.encode('utf-8'),
        document_type='chargeback',
        metadata={
            'source': 'model_n',
            'document_format': 'text'
        }
    )
    print(f"✅ Created document: {document.id}")
    
    # Configure DSPy processor
    # Get LLM provider from environment or use default
    llm_provider = os.getenv('LLM_PROVIDER', 'openai').lower()
    
    if llm_provider in ['local', 'ollama']:
        model = 'ollama/llama3.2'
        base_url = os.getenv('OLLAMA_BASE_URL', 'http://localhost:11434')
        config = {
            'model': model,
            'base_url': base_url,
            'use_chain_of_thought': True
        }
    elif llm_provider == 'claude':
        model = 'anthropic/claude-sonnet-4-5-20250929'
        api_key = os.getenv('ANTHROPIC_API_KEY')
        config = {
            'model': model,
            'api_key': api_key,
            'use_chain_of_thought': True
        }
    else:  # default to OpenAI
        model = 'openai/gpt-4o-mini'
        api_key = os.getenv('OPENAI_API_KEY')
        config = {
            'model': model,
            'api_key': api_key,
            'use_chain_of_thought': True
        }
    
    print(f"\n🤖 Using DSPy with model: {model}")
    
    # Create DSPy processor
    processor = ExtractIdentifiersDSPyProcessor(config, db=docex.db)
    
    # Process document
    print("\n⚙️  Processing document with DSPy...")
    result = await processor.process(document)
    
    if result.success:
        print("\n✅ Extraction successful!")
        print("\n📊 Extracted Identifiers:")
        print("=" * 60)
        
        metadata = result.metadata or {}
        for key, value in metadata.items():
            if value is not None:
                print(f"  {key}: {value}")
        
        # Show reasoning if available (from ChainOfThought)
        if 'reasoning' in metadata:
            print("\n💭 Reasoning:")
            print(f"  {metadata['reasoning']}")
        
        print("\n" + "=" * 60)
        
        # Verify document metadata was updated
        print("\n🔍 Verifying document metadata...")
        doc_metadata = document.get_metadata_dict()
        print(f"  Document has {len(doc_metadata)} metadata entries")
        
    else:
        print(f"\n❌ Extraction failed: {result.error}")
    
    print("\n✨ DSPy workflow complete!")


if __name__ == '__main__':
    asyncio.run(main())

