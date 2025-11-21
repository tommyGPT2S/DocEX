"""
Enhanced RAG Service with FAISS and Pinecone Integration

Extends the basic RAG service to support advanced vector databases
for improved performance and scalability.
"""

import logging
import asyncio
import numpy as np
from datetime import datetime
from typing import Dict, Any, List, Optional
from dataclasses import dataclass

from .rag_service import RAGService, RAGResult, SemanticSearchResult
from .vector_databases import BaseVectorDatabase, VectorDocument, VectorDatabaseFactory
from docex.processors.llm import BaseLLMProcessor
from docex.document import Document
from docex.processors.vector.semantic_search_service import SemanticSearchService

logger = logging.getLogger(__name__)


@dataclass
class EnhancedRAGConfig:
    """Configuration for enhanced RAG service"""
    
    # Vector database configuration
    vector_db_type: str = 'faiss'  # 'faiss' or 'pinecone'
    vector_db_config: Dict[str, Any] = None
    
    # Hybrid search configuration
    enable_hybrid_search: bool = True
    semantic_weight: float = 0.7  # Weight for semantic search results
    vector_weight: float = 0.3    # Weight for vector search results
    
    # Performance configuration
    enable_caching: bool = True
    cache_ttl_seconds: int = 3600
    batch_size: int = 100
    
    # RAG configuration (inherited from base)
    max_context_tokens: int = 4000
    top_k_documents: int = 5
    min_similarity: float = 0.7
    answer_style: str = 'detailed'
    include_citations: bool = True
    temperature: float = 0.3
    max_answer_tokens: int = 500

    def __post_init__(self):
        if self.vector_db_config is None:
            self.vector_db_config = {}


class EnhancedRAGService(RAGService):
    """
    Enhanced RAG service with support for multiple vector databases
    
    Features:
    - FAISS and Pinecone integration
    - Hybrid search combining semantic and vector search
    - Performance optimizations
    - Advanced caching
    """
    
    def __init__(
        self,
        semantic_search_service: SemanticSearchService,
        llm_adapter: BaseLLMProcessor,
        config: Optional[EnhancedRAGConfig] = None
    ):
        """
        Initialize enhanced RAG service
        
        Args:
            semantic_search_service: Existing semantic search service
            llm_adapter: LLM adapter for answer generation
            config: Enhanced RAG configuration
        """
        self.enhanced_config = config or EnhancedRAGConfig()
        
        # Initialize base RAG service
        base_config = {
            'max_context_tokens': self.enhanced_config.max_context_tokens,
            'top_k_documents': self.enhanced_config.top_k_documents,
            'min_similarity': self.enhanced_config.min_similarity,
            'answer_style': self.enhanced_config.answer_style,
            'include_citations': self.enhanced_config.include_citations,
            'temperature': self.enhanced_config.temperature,
            'max_answer_tokens': self.enhanced_config.max_answer_tokens
        }
        
        super().__init__(semantic_search_service, llm_adapter, base_config)
        
        # Initialize vector database
        self.vector_db: Optional[BaseVectorDatabase] = None
        self.vector_db_initialized = False
        
        # Initialize cache
        self.query_cache: Dict[str, RAGResult] = {}
        self.cache_timestamps: Dict[str, float] = {}
        
        logger.info(f"Enhanced RAG service initialized with config: {self.enhanced_config}")
    
    async def initialize_vector_db(self) -> bool:
        """Initialize the vector database"""
        try:
            logger.info(f"Initializing {self.enhanced_config.vector_db_type} vector database...")
            
            self.vector_db = VectorDatabaseFactory.create_database(
                self.enhanced_config.vector_db_type,
                self.enhanced_config.vector_db_config
            )
            
            self.vector_db_initialized = await self.vector_db.initialize()
            
            if self.vector_db_initialized:
                stats = await self.vector_db.get_statistics()
                logger.info(f"Vector database initialized successfully: {stats}")
            else:
                logger.error("Failed to initialize vector database")
            
            return self.vector_db_initialized
            
        except Exception as e:
            logger.error(f"Vector database initialization failed: {e}")
            return False
    
    async def query(
        self,
        question: str,
        basket_id: Optional[str] = None,
        filters: Optional[Dict[str, Any]] = None,
        context_override: Optional[Dict[str, Any]] = None
    ) -> RAGResult:
        """
        Enhanced query processing with vector database integration
        
        Args:
            question: User's question
            basket_id: Optional basket ID to limit search scope
            filters: Optional metadata filters
            context_override: Override configuration for this query
            
        Returns:
            RAGResult with enhanced search results
        """
        # Check cache first
        if self.enhanced_config.enable_caching:
            cached_result = self._get_cached_result(question, basket_id, filters)
            if cached_result:
                logger.info("Returning cached RAG result")
                return cached_result
        
        start_time = asyncio.get_event_loop().time()
        
        # Merge context override
        query_config = {**self.config, **(context_override or {})}
        
        logger.info(f"Processing enhanced RAG query: {question[:100]}...")
        
        try:
            # Determine search strategy
            if self.vector_db_initialized and self.enhanced_config.enable_hybrid_search:
                # Use hybrid search
                search_results = await self._hybrid_search(
                    question, basket_id, filters, query_config
                )
            elif self.vector_db_initialized:
                # Use vector database only
                search_results = await self._vector_search(
                    question, basket_id, filters, query_config
                )
            else:
                # Fallback to semantic search
                logger.info("Vector database not available, using semantic search")
                search_results = await self._retrieve_documents(
                    question, basket_id, filters, query_config
                )
            
            if not search_results:
                result = RAGResult(
                    query=question,
                    answer="I couldn't find any relevant documents to answer your question.",
                    sources=[],
                    confidence_score=0.0,
                    metadata={'no_sources_found': True, 'search_method': 'none'},
                    processing_time=asyncio.get_event_loop().time() - start_time
                )
            else:
                # Generate context and answer
                context = self._build_context(search_results, query_config)
                answer, confidence = await self._generate_answer(
                    question, context, search_results, query_config
                )
                
                result = RAGResult(
                    query=question,
                    answer=answer,
                    sources=search_results,
                    confidence_score=confidence,
                    metadata={
                        'num_sources': len(search_results),
                        'context_tokens': self._estimate_tokens(context),
                        'answer_style': query_config['answer_style'],
                        'llm_adapter': self.llm_adapter.__class__.__name__,
                        'search_method': self._get_search_method(),
                        'vector_db_type': self.enhanced_config.vector_db_type if self.vector_db_initialized else None
                    },
                    processing_time=asyncio.get_event_loop().time() - start_time
                )
            
            # Cache result
            if self.enhanced_config.enable_caching:
                self._cache_result(question, basket_id, filters, result)
            
            logger.info(f"Enhanced RAG query completed in {result.processing_time:.2f}s")
            return result
            
        except Exception as e:
            logger.error(f"Enhanced RAG query failed: {e}", exc_info=True)
            return RAGResult(
                query=question,
                answer=f"An error occurred while processing your question: {str(e)}",
                sources=[],
                confidence_score=0.0,
                metadata={'error': str(e)},
                processing_time=asyncio.get_event_loop().time() - start_time
            )
    
    async def _hybrid_search(
        self,
        question: str,
        basket_id: Optional[str],
        filters: Optional[Dict[str, Any]],
        config: Dict[str, Any]
    ) -> List[SemanticSearchResult]:
        """
        Perform hybrid search combining semantic and vector search
        """
        logger.info("Performing hybrid search...")
        
        # Get results from both search methods
        semantic_results_task = self._retrieve_documents(question, basket_id, filters, config)
        vector_results_task = self._vector_search(question, basket_id, filters, config)
        
        semantic_results, vector_results = await asyncio.gather(
            semantic_results_task,
            vector_results_task,
            return_exceptions=True
        )
        
        # Handle exceptions
        if isinstance(semantic_results, Exception):
            logger.warning(f"Semantic search failed: {semantic_results}")
            semantic_results = []
        
        if isinstance(vector_results, Exception):
            logger.warning(f"Vector search failed: {vector_results}")
            vector_results = []
        
        # Combine and rerank results
        combined_results = self._combine_search_results(
            semantic_results,
            vector_results,
            self.enhanced_config.semantic_weight,
            self.enhanced_config.vector_weight
        )
        
        # Deduplicate and sort by combined score
        final_results = self._deduplicate_results(combined_results)
        final_results.sort(key=lambda x: x.similarity_score, reverse=True)
        
        # Return top K results
        return final_results[:config['top_k_documents']]
    
    async def _vector_search(
        self,
        question: str,
        basket_id: Optional[str],
        filters: Optional[Dict[str, Any]],
        config: Dict[str, Any]
    ) -> List[SemanticSearchResult]:
        """
        Perform vector database search
        """
        if not self.vector_db_initialized:
            return []
        
        logger.info("Performing vector database search...")
        
        try:
            # Get query embedding using LLM adapter
            query_embedding = await self._get_query_embedding(question)
            
            # Search vector database
            vector_results = await self.vector_db.search(
                query_embedding=query_embedding,
                top_k=config['top_k_documents'] * 2,  # Get extra for filtering
                filters=filters,
                min_similarity=config['min_similarity']
            )
            
            # Convert vector results to semantic search results
            semantic_results = []
            for vector_result in vector_results:
                # Create a minimal mock Document for the vector result
                # since full Document construction requires many database fields
                class MockDocument:
                    def __init__(self, content, metadata, doc_id):
                        self.content = content
                        self.metadata = metadata
                        self.id = doc_id
                        self.name = metadata.get('original_name', f"doc_{doc_id}")
                        self.path = f"vector://{doc_id}"
                        self.content_type = "text/plain"
                        self.document_type = "vector"
                        self.size = len(content)
                        self.checksum = ""
                        self.status = "active"
                        self.created_at = datetime.now()
                        self.updated_at = datetime.now()
                
                doc = MockDocument(
                    content=vector_result.document.content,
                    metadata=vector_result.document.metadata,
                    doc_id=vector_result.document.id
                )
                
                semantic_result = SemanticSearchResult(
                    document=doc,
                    similarity_score=vector_result.similarity_score,
                    metadata={'vector_search': True, 'vector_id': vector_result.document.id}
                )
                semantic_results.append(semantic_result)
            
            return semantic_results
            
        except Exception as e:
            logger.error(f"Vector search failed: {e}")
            return []
    
    async def _get_query_embedding(self, question: str) -> np.ndarray:
        """Generate embedding for query using LLM adapter"""
        try:
            # Try to use the same embedding method as the vector indexing processor
            if hasattr(self.llm_adapter, 'generate_embeddings'):
                embeddings = await self.llm_adapter.generate_embeddings([question])
                return embeddings[0]
            
            # Fallback: use the semantic search service's embedding method
            elif hasattr(self.semantic_search, '_get_embedding'):
                return await self.semantic_search._get_embedding(question)
            
            else:
                # Last resort: create a simple embedding (not recommended for production)
                import numpy as np
                # This is a placeholder - in production, use proper embedding model
                return np.random.rand(384).astype(np.float32)  # Common embedding dimension
                
        except Exception as e:
            logger.error(f"Failed to generate query embedding: {e}")
            import numpy as np
            return np.random.rand(384).astype(np.float32)
    
    def _combine_search_results(
        self,
        semantic_results: List[SemanticSearchResult],
        vector_results: List[SemanticSearchResult],
        semantic_weight: float,
        vector_weight: float
    ) -> List[SemanticSearchResult]:
        """
        Combine results from different search methods with weighted scores
        """
        combined = []
        
        # Add semantic results with weights
        for result in semantic_results:
            weighted_score = result.similarity_score * semantic_weight
            new_result = SemanticSearchResult(
                document=result.document,
                similarity_score=weighted_score,
                metadata={
                    **result.metadata,
                    'search_method': 'semantic',
                    'original_score': result.similarity_score,
                    'weighted_score': weighted_score
                }
            )
            combined.append(new_result)
        
        # Add vector results with weights
        for result in vector_results:
            weighted_score = result.similarity_score * vector_weight
            new_result = SemanticSearchResult(
                document=result.document,
                similarity_score=weighted_score,
                metadata={
                    **result.metadata,
                    'search_method': 'vector',
                    'original_score': result.similarity_score,
                    'weighted_score': weighted_score
                }
            )
            combined.append(new_result)
        
        return combined
    
    def _deduplicate_results(
        self,
        results: List[SemanticSearchResult]
    ) -> List[SemanticSearchResult]:
        """
        Remove duplicate documents, keeping the highest scoring version
        """
        seen_docs = {}
        
        for result in results:
            # Create a key for deduplication (based on content or ID)
            doc_key = getattr(result.document, 'id', None) or result.document.content[:100]
            
            if doc_key not in seen_docs or result.similarity_score > seen_docs[doc_key].similarity_score:
                seen_docs[doc_key] = result
        
        return list(seen_docs.values())
    
    def _get_search_method(self) -> str:
        """Get the current search method being used"""
        if self.vector_db_initialized and self.enhanced_config.enable_hybrid_search:
            return 'hybrid'
        elif self.vector_db_initialized:
            return 'vector'
        else:
            return 'semantic'
    
    def _get_cached_result(
        self,
        question: str,
        basket_id: Optional[str],
        filters: Optional[Dict[str, Any]]
    ) -> Optional[RAGResult]:
        """Get cached result if available and not expired"""
        cache_key = self._get_cache_key(question, basket_id, filters)
        
        if cache_key in self.query_cache:
            timestamp = self.cache_timestamps.get(cache_key, 0)
            current_time = asyncio.get_event_loop().time()
            
            if current_time - timestamp < self.enhanced_config.cache_ttl_seconds:
                return self.query_cache[cache_key]
            else:
                # Remove expired cache entry
                self.query_cache.pop(cache_key, None)
                self.cache_timestamps.pop(cache_key, None)
        
        return None
    
    def _cache_result(
        self,
        question: str,
        basket_id: Optional[str],
        filters: Optional[Dict[str, Any]],
        result: RAGResult
    ):
        """Cache query result"""
        cache_key = self._get_cache_key(question, basket_id, filters)
        
        self.query_cache[cache_key] = result
        self.cache_timestamps[cache_key] = asyncio.get_event_loop().time()
        
        # Limit cache size
        if len(self.query_cache) > 1000:  # Arbitrary limit
            # Remove oldest entries
            sorted_items = sorted(
                self.cache_timestamps.items(),
                key=lambda x: x[1]
            )
            
            for old_key, _ in sorted_items[:100]:  # Remove oldest 100
                self.query_cache.pop(old_key, None)
                self.cache_timestamps.pop(old_key, None)
    
    def _get_cache_key(
        self,
        question: str,
        basket_id: Optional[str],
        filters: Optional[Dict[str, Any]]
    ) -> str:
        """Generate cache key for query"""
        import hashlib
        
        key_parts = [question]
        if basket_id:
            key_parts.append(f"basket:{basket_id}")
        if filters:
            key_parts.append(f"filters:{str(sorted(filters.items()))}")
        
        key_string = "|".join(key_parts)
        return hashlib.md5(key_string.encode()).hexdigest()
    
    async def add_documents_to_vector_db(self, documents: List[Document]) -> bool:
        """
        Add documents to the vector database
        
        Args:
            documents: List of Document objects to add
            
        Returns:
            True if successful, False otherwise
        """
        if not self.vector_db_initialized:
            logger.error("Vector database not initialized")
            return False
        
        try:
            logger.info(f"Adding {len(documents)} documents to vector database...")
            
            # Convert Documents to VectorDocuments
            vector_docs = []
            
            for doc in documents:
                # Generate embedding for document - get content properly
                try:
                    # Try to get content using Document's get_content method
                    if hasattr(doc, 'get_content'):
                        content = doc.get_content(mode='text')
                    elif hasattr(doc, 'content'):
                        content = doc.content
                    else:
                        content = str(doc)
                except Exception as e:
                    logger.warning(f"Failed to get content from document {doc}: {e}")
                    content = str(doc)
                
                embedding = await self._get_query_embedding(content)
                
                # Create VectorDocument
                vector_doc = VectorDocument(
                    id=getattr(doc, 'id', None) or str(hash(content)),
                    content=content,
                    embedding=embedding,
                    metadata=getattr(doc, 'metadata', {}),
                    basket_id=getattr(doc, 'basket_id', None)
                )
                vector_docs.append(vector_doc)
            
            # Add to vector database in batches
            batch_size = self.enhanced_config.batch_size
            for i in range(0, len(vector_docs), batch_size):
                batch = vector_docs[i:i + batch_size]
                success = await self.vector_db.add_documents(batch)
                
                if not success:
                    logger.error(f"Failed to add batch {i//batch_size + 1}")
                    return False
            
            logger.info(f"Successfully added {len(documents)} documents to vector database")
            return True
            
        except Exception as e:
            logger.error(f"Failed to add documents to vector database: {e}")
            return False
    
    async def get_vector_db_stats(self) -> Dict[str, Any]:
        """Get vector database statistics"""
        if not self.vector_db_initialized:
            return {'error': 'Vector database not initialized'}
        
        try:
            stats = await self.vector_db.get_statistics()
            stats['cache_size'] = len(self.query_cache)
            stats['search_method'] = self._get_search_method()
            return stats
        except Exception as e:
            logger.error(f"Failed to get vector DB stats: {e}")
            return {'error': str(e)}