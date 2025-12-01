"""
Chargeback Workflow with DSPy Optimization

Demonstrates using DSPy optimizers (MIPROv2, BootstrapFewShot) to improve
extraction quality over time with training examples.

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
    """Run chargeback workflow with DSPy optimization"""
    
    # Initialize DocEX
    print("🚀 Initializing DocEX...")
    docex = DocEX()
    
    # Get or create basket
    basket_name = 'chargeback_dspy_optimized'
    try:
        basket = DocBasket.find_by_name(docex.db, basket_name)
        print(f"✅ Using existing basket: {basket_name}")
    except Exception:
        basket = docex.create_basket(basket_name)
        print(f"✅ Created basket: {basket_name}")
    
    # Training examples for optimization
    # In production, these would come from labeled data
    training_examples = [
        {
            'chargeback_document_text': """
            Customer: ABC Healthcare Systems
            HIN: 123456789
            DEA: AB1234567
            Contract Number: CNT-2024-001
            NDC: 12345-6789-01
            Chargeback Amount: $5,000.00
            """,
            'customer_name': 'ABC Healthcare Systems',
            'hin': '123456789',
            'dea': 'AB1234567',
            'contract_number': 'CNT-2024-001',
            'ndc': '12345-6789-01',
            'chargeback_amount': 5000.00
        },
        {
            'chargeback_document_text': """
            Customer: XYZ Medical Center
            HIN: 987654321
            DEA: XY9876543
            Contract Number: CNT-2024-002
            NDC: 98765-4321-02
            Chargeback Amount: $3,500.00
            """,
            'customer_name': 'XYZ Medical Center',
            'hin': '987654321',
            'dea': 'XY9876543',
            'contract_number': 'CNT-2024-002',
            'ndc': '98765-4321-02',
            'chargeback_amount': 3500.00
        }
    ]
    
    # Test document
    test_text = """
    CHARGEBACK INVOICE
    
    Customer: New Hospital Inc
    Address: 456 Health Street
    City: New York
    State: NY
    ZIP: 10001
    
    HIN: 555666777
    DEA: NH5556667
    Contract Number: CNT-2024-003
    Contract Type: Direct
    NDC: 55566-7778-03
    Quantity: 200
    Invoice Date: 2024-02-20
    Chargeback Amount: $7,500.00
    Invoice Number: INV-2024-003
    Class of Trade: Hospital
    """
    
    # Create test document
    print("\n📄 Creating test chargeback document...")
    document = basket.add_document(
        content=test_text.encode('utf-8'),
        document_type='chargeback',
        metadata={
            'source': 'model_n',
            'document_format': 'text'
        }
    )
    print(f"✅ Created document: {document.id}")
    
    # Configure DSPy processor with optimizer
    llm_provider = os.getenv('LLM_PROVIDER', 'openai').lower()
    
    if llm_provider in ['local', 'ollama']:
        model = 'ollama/llama3.2'
        base_url = os.getenv('OLLAMA_BASE_URL', 'http://localhost:11434')
        config = {
            'model': model,
            'base_url': base_url,
            'use_chain_of_thought': True,
            'optimizer': {
                'type': 'BootstrapFewShot',  # Use simpler optimizer for local models
                'metric': lambda example, prediction, trace=None: (
                    example.customer_name == prediction.customer_name and
                    example.hin == prediction.hin
                )
            },
            'training_data': training_examples
        }
    elif llm_provider == 'claude':
        model = 'anthropic/claude-sonnet-4-5-20250929'
        api_key = os.getenv('ANTHROPIC_API_KEY')
        config = {
            'model': model,
            'api_key': api_key,
            'use_chain_of_thought': True,
            'optimizer': {
                'type': 'MIPROv2',  # Use advanced optimizer for Claude
                'metric': lambda example, prediction, trace=None: (
                    example.customer_name == prediction.customer_name and
                    example.hin == prediction.hin and
                    example.contract_number == prediction.contract_number
                )
            },
            'training_data': training_examples
        }
    else:  # default to OpenAI
        model = 'openai/gpt-4o-mini'
        api_key = os.getenv('OPENAI_API_KEY')
        config = {
            'model': model,
            'api_key': api_key,
            'use_chain_of_thought': True,
            'optimizer': {
                'type': 'BootstrapFewShot',  # Good balance of speed and quality
                'metric': lambda example, prediction, trace=None: (
                    example.customer_name == prediction.customer_name and
                    example.hin == prediction.hin and
                    example.contract_number == prediction.contract_number
                )
            },
            'training_data': training_examples
        }
    
    print(f"\n🤖 Using DSPy with model: {model}")
    print(f"📚 Training with {len(training_examples)} examples")
    print(f"🔧 Optimizer: {config['optimizer']['type']}")
    
    # Create DSPy processor (optimization happens during initialization)
    print("\n⚙️  Initializing DSPy processor with optimization...")
    processor = ExtractIdentifiersDSPyProcessor(config, db=docex.db)
    
    # Process document
    print("\n⚙️  Processing document with optimized DSPy module...")
    result = await processor.process(document)
    
    if result.success:
        print("\n✅ Extraction successful!")
        print("\n📊 Extracted Identifiers:")
        print("=" * 60)
        
        metadata = result.metadata or {}
        for key, value in metadata.items():
            if value is not None:
                print(f"  {key}: {value}")
        
        # Show reasoning if available
        if 'reasoning' in metadata:
            print("\n💭 Reasoning:")
            print(f"  {metadata['reasoning']}")
        
        print("\n" + "=" * 60)
        
        # Verify extraction quality
        print("\n✅ Verification:")
        expected = {
            'customer_name': 'New Hospital Inc',
            'hin': '555666777',
            'dea': 'NH5556667',
            'contract_number': 'CNT-2024-003'
        }
        
        for field, expected_value in expected.items():
            actual_value = metadata.get(field)
            if actual_value == expected_value:
                print(f"  ✅ {field}: {actual_value}")
            else:
                print(f"  ⚠️  {field}: expected '{expected_value}', got '{actual_value}'")
        
    else:
        print(f"\n❌ Extraction failed: {result.error}")
    
    print("\n✨ DSPy optimized workflow complete!")


if __name__ == '__main__':
    asyncio.run(main())

