"""
Example: Vector Indexing and Semantic Search with DocEX

This example demonstrates:
1. Indexing documents with vector embeddings
2. Performing semantic search queries
3. Using different vector database backends (memory for testing, pgvector for production)
4. Using UserContext for audit logging and security

Security Best Practices:
- Always use UserContext for audit logging
- UserContext enables operation tracking and multi-tenant support
- For multi-tenant applications, provide tenant_id in UserContext
"""

import asyncio
import os
import logging
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

from docex import DocEX
from docex.context import UserContext
from docex.processors.llm import OpenAIAdapter
from docex.processors.vector import VectorIndexingProcessor, SemanticSearchService

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def main():
    """Main example function"""
    
    # Check for OpenAI API key
    api_key = os.getenv('OPENAI_API_KEY')
    if not api_key:
        logger.error("OPENAI_API_KEY not set in .env file!")
        return
    
    logger.info("=" * 60)
    logger.info("Vector Indexing and Semantic Search Example")
    logger.info("=" * 60)
    
    # Create UserContext for audit logging
    user_context = UserContext(
        user_id="vector_user",
        user_email="vector@example.com",
        tenant_id="example_tenant",  # Optional: for multi-tenant applications
        roles=["user"]
    )
    
    # Initialize DocEX with UserContext (enables audit logging)
    docEX = DocEX(user_context=user_context)
    
    # Create a basket for testing
    import uuid
    basket_name = f'vector_test_{uuid.uuid4().hex[:8]}'
    basket = docEX.create_basket(
        basket_name,
        storage_config={
            'type': 'filesystem',
            'path': f'storage/{basket_name}'
        }
    )
    
    logger.info(f"✅ Created basket: {basket_name}")
    
    # Create sample documents
    documents_data = [
        {
            'name': 'ai_overview.txt',
            'content': """
            Artificial Intelligence (AI) is the simulation of human intelligence in machines.
            Machine Learning is a subset of AI that enables systems to learn from data.
            Deep Learning uses neural networks with multiple layers.
            Natural Language Processing helps computers understand human language.
            """
        },
        {
            'name': 'python_basics.txt',
            'content': """
            Python is a high-level programming language known for its simplicity.
            It supports multiple programming paradigms including object-oriented programming.
            Python has a large standard library and active community.
            It's widely used in data science, web development, and automation.
            """
        },
        {
            'name': 'database_concepts.txt',
            'content': """
            Databases store and organize data efficiently.
            SQL is the standard language for relational databases.
            PostgreSQL is an advanced open-source relational database.
            Vector databases enable similarity search for embeddings.
            """
        }
    ]
    
    # Add documents to basket
    documents = []
    temp_files = []
    
    try:
        for doc_data in documents_data:
            temp_file = Path(f"/tmp/{doc_data['name']}")
            temp_file.write_text(doc_data['content'])
            temp_files.append(temp_file)
            
            document = basket.add(
                str(temp_file),
                metadata={
                    'category': 'technical',
                    'source': 'example'
                }
            )
            documents.append(document)
            logger.info(f"✅ Added document: {document.name} (ID: {document.id})")
        
        # Initialize LLM adapter for embeddings
        llm_adapter = OpenAIAdapter({
            'api_key': api_key,
            'model': 'gpt-4o',
            'generate_embedding': True
        })
        
        # Initialize vector indexing processor (using memory backend for this example)
        vector_processor = VectorIndexingProcessor({
            'llm_adapter': llm_adapter,
            'vector_db_type': 'memory',  # Use 'pgvector' for PostgreSQL or 'pinecone' for Pinecone
            'store_in_metadata': True
        })
        
        logger.info("\n" + "=" * 60)
        logger.info("Step 1: Indexing Documents with Vector Embeddings")
        logger.info("=" * 60)
        
        # Index all documents
        for document in documents:
            logger.info(f"\n📄 Indexing document: {document.name}")
            result = await vector_processor.process(document)
            
            if result.success:
                logger.info(f"✅ Successfully indexed: {document.name}")
                metadata = document.get_metadata_dict()
                logger.info(f"   Vector indexed: {metadata.get('vector_indexed')}")
                logger.info(f"   Embedding dimension: {metadata.get('embedding_dimension')}")
            else:
                logger.error(f"❌ Failed to index: {result.error}")
        
        # Share memory database with search service
        # In production, this would be a shared database connection
        # Get the vectors dict from the processor
        memory_vectors = vector_processor.vector_db.get('vectors', {})
        
        # Initialize semantic search service with shared memory database
        search_service = SemanticSearchService(
            doc_ex=docEX,
            llm_adapter=llm_adapter,
            vector_db_type='memory',
            vector_db_config={'vectors': memory_vectors}
        )
        
        logger.info("\n" + "=" * 60)
        logger.info("Step 2: Semantic Search Queries")
        logger.info("=" * 60)
        
        # Test queries
        test_queries = [
            "What is machine learning?",
            "How does Python work?",
            "Tell me about databases"
        ]
        
        for query in test_queries:
            logger.info(f"\n🔍 Query: '{query}'")
            logger.info("-" * 60)
            
            results = await search_service.search(
                query=query,
                top_k=3,
                basket_id=basket.id
            )
            
            if results:
                logger.info(f"Found {len(results)} results:")
                for i, result in enumerate(results, 1):
                    logger.info(f"\n  {i}. {result.document.name}")
                    logger.info(f"     Similarity: {result.similarity_score:.4f}")
                    logger.info(f"     Document ID: {result.document.id}")
            else:
                logger.info("No results found")
        
        logger.info("\n" + "=" * 60)
        logger.info("✅ Example completed successfully!")
        logger.info("=" * 60)
        
    finally:
        # Cleanup temp files
        for temp_file in temp_files:
            if temp_file.exists():
                temp_file.unlink()


if __name__ == "__main__":
    asyncio.run(main())

