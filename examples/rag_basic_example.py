"""
Basic RAG Example using DocEX

This example demonstrates how to use the basic RAG service
with existing semantic search infrastructure.
"""

import asyncio
import logging
from docex.docbasket import DocBasket
from docex.processors.llm.claude_adapter import ClaudeAdapter
from docex.processors.vector.semantic_search_service import SemanticSearchService
from docex.processors.rag import RAGService

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def basic_rag_example():
    """Demonstrate basic RAG functionality"""
    
    print("🚀 DocEX Basic RAG Example")
    print("=" * 50)
    
    try:
        # Step 1: Create a DocBasket and add some documents
        print("📁 Creating DocBasket and adding documents...")
        basket = DocBasket()
        
        # Add some sample documents (you can replace these with your documents)
        sample_docs = [
            {
                'name': 'Python Guide',
                'content': 'Python is a high-level programming language known for its simplicity and readability. It supports multiple programming paradigms including procedural, object-oriented, and functional programming.'
            },
            {
                'name': 'Machine Learning Basics',
                'content': 'Machine learning is a subset of artificial intelligence that enables computers to learn and make decisions without being explicitly programmed. Common algorithms include linear regression, decision trees, and neural networks.'
            },
            {
                'name': 'Data Science Process',
                'content': 'Data science involves collecting, cleaning, analyzing, and interpreting large datasets to extract meaningful insights. The typical process includes data collection, preprocessing, exploratory analysis, modeling, and validation.'
            }
        ]
        
        for doc_info in sample_docs:
            doc = basket.create_document()
            doc.name = doc_info['name']
            doc.content = doc_info['content']
            doc.metadata = {'category': 'educational', 'type': 'guide'}
            await basket.add_document(doc)
        
        print(f"✅ Added {len(sample_docs)} documents to basket")
        
        # Step 2: Initialize semantic search service
        print("🔍 Initializing semantic search service...")
        
        # Configure for memory database (you can change to PostgreSQL)
        search_config = {
            'db_type': 'memory',  # or 'postgresql' 
            'embedding_model': 'text-embedding-ada-002',  # OpenAI model
            'max_results': 10
        }
        
        semantic_search = SemanticSearchService(config=search_config)
        await semantic_search.initialize()
        
        # Index the documents
        print("📚 Indexing documents for semantic search...")
        await semantic_search.index_documents(basket.get_all_documents(), basket.id)
        
        print("✅ Semantic search service initialized and documents indexed")
        
        # Step 3: Initialize Claude LLM adapter
        print("🤖 Initializing Claude LLM adapter...")
        
        claude_config = {
            'model': 'claude-3-haiku-20240307',
            'api_key_env': 'ANTHROPIC_API_KEY',  # Make sure this env var is set
            'max_tokens': 1000,
            'temperature': 0.3
        }
        
        claude_adapter = ClaudeAdapter()
        # You might need to configure the adapter based on your setup
        
        print("✅ Claude adapter initialized")
        
        # Step 4: Create RAG service
        print("🧠 Creating RAG service...")
        
        rag_config = {
            'max_context_tokens': 4000,
            'top_k_documents': 3,
            'min_similarity': 0.7,
            'answer_style': 'detailed',
            'include_citations': True,
            'temperature': 0.3
        }
        
        rag_service = RAGService(
            semantic_search_service=semantic_search,
            llm_adapter=claude_adapter,
            config=rag_config
        )
        
        print("✅ RAG service created successfully")
        
        # Step 5: Ask questions and get RAG responses
        print("\n💬 RAG Question & Answer Session")
        print("=" * 50)
        
        questions = [
            "What is Python and what are its key characteristics?",
            "Explain machine learning and give examples of algorithms",
            "What are the steps in the data science process?",
            "How does Python relate to machine learning?"
        ]
        
        for i, question in enumerate(questions, 1):
            print(f"\n❓ Question {i}: {question}")
            print("-" * 60)
            
            try:
                # Query the RAG service
                result = await rag_service.query(
                    question=question,
                    basket_id=basket.id,
                    filters={'category': 'educational'}  # Optional filter
                )
                
                print(f"💡 Answer (Confidence: {result.confidence_score:.2f}):")
                print(result.answer)
                
                print(f"\n📄 Sources ({len(result.sources)} documents):")
                for j, source in enumerate(result.sources, 1):
                    print(f"  {j}. {source.document.name} (Similarity: {source.similarity_score:.2f})")
                
                print(f"\n⏱️  Processing time: {result.processing_time:.2f} seconds")
                print(f"🔧 Metadata: {result.metadata}")
                
            except Exception as e:
                print(f"❌ Error processing question: {e}")
                logger.error(f"Question failed: {e}", exc_info=True)
        
        # Step 6: Demonstrate conversational RAG
        print("\n🗣️  Conversational RAG Example")
        print("=" * 50)
        
        try:
            from docex.processors.rag import AdvancedRAGService
            
            advanced_rag = AdvancedRAGService(semantic_search, claude_adapter, rag_config)
            
            conversation_id = "demo_conversation_1"
            
            # First question
            question1 = "What is machine learning?"
            result1 = await advanced_rag.conversational_query(
                question=question1,
                conversation_id=conversation_id,
                basket_id=basket.id
            )
            
            print(f"❓ Q1: {question1}")
            print(f"💡 A1: {result1.answer}")
            
            # Follow-up question
            question2 = "Can you give me specific examples of those algorithms?"
            result2 = await advanced_rag.conversational_query(
                question=question2,
                conversation_id=conversation_id,
                basket_id=basket.id
            )
            
            print(f"\n❓ Q2: {question2}")
            print(f"💡 A2: {result2.answer}")
            
            print(f"\n✅ Conversational RAG completed successfully")
            
        except Exception as e:
            print(f"⚠️  Conversational RAG not available: {e}")
        
        print("\n🎉 Basic RAG example completed successfully!")
        
    except Exception as e:
        print(f"❌ Error in RAG example: {e}")
        logger.error(f"RAG example failed: {e}", exc_info=True)


async def performance_test():
    """Test RAG performance with multiple queries"""
    
    print("\n🚄 RAG Performance Test")
    print("=" * 30)
    
    # This would run multiple queries and measure performance
    # Implementation depends on your specific needs
    
    print("Performance test would measure:")
    print("- Query response time")
    print("- Document retrieval accuracy") 
    print("- Answer quality metrics")
    print("- Cache hit rates")


if __name__ == "__main__":
    # Run the basic example
    asyncio.run(basic_rag_example())
    
    # Uncomment to run performance test
    # asyncio.run(performance_test())