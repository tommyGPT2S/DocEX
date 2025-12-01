"""
Chargeback Workflow Example with Local LLM (Ollama)

Demonstrates the chargeback processing workflow using DocEX processors with Ollama.
This example shows:
1. Creating baskets for chargeback documents
2. Adding a chargeback document
3. Running the extraction and duplicate check processors using local LLM
"""

import asyncio
from pathlib import Path
from docex import DocEX
from docex.processors.chargeback import ExtractIdentifiersProcessor, DuplicateCheckProcessor


async def main():
    """Run chargeback workflow example with local LLM"""
    
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
    temp_file = Path('temp_chargeback_local.txt')
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
        
        # Configure processors with LOCAL LLM (Ollama)
        print("\n" + "="*60)
        print("Using LOCAL LLM (Ollama) for extraction")
        print("="*60)
        print("Make sure Ollama is running: ollama serve")
        print("And model is available: ollama pull llama3.2")
        print("="*60 + "\n")
        
        llm_config = {
            'model': 'llama3.2',  # or 'mistral', 'llama3', etc.
            'base_url': 'http://localhost:11434',  # Default Ollama URL
            'prompt_name': 'chargeback_modeln'
        }
        
        extract_config = {
            'llm_provider': 'local',  # Use local/Ollama instead of OpenAI
            'llm_config': llm_config
        }
        
        duplicate_config = {
            'similarity_threshold': 0.85,
            'require_multiple_matches': True
        }
        
        # Step 1: Extract identifiers
        print("\n" + "="*50)
        print("Step 1: Extracting Identifiers (Local LLM)")
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
                print("\nTroubleshooting:")
                print("1. Make sure Ollama is running: ollama serve")
                print("2. Make sure model is available: ollama pull llama3.2")
                print("3. Check Ollama URL in config (default: http://localhost:11434)")
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
        try:
            final_metadata = document.get_metadata_dict()
        except (AttributeError, TypeError):
            # Fallback: get metadata directly
            from docex.services.metadata_service import MetadataService
            metadata_service = MetadataService()
            final_metadata = metadata_service.get_metadata(document.id)
        
        for key, value in sorted(final_metadata.items()):
            if value is not None:
                print(f"  {key}: {value}")
        
        print("\n✅ Chargeback workflow example completed!")
        
    finally:
        # Clean up temporary file
        if temp_file.exists():
            temp_file.unlink()


if __name__ == '__main__':
    print("="*60)
    print("Chargeback Workflow Example - Local LLM (Ollama)")
    print("="*60)
    print("\nPrerequisites:")
    print("1. Install Ollama: https://ollama.ai")
    print("2. Start Ollama server: ollama serve")
    print("3. Pull a model: ollama pull llama3.2")
    print("\n" + "="*60 + "\n")
    
    asyncio.run(main())

