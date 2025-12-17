"""
Semantic Search Service for DocEX

Provides semantic search capabilities using vector embeddings,
leveraging DocEX's document retrieval and metadata systems.
"""

import logging
import time
import hashlib
from typing import Dict, Any, Optional, List, Tuple

try:
    import numpy as np
    HAS_NUMPY = True
except ImportError:
    HAS_NUMPY = False
    # Fallback cosine similarity without numpy

from docex import DocEX
from docex.document import Document
from docex.processors.llm import BaseLLMProcessor

logger = logging.getLogger(__name__)


class SemanticSearchResult:
    """Result of a semantic search query"""
    
    def __init__(
        self,
        document: Document,
        similarity_score: float,
        metadata: Optional[Dict[str, Any]] = None
    ):
        self.document = document
        self.similarity_score = similarity_score
        self.metadata = metadata or {}
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            'document_id': self.document.id,
            'document_name': self.document.name,
            'similarity_score': self.similarity_score,
            'metadata': self.metadata
        }


class SemanticSearchService:
    """
    Semantic search service leveraging DocEX and vector databases.
    
    This service:
    1. Generates query embeddings using LLM adapters
    2. Searches vector database for similar documents
    3. Retrieves full documents from DocEX
    4. Filters and ranks results using DocEX metadata
    """
    
    def __init__(
        self,
        doc_ex: DocEX,
        llm_adapter: BaseLLMProcessor,
        vector_db_type: str = 'memory',
        vector_db_config: Optional[Dict[str, Any]] = None
    ):
        """
        Initialize semantic search service
        
        Args:
            doc_ex: DocEX instance for document retrieval
            llm_adapter: LLM adapter for generating embeddings
            vector_db_type: Type of vector database ('pgvector' for production, 'memory' for testing)
            vector_db_config: Configuration for vector database (not needed for memory)
        """
        self.doc_ex = doc_ex
        self.llm_adapter = llm_adapter
        self.vector_db_type = vector_db_type
        self.vector_db_config = vector_db_config or {}
        
        # Initialize vector database connection
        self.vector_db = self._initialize_vector_db()
        
        # Performance optimization: Cache for basket lookups
        self._basket_cache: Dict[str, Any] = {}
        self._basket_id_cache: Dict[str, str] = {}  # document_id -> basket_id cache
        
        # Query result cache for repeated searches
        self._query_cache: Dict[str, Tuple[List[SemanticSearchResult], float]] = {}
        self._cache_max_size = 100  # Maximum number of cached queries
        self._cache_ttl = 3600  # Cache TTL in seconds (1 hour)
    
    def _initialize_vector_db(self):
        """Initialize vector database based on type"""
        if self.vector_db_type == 'pgvector':
            return self._init_pgvector()
        elif self.vector_db_type == 'memory':
            return self._init_memory_db()
        else:
            raise ValueError(f"Unsupported vector_db_type: {self.vector_db_type}. Supported types: 'pgvector', 'memory'")
    
    def _init_pgvector(self):
        """Initialize pgvector connection"""
        from docex.db.connection import Database
        # Try to get tenant_id from doc_ex context if available
        tenant_id = None
        if hasattr(self.doc_ex, 'user_context') and self.doc_ex.user_context:
            tenant_id = getattr(self.doc_ex.user_context, 'tenant_id', None)
        db = Database(tenant_id=tenant_id) if tenant_id else Database()
        return {'type': 'pgvector', 'db': db}
    
    
    def _init_memory_db(self):
        """Initialize memory database (for testing)"""
        # Get vectors from config if provided (shared from VectorIndexingProcessor)
        vectors = self.vector_db_config.get('vectors', {})
        return {'type': 'memory', 'vectors': vectors}
    
    async def search(
        self,
        query: str,
        top_k: int = 10,
        basket_id: Optional[str] = None,
        filters: Optional[Dict[str, Any]] = None,
        min_similarity: float = 0.0,
        use_cache: bool = True
    ) -> List[SemanticSearchResult]:
        """
        Perform semantic search
        
        Args:
            query: Search query text
            top_k: Number of results to return
            basket_id: Optional basket ID to limit search
            filters: Optional metadata filters
            min_similarity: Minimum similarity score (0.0 to 1.0)
            use_cache: Whether to use query result cache
            
        Returns:
            List of SemanticSearchResult objects
        """
        try:
            # Check cache first
            if use_cache:
                cache_key = self._get_query_cache_key(query, basket_id, filters, top_k, min_similarity)
                cached_result = self._get_cached_query(cache_key)
                if cached_result is not None:
                    logger.debug(f"Returning cached search results for query: {query[:50]}...")
                    return cached_result
            
            # Generate query embedding
            logger.info(f"Generating embedding for query: {query[:50]}...")
            query_embedding = await self.llm_adapter.llm_service.generate_embedding(query)
            
            if not query_embedding:
                logger.error("Failed to generate query embedding")
                return []
            
            # Search vector database
            vector_results = await self._search_vectors(
                query_embedding,
                top_k=top_k * 2,  # Get more results for filtering
                basket_id=basket_id,
                filters=filters
            )
            
            # Apply minimum similarity threshold early
            filtered_results = [
                r for r in vector_results 
                if r['similarity'] >= min_similarity
            ]
            
            # Batch retrieve documents for better performance
            results = await self._batch_retrieve_documents(
                filtered_results,
                basket_id=basket_id,
                filters=filters,
                top_k=top_k
            )
            
            # Cache results
            if use_cache:
                self._cache_query(cache_key, results)
            
            return results
            
        except Exception as e:
            logger.error(f"Semantic search failed: {e}")
            return []
    
    async def _search_vectors(
        self,
        query_embedding: List[float],
        top_k: int,
        basket_id: Optional[str] = None,
        filters: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """Search vectors in database"""
        if self.vector_db_type == 'pgvector':
            return await self._search_pgvector(query_embedding, top_k, basket_id, filters)
        elif self.vector_db_type == 'memory':
            return await self._search_memory(query_embedding, top_k, basket_id, filters)
        else:
            raise ValueError(f"Unsupported vector_db_type: {self.vector_db_type}")
    
    async def _search_pgvector(
        self,
        query_embedding: List[float],
        top_k: int,
        basket_id: Optional[str] = None,
        filters: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """Search using pgvector"""
        db = self.vector_db['db']
        
        with db.session() as session:
            from sqlalchemy import text
            import json
            
            # Validate embedding input
            if not query_embedding or not isinstance(query_embedding, list):
                raise ValueError("Invalid query_embedding: must be a non-empty list")
            
            # Validate all embedding values are numeric
            try:
                embedding_array = [float(x) for x in query_embedding]
            except (ValueError, TypeError) as e:
                raise ValueError(f"Invalid embedding values: {e}")
            
            # Convert embedding to PostgreSQL array format using JSON for safe parameterization
            # PostgreSQL can cast JSON arrays to vector type
            embedding_json = json.dumps(embedding_array)
            
            # Ensure search_path includes public where pgvector types are
            try:
                current_schema = session.execute(text("SELECT current_schema()")).scalar()
                # Validate schema name to prevent injection (alphanumeric, underscore, hyphen only)
                if current_schema and not all(c.isalnum() or c in ('_', '-') for c in current_schema):
                    raise ValueError(f"Invalid schema name: {current_schema}")
                # Use quoted identifier for schema name to handle special characters safely
                # Note: SET search_path doesn't support parameters, so we validate the schema name instead
                if current_schema:
                    session.execute(text(f'SET search_path TO "{current_schema}", public, pg_catalog'))
                else:
                    session.execute(text('SET search_path TO public, pg_catalog'))
            except ValueError:
                # Re-raise ValueError (validation errors) - these are security issues
                raise
            except Exception as e:
                logger.debug(f"Could not set search_path: {e}")
            
            # Validate top_k
            if top_k <= 0 or top_k > 10000:
                raise ValueError(f"Invalid top_k value: {top_k} (must be between 1 and 10000)")
            
            # Validate basket_id if provided
            if basket_id:
                if not isinstance(basket_id, str) or not basket_id.strip():
                    raise ValueError("Invalid basket_id")
                basket_id = basket_id.strip()
            
            # Build parameterized query to prevent SQL injection
            # Optimized: Include basket_id in SELECT and apply metadata filters at database level
            query_str = """
                SELECT 
                    d.id,
                    d.basket_id,
                    1 - (d.embedding <=> CAST(:embedding_json::jsonb AS public.vector)) AS similarity
                FROM document d
            """
            
            params = {
                'embedding_json': embedding_json,
                'limit': int(top_k)
            }
            
            # Build WHERE clause
            where_clauses = ["d.embedding IS NOT NULL"]
            
            if basket_id:
                where_clauses.append("d.basket_id = :basket_id")
                params['basket_id'] = basket_id
            
            # Apply metadata filters at database level for better performance
            if filters:
                from docex.db.models import DocumentMetadata
                # Join with metadata table
                query_str += " INNER JOIN document_metadata dm ON dm.document_id = d.id"
                
                # Add metadata filter conditions
                filter_idx = 0
                for key, value in filters.items():
                    alias = f"dm{filter_idx}"
                    if filter_idx == 0:
                        # First filter uses the existing join
                        where_clauses.append("dm.key = :filter_key_0")
                        where_clauses.append("dm.value = :filter_value_0")
                    else:
                        # Additional filters need separate joins
                        query_str += f" INNER JOIN document_metadata {alias} ON {alias}.document_id = d.id"
                        where_clauses.append(f"{alias}.key = :filter_key_{filter_idx}")
                        where_clauses.append(f"{alias}.value = :filter_value_{filter_idx}")
                    
                    params[f'filter_key_{filter_idx}'] = key
                    params[f'filter_value_{filter_idx}'] = str(value)
                    filter_idx += 1
            
            # Combine WHERE clauses
            query_str += " WHERE " + " AND ".join(where_clauses)
            
            # Add ORDER BY and LIMIT with parameterized values
            query_str += " ORDER BY d.embedding <=> CAST(:embedding_json::jsonb AS public.vector) LIMIT :limit"
            
            query_sql = text(query_str)
            
            # Validate top_k
            if params['limit'] <= 0 or params['limit'] > 10000:
                raise ValueError(f"Invalid top_k value: {top_k} (must be between 1 and 10000)")
            
            results = session.execute(query_sql, params).fetchall()
            
            # Return results with basket_id included for batch retrieval optimization
            return [
                {
                    'document_id': row[0],
                    'basket_id': row[1],  # Include basket_id to avoid separate lookup
                    'similarity': float(row[2]),
                    'metadata': {}
                }
                for row in results
            ]
    
    async def _search_memory(
        self,
        query_embedding: List[float],
        top_k: int,
        basket_id: Optional[str] = None,
        filters: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """Search in-memory vectors (for testing) - Optimized with vectorized operations"""
        vectors = self.vector_db.get('vectors', {})
        
        if not vectors:
            logger.warning("No vectors found in memory database")
            return []
        
        # Pre-filter by basket_id if provided
        filtered_vectors = {}
        for doc_id, vector_data in vectors.items():
            if basket_id and vector_data.get('basket_id') != basket_id:
                continue
            embedding = vector_data.get('embedding')
            if embedding:
                filtered_vectors[doc_id] = vector_data
        
        if not filtered_vectors:
            return []
        
        # Vectorized similarity calculation using numpy for better performance
        if HAS_NUMPY and len(filtered_vectors) > 10:  # Use vectorized for larger sets
            similarities = self._batch_cosine_similarity(query_embedding, filtered_vectors)
        else:
            # Fallback to individual calculations for small sets
            similarities = []
            for doc_id, vector_data in filtered_vectors.items():
                similarity = self._cosine_similarity(query_embedding, vector_data['embedding'])
                similarities.append({
                    'document_id': doc_id,
                    'basket_id': vector_data.get('basket_id'),
                    'similarity': similarity,
                    'metadata': vector_data.get('metadata', {})
                })
        
        # Sort by similarity and return top_k
        similarities.sort(key=lambda x: x['similarity'], reverse=True)
        return similarities[:top_k]
    
    def _cosine_similarity(self, vec1: List[float], vec2: List[float]) -> float:
        """Calculate cosine similarity between two vectors"""
        try:
            if HAS_NUMPY:
                v1 = np.array(vec1)
                v2 = np.array(vec2)
                dot_product = np.dot(v1, v2)
                norm1 = np.linalg.norm(v1)
                norm2 = np.linalg.norm(v2)
                
                if norm1 == 0 or norm2 == 0:
                    return 0.0
                
                return float(dot_product / (norm1 * norm2))
            else:
                # Fallback without numpy
                dot_product = sum(a * b for a, b in zip(vec1, vec2))
                norm1 = sum(a * a for a in vec1) ** 0.5
                norm2 = sum(b * b for b in vec2) ** 0.5
                
                if norm1 == 0 or norm2 == 0:
                    return 0.0
                
                return float(dot_product / (norm1 * norm2))
        except Exception as e:
            logger.error(f"Error calculating cosine similarity: {e}")
            return 0.0
    
    def _batch_cosine_similarity(
        self,
        query_embedding: List[float],
        vectors: Dict[str, Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """Calculate cosine similarity for multiple vectors using vectorized operations"""
        if not HAS_NUMPY:
            # Fallback to individual calculations
            return [
                {
                    'document_id': doc_id,
                    'basket_id': vector_data.get('basket_id'),
                    'similarity': self._cosine_similarity(query_embedding, vector_data['embedding']),
                    'metadata': vector_data.get('metadata', {})
                }
                for doc_id, vector_data in vectors.items()
            ]
        
        try:
            # Convert query to numpy array
            query_vec = np.array(query_embedding, dtype=np.float32)
            query_norm = np.linalg.norm(query_vec)
            
            if query_norm == 0:
                return []
            
            # Normalize query vector
            query_vec = query_vec / query_norm
            
            # Prepare all embeddings
            doc_ids = []
            embeddings_list = []
            basket_ids = []
            metadata_list = []
            
            for doc_id, vector_data in vectors.items():
                doc_ids.append(doc_id)
                embeddings_list.append(vector_data['embedding'])
                basket_ids.append(vector_data.get('basket_id'))
                metadata_list.append(vector_data.get('metadata', {}))
            
            # Stack embeddings into a matrix
            embeddings_matrix = np.array(embeddings_list, dtype=np.float32)
            
            # Normalize all embeddings
            norms = np.linalg.norm(embeddings_matrix, axis=1, keepdims=True)
            norms[norms == 0] = 1  # Avoid division by zero
            embeddings_matrix = embeddings_matrix / norms
            
            # Calculate dot products (cosine similarity for normalized vectors)
            similarities = np.dot(embeddings_matrix, query_vec)
            
            # Build results
            results = [
                {
                    'document_id': doc_ids[i],
                    'basket_id': basket_ids[i],
                    'similarity': float(similarities[i]),
                    'metadata': metadata_list[i]
                }
                for i in range(len(doc_ids))
            ]
            
            return results
            
        except Exception as e:
            logger.warning(f"Vectorized similarity calculation failed, falling back: {e}")
            # Fallback to individual calculations
            return [
                {
                    'document_id': doc_id,
                    'basket_id': vector_data.get('basket_id'),
                    'similarity': self._cosine_similarity(query_embedding, vector_data['embedding']),
                    'metadata': vector_data.get('metadata', {})
                }
                for doc_id, vector_data in vectors.items()
            ]
    
    async def _batch_retrieve_documents(
        self,
        vector_results: List[Dict[str, Any]],
        basket_id: Optional[str] = None,
        filters: Optional[Dict[str, Any]] = None,
        top_k: int = 10
    ) -> List[SemanticSearchResult]:
        """Batch retrieve documents for better performance"""
        if not vector_results:
            return []
        
        # Group by basket_id for efficient batch retrieval
        basket_groups: Dict[str, List[Dict[str, Any]]] = {}
        for result in vector_results:
            result_basket_id = result.get('basket_id') or basket_id
            if not result_basket_id:
                # Need to look up basket_id
                result_basket_id = self._get_basket_id_for_document(result['document_id'])
            
            if result_basket_id:
                if result_basket_id not in basket_groups:
                    basket_groups[result_basket_id] = []
                basket_groups[result_basket_id].append(result)
        
        # Retrieve documents in batches per basket
        results = []
        for result_basket_id, group_results in basket_groups.items():
            try:
                basket = self._get_basket_cached(result_basket_id)
                if not basket:
                    continue
                
                # Batch get documents
                doc_ids = [r['document_id'] for r in group_results]
                documents = {}
                
                # Try to get documents in batch if possible
                for doc_id in doc_ids:
                    try:
                        doc = basket.get_document(doc_id)
                        if doc:
                            documents[doc_id] = doc
                    except Exception as e:
                        logger.debug(f"Failed to get document {doc_id}: {e}")
                        continue
                
                # Create results for successfully retrieved documents
                for result in group_results:
                    doc_id = result['document_id']
                    if doc_id in documents:
                        document = documents[doc_id]
                        # Apply filters if needed
                        if self._matches_filters(document, filters):
                            results.append(SemanticSearchResult(
                                document=document,
                                similarity_score=result['similarity'],
                                metadata=result.get('metadata', {})
                            ))
                            
                            # Stop if we have enough results
                            if len(results) >= top_k:
                                break
                
                if len(results) >= top_k:
                    break
                    
            except Exception as e:
                logger.warning(f"Failed to retrieve documents from basket {result_basket_id}: {e}")
                continue
        
        # Sort by similarity (descending) and return top_k
        results.sort(key=lambda x: x.similarity_score, reverse=True)
        return results[:top_k]
    
    def _get_basket_cached(self, basket_id: str):
        """Get basket with caching"""
        if basket_id in self._basket_cache:
            return self._basket_cache[basket_id]
        
        try:
            basket = self.doc_ex.get_basket(basket_id)
            self._basket_cache[basket_id] = basket
            return basket
        except Exception:
            return None
    
    def _get_basket_id_for_document(self, document_id: str) -> Optional[str]:
        """Get basket_id for a document with caching"""
        if document_id in self._basket_id_cache:
            return self._basket_id_cache[document_id]
        
        from docex.db.connection import Database
        from docex.db.models import Document as DocumentModel
        
        try:
            db = Database()
            with db.session() as session:
                doc = session.get(DocumentModel, document_id)
                if doc:
                    self._basket_id_cache[document_id] = doc.basket_id
                    return doc.basket_id
        except Exception as e:
            logger.debug(f"Failed to get basket_id for document {document_id}: {e}")
        
        return None
    
    def _find_basket_for_document(self, document_id: str):
        """Find basket containing a document - uses cache"""
        basket_id = self._get_basket_id_for_document(document_id)
        if basket_id:
            return self._get_basket_cached(basket_id)
        return None
    
    def clear_cache(self):
        """Clear the basket, basket_id, and query result caches"""
        self._basket_cache.clear()
        self._basket_id_cache.clear()
        self._query_cache.clear()
    
    def _get_query_cache_key(
        self,
        query: str,
        basket_id: Optional[str],
        filters: Optional[Dict[str, Any]],
        top_k: int,
        min_similarity: float
    ) -> str:
        """Generate cache key for query"""
        key_parts = [
            query,
            str(basket_id) if basket_id else '',
            str(sorted(filters.items())) if filters else '',
            str(top_k),
            str(min_similarity)
        ]
        key_string = '|'.join(key_parts)
        return hashlib.md5(key_string.encode()).hexdigest()
    
    def _get_cached_query(self, cache_key: str) -> Optional[List[SemanticSearchResult]]:
        """Get cached query result if available and not expired"""
        if cache_key in self._query_cache:
            cached_results, timestamp = self._query_cache[cache_key]
            current_time = time.time()
            
            if current_time - timestamp < self._cache_ttl:
                return cached_results
            else:
                # Remove expired cache entry
                self._query_cache.pop(cache_key, None)
        
        return None
    
    def _cache_query(self, cache_key: str, results: List[SemanticSearchResult]):
        """Cache query result"""
        # Limit cache size
        if len(self._query_cache) >= self._cache_max_size:
            # Remove oldest entries (simple FIFO)
            oldest_key = min(
                self._query_cache.keys(),
                key=lambda k: self._query_cache[k][1]
            )
            self._query_cache.pop(oldest_key, None)
        
        self._query_cache[cache_key] = (results, time.time())
    
    def _matches_filters(self, document: Document, filters: Optional[Dict[str, Any]]) -> bool:
        """Check if document matches filters"""
        if not filters:
            return True
        
        metadata = document.get_metadata_dict()
        
        for key, value in filters.items():
            # Extract actual value from metadata dict structure
            meta_value = metadata.get(key)
            if isinstance(meta_value, dict) and 'extra' in meta_value:
                meta_value = meta_value['extra'].get('value', meta_value)
            
            if meta_value != value:
                return False
        
        return True

