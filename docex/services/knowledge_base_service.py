"""
Knowledge Base Service for DocEX

Provides RAG-powered querying of rule books (GPO Rosters, DDD Matrix, Eligibility Guides)
for chargeback automation workflow.

This service wraps EnhancedRAGService with KB-specific methods for:
- Rule book ingestion and indexing
- Natural language querying with structured data extraction
- Contract eligibility validation (Step 3)
- GPO Roster validation (Step 4)
- Class-of-trade determination (Step 6)
"""

import logging
import json
from typing import Dict, Any, List, Optional
from datetime import datetime

from docex.docbasket import DocBasket
from docex.document import Document
from docex.processors.rag.enhanced_rag_service import EnhancedRAGService, EnhancedRAGConfig
from docex.processors.rag.rag_service import RAGResult
from docex.processors.llm import BaseLLMProcessor
from docex.processors.vector.semantic_search_service import SemanticSearchService

logger = logging.getLogger(__name__)


class KnowledgeBaseService:
    """
    Knowledge Base Service for querying rule books using RAG
    
    Features:
    - RAG-powered semantic search across rule books
    - LLM-based answer generation with source citations
    - Structured data extraction (JSON) for programmatic use
    - Version control and change tracking
    - Fast lookup by indexed fields
    """
    
    def __init__(
        self,
        rag_service: EnhancedRAGService,
        llm_adapter: BaseLLMProcessor,
        basket: Optional[DocBasket] = None
    ):
        """
        Initialize Knowledge Base Service
        
        Args:
            rag_service: Configured EnhancedRAGService instance
            llm_adapter: LLM adapter for structured data extraction
            basket: Optional DocBasket for rule book storage
        """
        self.rag_service = rag_service
        self.llm_adapter = llm_adapter
        self.basket = basket
        
        # Rule book metadata tracking
        self.rule_books: Dict[str, Dict[str, Any]] = {}
        
        logger.info("Knowledge Base Service initialized")
    
    async def ingest_rule_book(
        self,
        document: Document,
        rule_book_type: str,
        version: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> bool:
        """
        Ingest a rule book document into the knowledge base
        
        Args:
            document: Document containing rule book content
            rule_book_type: Type of rule book ('gpo_roster', 'ddd_matrix', 'eligibility_guide')
            version: Optional version identifier
            metadata: Optional additional metadata
            
        Returns:
            True if successful, False otherwise
        """
        try:
            logger.info(f"Ingesting {rule_book_type} rule book: {document.name}")
            
            # Store rule book metadata
            rule_book_id = f"{rule_book_type}_{document.id}"
            self.rule_books[rule_book_id] = {
                'type': rule_book_type,
                'document_id': document.id,
                'name': document.name,
                'version': version or datetime.now().isoformat(),
                'ingested_at': datetime.now().isoformat(),
                'metadata': metadata or {}
            }
            
            # Add document to basket if provided
            if self.basket:
                # Document should already be in basket, just ensure metadata is set
                pass
            
            # Index document in vector database if available
            if hasattr(self.rag_service, 'add_documents_to_vector_db'):
                success = await self.rag_service.add_documents_to_vector_db([document])
                if not success:
                    logger.warning("Failed to add document to vector database, continuing with semantic search only")
            
            logger.info(f"Successfully ingested rule book: {rule_book_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to ingest rule book: {e}", exc_info=True)
            return False
    
    async def query_rule_book(
        self,
        question: str,
        rule_book_type: Optional[str] = None,
        extract_structured: bool = True,
        filters: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Query rule books using natural language
        
        Args:
            question: Natural language question
            rule_book_type: Optional filter by rule book type
            extract_structured: Whether to extract structured data (JSON)
            filters: Optional metadata filters
            
        Returns:
            Dictionary with answer, structured data, and metadata
        """
        try:
            logger.info(f"Querying rule book: {question[:100]}...")
            
            # Build filters
            query_filters = filters or {}
            if rule_book_type:
                query_filters['rule_book_type'] = rule_book_type
            
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
                structured_data = await self._extract_structured_data(
                    question,
                    rag_result.answer,
                    rag_result.sources
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
            logger.error(f"Failed to query rule book: {e}", exc_info=True)
            return {
                'query': question,
                'answer': f"Error querying rule book: {str(e)}",
                'structured_data': None,
                'confidence_score': 0.0,
                'sources': [],
                'error': str(e)
            }
    
    async def validate_contract_eligibility(
        self,
        customer_name: str,
        contract_id: Optional[str] = None,
        product_code: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Validate contract eligibility (Step 3 of chargeback workflow)
        
        Queries GPO Roster and Eligibility Guide to determine if customer
        is eligible for the contract.
        
        Args:
            customer_name: Name of the customer
            contract_id: Optional contract identifier
            product_code: Optional product code
            
        Returns:
            Dictionary with eligibility result and structured data
        """
        # Build query
        query_parts = [f"Is {customer_name} eligible"]
        if contract_id:
            query_parts.append(f"for contract {contract_id}")
        if product_code:
            query_parts.append(f"for product {product_code}")
        query = " ".join(query_parts) + "?"
        
        # Query both GPO Roster and Eligibility Guide
        result = await self.query_rule_book(
            question=query,
            rule_book_type=None,  # Search all rule books
            extract_structured=True,
            filters={'rule_book_type': ['gpo_roster', 'eligibility_guide']}
        )
        
        # Extract eligibility information
        eligibility_data = result.get('structured_data', {})
        
        return {
            'customer_name': customer_name,
            'contract_id': contract_id,
            'product_code': product_code,
            'eligible': eligibility_data.get('eligible', False) if eligibility_data else False,
            'reason': eligibility_data.get('reason', result.get('answer', 'Unknown')) if eligibility_data else result.get('answer', 'Unknown'),
            'confidence_score': result.get('confidence_score', 0.0),
            'sources': result.get('sources', []),
            'raw_result': result
        }
    
    async def validate_gpo_roster(
        self,
        customer_name: str,
        gpo_name: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Validate GPO Roster entry (Step 4 of chargeback workflow)
        
        Queries GPO Roster to verify customer is listed.
        
        Args:
            customer_name: Name of the customer
            gpo_name: Optional GPO name
            
        Returns:
            Dictionary with validation result
        """
        query = f"Is {customer_name} listed in the GPO Roster"
        if gpo_name:
            query += f" for {gpo_name}"
        query += "?"
        
        result = await self.query_rule_book(
            question=query,
            rule_book_type='gpo_roster',
            extract_structured=True
        )
        
        roster_data = result.get('structured_data', {})
        
        return {
            'customer_name': customer_name,
            'gpo_name': gpo_name,
            'listed': roster_data.get('listed', False) if roster_data else False,
            'gpo_details': roster_data.get('gpo_details', {}) if roster_data else {},
            'confidence_score': result.get('confidence_score', 0.0),
            'sources': result.get('sources', []),
            'raw_result': result
        }
    
    async def get_class_of_trade(
        self,
        customer_name: str,
        customer_type: Optional[str] = None,
        federal_data: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Determine class-of-trade (COT) using DDD Matrix (Step 6 of chargeback workflow)
        
        Args:
            customer_name: Name of the customer
            customer_type: Optional customer type
            federal_data: Optional federal database lookup results
            
        Returns:
            Dictionary with COT determination
        """
        # Build query with context
        query_parts = [f"What is the class-of-trade (COT) for {customer_name}"]
        if customer_type:
            query_parts.append(f"({customer_type})")
        if federal_data:
            query_parts.append(f"with federal data: {json.dumps(federal_data)}")
        query = " ".join(query_parts) + "?"
        
        result = await self.query_rule_book(
            question=query,
            rule_book_type='ddd_matrix',
            extract_structured=True
        )
        
        cot_data = result.get('structured_data', {})
        
        return {
            'customer_name': customer_name,
            'customer_type': customer_type,
            'cot_code': cot_data.get('cot_code', None) if cot_data else None,
            'cot_description': cot_data.get('cot_description', None) if cot_data else None,
            'cot_rules': cot_data.get('cot_rules', []) if cot_data else [],
            'confidence_score': result.get('confidence_score', 0.0),
            'sources': result.get('sources', []),
            'raw_result': result
        }
    
    async def get_rule_book_version(self, rule_book_type: str) -> Optional[Dict[str, Any]]:
        """
        Get version information for a rule book type
        
        Args:
            rule_book_type: Type of rule book
            
        Returns:
            Dictionary with version information or None if not found
        """
        # Find rule books of this type
        matching_books = [
            book for book in self.rule_books.values()
            if book['type'] == rule_book_type
        ]
        
        if not matching_books:
            return None
        
        # Return most recent version
        latest = max(matching_books, key=lambda x: x.get('ingested_at', ''))
        
        return {
            'type': rule_book_type,
            'version': latest.get('version'),
            'name': latest.get('name'),
            'ingested_at': latest.get('ingested_at'),
            'document_id': latest.get('document_id'),
            'metadata': latest.get('metadata', {})
        }
    
    async def _extract_structured_data(
        self,
        question: str,
        answer: str,
        sources: List[Any]
    ) -> Optional[Dict[str, Any]]:
        """
        Extract structured data from RAG answer using LLM
        
        Args:
            question: Original question
            answer: RAG-generated answer
            sources: Source documents
            
        Returns:
            Structured data dictionary or None
        """
        try:
            # Build extraction prompt
            extraction_prompt = f"""Extract structured data from the following question and answer.

QUESTION: {question}

ANSWER: {answer}

Extract the relevant information as JSON. The structure should match the type of query:
- For eligibility queries: {{"eligible": bool, "reason": str, "contract_id": str, "customer_name": str}}
- For GPO Roster queries: {{"listed": bool, "gpo_details": {{"gpo_name": str, "contract_id": str, "effective_date": str}}}}
- For COT queries: {{"cot_code": str, "cot_description": str, "cot_rules": [str]}}

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
                # Try to extract JSON from response (might have markdown code blocks)
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

