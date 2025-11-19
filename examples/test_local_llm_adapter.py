"""
Local LLM (Ollama) Adapter Example

This example demonstrates how to use the Local LLM adapter with DocEX and Ollama.
"""

import asyncio
import logging
from pathlib import Path
import tempfile

from docex import DocEX
from docex.processors.llm import LocalLLMAdapter

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


async def test_local_llm_basic():
    """Test Local LLM adapter with basic document processing"""
    
    try:
        # Initialize DocEX
        logger.info("🚀 Initializing DocEX...")
        docex = DocEX()
        basket = docex.basket('local_llm_test')
        
        # Create a sample document
        sample_text = """
        Meeting Notes - Project Planning
        Date: November 18, 2024
        Attendees: John Smith, Sarah Johnson, Mike Chen
        
        Agenda:
        1. Project timeline review
        2. Budget allocation
        3. Resource planning
        4. Next steps
        
        Key Decisions:
        - Launch date moved to Q1 2025
        - Additional budget approved: $50,000
        - New team member to be hired
        
        Action Items:
        - John: Finalize project scope by Nov 25
        - Sarah: Prepare budget breakdown by Nov 22
        - Mike: Interview candidates for new position
        
        Next Meeting: November 25, 2024
        """
        
        # Create temporary file
        temp_file = Path(tempfile.mktemp(suffix='.txt'))
        temp_file.write_text(sample_text)
        
        logger.info(f"📄 Created sample document at: {temp_file}")
        
        # Add document to basket
        document = basket.add(str(temp_file))
        logger.info(f"📋 Added document to basket: {document.id}")
        
        # Initialize Local LLM adapter
        logger.info("🧠 Initializing Local LLM adapter...")
        adapter = LocalLLMAdapter({
            'base_url': 'http://localhost:11434',  # Default Ollama URL
            'model': 'llama3.2',  # Using Llama 3.2 model
            'prompt_name': 'generic_extraction',  # Uses external YAML file
            'generate_summary': True,
            'generate_embedding': True,
            'return_raw_response': True
        })
        logger.info("✅ Adapter initialized")
        
        # Process document
        logger.info("\n⚙️  Processing document with Local LLM...")
        logger.info("Note: This requires Ollama to be running locally")
        logger.info("Install: https://ollama.ai/")
        logger.info("Start: ollama serve")
        
        result = await adapter.process(document)
        
        if result.success:
            logger.info("✅ Processing successful!")
            logger.info("\n📊 Extracted Data:")
            logger.info(f"  {result.content}")
            
            # Check metadata
            metadata = document.get_metadata()
            logger.info("\n📋 Document Metadata:")
            for key, value in metadata.items():
                if key.startswith('llm_'):
                    logger.info(f"  {key}: {value}")
            
        else:
            logger.error(f"❌ Processing failed: {result.error}")
            logger.info("\n🔍 Troubleshooting:")
            logger.info("1. Make sure Ollama is installed: https://ollama.ai/")
            logger.info("2. Start Ollama server: ollama serve")
            logger.info("3. Pull the model: ollama pull llama3.2")
    
    except Exception as e:
        logger.error(f"❌ Error: {str(e)}")
        logger.info("\n🔍 Troubleshooting:")
        logger.info("1. Make sure Ollama is installed and running")
        logger.info("2. Check if the model is available: ollama list")
        logger.info("3. Pull the model if needed: ollama pull llama3.2")
        import traceback
        traceback.print_exc()
    
    finally:
        # Cleanup
        if temp_file.exists():
            temp_file.unlink()
            logger.info("\n🧹 Cleaned up temporary file")


async def test_local_llm_different_model():
    """Test Local LLM with a different model"""
    
    try:
        # Initialize DocEX
        docex = DocEX()
        basket = docex.basket('local_llm_codellama_test')
        
        # Create a code document
        sample_text = """
        def calculate_fibonacci(n):
            '''Calculate the nth Fibonacci number'''
            if n <= 1:
                return n
            else:
                return calculate_fibonacci(n-1) + calculate_fibonacci(n-2)
        
        # Example usage
        result = calculate_fibonacci(10)
        print(f"The 10th Fibonacci number is: {result}")
        """
        
        temp_file = Path(tempfile.mktemp(suffix='.py'))
        temp_file.write_text(sample_text)
        
        document = basket.add(str(temp_file))
        
        # Use Code Llama model for code analysis
        adapter = LocalLLMAdapter({
            'base_url': 'http://localhost:11434',
            'model': 'codellama',  # Specialized for code
            'prompt_name': 'generic_extraction',
            'generate_summary': True
        })
        
        logger.info("\n⚙️  Processing code document with CodeLlama...")
        logger.info("Note: This requires CodeLlama model")
        logger.info("Install: ollama pull codellama")
        
        result = await adapter.process(document)
        
        if result.success:
            logger.info("✅ Code processing successful!")
            logger.info("\n📊 Extracted Code Data:")
            for key, value in result.content.items():
                logger.info(f"  {key}: {value}")
        else:
            logger.error(f"❌ Processing failed: {result.error}")
    
    except Exception as e:
        logger.error(f"❌ Error: {str(e)}")
    
    finally:
        if temp_file.exists():
            temp_file.unlink()


async def test_embedding_generation():
    """Test embedding generation with local model"""
    
    try:
        # Initialize adapter with embedding support
        adapter = LocalLLMAdapter({
            'base_url': 'http://localhost:11434',
            'model': 'llama3.2',
            'generate_embedding': True
        })
        
        # Simple text for embedding
        text = "This is a test document for embedding generation."
        
        logger.info("\n📊 Testing embedding generation...")
        logger.info("Note: This requires nomic-embed-text model")
        logger.info("Install: ollama pull nomic-embed-text")
        
        try:
            embedding = await adapter.llm_service.generate_embedding(text)
            if embedding:
                logger.info(f"✅ Generated embedding with {len(embedding)} dimensions")
                logger.info(f"First 5 values: {embedding[:5]}")
            else:
                logger.warning("⚠️  Embedding generation not supported or failed")
        except Exception as e:
            logger.warning(f"⚠️  Embedding generation failed: {str(e)}")
    
    except Exception as e:
        logger.error(f"❌ Embedding test error: {str(e)}")


def main():
    """Main entry point"""
    logger.info("🎯 Local LLM (Ollama) Adapter Example")
    logger.info("=" * 50)
    
    # Test basic functionality
    asyncio.run(test_local_llm_basic())
    
    logger.info("\n" + "=" * 50)
    
    # Test different model
    asyncio.run(test_local_llm_different_model())
    
    logger.info("\n" + "=" * 50)
    
    # Test embedding generation
    asyncio.run(test_embedding_generation())
    
    logger.info("\n🎉 Local LLM adapter examples completed!")
    logger.info("\n📖 Ollama Resources:")
    logger.info("  Website: https://ollama.ai/")
    logger.info("  Models: https://ollama.ai/library")
    logger.info("  Setup: ollama serve && ollama pull llama3.2")


if __name__ == "__main__":
    main()