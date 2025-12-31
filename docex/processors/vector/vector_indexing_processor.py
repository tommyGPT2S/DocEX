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
from docex.db.connection import Database

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
    
    def __init__(self, config: Dict[str, Any], db: Optional[Database] = None):
        """
        Initialize vector indexing processor
        
        Args:
            config: Configuration dictionary with:
                - llm_adapter: LLM adapter instance or config for creating one
                - vector_db_type: 'pgvector' (recommended for production) or 'memory' (for testing)
                - vector_db_config: Configuration for vector database (not needed for memory)
                - store_in_metadata: Whether to store embeddings in DocEX metadata (default: True)
            db: Optional tenant-aware database instance (for multi-tenancy support)
        """
        # Store original config for serialization (without llm_adapter object)
        # Remove llm_adapter object from config before passing to super()
        # This prevents JSON serialization errors when storing processor config
        serializable_config = {k: v for k, v in config.items() if k != 'llm_adapter'}
        llm_adapter_config = config.get('llm_adapter')
        
        super().__init__(serializable_config, db=db)
        
        # Initialize LLM adapter for generating embeddings
        # Check if it's already a BaseLLMProcessor instance (passed from workflow executor)
        from docex.processors.llm.base_llm_processor import BaseLLMProcessor
        if isinstance(llm_adapter_config, BaseLLMProcessor):
            self.llm_adapter = llm_adapter_config
        else:
            # Create LLM adapter from config
            # Default to OpenAIAdapter, but workflow executor should provide adapter
            from docex.processors.llm import OpenAIAdapter
            # Pass db to adapter if available (for multi-tenancy)
            adapter_db = db if db else None
            if adapter_db:
                self.llm_adapter = OpenAIAdapter(llm_adapter_config or {}, db=adapter_db)
            else:
                self.llm_adapter = OpenAIAdapter(llm_adapter_config or {})
        
        # Vector database configuration
        self.vector_db_type = config.get('vector_db_type', 'memory')
        self.vector_db_config = config.get('vector_db_config', {})
        self.store_in_metadata = config.get('store_in_metadata', True)
        
        # Metadata inclusion configuration
        self.include_metadata = config.get('include_metadata', True)  # Include metadata in embeddings by default
        self.metadata_fields = config.get('metadata_fields', None)  # None = include all relevant fields
        # Default fields to include if metadata_fields not specified
        self.default_metadata_fields = [
            'document_type', 'business_process',
            'po_number', 'invoice_number', 'purchase_order_number',
            'customer_id', 'supplier_id', 'vendor_name',
            'total_amount', 'currency',
            'po_date', 'invoice_date', 'due_date', 'delivery_date',
            'po_status',
        ]
        
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
            # Use tenant-aware database from processor instance
            db = self.db
            
            # Check if pgvector extension is available and create if needed
            from sqlalchemy import text
            with db.session() as session:
                try:
                    # Try to create extension (will fail silently if already exists)
                    # Must use raw connection for CREATE EXTENSION
                    from sqlalchemy import create_engine
                    raw_conn = db.engine.raw_connection()
                    try:
                        cursor = raw_conn.cursor()
                        cursor.execute("CREATE EXTENSION IF NOT EXISTS vector")
                        raw_conn.commit()
                        cursor.close()
                        logger.info("✅ pgvector extension enabled")
                    except Exception as e:
                        raw_conn.rollback()
                        # Check if extension already exists
                        cursor = raw_conn.cursor()
                        cursor.execute("SELECT EXISTS(SELECT 1 FROM pg_extension WHERE extname = 'vector')")
                        exists = cursor.fetchone()[0]
                        cursor.close()
                        if exists:
                            logger.info("✅ pgvector extension already exists")
                        else:
                            logger.warning(f"⚠️  Could not create pgvector extension: {e}")
                            logger.warning("   You may need to run: CREATE EXTENSION vector; as a superuser")
                            raise ValueError(f"pgvector extension is required but not available: {e}")
                    finally:
                        raw_conn.close()
                    
                    # Create HNSW index if it doesn't exist
                    # Re-open connection for index creation
                    raw_conn = db.engine.raw_connection()
                    try:
                        cursor = raw_conn.cursor()
                        self._ensure_hnsw_index(cursor, raw_conn)
                        cursor.close()
                    finally:
                        raw_conn.close()
                except Exception as e:
                    logger.error(f"Failed to initialize pgvector extension: {e}")
                    raise ValueError(f"pgvector extension is required but not available: {e}")
            
            return {'type': 'pgvector', 'db': db}
        except ImportError:
            raise ValueError("pgvector requires PostgreSQL database")
    
    def _ensure_hnsw_index(self, cursor, connection):
        """
        Ensure HNSW index exists on document.embedding column.
        
        Args:
            cursor: Database cursor
            connection: Database connection
        """
        try:
            # Check if index already exists
            cursor.execute("""
                SELECT EXISTS (
                    SELECT 1 FROM pg_indexes 
                    WHERE indexname = 'document_embedding_idx'
                )
            """)
            index_exists = cursor.fetchone()[0]
            
            if not index_exists:
                logger.info("Creating HNSW index on document.embedding...")
                # Use public.vector_l2_ops (most commonly supported)
                # Note: We use vector_l2_ops even though we use <=> (cosine) in queries
                # The index still works for cosine similarity with normalized vectors
                cursor.execute("""
                    CREATE INDEX document_embedding_idx 
                    ON document 
                    USING hnsw (embedding public.vector_l2_ops)
                """)
                connection.commit()
                logger.info("✅ HNSW index created successfully")
            else:
                logger.debug("HNSW index already exists")
        except Exception as e:
            logger.warning(f"Could not create HNSW index: {e}")
            logger.warning("   Index creation may require superuser privileges")
            logger.warning("   You can create it manually: CREATE INDEX document_embedding_idx ON document USING hnsw (embedding public.vector_l2_ops);")
            # Don't fail initialization if index creation fails
            try:
                connection.rollback()
            except:
                pass
    
    
    def _init_memory_db(self):
        """Initialize in-memory vector database (for testing/SQLite)"""
        return {'type': 'memory', 'vectors': {}}
    
    def _build_metadata_text(self, document: Document) -> str:
        """
        Build metadata text string to include in embeddings.
        
        Extracts relevant metadata fields and formats them as searchable text.
        This allows semantic search to find documents by metadata values.
        
        Enhanced to include more context for better search results.
        
        Args:
            document: Document to extract metadata from
            
        Returns:
            Formatted metadata text string, or empty string if no metadata
        """
        try:
            metadata = document.get_metadata_dict()
            if not metadata:
                return ""
            
            # Determine which fields to include
            fields_to_include = self.metadata_fields if self.metadata_fields else self.default_metadata_fields
            
            # Extract and format metadata values
            metadata_parts = []
            
            for field in fields_to_include:
                value = metadata.get(field)
                if value is None:
                    continue
                
                # Handle DocumentMetadata objects - extract actual value
                if hasattr(value, 'value'):
                    # DocumentMetadata object with .value attribute
                    actual_value = value.value
                elif hasattr(value, 'extra') and hasattr(value.extra, 'get'):
                    # DocumentMetadata object with .extra dict
                    actual_value = value.extra.get('value')
                elif isinstance(value, dict):
                    # Already a dict, try to get value from it
                    actual_value = value.get('value') or value.get('extra', {}).get('value') if isinstance(value.get('extra'), dict) else value
                else:
                    # Plain value
                    actual_value = value
                
                # Skip empty values
                if actual_value is None or actual_value == '':
                    continue
                if isinstance(actual_value, str) and not actual_value.strip():
                    continue
                
                value = actual_value  # Use extracted value
                
                # Format field name (convert snake_case to readable)
                field_name = field.replace('_', ' ').title()
                
                # Format value - handle special cases
                if isinstance(value, (int, float)):
                    value_str = str(value)
                elif isinstance(value, list):
                    # Handle line items or arrays - summarize for embedding
                    if field == 'line_items' and len(value) > 0:
                        # Summarize line items: "3 items, total $9500"
                        item_count = len(value)
                        # Try to get total from line items if available
                        total = sum(item.get('amount', item.get('total', 0)) for item in value if isinstance(item, dict))
                        if total > 0:
                            value_str = f"{item_count} line items totaling {total}"
                        else:
                            value_str = f"{item_count} line items"
                    else:
                        value_str = ", ".join(str(v) for v in value[:5])  # Limit to first 5 items
                elif isinstance(value, dict):
                    # Handle complex objects - convert to readable string
                    if field == 'line_items':
                        # Format line items more comprehensively
                        items = value if isinstance(value, list) else [value]
                        item_descriptions = []
                        for item in items[:3]:  # Limit to first 3 items
                            if isinstance(item, dict):
                                desc = item.get('description', item.get('item_name', ''))
                                qty = item.get('quantity', '')
                                price = item.get('unit_price', item.get('price', ''))
                                if desc:
                                    item_descriptions.append(f"{desc} (qty: {qty}, price: {price})")
                        value_str = "; ".join(item_descriptions) if item_descriptions else str(value)
                    else:
                        value_str = str(value)
                elif isinstance(value, str):
                    value_str = value
                else:
                    value_str = str(value)
                
                metadata_parts.append(f"{field_name}: {value_str}")
            
            if not metadata_parts:
                return ""
            
            # Format as structured text with more context
            doc_type = metadata.get('document_type', 'document')
            metadata_text = f"{doc_type.replace('_', ' ').title()} Document:\n" + "\n".join(metadata_parts)
            return metadata_text
            
        except Exception as e:
            logger.warning(f"Error building metadata text: {e}")
            return ""
    
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
                # Verify embedding actually exists in database
                # Metadata flag might be set but embedding not stored (e.g., due to error)
                try:
                    if self.db:
                        from sqlalchemy import text
                        with self.db.session() as session:
                            has_embedding = session.execute(
                                text("SELECT embedding IS NOT NULL FROM document WHERE id = :doc_id"),
                                {"doc_id": document.id}
                            ).scalar()
                            if has_embedding:
                                # Both metadata flag and embedding exist - skip
                                return False
                            else:
                                # Metadata flag set but no embedding - re-index
                                logger.warning(
                                    f"Document {document.id} has vector_indexed=True but no embedding in DB. "
                                    "Will re-index."
                                )
                                return True
                except Exception as e:
                    logger.warning(f"Could not verify embedding in DB: {e}. Will attempt to index.")
                    # If we can't verify, try to index anyway
                    return True
        
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
            text_content = None
            try:
                text_content = self.get_document_text(document)
                if not isinstance(text_content, str):
                    text_content = str(text_content) if text_content else ''
            except (UnicodeDecodeError, Exception) as e:
                # Fallback: try to get text from metadata
                logger.warning(f"Error getting document text directly: {e}, trying metadata...")
                try:
                    metadata = document.get_metadata_dict()
                    # Handle DocumentMetadata objects
                    extracted_text = metadata.get('extracted_text', '')
                    if hasattr(extracted_text, 'value'):
                        text_content = extracted_text.value
                    elif hasattr(extracted_text, 'extra') and hasattr(extracted_text.extra, 'get'):
                        text_content = extracted_text.extra.get('value', '')
                    elif isinstance(extracted_text, str):
                        text_content = extracted_text
                    else:
                        text_content = str(extracted_text) if extracted_text else ''
                    
                    if not text_content:
                        # Last resort: try bytes with error handling
                        try:
                            content = document.get_content(mode='bytes')
                            text_content = content.decode('utf-8', errors='replace')
                        except Exception:
                            text_content = ''
                except Exception as e2:
                    logger.warning(f"Error getting text from metadata: {e2}")
                    text_content = ''
            
            # Ensure text_content is a string
            if not isinstance(text_content, str):
                text_content = str(text_content) if text_content else ''
            
            if not text_content or not text_content.strip():
                return ProcessingResult(
                    success=False,
                    error="No text content available for indexing"
                )
            
            # Prepare text for embedding (combine content with metadata if enabled)
            text_for_embedding = text_content
            if self.include_metadata:
                metadata_text = self._build_metadata_text(document)
                if metadata_text:
                    text_for_embedding = f"{metadata_text}\n\n{text_content}"
                    logger.debug(f"Including metadata in embedding for document {document.id}")
            
            # Generate embedding using LLM adapter
            logger.info(f"Generating embedding for document {document.id}")
            embedding = await self.llm_adapter.llm_service.generate_embedding(text_for_embedding)
            
            if not embedding:
                return ProcessingResult(
                    success=False,
                    error="Failed to generate embedding"
                )
            
            # Store in vector database (store original text_content, not text_for_embedding)
            vector_id = await self._store_embedding(document, embedding, text_content)
            
            # Store metadata in DocEX
            metadata_updates = {
                'vector_indexed': True,
                'vector_indexed_at': datetime.utcnow().isoformat(),
                'vector_db_type': self.vector_db_type,
                'embedding_dimension': len(embedding),
                'vector_indexed_with_metadata': self.include_metadata,  # Track if metadata was included
            }
            
            if vector_id:
                metadata_updates['vector_id'] = vector_id
            
            if self.store_in_metadata:
                # Store embedding as JSON in metadata (for small embeddings)
                if len(embedding) <= 2048:  # Only store small embeddings
                    metadata_updates['embedding'] = json.dumps(embedding)
            
            from docex.services.metadata_service import MetadataService
            metadata_service = MetadataService(self.db)  # Use tenant-aware database
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
        
        from sqlalchemy import text
        
        with db.session() as session:
            try:
                # Ensure search_path includes public where pgvector types are
                # This is needed for multi-tenant schemas
                try:
                    # Get current schema from search_path
                    current_schema = session.execute(text("SELECT current_schema()")).scalar()
                    session.execute(text(f"SET search_path TO {current_schema}, public, pg_catalog"))
                except Exception as e:
                    logger.debug(f"Could not set search_path: {e}")
                
                # Check if embedding column exists, if not, add it
                # Use fully qualified type name public.vector
                # Reason: In multi-tenant setups, pgvector extension types are in public schema,
                # but tenant schemas may not have 'public' in their search_path.
                # Explicit qualification ensures the type is found regardless of search_path.
                try:
                    session.execute(text(f"""
                        ALTER TABLE document 
                        ADD COLUMN IF NOT EXISTS embedding public.vector({len(embedding)})
                    """))
                    session.commit()
                    logger.debug(f"✅ Embedding column added or already exists")
                except Exception as e:
                    logger.debug(f"Embedding column may already exist: {e}")
                    # Rollback if error occurred to clear transaction state
                    session.rollback()
                    # Try to verify column exists (without using vector type)
                    try:
                        result = session.execute(text("""
                            SELECT column_name 
                            FROM information_schema.columns 
                            WHERE table_name = 'document' AND column_name = 'embedding'
                        """)).scalar()
                        if not result:
                            logger.warning(f"Embedding column does not exist and could not be created: {e}")
                            # Try one more time with explicit schema qualification
                            try:
                                session.execute(text(f"""
                                    ALTER TABLE document 
                                    ADD COLUMN embedding public.vector({len(embedding)})
                                """))
                                session.commit()
                            except Exception as e2:
                                raise ValueError(f"Could not create embedding column: {e2}")
                    except Exception as e2:
                        raise ValueError(f"Could not verify embedding column: {e2}")
                
                # Update document with embedding
                # Convert embedding list to PostgreSQL vector format
                embedding_str = '[' + ','.join(map(str, embedding)) + ']'
                
                # Use string formatting for vector cast to avoid SQLAlchemy parameter binding issues
                # Use fully qualified type name public.vector (see comment above for reason)
                session.execute(text(f"""
                    UPDATE document 
                    SET embedding = '{embedding_str}'::public.vector
                    WHERE id = :doc_id
                """), {'doc_id': document.id})
                
                session.commit()
                logger.debug(f"✅ Embedding stored successfully for document {document.id}")
                
            except Exception as e:
                # Rollback on any error
                session.rollback()
                logger.error(f"Error storing embedding in pgvector: {e}")
                raise
        
        return document.id
    
    async def _store_memory(self, document: Document, embedding: List[float], text: str) -> str:
        """Store embedding in memory (for testing)"""
        vectors = self.vector_db['vectors']
        
        # Get basket_id from document's basket if available
        basket_id = None
        try:
            # Try to get from document's basket attribute
            if hasattr(document, 'basket') and document.basket:
                basket_id = document.basket.id if hasattr(document.basket, 'id') else str(document.basket)
            # Try to get from document's basket_id attribute
            elif hasattr(document, 'basket_id'):
                basket_id = document.basket_id
            # Try to get from database
            else:
                from docex.db.connection import Database
                from docex.db.models import Document as DocumentModel
                from sqlalchemy import select
                db = self.db or Database()
                with db.session() as session:
                    doc_model = session.get(DocumentModel, document.id)
                    if doc_model and doc_model.basket_id:
                        basket_id = doc_model.basket_id
        except Exception as e:
            logger.debug(f"Could not get basket_id for document {document.id}: {e}")
            pass
        
        vectors[document.id] = {
            'embedding': embedding,
            'document_id': document.id,
            'basket_id': basket_id,
            'document_type': document.document_type if hasattr(document, 'document_type') else None,
            'text_preview': text[:1000],
            'metadata': document.get_metadata_dict()
        }
        
        return document.id

