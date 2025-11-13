"""
Vector Indexing Processor for DocEX

Processes documents to generate embeddings and store them in a vector database
for semantic search capabilities.
"""

import logging
import json
from typing import Dict, Any, Optional, List
from datetime import datetime

from docex.processors.base import BaseProcessor, ProcessingResult
from docex.document import Document
from docex.processors.llm import BaseLLMProcessor

logger = logging.getLogger(__name__)


class VectorIndexingProcessor(BaseProcessor):
    """
    Processor that indexes documents in a vector database for semantic search.
    
    This processor:
    1. Generates embeddings using an LLM adapter
    2. Stores embeddings in a vector database (pgvector for production, memory for testing)
    3. Stores vector metadata in DocEX metadata system
    4. Tracks indexing operations in DocEX
    """
    
    def __init__(self, config: Dict[str, Any]):
        """
        Initialize vector indexing processor
        
        Args:
            config: Configuration dictionary with:
                - llm_adapter: LLM adapter instance or config for creating one
                - vector_db_type: 'pgvector' (recommended for production) or 'memory' (for testing)
                - vector_db_config: Configuration for vector database (not needed for memory)
                - store_in_metadata: Whether to store embeddings in DocEX metadata (default: True)
        """
        # Store original config for serialization (without llm_adapter object)
        # Remove llm_adapter object from config before passing to super()
        # This prevents JSON serialization errors when storing processor config
        serializable_config = {k: v for k, v in config.items() if k != 'llm_adapter'}
        llm_adapter_config = config.get('llm_adapter')
        
        super().__init__(serializable_config)
        
        # Initialize LLM adapter for generating embeddings
        if isinstance(llm_adapter_config, BaseLLMProcessor):
            self.llm_adapter = llm_adapter_config
        else:
            # Create LLM adapter from config
            from docex.processors.llm import OpenAIAdapter
            self.llm_adapter = OpenAIAdapter(llm_adapter_config or {})
        
        # Vector database configuration
        self.vector_db_type = config.get('vector_db_type', 'memory')
        self.vector_db_config = config.get('vector_db_config', {})
        self.store_in_metadata = config.get('store_in_metadata', True)
        
        # Validate vector_db_type
        if self.vector_db_type not in ['pgvector', 'memory']:
            raise ValueError(f"Unsupported vector_db_type: {self.vector_db_type}. Supported types: 'pgvector' (recommended for production), 'memory' (for testing)")
        
        # Initialize vector database
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
        """Initialize pgvector (PostgreSQL extension)"""
        try:
            from docex.db.connection import Database
            db = Database()
            
            # Check if pgvector extension is available
            with db.session() as session:
                result = session.execute(
                    "SELECT EXISTS(SELECT 1 FROM pg_extension WHERE extname = 'vector')"
                ).scalar()
                
                if not result:
                    logger.warning("pgvector extension not found. Attempting to create...")
                    try:
                        session.execute("CREATE EXTENSION IF NOT EXISTS vector")
                        session.commit()
                        logger.info("pgvector extension created successfully")
                    except Exception as e:
                        logger.error(f"Failed to create pgvector extension: {e}")
                        raise ValueError("pgvector extension is required but not available")
            
            return {'type': 'pgvector', 'db': db}
        except ImportError:
            raise ValueError("pgvector requires PostgreSQL database")
    
    
    def _init_memory_db(self):
        """Initialize in-memory vector database (for testing/SQLite)"""
        return {'type': 'memory', 'vectors': {}}
    
    def can_process(self, document: Document) -> bool:
        """
        Check if document can be processed for vector indexing
        
        Args:
            document: Document to check
            
        Returns:
            True if document can be indexed
        """
        # Skip if already indexed (unless force re-index)
        if not self.config.get('force_reindex', False):
            metadata = document.get_metadata_dict()
            if metadata.get('vector_indexed'):
                return False
        
        # Process all documents that have text content
        return True
    
    async def process(self, document: Document) -> ProcessingResult:
        """
        Index document in vector database
        
        Args:
            document: Document to index
            
        Returns:
            ProcessingResult with indexing outcome
        """
        try:
            # Record operation start
            self._record_operation(
                document,
                status='in_progress',
                input_metadata={'document_id': document.id, 'vector_db_type': self.vector_db_type}
            )
            
            # Get document text content
            text_content = self.get_document_text(document)
            
            if not text_content.strip():
                return ProcessingResult(
                    success=False,
                    error="No text content available for indexing"
                )
            
            # Generate embedding using LLM adapter
            logger.info(f"Generating embedding for document {document.id}")
            embedding = await self.llm_adapter.llm_service.generate_embedding(text_content)
            
            if not embedding:
                return ProcessingResult(
                    success=False,
                    error="Failed to generate embedding"
                )
            
            # Store in vector database
            vector_id = await self._store_embedding(document, embedding, text_content)
            
            # Store metadata in DocEX
            metadata_updates = {
                'vector_indexed': True,
                'vector_indexed_at': datetime.utcnow().isoformat(),
                'vector_db_type': self.vector_db_type,
                'embedding_dimension': len(embedding),
            }
            
            if vector_id:
                metadata_updates['vector_id'] = vector_id
            
            if self.store_in_metadata:
                # Store embedding as JSON in metadata (for small embeddings)
                if len(embedding) <= 2048:  # Only store small embeddings
                    metadata_updates['embedding'] = json.dumps(embedding)
            
            from docex.services.metadata_service import MetadataService
            metadata_service = MetadataService()
            metadata_service.update_metadata(document.id, metadata_updates)
            
            # Record success
            self._record_operation(
                document,
                status='success',
                output_metadata={
                    'vector_id': vector_id,
                    'embedding_dimension': len(embedding),
                    'vector_db_type': self.vector_db_type
                }
            )
            
            return ProcessingResult(
                success=True,
                content=text_content,
                metadata=metadata_updates
            )
            
        except Exception as e:
            logger.error(f"Vector indexing failed for document {document.id}: {e}")
            self._record_operation(
                document,
                status='failed',
                error=str(e)
            )
            return ProcessingResult(success=False, error=str(e))
    
    async def _store_embedding(self, document: Document, embedding: List[float], text: str) -> Optional[str]:
        """Store embedding in vector database"""
        if self.vector_db_type == 'pgvector':
            return await self._store_pgvector(document, embedding, text)
        elif self.vector_db_type == 'memory':
            return await self._store_memory(document, embedding, text)
        else:
            raise ValueError(f"Unsupported vector_db_type: {self.vector_db_type}")
    
    async def _store_pgvector(self, document: Document, embedding: List[float], text: str) -> str:
        """Store embedding in pgvector"""
        db = self.vector_db['db']
        
        # Get document metadata for filtering
        metadata_dict = document.get_metadata_dict()
        
        with db.session() as session:
            # Check if embedding column exists, if not, add it
            try:
                from sqlalchemy import text
                session.execute(text(f"""
                    ALTER TABLE document 
                    ADD COLUMN IF NOT EXISTS embedding vector({len(embedding)})
                """))
                session.commit()
            except Exception as e:
                logger.debug(f"Embedding column may already exist: {e}")
            
            # Update document with embedding
            # Convert embedding list to PostgreSQL vector format
            embedding_str = '[' + ','.join(map(str, embedding)) + ']'
            from sqlalchemy import text
            session.execute(text("""
                UPDATE document 
                SET embedding = :embedding::vector
                WHERE id = :doc_id
            """), {'embedding': embedding_str, 'doc_id': document.id})
            
            session.commit()
        
        return document.id
    
    async def _store_memory(self, document: Document, embedding: List[float], text: str) -> str:
        """Store embedding in memory (for testing)"""
        vectors = self.vector_db['vectors']
        
        vectors[document.id] = {
            'embedding': embedding,
            'document_id': document.id,
            'basket_id': document.basket_id,
            'document_type': document.document_type,
            'text_preview': text[:1000],
            'metadata': document.get_metadata_dict()
        }
        
        return document.id

