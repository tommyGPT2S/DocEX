"""
Chargeback Workflow Example

Demonstrates the chargeback processing workflow using DocEX processors.
This example shows:
1. Creating baskets for chargeback documents
2. Adding a chargeback document
3. Running the extraction and duplicate check processors
"""

import asyncio
import os
from pathlib import Path
from docex import DocEX
from docex.processors.chargeback import ExtractIdentifiersProcessor, DuplicateCheckProcessor


async def main():
    """Run chargeback workflow example"""
    
    # Initialize DocEX
    doc_ex = DocEX()
    
    # Create or get basket for raw chargebacks
    print("Creating/getting chargeback basket...")
    try:
        basket = doc_ex.create_basket(
            'raw_chargebacks',
            description='Raw chargeback documents from Model N'
        )
        print(f"Created basket: {basket.id}")
    except ValueError as e:
        # Basket already exists, get it
        if 'already exists' in str(e):
            # Get existing basket by listing and finding by name
            baskets = doc_ex.list_baskets()
            basket = next((b for b in baskets if b.name == 'raw_chargebacks'), None)
            if basket:
                print(f"Using existing basket: {basket.id}")
            else:
                raise ValueError("Basket 'raw_chargebacks' should exist but not found")
        else:
            raise
    
    # Create a sample chargeback document (for demo purposes)
    # In production, this would come from Model N, email, or file upload
    sample_chargeback_text = """
    CHARGEBACK DOCUMENT
    ===================
    
    Customer Information:
    Name: ABC Pharmacy Inc.
    Address: 123 Main Street
    City: San Francisco
    State: CA
    ZIP: 94102
    
    Identifiers:
    HIN: HIN123456789
    DEA: DEA1234567
    
    Contract Information:
    Contract Number: CONTRACT-2024-001
    Contract Type: GPO
    Class of Trade: Retail Pharmacy
    
    Chargeback Details:
    Invoice Number: INV-2024-001
    Invoice Date: 2024-01-15
    NDC: 12345-6789-01
    Quantity: 100
    Chargeback Amount: $5,000.00
    """
    
    # Create a temporary file with the chargeback text
    temp_file = Path('temp_chargeback.txt')
    temp_file.write_text(sample_chargeback_text)
    
    try:
        # Add document to basket
        print("\nAdding chargeback document to basket...")
        document = basket.add(
            str(temp_file),
            metadata={
                'document_type': 'chargeback',
                'source': 'model_n',
                'biz_doc_type': 'chargeback'
            }
        )
        print(f"Added document: {document.id}")
        print(f"Document name: {document.name}")
        
        # Configure processors
        # Option 1: Use OpenAI (default)
        # Option 2: Use Local/Ollama - set llm_provider='local' and configure base_url/model
        # Option 3: Use Claude - set llm_provider='claude' and set ANTHROPIC_API_KEY
        
        llm_provider = os.getenv('LLM_PROVIDER', 'openai').lower()  # 'openai', 'local', 'claude'
        
        if llm_provider == 'local':
            llm_config = {
                'model': 'llama3.2',  # or 'mistral', 'llama3', etc.
                'base_url': 'http://localhost:11434',
                'prompt_name': 'chargeback_modeln'
            }
        elif llm_provider == 'claude':
            llm_config = {
                'api_key': os.getenv('ANTHROPIC_API_KEY'),
                'model': 'claude-3-5-sonnet-20241022',
                'prompt_name': 'chargeback_modeln'
            }
        else:  # OpenAI (default)
            llm_config = {
                'api_key': os.getenv('OPENAI_API_KEY'),
                'model': 'gpt-4o',
                'prompt_name': 'chargeback_modeln'
            }
        
        extract_config = {
            'llm_provider': llm_provider,
            'llm_config': llm_config
        }
        
        duplicate_config = {
            'similarity_threshold': 0.85,
            'require_multiple_matches': True
        }
        
        # Step 1: Extract identifiers
        print("\n" + "="*50)
        print("Step 1: Extracting Identifiers")
        print("="*50)
        
        extract_processor = ExtractIdentifiersProcessor(extract_config)
        
        if extract_processor.can_process(document):
            result = await extract_processor.process(document)
            
            if result.success:
                print("✅ Identifiers extracted successfully!")
                print("\nExtracted identifiers:")
                for key, value in result.metadata.items():
                    if value is not None:
                        print(f"  {key}: {value}")
                
                # Update document metadata with extracted data
                from docex.services.metadata_service import MetadataService
                metadata_service = MetadataService()
                metadata_service.update_metadata(document.id, result.metadata)
            else:
                print(f"❌ Extraction failed: {result.error}")
                return
        else:
            print("❌ Document cannot be processed by ExtractIdentifiersProcessor")
            return
        
        # Step 2: Check for duplicates
        print("\n" + "="*50)
        print("Step 2: Checking for Duplicates")
        print("="*50)
        
        duplicate_processor = DuplicateCheckProcessor(duplicate_config)
        
        if duplicate_processor.can_process(document):
            result = await duplicate_processor.process(document)
            
            if result.success:
                print("✅ Duplicate check completed!")
                print("\nDuplicate check results:")
                for key, value in result.metadata.items():
                    print(f"  {key}: {value}")
                
                # Update document metadata
                from docex.services.metadata_service import MetadataService
                metadata_service = MetadataService()
                metadata_service.update_metadata(document.id, result.metadata)
                
                # Check if duplicate
                if result.metadata.get('is_duplicate'):
                    print("\n⚠️  DUPLICATE CHARGEBACK DETECTED!")
                    print(f"   Matched entity: {result.metadata.get('duplicate_entity_id')}")
                    print(f"   Confidence: {result.metadata.get('duplicate_confidence', 0):.2%}")
                else:
                    print("\n✅ New chargeback - no duplicates found")
            else:
                print(f"❌ Duplicate check failed: {result.error}")
        else:
            print("❌ Document cannot be processed by DuplicateCheckProcessor")
        
        # Show final document metadata
        print("\n" + "="*50)
        print("Final Document Metadata")
        print("="*50)
        final_metadata = document.get_metadata_dict()
        for key, value in sorted(final_metadata.items()):
            if value is not None:
                print(f"  {key}: {value}")
        
        print("\n✅ Chargeback workflow example completed!")
        
    finally:
        # Clean up temporary file
        if temp_file.exists():
            temp_file.unlink()


if __name__ == '__main__':
    # Check for OpenAI API key
    if not os.getenv('OPENAI_API_KEY'):
        print("⚠️  Warning: OPENAI_API_KEY environment variable not set")
        print("   Set it to run the LLM extraction processor")
        print("   Example: export OPENAI_API_KEY='your-key-here'")
        print()
    
    asyncio.run(main())

