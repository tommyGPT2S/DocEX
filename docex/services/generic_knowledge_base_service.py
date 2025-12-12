"""
Generic Knowledge Base Service for DocEX

A domain-agnostic RAG-powered knowledge base service that can be configured
for any document type and use case. Provides natural language querying,
structured data extraction, and document versioning.

This service wraps DocEX's EnhancedRAGService with generic knowledge base
capabilities that can be customized for specific domains.
"""

import logging
import json
from typing import Dict, Any, List, Optional, Union
from datetime import datetime

from docex.docbasket import DocBasket
from docex.document import Document
from docex.processors.rag.enhanced_rag_service import EnhancedRAGService, EnhancedRAGConfig
from docex.processors.rag.rag_service import RAGResult
from docex.processors.llm import BaseLLMProcessor
from docex.processors.vector.semantic_search_service import SemanticSearchService

logger = logging.getLogger(__name__)


class GenericKnowledgeBaseService:
    """
    Generic Knowledge Base Service for querying documents using RAG
    
    Features:
    - RAG-powered semantic search across knowledge base documents
    - LLM-based answer generation with source citations
    - Structured data extraction (JSON) for programmatic use
    - Version control and change tracking
    - Configurable document types and extraction schemas
    - Domain-agnostic design
    
    Usage:
        # Initialize with DocEX components
        kb_service = GenericKnowledgeBaseService(
            rag_service=rag_service,
            llm_adapter=llm_adapter,
            basket=basket,
            config={
                'document_types': {
                    'policy': {'description': 'Company policies'},
                    'contract': {'description': 'Legal contracts'},
                    'guide': {'description': 'User guides'}
                }
            }
        )
        
        # Ingest documents
        await kb_service.ingest_document(
            document=document,
            doc_type='policy',
            version='1.0'
        )
        
        # Query knowledge base
        result = await kb_service.query(
            question="What is the refund policy?",
            doc_type='policy',
            extract_structured=True
        )
    """
    
    def __init__(
        self,
        rag_service: EnhancedRAGService,
        llm_adapter: BaseLLMProcessor,
        basket: Optional[DocBasket] = None,
        config: Optional[Dict[str, Any]] = None
    ):
        """
        Initialize Generic Knowledge Base Service
        
        Args:
            rag_service: Configured EnhancedRAGService instance
            llm_adapter: LLM adapter for structured data extraction
            basket: Optional DocBasket for document storage
            config: Optional configuration dictionary with:
                - document_types: Dict mapping doc_type -> metadata
                - extraction_schemas: Dict mapping doc_type -> JSON schema for extraction
                - default_extraction_schema: Default schema for structured extraction
        """
        self.rag_service = rag_service
        self.llm_adapter = llm_adapter
        self.basket = basket
        
        # Configuration
        self.config = config or {}
        self.document_types = self.config.get('document_types', {})
        self.extraction_schemas = self.config.get('extraction_schemas', {})
        self.default_extraction_schema = self.config.get('default_extraction_schema', {
            'description': 'Extract key information from the document',
            'fields': ['summary', 'key_points', 'metadata']
        })
        
        # Document metadata tracking
        self.documents: Dict[str, Dict[str, Any]] = {}
        
        logger.info("Generic Knowledge Base Service initialized")
    
    async def ingest_document(
        self,
        document: Document,
        doc_type: str,
        version: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
        extract_structured: bool = True
    ) -> bool:
        """
        Ingest a document into the knowledge base
        
        Args:
            document: Document to ingest
            doc_type: Type/category of document (e.g., 'policy', 'contract', 'guide')
            version: Optional version identifier
            metadata: Optional additional metadata
            extract_structured: Whether to extract structured data using LLM
            
        Returns:
            True if successful, False otherwise
        """
        try:
            logger.info(f"Ingesting {doc_type} document: {document.name}")
            
            # Validate document type
            if doc_type not in self.document_types and self.document_types:
                logger.warning(f"Document type '{doc_type}' not in configured types, proceeding anyway")
            
            # Extract structured data if requested
            extracted_data = None
            if extract_structured and self.llm_adapter:
                extracted_data = await self._extract_structured_data(
                    document,
                    doc_type
                )
            
            # Store document metadata
            doc_id = f"{doc_type}_{document.id}"
            self.documents[doc_id] = {
                'type': doc_type,
                'document_id': document.id,
                'name': document.name,
                'version': version or datetime.now().isoformat(),
                'ingested_at': datetime.now().isoformat(),
                'metadata': metadata or {},
                'extracted_data': extracted_data
            }
            
            # Add document to basket if provided
            if self.basket:
                # Document should already be in basket, just ensure metadata is set
                metadata_updates = {
                    'kb_doc_type': doc_type,
                    'kb_version': version or datetime.now().isoformat()
                }
                if extracted_data:
                    metadata_updates['kb_extracted_data'] = json.dumps(extracted_data)
                document.update_metadata(metadata_updates)
            
            # Index document in vector database if available
            if hasattr(self.rag_service, 'add_documents_to_vector_db'):
                success = await self.rag_service.add_documents_to_vector_db([document])
                if not success:
                    logger.warning("Failed to add document to vector database, continuing with semantic search only")
            
            logger.info(f"Successfully ingested document: {doc_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to ingest document: {e}", exc_info=True)
            return False
    
    async def query(
        self,
        question: str,
        doc_type: Optional[str] = None,
        extract_structured: bool = True,
        filters: Optional[Dict[str, Any]] = None,
        top_k: int = 5
    ) -> Dict[str, Any]:
        """
        Query knowledge base using natural language
        
        Args:
            question: Natural language question
            doc_type: Optional filter by document type
            extract_structured: Whether to extract structured data (JSON)
            filters: Optional metadata filters
            top_k: Number of top documents to retrieve
            
        Returns:
            Dictionary with answer, structured data, sources, and metadata
        """
        try:
            logger.info(f"Querying knowledge base: {question[:100]}...")
            
            # Build filters
            query_filters = filters or {}
            if doc_type:
                query_filters['kb_doc_type'] = doc_type
            
            # Query RAG service
            basket_id = self.basket.id if self.basket else None
            rag_result = await self.rag_service.query(
                question=question,
                basket_id=basket_id,
                filters=query_filters if query_filters else None
            )
            
            # Extract structured data if requested
            structured_data = None
            if extract_structured:
                structured_data = await self._extract_structured_data_from_query(
                    question,
                    rag_result.answer,
                    rag_result.sources,
                    doc_type
                )
            
            result = {
                'query': question,
                'answer': rag_result.answer,
                'structured_data': structured_data,
                'confidence_score': rag_result.confidence_score,
                'sources': [
                    {
                        'document_id': source.document.id,
                        'document_name': getattr(source.document, 'name', 'Unknown'),
                        'doc_type': source.document.get_metadata_dict().get('kb_doc_type', 'unknown'),
                        'similarity_score': source.similarity_score,
                        'metadata': source.metadata
                    }
                    for source in rag_result.sources
                ],
                'processing_time': rag_result.processing_time,
                'metadata': rag_result.metadata
            }
            
            logger.info(f"Query completed in {rag_result.processing_time:.2f}s")
            return result
            
        except Exception as e:
            logger.error(f"Failed to query knowledge base: {e}", exc_info=True)
            return {
                'query': question,
                'answer': f"Error querying knowledge base: {str(e)}",
                'structured_data': None,
                'confidence_score': 0.0,
                'sources': [],
                'error': str(e)
            }
    
    async def search(
        self,
        query: str,
        doc_type: Optional[str] = None,
        filters: Optional[Dict[str, Any]] = None,
        top_k: int = 10
    ) -> List[Dict[str, Any]]:
        """
        Semantic search across knowledge base documents
        
        Args:
            query: Search query
            doc_type: Optional filter by document type
            filters: Optional metadata filters
            top_k: Number of results to return
            
        Returns:
            List of matching documents with similarity scores
        """
        try:
            # Build filters
            query_filters = filters or {}
            if doc_type:
                query_filters['kb_doc_type'] = doc_type
            
            # Use semantic search service directly
            if hasattr(self.rag_service, 'semantic_search_service'):
                search_service = self.rag_service.semantic_search_service
                basket_id = self.basket.id if self.basket else None
                
                results = await search_service.search(
                    query=query,
                    basket_id=basket_id,
                    top_k=top_k,
                    filters=query_filters if query_filters else None
                )
                
                return [
                    {
                        'document_id': result.document.id,
                        'document_name': getattr(result.document, 'name', 'Unknown'),
                        'doc_type': result.document.get_metadata_dict().get('kb_doc_type', 'unknown'),
                        'similarity_score': result.similarity_score,
                        'metadata': result.metadata
                    }
                    for result in results
                ]
            else:
                # Fallback to RAG query
                rag_result = await self.query(query, doc_type=doc_type, extract_structured=False, top_k=top_k)
                return rag_result.get('sources', [])
                
        except Exception as e:
            logger.error(f"Failed to search knowledge base: {e}", exc_info=True)
            return []
    
    async def get_document_version(self, doc_type: str) -> Optional[Dict[str, Any]]:
        """
        Get version information for documents of a specific type
        
        Args:
            doc_type: Document type
            
        Returns:
            Dictionary with version information or None if not found
        """
        # Find documents of this type
        matching_docs = [
            doc for doc in self.documents.values()
            if doc['type'] == doc_type
        ]
        
        if not matching_docs:
            return None
        
        # Return most recent version
        latest = max(matching_docs, key=lambda x: x.get('ingested_at', ''))
        
        return {
            'type': doc_type,
            'version': latest.get('version'),
            'name': latest.get('name'),
            'ingested_at': latest.get('ingested_at'),
            'document_id': latest.get('document_id'),
            'metadata': latest.get('metadata', {})
        }
    
    async def list_documents(
        self,
        doc_type: Optional[str] = None,
        limit: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """
        List all documents in the knowledge base
        
        Args:
            doc_type: Optional filter by document type
            limit: Optional limit on number of results
            
        Returns:
            List of document metadata dictionaries
        """
        docs = list(self.documents.values())
        
        # Filter by type if specified
        if doc_type:
            docs = [doc for doc in docs if doc['type'] == doc_type]
        
        # Sort by ingestion date (newest first)
        docs.sort(key=lambda x: x.get('ingested_at', ''), reverse=True)
        
        # Apply limit
        if limit:
            docs = docs[:limit]
        
        return docs
    
    async def _extract_structured_data(
        self,
        document: Document,
        doc_type: str
    ) -> Optional[Dict[str, Any]]:
        """
        Extract structured data from document using LLM
        
        Args:
            document: Document to extract from
            doc_type: Document type
            
        Returns:
            Structured data dictionary or None
        """
        if not self.llm_adapter:
            return None
        
        try:
            # Get document text
            text_content = document.get_content(mode='text')
            if not text_content:
                return None
            
            # Get extraction schema for this document type
            schema = self.extraction_schemas.get(doc_type, self.default_extraction_schema)
            
            # Build extraction prompt
            extraction_prompt = self._build_extraction_prompt(text_content, schema, doc_type)
            
            # Use LLM to extract structured data
            if hasattr(self.llm_adapter, 'llm_service'):
                response = await self.llm_adapter.llm_service.generate_completion(
                    prompt=extraction_prompt,
                    max_tokens=1000,
                    temperature=0.1
                )
            elif hasattr(self.llm_adapter, 'generate'):
                response = await self.llm_adapter.generate(
                    extraction_prompt,
                    max_tokens=1000,
                    temperature=0.1
                )
            else:
                logger.warning("LLM adapter doesn't support direct generation, skipping structured extraction")
                return None
            
            # Parse JSON response
            try:
                import re
                json_match = re.search(r'\{.*\}', response, re.DOTALL)
                if json_match:
                    json_str = json_match.group(0)
                else:
                    json_str = response
                
                structured_data = json.loads(json_str)
                return structured_data
            except json.JSONDecodeError:
                logger.warning(f"Failed to parse JSON from LLM response: {response}")
                return None
                
        except Exception as e:
            logger.error(f"Failed to extract structured data: {e}")
            return None
    
    async def _extract_structured_data_from_query(
        self,
        question: str,
        answer: str,
        sources: List[Any],
        doc_type: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Extract structured data from query answer using LLM
        
        Args:
            question: Original question
            answer: RAG-generated answer
            sources: Source documents
            doc_type: Optional document type
            
        Returns:
            Structured data dictionary or None
        """
        if not self.llm_adapter:
            return None
        
        try:
            # Get extraction schema
            schema = self.extraction_schemas.get(doc_type, self.default_extraction_schema) if doc_type else self.default_extraction_schema
            
            # Build extraction prompt
            extraction_prompt = f"""Extract structured data from the following question and answer.

QUESTION: {question}

ANSWER: {answer}

Extract the relevant information as JSON based on the following schema:
{json.dumps(schema, indent=2)}

Return only valid JSON, no additional text."""

            # Use LLM to extract structured data
            if hasattr(self.llm_adapter, 'llm_service'):
                response = await self.llm_adapter.llm_service.generate_completion(
                    prompt=extraction_prompt,
                    max_tokens=500,
                    temperature=0.1
                )
            elif hasattr(self.llm_adapter, 'generate'):
                response = await self.llm_adapter.generate(
                    extraction_prompt,
                    max_tokens=500,
                    temperature=0.1
                )
            else:
                logger.warning("LLM adapter doesn't support direct generation, skipping structured extraction")
                return None
            
            # Parse JSON response
            try:
                import re
                json_match = re.search(r'\{.*\}', response, re.DOTALL)
                if json_match:
                    json_str = json_match.group(0)
                else:
                    json_str = response
                
                structured_data = json.loads(json_str)
                return structured_data
            except json.JSONDecodeError:
                logger.warning(f"Failed to parse JSON from LLM response: {response}")
                return None
                
        except Exception as e:
            logger.error(f"Failed to extract structured data from query: {e}")
            return None
    
    def _build_extraction_prompt(
        self,
        text_content: str,
        schema: Dict[str, Any],
        doc_type: str
    ) -> str:
        """
        Build extraction prompt from schema
        
        Args:
            text_content: Document text content
            schema: Extraction schema
            doc_type: Document type
            
        Returns:
            Extraction prompt string
        """
        schema_description = schema.get('description', 'Extract key information')
        fields = schema.get('fields', [])
        
        prompt = f"""Extract structured data from the following {doc_type} document.

{schema_description}

Extract the following fields: {', '.join(fields)}

Return the extracted data as JSON with the following structure:
{json.dumps({field: 'value' for field in fields}, indent=2)}

Document content:
{text_content[:5000]}  # Limit to first 5000 chars

Return only valid JSON, no additional text."""
        
        return prompt

