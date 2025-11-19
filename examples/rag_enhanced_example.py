"""
Enhanced RAG Example with FAISS and Pinecone

This example demonstrates the advanced RAG service with vector database integration
"""

import asyncio
import logging
import os
from docex.docbasket import DocBasket
from docex.processors.llm.claude_adapter import ClaudeAdapter
from docex.processors.vector.semantic_search_service import SemanticSearchService
from docex.processors.rag import EnhancedRAGService, EnhancedRAGConfig

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def faiss_rag_example():
    """Demonstrate RAG with FAISS vector database"""
    
    print("🔬 DocEX Enhanced RAG with FAISS")
    print("=" * 50)
    
    try:
        # Step 1: Create documents
        print("📁 Creating sample document collection...")
        basket = DocBasket()
        
        # More comprehensive document set for vector search
        documents = [
            {
                'name': 'Python Programming Guide',
                'content': '''Python is a versatile, high-level programming language that emphasizes code readability and simplicity. 
                It supports multiple programming paradigms including object-oriented, procedural, and functional programming. 
                Python's extensive standard library and vast ecosystem of third-party packages make it ideal for web development, 
                data science, artificial intelligence, automation, and scientific computing. Key features include dynamic typing, 
                automatic memory management, and an interpreted nature that enables rapid development cycles.'''
            },
            {
                'name': 'Machine Learning Fundamentals',
                'content': '''Machine learning is a branch of artificial intelligence that enables systems to automatically learn 
                and improve from experience without being explicitly programmed. The field encompasses supervised learning 
                (classification and regression), unsupervised learning (clustering and dimensionality reduction), and 
                reinforcement learning. Popular algorithms include linear regression, logistic regression, decision trees, 
                random forests, support vector machines, k-means clustering, and neural networks. Modern deep learning 
                approaches use multi-layered neural networks for complex pattern recognition tasks.'''
            },
            {
                'name': 'Data Science Methodology',
                'content': '''Data science combines domain expertise, programming skills, and knowledge of mathematics and statistics 
                to extract meaningful insights from data. The data science process typically follows these phases: business understanding, 
                data mining, data understanding, data preparation, modeling, evaluation, and deployment. Essential tools include 
                Python and R for programming, pandas and numpy for data manipulation, matplotlib and seaborn for visualization, 
                scikit-learn for machine learning, and TensorFlow or PyTorch for deep learning applications.'''
            },
            {
                'name': 'AI and Deep Learning',
                'content': '''Artificial Intelligence encompasses machine learning, natural language processing, computer vision, 
                and robotics. Deep learning, a subset of machine learning, uses artificial neural networks with multiple layers 
                to model and understand complex patterns in data. Convolutional Neural Networks (CNNs) excel at image recognition, 
                Recurrent Neural Networks (RNNs) and Transformers handle sequential data like text and speech. Popular frameworks 
                include TensorFlow, PyTorch, and Keras. Applications span from autonomous vehicles to medical diagnosis and 
                language translation.'''
            },
            {
                'name': 'Database Systems',
                'content': '''Database management systems store, organize, and retrieve data efficiently. Relational databases like 
                PostgreSQL, MySQL, and SQLite use structured query language (SQL) and follow ACID principles. NoSQL databases 
                include document stores (MongoDB), key-value stores (Redis), column-family (Cassandra), and graph databases (Neo4j). 
                Vector databases like Pinecone, Weaviate, and FAISS specialize in storing and searching high-dimensional vectors 
                for machine learning applications. Database design involves normalization, indexing, and query optimization.'''
            },
            {
                'name': 'Cloud Computing Platforms',
                'content': '''Cloud computing provides on-demand access to computing resources over the internet. Major providers 
                include Amazon Web Services (AWS), Microsoft Azure, and Google Cloud Platform (GCP). Services encompass Infrastructure 
                as a Service (IaaS), Platform as a Service (PaaS), and Software as a Service (SaaS). Key benefits include scalability, 
                cost-effectiveness, reliability, and global accessibility. Cloud-native technologies like containers (Docker), 
                orchestration (Kubernetes), and serverless computing enable modern application deployment and management.'''
            }
        ]
        
        for doc_info in documents:
            doc = basket.create_document()
            doc.name = doc_info['name']
            doc.content = doc_info['content']
            doc.metadata = {'category': 'technology', 'type': 'guide', 'added_by': 'example'}
            await basket.add_document(doc)
        
        print(f"✅ Created {len(documents)} documents")
        
        # Step 2: Initialize semantic search (for hybrid search)
        print("🔍 Initializing semantic search service...")
        
        semantic_search = SemanticSearchService(config={
            'db_type': 'memory',
            'embedding_model': 'text-embedding-ada-002',
            'max_results': 10
        })
        
        await semantic_search.initialize()
        await semantic_search.index_documents(basket.get_all_documents(), basket.id)
        
        print("✅ Semantic search initialized")
        
        # Step 3: Initialize LLM adapter
        print("🤖 Initializing Claude adapter...")
        claude_adapter = ClaudeAdapter()
        print("✅ Claude adapter ready")
        
        # Step 4: Configure enhanced RAG with FAISS
        print("⚡ Configuring enhanced RAG with FAISS...")
        
        # FAISS configuration
        faiss_config = {
            'dimension': 1536,  # OpenAI embedding dimension
            'index_type': 'flat',  # Simple flat index for demo
            'metric': 'cosine',
            'storage_path': './storage/faiss_index.bin'  # Persist index
        }
        
        enhanced_config = EnhancedRAGConfig(
            vector_db_type='faiss',
            vector_db_config=faiss_config,
            enable_hybrid_search=True,
            semantic_weight=0.6,
            vector_weight=0.4,
            enable_caching=True,
            top_k_documents=5,
            min_similarity=0.75
        )
        
        # Create enhanced RAG service
        rag_service = EnhancedRAGService(
            semantic_search_service=semantic_search,
            llm_adapter=claude_adapter,
            config=enhanced_config
        )
        
        # Initialize vector database
        print("🗄️  Initializing FAISS vector database...")
        success = await rag_service.initialize_vector_db()
        
        if not success:
            print("❌ Failed to initialize FAISS. Make sure faiss-cpu is installed: pip install faiss-cpu")
            return
        
        print("✅ FAISS vector database initialized")
        
        # Step 5: Add documents to vector database
        print("📊 Adding documents to FAISS vector database...")
        
        docs_added = await rag_service.add_documents_to_vector_db(basket.get_all_documents())
        
        if docs_added:
            print("✅ Documents added to vector database")
        else:
            print("❌ Failed to add documents to vector database")
            return
        
        # Step 6: Get vector database statistics
        stats = await rag_service.get_vector_db_stats()
        print(f"📈 Vector DB Stats: {stats}")
        
        # Step 7: Test enhanced RAG queries
        print("\n💬 Enhanced RAG Question & Answer Session")
        print("=" * 60)
        
        test_questions = [
            "What are the key features and applications of Python programming?",
            "Explain different types of machine learning algorithms and their use cases",
            "How do vector databases work and what are some examples?",
            "What is the relationship between AI, machine learning, and deep learning?",
            "Compare different cloud computing service models",
            "What tools and technologies are essential for data science?"
        ]
        
        for i, question in enumerate(test_questions, 1):
            print(f"\n❓ Question {i}: {question}")
            print("-" * 70)
            
            try:
                # Query with enhanced RAG
                result = await rag_service.query(
                    question=question,
                    basket_id=basket.id,
                    filters={'category': 'technology'}
                )
                
                print(f"💡 Answer (Confidence: {result.confidence_score:.2f}):")
                print(result.answer)
                
                print(f"\n📚 Sources ({len(result.sources)} documents):")
                for j, source in enumerate(result.sources, 1):
                    search_method = source.metadata.get('search_method', 'unknown')
                    print(f"  {j}. {source.document.name} (Score: {source.similarity_score:.3f}, Method: {search_method})")
                
                print(f"\n⏱️  Processing: {result.processing_time:.2f}s | 🔧 Method: {result.metadata.get('search_method', 'unknown')}")
                
            except Exception as e:
                print(f"❌ Error: {e}")
                logger.error(f"Query failed: {e}", exc_info=True)
        
        print("\n🎉 FAISS RAG example completed successfully!")
        
    except Exception as e:
        print(f"❌ FAISS example failed: {e}")
        logger.error(f"FAISS example error: {e}", exc_info=True)


async def pinecone_rag_example():
    """Demonstrate RAG with Pinecone vector database"""
    
    print("\n☁️  DocEX Enhanced RAG with Pinecone")
    print("=" * 50)
    
    # Check for Pinecone configuration
    if not os.getenv('PINECONE_API_KEY') or not os.getenv('PINECONE_ENVIRONMENT'):
        print("⚠️  Pinecone example requires PINECONE_API_KEY and PINECONE_ENVIRONMENT environment variables")
        print("   Set these variables to run the Pinecone example")
        return
    
    try:
        print("📁 Setting up documents for Pinecone...")
        basket = DocBasket()
        
        # Create sample documents
        tech_docs = [
            {
                'name': 'Vector Databases Guide',
                'content': '''Vector databases are specialized database systems designed to store, index, and query high-dimensional 
                vectors efficiently. They are essential for modern AI applications including semantic search, recommendation systems, 
                and retrieval-augmented generation (RAG). Popular vector databases include Pinecone, Weaviate, Qdrant, Milvus, and 
                Chroma. These systems use sophisticated indexing algorithms like Approximate Nearest Neighbor (ANN) search, HNSW 
                (Hierarchical Navigable Small Worlds), and IVF (Inverted File) to enable fast similarity search across millions 
                or billions of vectors.'''
            },
            {
                'name': 'Natural Language Processing',
                'content': '''Natural Language Processing (NLP) enables computers to understand, interpret, and generate human language. 
                Key tasks include tokenization, part-of-speech tagging, named entity recognition, sentiment analysis, machine translation, 
                and text summarization. Modern NLP relies heavily on transformer architectures like BERT, GPT, T5, and their variants. 
                Embedding models convert text into dense vector representations that capture semantic meaning, enabling similarity 
                comparisons and downstream machine learning tasks. Applications range from chatbots and virtual assistants to 
                document analysis and content generation.'''
            }
        ]
        
        for doc_info in tech_docs:
            doc = basket.create_document()
            doc.name = doc_info['name']
            doc.content = doc_info['content']
            doc.metadata = {'category': 'nlp', 'type': 'advanced'}
            await basket.add_document(doc)
        
        # Initialize semantic search
        semantic_search = SemanticSearchService(config={'db_type': 'memory'})
        await semantic_search.initialize()
        await semantic_search.index_documents(basket.get_all_documents(), basket.id)
        
        # Initialize Claude adapter
        claude_adapter = ClaudeAdapter()
        
        # Configure Pinecone
        pinecone_config = {
            'api_key': os.getenv('PINECONE_API_KEY'),
            'environment': os.getenv('PINECONE_ENVIRONMENT'),
            'index_name': 'docex-rag-demo',
            'dimension': 1536,
            'metric': 'cosine'
        }
        
        enhanced_config = EnhancedRAGConfig(
            vector_db_type='pinecone',
            vector_db_config=pinecone_config,
            enable_hybrid_search=True,
            semantic_weight=0.5,
            vector_weight=0.5
        )
        
        # Create enhanced RAG service
        rag_service = EnhancedRAGService(
            semantic_search_service=semantic_search,
            llm_adapter=claude_adapter,
            config=enhanced_config
        )
        
        # Initialize Pinecone
        print("☁️  Initializing Pinecone vector database...")
        success = await rag_service.initialize_vector_db()
        
        if not success:
            print("❌ Failed to initialize Pinecone. Check your API key and environment.")
            return
        
        print("✅ Pinecone initialized")
        
        # Add documents
        print("📊 Adding documents to Pinecone...")
        await rag_service.add_documents_to_vector_db(basket.get_all_documents())
        
        # Test queries
        pinecone_questions = [
            "What are vector databases and how do they work?",
            "Explain the key components of natural language processing"
        ]
        
        for question in pinecone_questions:
            print(f"\n❓ {question}")
            result = await rag_service.query(question, basket_id=basket.id)
            print(f"💡 {result.answer}")
            print(f"⏱️  {result.processing_time:.2f}s | Confidence: {result.confidence_score:.2f}")
        
        print("\n✅ Pinecone example completed!")
        
    except Exception as e:
        print(f"❌ Pinecone example failed: {e}")
        logger.error(f"Pinecone error: {e}", exc_info=True)


async def comparison_demo():
    """Compare different search methods"""
    
    print("\n⚖️  Search Method Comparison")
    print("=" * 40)
    
    comparison_results = {
        'semantic_only': 'Uses existing DocEX semantic search with pgvector/memory',
        'vector_only': 'Uses FAISS or Pinecone vector databases exclusively',
        'hybrid': 'Combines semantic and vector search with weighted scoring'
    }
    
    for method, description in comparison_results.items():
        print(f"🔹 {method.title().replace('_', ' ')}: {description}")
    
    print("\nHybrid search typically provides the best results by leveraging")
    print("the strengths of both semantic understanding and vector similarity.")


if __name__ == "__main__":
    print("🚀 DocEX Enhanced RAG Examples")
    print("=" * 60)
    
    # Run FAISS example
    asyncio.run(faiss_rag_example())
    
    # Run Pinecone example (requires environment variables)
    asyncio.run(pinecone_rag_example())
    
    # Show comparison
    asyncio.run(comparison_demo())
    
    print("\n🎯 Next Steps:")
    print("- Install vector database dependencies:")
    print("  pip install faiss-cpu pinecone-client")
    print("- Set environment variables for Pinecone:")
    print("  export PINECONE_API_KEY=your_api_key")
    print("  export PINECONE_ENVIRONMENT=your_environment") 
    print("- Customize vector database configurations for your use case")
    print("- Experiment with different embedding models and search parameters")