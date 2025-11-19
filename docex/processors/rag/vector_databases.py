"""
Vector Database Adapters for FAISS and Pinecone Integration

Provides standardized interfaces for different vector database backends
to support advanced RAG functionality in DocEX.
"""

import logging
import numpy as np
import json
import asyncio
from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional
from dataclasses import dataclass
from datetime import datetime

logger = logging.getLogger(__name__)


@dataclass
class VectorDocument:
    """Document representation for vector storage"""
    
    id: str
    content: str
    embedding: np.ndarray
    metadata: Dict[str, Any]
    basket_id: Optional[str] = None
    timestamp: Optional[datetime] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization"""
        return {
            'id': self.id,
            'content': self.content,
            'embedding': self.embedding.tolist() if isinstance(self.embedding, np.ndarray) else self.embedding,
            'metadata': self.metadata,
            'basket_id': self.basket_id,
            'timestamp': self.timestamp.isoformat() if self.timestamp else None
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'VectorDocument':
        """Create from dictionary"""
        embedding = np.array(data['embedding']) if isinstance(data['embedding'], list) else data['embedding']
        timestamp = datetime.fromisoformat(data['timestamp']) if data['timestamp'] else None
        
        return cls(
            id=data['id'],
            content=data['content'],
            embedding=embedding,
            metadata=data['metadata'],
            basket_id=data.get('basket_id'),
            timestamp=timestamp
        )


@dataclass
class VectorSearchResult:
    """Result from vector search"""
    
    document: VectorDocument
    similarity_score: float
    rank: int
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            'document': self.document.to_dict(),
            'similarity_score': self.similarity_score,
            'rank': self.rank
        }


class BaseVectorDatabase(ABC):
    """Abstract base class for vector database implementations"""
    
    @abstractmethod
    async def initialize(self) -> bool:
        """Initialize the vector database"""
        pass
    
    @abstractmethod
    async def add_documents(self, documents: List[VectorDocument]) -> bool:
        """Add documents to the vector database"""
        pass
    
    @abstractmethod
    async def search(
        self,
        query_embedding: np.ndarray,
        top_k: int = 10,
        filters: Optional[Dict[str, Any]] = None,
        min_similarity: Optional[float] = None
    ) -> List[VectorSearchResult]:
        """Search for similar vectors"""
        pass
    
    @abstractmethod
    async def delete_documents(self, document_ids: List[str]) -> bool:
        """Delete documents by IDs"""
        pass
    
    @abstractmethod
    async def update_document(self, document: VectorDocument) -> bool:
        """Update a document"""
        pass
    
    @abstractmethod
    async def get_document_count(self) -> int:
        """Get total number of documents"""
        pass
    
    @abstractmethod
    async def get_statistics(self) -> Dict[str, Any]:
        """Get database statistics"""
        pass


class FAISSVectorDatabase(BaseVectorDatabase):
    """
    FAISS (Facebook AI Similarity Search) vector database implementation
    
    Provides high-performance similarity search using FAISS library
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        Initialize FAISS vector database
        
        Args:
            config: Configuration with:
                - index_type: 'flat', 'ivf', 'hnsw' (default: 'flat')
                - dimension: Embedding dimension (required)
                - metric: 'cosine', 'l2', 'inner_product' (default: 'cosine')
                - nlist: Number of clusters for IVF (default: 100)
                - storage_path: Path to persist index (optional)
                - enable_gpu: Use GPU acceleration if available (default: False)
        """
        self.config = config or {}
        self.index = None
        self.documents: Dict[str, VectorDocument] = {}
        self.id_to_index: Dict[str, int] = {}
        self.index_to_id: Dict[int, str] = {}
        self.dimension = self.config.get('dimension')
        self.is_initialized = False
        
        if not self.dimension:
            raise ValueError("Dimension must be specified in config")
    
    async def initialize(self) -> bool:
        """Initialize FAISS index"""
        try:
            import faiss
            
            dimension = self.dimension
            index_type = self.config.get('index_type', 'flat')
            metric = self.config.get('metric', 'cosine')
            
            logger.info(f"Initializing FAISS index: {index_type}, dimension: {dimension}, metric: {metric}")
            
            # Create index based on type
            if index_type == 'flat':
                if metric == 'cosine':
                    # Normalize vectors and use inner product for cosine similarity
                    self.index = faiss.IndexFlatIP(dimension)
                    self.normalize_embeddings = True
                elif metric == 'l2':
                    self.index = faiss.IndexFlatL2(dimension)
                    self.normalize_embeddings = False
                else:
                    self.index = faiss.IndexFlatIP(dimension)
                    self.normalize_embeddings = False
            
            elif index_type == 'ivf':
                nlist = self.config.get('nlist', 100)
                quantizer = faiss.IndexFlatIP(dimension) if metric == 'cosine' else faiss.IndexFlatL2(dimension)
                self.index = faiss.IndexIVFFlat(quantizer, dimension, nlist)
                self.normalize_embeddings = metric == 'cosine'
            
            elif index_type == 'hnsw':
                m = self.config.get('hnsw_m', 32)
                self.index = faiss.IndexHNSWFlat(dimension, m)
                if metric == 'cosine':
                    self.index.metric_type = faiss.METRIC_INNER_PRODUCT
                    self.normalize_embeddings = True
                else:
                    self.index.metric_type = faiss.METRIC_L2
                    self.normalize_embeddings = False
            
            else:
                raise ValueError(f"Unsupported index type: {index_type}")
            
            # Enable GPU if requested and available
            if self.config.get('enable_gpu', False):
                try:
                    gpu_index = faiss.index_cpu_to_gpu(faiss.StandardGpuResources(), 0, self.index)
                    self.index = gpu_index
                    logger.info("GPU acceleration enabled")
                except Exception as e:
                    logger.warning(f"GPU acceleration failed, using CPU: {e}")
            
            # Load existing index if storage path provided
            storage_path = self.config.get('storage_path')
            if storage_path:
                try:
                    self.index = faiss.read_index(storage_path)
                    # Load document metadata
                    metadata_path = storage_path + '.metadata'
                    with open(metadata_path, 'r') as f:
                        metadata = json.load(f)
                        self.documents = {
                            doc_id: VectorDocument.from_dict(doc_data)
                            for doc_id, doc_data in metadata['documents'].items()
                        }
                        self.id_to_index = metadata['id_to_index']
                        self.index_to_id = {v: k for k, v in self.id_to_index.items()}
                    
                    logger.info(f"Loaded existing FAISS index with {len(self.documents)} documents")
                except Exception as e:
                    logger.warning(f"Failed to load existing index: {e}")
            
            self.is_initialized = True
            logger.info("FAISS vector database initialized successfully")
            return True
            
        except ImportError:
            logger.error("FAISS library not found. Install with: pip install faiss-cpu or pip install faiss-gpu")
            return False
        except Exception as e:
            logger.error(f"Failed to initialize FAISS database: {e}")
            return False
    
    async def add_documents(self, documents: List[VectorDocument]) -> bool:
        """Add documents to FAISS index"""
        if not self.is_initialized:
            logger.error("Database not initialized")
            return False
        
        try:
            import faiss
            
            embeddings = []
            for doc in documents:
                # Store document metadata
                self.documents[doc.id] = doc
                
                # Prepare embedding
                embedding = doc.embedding.copy()
                if self.normalize_embeddings:
                    faiss.normalize_L2(embedding.reshape(1, -1))
                embeddings.append(embedding)
                
                # Update index mappings
                next_index = len(self.id_to_index)
                self.id_to_index[doc.id] = next_index
                self.index_to_id[next_index] = doc.id
            
            # Add to FAISS index
            embeddings_array = np.vstack(embeddings).astype(np.float32)
            self.index.add(embeddings_array)
            
            # Train index if needed (for IVF)
            if hasattr(self.index, 'is_trained') and not self.index.is_trained:
                if self.index.ntotal >= self.config.get('nlist', 100):
                    self.index.train(embeddings_array)
                    logger.info("FAISS index trained")
            
            # Save index if storage path provided
            await self._save_index()
            
            logger.info(f"Added {len(documents)} documents to FAISS index")
            return True
            
        except Exception as e:
            logger.error(f"Failed to add documents to FAISS: {e}")
            return False
    
    async def search(
        self,
        query_embedding: np.ndarray,
        top_k: int = 10,
        filters: Optional[Dict[str, Any]] = None,
        min_similarity: Optional[float] = None
    ) -> List[VectorSearchResult]:
        """Search for similar vectors in FAISS"""
        if not self.is_initialized:
            logger.error("Database not initialized")
            return []
        
        try:
            import faiss
            
            # Prepare query embedding
            query_vec = query_embedding.copy().reshape(1, -1).astype(np.float32)
            if self.normalize_embeddings:
                faiss.normalize_L2(query_vec)
            
            # Search
            scores, indices = self.index.search(query_vec, min(top_k * 2, self.index.ntotal))
            
            results = []
            for rank, (score, idx) in enumerate(zip(scores[0], indices[0])):
                if idx == -1:  # FAISS returns -1 for invalid results
                    continue
                
                doc_id = self.index_to_id.get(idx)
                if not doc_id or doc_id not in self.documents:
                    continue
                
                document = self.documents[doc_id]
                
                # Convert score to similarity
                if self.normalize_embeddings:
                    # For cosine similarity (inner product with normalized vectors)
                    similarity = float(score)
                else:
                    # For L2 distance, convert to similarity
                    similarity = 1.0 / (1.0 + float(score))
                
                # Apply minimum similarity filter
                if min_similarity and similarity < min_similarity:
                    continue
                
                # Apply metadata filters
                if filters and not self._matches_filters(document, filters):
                    continue
                
                results.append(VectorSearchResult(
                    document=document,
                    similarity_score=similarity,
                    rank=rank
                ))
                
                if len(results) >= top_k:
                    break
            
            return results
            
        except Exception as e:
            logger.error(f"FAISS search failed: {e}")
            return []
    
    async def delete_documents(self, document_ids: List[str]) -> bool:
        """Delete documents by IDs (rebuilds index for FAISS)"""
        try:
            # Remove from metadata
            for doc_id in document_ids:
                self.documents.pop(doc_id, None)
            
            # Rebuild index (FAISS doesn't support efficient deletion)
            remaining_docs = list(self.documents.values())
            
            # Reset index
            self.index.reset()
            self.id_to_index.clear()
            self.index_to_id.clear()
            
            # Re-add remaining documents
            if remaining_docs:
                return await self.add_documents(remaining_docs)
            
            await self._save_index()
            return True
            
        except Exception as e:
            logger.error(f"Failed to delete documents from FAISS: {e}")
            return False
    
    async def update_document(self, document: VectorDocument) -> bool:
        """Update a document (delete and re-add for FAISS)"""
        if document.id in self.documents:
            await self.delete_documents([document.id])
        
        return await self.add_documents([document])
    
    async def get_document_count(self) -> int:
        """Get total number of documents"""
        return len(self.documents)
    
    async def get_statistics(self) -> Dict[str, Any]:
        """Get database statistics"""
        return {
            'total_documents': len(self.documents),
            'index_type': self.config.get('index_type', 'flat'),
            'dimension': self.dimension,
            'metric': self.config.get('metric', 'cosine'),
            'is_trained': getattr(self.index, 'is_trained', True) if self.index else False,
            'storage_path': self.config.get('storage_path')
        }
    
    def _matches_filters(self, document: VectorDocument, filters: Dict[str, Any]) -> bool:
        """Check if document matches metadata filters"""
        for key, value in filters.items():
            if key == 'basket_id':
                if document.basket_id != value:
                    return False
            elif key in document.metadata:
                if document.metadata[key] != value:
                    return False
            else:
                return False
        return True
    
    async def _save_index(self):
        """Save FAISS index and metadata to disk"""
        storage_path = self.config.get('storage_path')
        if not storage_path:
            return
        
        try:
            import faiss
            
            # Save index
            faiss.write_index(self.index, storage_path)
            
            # Save metadata
            metadata = {
                'documents': {doc_id: doc.to_dict() for doc_id, doc in self.documents.items()},
                'id_to_index': self.id_to_index
            }
            
            metadata_path = storage_path + '.metadata'
            with open(metadata_path, 'w') as f:
                json.dump(metadata, f, indent=2)
            
            logger.debug(f"Saved FAISS index to {storage_path}")
            
        except Exception as e:
            logger.warning(f"Failed to save FAISS index: {e}")


class PineconeVectorDatabase(BaseVectorDatabase):
    """
    Pinecone vector database implementation
    
    Provides managed vector search using Pinecone service
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        Initialize Pinecone vector database
        
        Args:
            config: Configuration with:
                - api_key: Pinecone API key (required)
                - environment: Pinecone environment (required)
                - index_name: Index name (required)
                - dimension: Embedding dimension (required)
                - metric: 'cosine', 'euclidean', 'dotproduct' (default: 'cosine')
                - pod_type: Pod type for index (default: 'p1.x1')
                - replicas: Number of replicas (default: 1)
        """
        self.config = config or {}
        self.client = None
        self.index = None
        self.is_initialized = False
        
        required_fields = ['api_key', 'environment', 'index_name', 'dimension']
        for field in required_fields:
            if not self.config.get(field):
                raise ValueError(f"{field} must be specified in config")
    
    async def initialize(self) -> bool:
        """Initialize Pinecone client and index"""
        try:
            import pinecone
            
            # Initialize Pinecone
            pinecone.init(
                api_key=self.config['api_key'],
                environment=self.config['environment']
            )
            
            self.client = pinecone
            
            # Check if index exists, create if not
            index_name = self.config['index_name']
            if index_name not in pinecone.list_indexes():
                logger.info(f"Creating Pinecone index: {index_name}")
                
                pinecone.create_index(
                    name=index_name,
                    dimension=self.config['dimension'],
                    metric=self.config.get('metric', 'cosine'),
                    pod_type=self.config.get('pod_type', 'p1.x1'),
                    replicas=self.config.get('replicas', 1)
                )
                
                # Wait for index to be ready
                while index_name not in pinecone.list_indexes():
                    await asyncio.sleep(1)
            
            # Connect to index
            self.index = pinecone.Index(index_name)
            
            self.is_initialized = True
            logger.info("Pinecone vector database initialized successfully")
            return True
            
        except ImportError:
            logger.error("Pinecone library not found. Install with: pip install pinecone-client")
            return False
        except Exception as e:
            logger.error(f"Failed to initialize Pinecone database: {e}")
            return False
    
    async def add_documents(self, documents: List[VectorDocument]) -> bool:
        """Add documents to Pinecone index"""
        if not self.is_initialized:
            logger.error("Database not initialized")
            return False
        
        try:
            # Prepare vectors for Pinecone
            vectors = []
            for doc in documents:
                vector_data = {
                    'id': doc.id,
                    'values': doc.embedding.tolist(),
                    'metadata': {
                        'content': doc.content[:1000],  # Truncate content for metadata
                        'basket_id': doc.basket_id,
                        'timestamp': doc.timestamp.isoformat() if doc.timestamp else None,
                        **doc.metadata
                    }
                }
                vectors.append(vector_data)
            
            # Upsert in batches (Pinecone has batch size limits)
            batch_size = 100
            for i in range(0, len(vectors), batch_size):
                batch = vectors[i:i + batch_size]
                self.index.upsert(vectors=batch)
            
            logger.info(f"Added {len(documents)} documents to Pinecone index")
            return True
            
        except Exception as e:
            logger.error(f"Failed to add documents to Pinecone: {e}")
            return False
    
    async def search(
        self,
        query_embedding: np.ndarray,
        top_k: int = 10,
        filters: Optional[Dict[str, Any]] = None,
        min_similarity: Optional[float] = None
    ) -> List[VectorSearchResult]:
        """Search for similar vectors in Pinecone"""
        if not self.is_initialized:
            logger.error("Database not initialized")
            return []
        
        try:
            # Prepare query
            query_params = {
                'vector': query_embedding.tolist(),
                'top_k': top_k,
                'include_metadata': True,
                'include_values': False
            }
            
            # Add filters
            if filters:
                pinecone_filter = {}
                for key, value in filters.items():
                    pinecone_filter[key] = {'$eq': value}
                query_params['filter'] = pinecone_filter
            
            # Search
            response = self.index.query(**query_params)
            
            results = []
            for rank, match in enumerate(response['matches']):
                similarity = float(match['score'])
                
                # Apply minimum similarity filter
                if min_similarity and similarity < min_similarity:
                    continue
                
                # Reconstruct document from metadata
                metadata = match['metadata']
                document = VectorDocument(
                    id=match['id'],
                    content=metadata.get('content', ''),
                    embedding=query_embedding,  # Placeholder, we don't store full embeddings in metadata
                    metadata={k: v for k, v in metadata.items() if k not in ['content', 'basket_id', 'timestamp']},
                    basket_id=metadata.get('basket_id'),
                    timestamp=datetime.fromisoformat(metadata['timestamp']) if metadata.get('timestamp') else None
                )
                
                results.append(VectorSearchResult(
                    document=document,
                    similarity_score=similarity,
                    rank=rank
                ))
            
            return results
            
        except Exception as e:
            logger.error(f"Pinecone search failed: {e}")
            return []
    
    async def delete_documents(self, document_ids: List[str]) -> bool:
        """Delete documents by IDs from Pinecone"""
        if not self.is_initialized:
            logger.error("Database not initialized")
            return False
        
        try:
            # Delete in batches
            batch_size = 1000
            for i in range(0, len(document_ids), batch_size):
                batch = document_ids[i:i + batch_size]
                self.index.delete(ids=batch)
            
            logger.info(f"Deleted {len(document_ids)} documents from Pinecone")
            return True
            
        except Exception as e:
            logger.error(f"Failed to delete documents from Pinecone: {e}")
            return False
    
    async def update_document(self, document: VectorDocument) -> bool:
        """Update a document in Pinecone (upsert operation)"""
        return await self.add_documents([document])
    
    async def get_document_count(self) -> int:
        """Get total number of documents"""
        try:
            stats = self.index.describe_index_stats()
            return stats['total_vector_count']
        except Exception as e:
            logger.error(f"Failed to get document count: {e}")
            return 0
    
    async def get_statistics(self) -> Dict[str, Any]:
        """Get database statistics"""
        try:
            stats = self.index.describe_index_stats()
            return {
                'total_documents': stats['total_vector_count'],
                'dimension': stats['dimension'],
                'index_name': self.config['index_name'],
                'environment': self.config['environment'],
                'metric': self.config.get('metric', 'cosine'),
                'namespaces': stats.get('namespaces', {})
            }
        except Exception as e:
            logger.error(f"Failed to get statistics: {e}")
            return {}


class VectorDatabaseFactory:
    """Factory for creating vector database instances"""
    
    @staticmethod
    def create_database(db_type: str, config: Dict[str, Any]) -> BaseVectorDatabase:
        """
        Create a vector database instance
        
        Args:
            db_type: 'faiss' or 'pinecone'
            config: Database-specific configuration
            
        Returns:
            Configured vector database instance
        """
        
        if db_type.lower() == 'faiss':
            return FAISSVectorDatabase(config)
        elif db_type.lower() == 'pinecone':
            return PineconeVectorDatabase(config)
        else:
            raise ValueError(f"Unsupported vector database type: {db_type}")