"""
Semantic Search Service for DocEX

Provides semantic search capabilities using vector embeddings,
leveraging DocEX's document retrieval and metadata systems.
"""

import logging
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
        min_similarity: float = 0.0
    ) -> List[SemanticSearchResult]:
        """
        Perform semantic search
        
        Args:
            query: Search query text
            top_k: Number of results to return
            basket_id: Optional basket ID to limit search
            filters: Optional metadata filters
            min_similarity: Minimum similarity score (0.0 to 1.0)
            
        Returns:
            List of SemanticSearchResult objects
        """
        try:
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
            
            # Retrieve documents from DocEX and filter
            results = []
            for vector_result in vector_results:
                doc_id = vector_result['document_id']
                similarity = vector_result['similarity']
                
                # Apply minimum similarity threshold
                if similarity < min_similarity:
                    continue
                
                # Get document from DocEX
                try:
                    # Try to get basket first
                    if basket_id:
                        try:
                            basket = self.doc_ex.get_basket(basket_id)
                        except Exception:
                            basket = None
                    else:
                        # Find basket by searching all baskets
                        basket = self._find_basket_for_document(doc_id)
                    
                    if basket:
                        document = basket.get_document(doc_id)
                        if document:
                            # Apply additional filters if needed
                            if self._matches_filters(document, filters):
                                results.append(SemanticSearchResult(
                                    document=document,
                                    similarity_score=similarity,
                                    metadata=vector_result.get('metadata', {})
                                ))
                except Exception as e:
                    logger.warning(f"Failed to retrieve document {doc_id}: {e}")
                    continue
                
                # Stop if we have enough results
                if len(results) >= top_k:
                    break
            
            # Sort by similarity (descending)
            results.sort(key=lambda x: x.similarity_score, reverse=True)
            
            return results[:top_k]
            
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
            # Use CAST with parameterized JSON array instead of string interpolation
            # Build query string with conditional WHERE clause
            query_str = """
                SELECT 
                    id,
                    1 - (embedding <=> CAST(:embedding_json::jsonb AS public.vector)) AS similarity
                FROM document
                WHERE embedding IS NOT NULL
            """
            
            params = {
                'embedding_json': embedding_json,
                'limit': int(top_k)
            }
            
            if basket_id:
                query_str += " AND basket_id = :basket_id"
                params['basket_id'] = basket_id
            
            # Add ORDER BY and LIMIT with parameterized values
            query_str += " ORDER BY embedding <=> CAST(:embedding_json::jsonb AS public.vector) LIMIT :limit"
            
            query_sql = text(query_str)
            
            # Validate top_k
            if params['limit'] <= 0 or params['limit'] > 10000:
                raise ValueError(f"Invalid top_k value: {top_k} (must be between 1 and 10000)")
            
            results = session.execute(query_sql, params).fetchall()
            
            return [
                {
                    'document_id': row[0],
                    'similarity': float(row[1]),
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
        """Search in-memory vectors (for testing)"""
        vectors = self.vector_db.get('vectors', {})
        
        if not vectors:
            logger.warning("No vectors found in memory database")
            return []
        
        # Calculate cosine similarity for all vectors
        similarities = []
        for doc_id, vector_data in vectors.items():
            # Apply filters
            if basket_id and vector_data.get('basket_id') != basket_id:
                continue
            
            embedding = vector_data.get('embedding')
            if not embedding:
                continue
            
            # Calculate cosine similarity
            similarity = self._cosine_similarity(query_embedding, embedding)
            
            similarities.append({
                'document_id': doc_id,
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
    
    def _find_basket_for_document(self, document_id: str):
        """Find basket containing a document"""
        # This is a helper method - in practice, you might want to store basket_id in vector metadata
        from docex.db.connection import Database
        from docex.db.models import Document as DocumentModel
        from sqlalchemy import select
        
        db = Database()
        with db.session() as session:
            doc = session.get(DocumentModel, document_id)
            if doc:
                return self.doc_ex.get_basket(doc.basket_id)
        return None
    
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

