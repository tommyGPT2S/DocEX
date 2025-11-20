"""
Enhanced RAG Example with FAISS and Pinecone

This example demonstrates the advanced RAG service with vector database integration
"""

import asyncio
import logging
import os
import tempfile
import numpy as np
import hashlib
from typing import List
from docex.docbasket import DocBasket
from docex.processors.llm.claude_adapter import ClaudeAdapter
from docex.processors.vector.semantic_search_service import SemanticSearchService
from docex.processors.rag import EnhancedRAGService, EnhancedRAGConfig

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class EmbeddingService:
    """Unified embedding service with automatic provider detection.
    
    Automatically detects and initializes the best available embedding provider:
    1. OpenAI (if API key available)
    2. Ollama (if server running locally)
    3. Mock embeddings (fallback for testing)
    
    Supports different embedding dimensions and models for optimal performance.
    """
    """Embedding service supporting multiple providers"""
    
    def __init__(self, provider: str = "auto", **kwargs):
        self.provider = provider
        self.client = None
        self.model_name = None
        self.dimension = 1536  # Default OpenAI dimension
        
        if provider == "auto":
            self._auto_detect_provider(**kwargs)
        elif provider == "openai":
            self._init_openai(**kwargs)
        elif provider == "ollama":
            self._init_ollama(**kwargs)
        elif provider == "mock":
            self._init_mock(**kwargs)
        else:
            raise ValueError(f"Unsupported embedding provider: {provider}")
    
    def _auto_detect_provider(self, **kwargs):
        """Auto-detect the best available embedding provider"""
        # Try OpenAI first
        try:
            import openai
            if os.getenv('OPENAI_API_KEY'):
                self._init_openai(**kwargs)
                return
        except ImportError:
            pass
        
        # Try Ollama
        try:
            import ollama
            # Test if Ollama is running
            ollama.list()
            self._init_ollama(**kwargs)
            return
        except (ImportError, Exception):
            pass
        
        # Fallback to mock
        logger.warning("No embedding provider available, using mock embeddings")
        self._init_mock(**kwargs)
    
    def _init_openai(self, **kwargs):
        """Initialize OpenAI embedding service"""
        try:
            import openai
            self.client = openai.OpenAI()
            self.model_name = kwargs.get('model', 'text-embedding-3-small')
            self.dimension = 1536  # text-embedding-3-small dimension
            self.provider = "openai"
            logger.info(f"Initialized OpenAI embeddings with model: {self.model_name}")
        except Exception as e:
            logger.error(f"Failed to initialize OpenAI: {e}")
            self._init_mock(**kwargs)
    
    def _init_ollama(self, **kwargs):
        """Initialize Ollama embedding service"""
        try:
            import ollama
            self.client = ollama
            # Use a common embedding model for Ollama
            self.model_name = kwargs.get('model', 'nomic-embed-text')
            self.dimension = 768  # Common dimension for nomic-embed-text
            self.provider = "ollama"
            
            # Test the model
            try:
                test_result = self.client.embeddings(model=self.model_name, prompt="test")
                if 'embedding' in test_result:
                    self.dimension = len(test_result['embedding'])
                    logger.info(f"Initialized Ollama embeddings with model: {self.model_name}, dimension: {self.dimension}")
                else:
                    raise Exception("Model test failed")
            except Exception:
                logger.warning(f"Model {self.model_name} not available, trying to pull...")
                try:
                    self.client.pull(self.model_name)
                    logger.info(f"Successfully pulled {self.model_name}")
                except Exception as pull_error:
                    logger.error(f"Failed to pull model: {pull_error}")
                    self._init_mock(**kwargs)
                    return
                    
        except Exception as e:
            logger.error(f"Failed to initialize Ollama: {e}")
            self._init_mock(**kwargs)
    
    def _init_mock(self, **kwargs):
        """Initialize mock embedding service"""
        self.provider = "mock"
        self.model_name = "mock-embeddings"
        self.dimension = kwargs.get('dimension', 1536)
        logger.info(f"Initialized mock embeddings with dimension: {self.dimension}")
    
    async def get_embeddings(self, texts: List[str]) -> List[np.ndarray]:
        """Get embeddings for a list of texts"""
        if self.provider == "openai":
            return await self._get_openai_embeddings(texts)
        elif self.provider == "ollama":
            return await self._get_ollama_embeddings(texts)
        else:
            return await self._get_mock_embeddings(texts)
    
    async def _get_openai_embeddings(self, texts: List[str]) -> List[np.ndarray]:
        """Get embeddings from OpenAI"""
        try:
            response = self.client.embeddings.create(
                input=texts,
                model=self.model_name
            )
            embeddings = [np.array(data.embedding, dtype=np.float32) for data in response.data]
            return embeddings
        except Exception as e:
            logger.error(f"OpenAI embedding error: {e}")
            return await self._get_mock_embeddings(texts)
    
    async def _get_ollama_embeddings(self, texts: List[str]) -> List[np.ndarray]:
        """Get embeddings from Ollama"""
        try:
            embeddings = []
            for text in texts:
                response = self.client.embeddings(
                    model=self.model_name,
                    prompt=text
                )
                embedding = np.array(response['embedding'], dtype=np.float32)
                embeddings.append(embedding)
            return embeddings
        except Exception as e:
            logger.error(f"Ollama embedding error: {e}")
            return await self._get_mock_embeddings(texts)
    
    async def _get_mock_embeddings(self, texts: List[str]) -> List[np.ndarray]:
        """Generate mock embeddings based on text hash"""
        embeddings = []
        for text in texts:
            # Create deterministic embedding based on text hash
            hash_obj = hashlib.md5(text.encode())
            seed = int(hash_obj.hexdigest()[:8], 16)
            np.random.seed(seed)
            embedding = np.random.rand(self.dimension).astype(np.float32)
            # Normalize the embedding
            embedding = embedding / np.linalg.norm(embedding)
            embeddings.append(embedding)
        return embeddings


async def faiss_rag_example():
    """Demonstrate RAG with FAISS vector database.
    
    This example shows:
    - Local document processing and storage
    - FAISS vector indexing with cosine similarity
    - Ollama embeddings for semantic representation
    - Query processing with similarity search
    - Persistent storage for vector index
    
    FAISS is ideal for:
    - Local development and testing
    - Privacy-sensitive applications
    - Offline processing
    - Cost-effective vector search
    """
    """Demonstrate RAG with FAISS vector database"""
    
    print("🔬 DocEX Enhanced RAG with FAISS")
    print("=" * 50)
    
    try:
        # Step 1: Create documents
        print("📁 Creating sample document collection...")
        
        # Create basket using the proper create method with unique name
        import datetime
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        basket_name = f"Tech_Docs_FAISS_{timestamp}"
        
        basket = DocBasket.create(
            name=basket_name,
            description="Sample technology documentation for FAISS RAG testing"
        )
        
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
            # Create temporary file with the document content
            with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as tmp_file:
                tmp_file.write(doc_info['content'])
                tmp_file_path = tmp_file.name
            
            try:
                # Add document to basket using file path
                doc = basket.add(
                    file_path=tmp_file_path,
                    document_type='file',
                    metadata={
                        'category': 'technology',
                        'type': 'guide', 
                        'added_by': 'example',
                        'original_name': doc_info['name']
                    }
                )
                
                # Update document name to be more descriptive
                doc.name = doc_info['name']
                
            finally:
                # Clean up temporary file
                try:
                    os.unlink(tmp_file_path)
                except OSError:
                    pass
        
        print(f"✅ Created {len(documents)} documents")
        
        # Step 2: Initialize embedding service
        print("🔍 Initializing embedding service...")
        embedding_service = EmbeddingService(provider="auto")
        
        # Step 3: Initialize LLM adapter
        print("🤖 Initializing Ollama LLM adapter...")
        try:
            from docex.processors.llm.ollama_adapter import OllamaAdapter
            ollama_config = {
                'base_url': 'http://127.0.0.1:11434',
                'model': 'llama3.2',  # Use available model
                'max_tokens': 4000
            }
            llm_adapter = OllamaAdapter(ollama_config)
        except ImportError:
            # Fallback to Claude if Ollama adapter doesn't exist
            print("   Ollama adapter not found, using Claude...")
            claude_config = {
                'api_key': os.getenv('ANTHROPIC_API_KEY'),  # Use environment variable
            'model': 'claude-3-sonnet-20240229',
            'max_tokens': 4000
            }
            llm_adapter = ClaudeAdapter(claude_config)
        
        # Add embedding capability to LLM adapter
        llm_adapter.generate_embeddings = embedding_service.get_embeddings
        print(f"✅ LLM adapter ready with {embedding_service.provider} embeddings (dim: {embedding_service.dimension})")
        
        # Step 3: For this demo, we'll skip semantic search initialization
        # as it requires more complex setup. We'll focus on vector database RAG.
        print("🔍 Skipping semantic search for this FAISS demo...")
        semantic_search = None
        
        # Step 4: Configure enhanced RAG with FAISS (vector-only mode)
        print("⚡ Configuring enhanced RAG with FAISS...")
        
        # FAISS configuration (use embedding service dimension)
        faiss_config = {
            'dimension': embedding_service.dimension,
            'index_type': 'flat',  # Simple flat index for demo
            'metric': 'cosine',
            'storage_path': f'./storage/faiss_index_{embedding_service.provider}.bin'  # Provider-specific index
        }
        
        enhanced_config = EnhancedRAGConfig(
            vector_db_type='faiss',
            vector_db_config=faiss_config,
            enable_hybrid_search=False,  # Vector-only for demo
            semantic_weight=0.0,
            vector_weight=1.0,
            enable_caching=True,
            top_k_documents=5,
            min_similarity=0.3  # Lower threshold for demo (was 0.75)
        )
        
        # Create enhanced RAG service
        rag_service = EnhancedRAGService(
            semantic_search_service=semantic_search,
            llm_adapter=llm_adapter,
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
        
        basket_docs = basket.list()
        docs_added = await rag_service.add_documents_to_vector_db(basket_docs)
        
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
    """Demonstrate RAG with Pinecone cloud vector database.
    
    This example shows:
    - Cloud-based vector storage and retrieval
    - Scalable indexing for large document collections
    - Ollama LLM integration for local text generation
    - Enhanced RAG service with confidence scoring
    - Proper DocBasket integration
    
    Pinecone is ideal for:
    - Production applications
    - Large-scale document collections
    - Multi-user systems
    - Hybrid cloud architectures
    """
    """Demonstrate RAG with Pinecone vector database"""
    
    print("\n☁️  DocEX Enhanced RAG with Pinecone")
    print("=" * 50)
    
    # We'll set up to use environment variables that you can provide
    print("🔑 Pinecone Configuration:")
    print("   PINECONE_API_KEY: [To be provided]")
    print("   PINECONE_ENVIRONMENT: [To be provided]")
    print("   INDEX_NAME: docex-demo")
    
    try:
        print("📊 Setting up documents for Pinecone...")
        
        # Create basket with unique name
        import datetime
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        basket_name = f"Pinecone_Demo_{timestamp}"
        
        basket = DocBasket.create(
            name=basket_name,
            description="Pinecone vector database demo documents"
        )
        
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
            # Create temporary file with the document content
            with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as tmp_file:
                tmp_file.write(doc_info['content'])
                tmp_file_path = tmp_file.name
            
            try:
                # Add document to basket using file path
                doc = basket.add(
                    file_path=tmp_file_path,
                    document_type='file',
                    metadata={
                        'category': 'nlp',
                        'type': 'advanced', 
                        'added_by': 'pinecone_example',
                        'original_name': doc_info['name']
                    }
                )
                
                # Update document name
                doc.name = doc_info['name']
                
            finally:
                # Clean up temporary file
                try:
                    os.unlink(tmp_file_path)
                except OSError:
                    pass
        
        print(f"✅ Created {len(tech_docs)} documents")
        
        # Initialize embedding service
        print("🔍 Initializing embedding service...")
        embedding_service = EmbeddingService(provider="auto")
        
        # Initialize LLM adapter
        print("🤖 Initializing Ollama LLM adapter...")
        try:
            from docex.processors.llm.ollama_adapter import OllamaAdapter
            ollama_config = {
                'base_url': 'http://127.0.0.1:11434',
                'model': 'llama3.2',  # Use available model
                'max_tokens': 4000
            }
            llm_adapter = OllamaAdapter(ollama_config)
            await llm_adapter.initialize()
            print("   ✅ Ollama LLM adapter ready")
        except Exception as e:
            # Fallback to Claude if Ollama adapter doesn't work
            print(f"   ❌ Ollama adapter failed: {e}")
            print("   Fallback to Claude...")
            from docex.processors.llm.claude_adapter import ClaudeAdapter
            claude_config = {
                'api_key': os.getenv('ANTHROPIC_API_KEY'),  # Use environment variable
                'model': 'claude-3-sonnet-20240229',
                'max_tokens': 4000
            }
            llm_adapter = ClaudeAdapter(claude_config)
        
        llm_adapter.generate_embeddings = embedding_service.get_embeddings
        print(f"✅ Services ready with {embedding_service.provider} embeddings (dim: {embedding_service.dimension})")
        
        # For this demo, we'll skip semantic search setup
        semantic_search = None
        
        # Configure Pinecone with your credentials
        print("☁️  Configuring Pinecone...")
        pinecone_config = {
            'api_key': os.getenv('PINECONE_API_KEY'),  # Use environment variable
            'index_name': 'docex-rag-demo',
            'dimension': embedding_service.dimension,  # Use actual embedding dimension
            'metric': 'cosine'
        }
        
        enhanced_config = EnhancedRAGConfig(
            vector_db_type='pinecone',
            vector_db_config=pinecone_config,
            enable_hybrid_search=False,  # Vector-only for demo
            semantic_weight=0.0,
            vector_weight=1.0,
            enable_caching=True,
            top_k_documents=5,
            min_similarity=0.3  # Lower threshold for demo
        )
        
        # Show configuration
        print(f"   API Key: {pinecone_config['api_key'][:20]}...")
        print(f"   Index Name: {pinecone_config['index_name']}")
        print(f"   Dimension: {pinecone_config['dimension']}")
        
        # Create enhanced RAG service
        rag_service = EnhancedRAGService(
            semantic_search_service=semantic_search,
            llm_adapter=llm_adapter,
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
        basket_docs = basket.list()
        docs_added = await rag_service.add_documents_to_vector_db(basket_docs)
        
        if docs_added:
            print("✅ Documents added to Pinecone")
        else:
            print("❌ Failed to add documents to Pinecone")
            return
        
        # Get stats
        stats = await rag_service.get_vector_db_stats()
        print(f"📈 Pinecone Stats: {stats}")
        
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