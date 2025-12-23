# Knowledge Base Service Implementation Proposal
## Novartis + Keystone MMF AI Project

**Project:** Keystone RAIN Platform for Novartis Managed Markets Finance (MMF)  
**Document Version:** 2.0  
**Date:** Current Session  
**Status:** Implementation Proposal  
**Related Documents:**
- `Keystone.ai x Novartis - MMF AI Proposal - v.live.pdf`
- `Architecture_Review_and_Enhancements.md`
- `Technical_Specification.html`
- `Project_Proposal.html`
- `Updated_RAIN_Architecture_Diagram.html`

---

## Executive Summary

This document proposes the implementation of a **Knowledge Base (KB) Service** for the Novartis MMF AI project, which enables automated querying of rule books (GPO Rosters, DDD Matrix, ICCR Eligibility Guides) using RAG (Retrieval-Augmented Generation) and LLM technology. The KB service is a critical component that supports **Steps 3, 4, and 6** of the 8-step chargeback process automation workflow.

### Key Business Value

- **Time Savings**: Automates manual rule book lookups, contributing to 10+ minute reduction per chargeback kickout
- **Accuracy**: Enables 99.9% automated resolution rate for "Customer not found" kickouts
- **Compliance**: Maintains complete audit trail of all KB queries for SOX compliance
- **Scalability**: Supports processing 50-200 chargebacks daily with ability to scale

### Technical Approach

- **Leverages Existing DocEX Infrastructure**: Uses EnhancedRAGService, LLM adapters, and vector databases
- **RAG-Powered Querying**: Combines semantic search with LLM generation for intelligent answers
- **Structured Data Extraction**: LLM extracts structured data (JSON) for programmatic use
- **Workflow Integration**: Seamlessly integrates with chargeback workflow processors

---

## Project Context

This document proposes a comprehensive solution for implementing the Knowledge Base (KB) service as part of the **Keystone RAIN Platform deployment for Novartis MMF use cases**. The KB service is a critical component that enables automated workflow decisions in the chargeback process automation, leveraging existing DocEX RAG capabilities and LLM adapters to intelligently query rule books (GPO Rosters, DDD Matrix, ICCR Eligibility Guides).

### Business Context

The KB service directly addresses requirements from the **Novartis MMF AI Proposal** for automating the 8-step chargeback process:

- **Step 3:** Contract Eligibility Validation (queries GPO Roster and Eligibility Guide)
- **Step 4:** GPO Roster Validation (queries GPO Roster)
- **Step 6:** Class-of-Trade Determination (queries DDD Matrix)

### Novartis-Specific Requirements

Based on the project proposal, the following Novartis-specific requirements must be addressed:

1. **99.9% vs 0.1% Split**: 
   - 99.9% of "Customer not found" kickouts result in customer creation (eligible)
   - 0.1% are rejected due to ineligibility
   - KB service must handle both cases with appropriate routing

2. **Priority Order** (from Novartis scoping):
   - **Highest Priority**: API calls to Federal websites, GPO Roster pulls
   - **High Priority**: Class-of-trade determination
   - **Medium Priority**: Additional validation steps

3. **Rule Book Update Frequency**:
   - GPO Rosters: Updated when new contracts/amendments are received
   - DDD Matrix: Updated with contract changes
   - ICCR Eligibility Guide: Updated with contract amendments
   - KB service must support version control and change tracking

4. **Compliance Requirements**:
   - Automatic capture of validation results for audit trail
   - Screenshots/responses stored as document metadata
   - Complete query history with timestamps for SOX compliance

5. **Data Lag Handling**:
   - Novartis has experienced data lag issues with federal database APIs
   - KB service must implement caching and retry logic
   - Fallback mechanisms for API failures

### Use Case Alignment

This KB implementation supports:
1. **Chargeback Process Automation** - Automated resolution of "Customer not found" kickouts (50-200 daily)
2. **Medicaid Rebate Automation** - Contract rules and dispute rules for invoice processing
3. **Medicaid GTN Forecasting** - Historical patterns and business rules for forecasting models

### Related Documents

- `Keystone.ai x Novartis - MMF AI Proposal - v.live.pdf` - Project definition
- `Architecture_Review_and_Enhancements.md` - Architecture adjustments
- `Technical_Specification.html` - Technical specifications
- `Project_Proposal.html` - Project proposal
- `Updated_RAIN_Architecture_Diagram.html` - Updated architecture

---

## Overview

This document proposes a comprehensive solution for implementing the Knowledge Base (KB) service in DocEX, leveraging existing RAG capabilities and LLM adapters to enable intelligent querying of rule books (GPO Rosters, DDD Matrix, Eligibility Guides) for automated workflow decisions in the Novartis MMF chargeback automation workflow.

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    Knowledge Base Service                    │
├─────────────────────────────────────────────────────────────┤
│  • Rule Book Ingestion & Indexing                           │
│  • RAG-Powered Query Engine                                 │
│  • LLM-Based Answer Generation                              │
│  • Structured Rule Extraction                               │
│  • Version Control & Change Tracking                        │
└─────────────────────────────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────┐
│                    DocEX Infrastructure                      │
├─────────────────────────────────────────────────────────────┤
│  • EnhancedRAGService (FAISS/Pinecone)                      │
│  • BaseLLMProcessor (OpenAI/Claude/Local)                   │
│  • DocBasket (Rule Book Storage)                             │
│  • SemanticSearchService                                    │
└─────────────────────────────────────────────────────────────┘
```

## Implementation Components

### 1. Knowledge Base Service (`docex/services/knowledge_base_service.py`)

Core service that wraps RAG capabilities for KB-specific queries.

**Key Features:**
- Rule book ingestion and indexing
- RAG-powered semantic search
- LLM-based answer generation
- Structured rule extraction
- Fast lookup by indexed fields
- Version control

### 2. Rule Book Processors (`docex/processors/kb/`)

Specialized processors for ingesting and processing rule books.

**Components:**
- `rule_book_processor.py` - Base processor for rule book ingestion
- `gpo_roster_processor.py` - GPO Roster extraction
- `ddd_matrix_processor.py` - DDD Matrix extraction
- `eligibility_guide_processor.py` - Eligibility Guide extraction

### 3. KB Query Processors (`docex/processors/kb/`)

Processors that use KB service for workflow integration.

**Components:**
- `contract_eligibility_processor.py` - Query contract eligibility
- `cot_determination_processor.py` - Determine class-of-trade
- `customer_validation_processor.py` - Validate customer against rules

### 4. Prompts (`docex/prompts/kb/`)

YAML-based prompts for KB-specific extractions and queries, tailored for Novartis MMF use cases.

**Prompts:**
- `rule_extraction.yaml` - Extract structured rules from Novartis rule books (GPO Rosters, DDD Matrix)
- `eligibility_query.yaml` - Query eligibility information from GPO Roster and ICCR Eligibility Guide
- `cot_determination.yaml` - Determine class-of-trade using DDD Matrix and federal database results
- `contract_validation.yaml` - Validate contract specifications from chargeback EDIs

## Detailed Implementation

### Component 1: Knowledge Base Service

```python
"""
Knowledge Base Service for DocEX

Provides intelligent querying of rule books using RAG and LLM.
"""

import logging
from typing import Dict, Any, List, Optional
from datetime import datetime
from dataclasses import dataclass

from docex.processors.rag.enhanced_rag_service import EnhancedRAGService, EnhancedRAGConfig, RAGResult
from docex.processors.llm import BaseLLMProcessor
from docex.processors.vector.semantic_search_service import SemanticSearchService
from docex.document import Document
from docex.docbasket import DocBasket

logger = logging.getLogger(__name__)


@dataclass
class KBQueryResult:
    """Result from KB query"""
    query: str
    answer: str
    structured_data: Optional[Dict[str, Any]] = None
    confidence_score: float = 0.0
    sources: List[Dict[str, Any]] = None
    metadata: Dict[str, Any] = None


class KnowledgeBaseService:
    """
    Knowledge Base Service for managing and querying rule books
    
    Leverages RAG and LLM to provide intelligent answers about
    business rules, eligibility, and contract specifications.
    """
    
    def __init__(
        self,
        rag_service: EnhancedRAGService,
        llm_adapter: BaseLLMProcessor,
        kb_baskets: Dict[str, str] = None
    ):
        """
        Initialize Knowledge Base Service
        
        Args:
            rag_service: Enhanced RAG service for document retrieval
            llm_adapter: LLM adapter for answer generation
            kb_baskets: Dictionary mapping rule book types to basket IDs
                       e.g., {'gpo_roster': 'bas_xxx', 'ddd_matrix': 'bas_yyy'}
        """
        self.rag_service = rag_service
        self.llm_adapter = llm_adapter
        self.kb_baskets = kb_baskets or {}
        
        # Initialize vector database if not already done
        if not self.rag_service.vector_db_initialized:
            logger.info("Initializing vector database for KB service...")
            # This will be async, so we'll handle it in async methods
        
        logger.info(f"Knowledge Base Service initialized with baskets: {list(self.kb_baskets.keys())}")
    
    async def initialize(self) -> bool:
        """Initialize KB service and vector database"""
        return await self.rag_service.initialize_vector_db()
    
    async def ingest_rule_book(
        self,
        rule_book_type: str,
        document: Document,
        basket_id: Optional[str] = None
    ) -> bool:
        """
        Ingest a rule book document into the knowledge base
        
        Args:
            rule_book_type: Type of rule book (gpo_roster, ddd_matrix, eligibility_guide)
            document: DocEX document containing the rule book
            basket_id: Optional basket ID (will use kb_baskets if not provided)
        
        Returns:
            True if successful, False otherwise
        """
        try:
            logger.info(f"Ingesting {rule_book_type} rule book: {document.name}")
            
            # Determine basket ID
            if not basket_id:
                basket_id = self.kb_baskets.get(rule_book_type)
                if not basket_id:
                    logger.error(f"No basket configured for rule book type: {rule_book_type}")
                    return False
            
            # Add document to vector database for semantic search
            success = await self.rag_service.add_documents_to_vector_db([document])
            
            if success:
                # Store rule book metadata
                from docex.services.metadata_service import MetadataService
                metadata_service = MetadataService(document.db)
                metadata_service.update_metadata(document.id, {
                    'rule_book_type': rule_book_type,
                    'ingested_at': datetime.now().isoformat(),
                    'basket_id': basket_id
                })
                
                logger.info(f"Successfully ingested {rule_book_type} rule book")
            
            return success
            
        except Exception as e:
            logger.error(f"Failed to ingest rule book: {e}")
            return False
    
    async def query_rule_book(
        self,
        query: str,
        rule_book_type: Optional[str] = None,
        basket_ids: Optional[List[str]] = None,
        extract_structured: bool = True
    ) -> KBQueryResult:
        """
        Query the knowledge base using RAG
        
        Args:
            query: Natural language query about rules/eligibility
            rule_book_type: Optional rule book type to limit search
            basket_ids: Optional list of basket IDs to search
            extract_structured: Whether to extract structured data from answer
        
        Returns:
            KBQueryResult with answer and structured data
        """
        try:
            # Determine which baskets to search
            if basket_ids:
                search_baskets = basket_ids
            elif rule_book_type:
                basket_id = self.kb_baskets.get(rule_book_type)
                search_baskets = [basket_id] if basket_id else None
            else:
                # Search all KB baskets
                search_baskets = list(self.kb_baskets.values())
            
            # Perform RAG query
            rag_result = await self.rag_service.query(
                question=query,
                basket_id=search_baskets[0] if search_baskets and len(search_baskets) == 1 else None,
                filters={'rule_book_type': rule_book_type} if rule_book_type else None
            )
            
            # Extract structured data if requested
            structured_data = None
            if extract_structured and rag_result.answer:
                structured_data = await self._extract_structured_data(
                    query, rag_result.answer, rag_result.sources
                )
            
            # Build sources list
            sources = []
            for source in rag_result.sources:
                sources.append({
                    'document_id': source.document.id,
                    'document_name': getattr(source.document, 'name', 'Unknown'),
                    'similarity_score': source.similarity_score,
                    'metadata': source.metadata
                })
            
            return KBQueryResult(
                query=query,
                answer=rag_result.answer,
                structured_data=structured_data,
                confidence_score=rag_result.confidence_score,
                sources=sources,
                metadata={
                    'num_sources': len(rag_result.sources),
                    'processing_time': rag_result.processing_time,
                    'search_method': rag_result.metadata.get('search_method', 'unknown')
                }
            )
            
        except Exception as e:
            logger.error(f"KB query failed: {e}")
            return KBQueryResult(
                query=query,
                answer=f"Error querying knowledge base: {str(e)}",
                confidence_score=0.0
            )
    
    async def validate_contract_eligibility(
        self,
        customer_id: str,
        contract_spec: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Validate customer contract eligibility using KB
        
        Args:
            customer_id: Customer identifier (HIN, DEA, etc.)
            contract_spec: Contract specifications from chargeback EDI
        
        Returns:
            Validation result with eligibility details
        """
        # Build query for LLM
        query = f"""
        Check if customer {customer_id} is eligible for contract with specifications:
        - Contract Number: {contract_spec.get('contract_number', 'N/A')}
        - Program: {contract_spec.get('program', 'N/A')}
        - Eligibility Start: {contract_spec.get('eligibility_start', 'N/A')}
        - Eligibility End: {contract_spec.get('eligibility_end', 'N/A')}
        
        Please check the GPO Roster and Eligibility Guide to determine if this customer
        is eligible for this contract. Return a structured response with:
        1. Is eligible (true/false)
        2. Reason
        3. Matching contract details if found
        4. Any discrepancies
        """
        
        # Query KB using RAG
        result = await self.query_rule_book(
            query=query,
            rule_book_type='gpo_roster',  # Search GPO roster and eligibility guide
            extract_structured=True
        )
        
        # Parse structured response
        if result.structured_data:
            return {
                'eligible': result.structured_data.get('is_eligible', False),
                'reason': result.structured_data.get('reason', ''),
                'contract_details': result.structured_data.get('contract_details', {}),
                'discrepancies': result.structured_data.get('discrepancies', []),
                'confidence': result.confidence_score,
                'sources': result.sources
            }
        else:
            # Fallback: parse from answer text
            return {
                'eligible': 'eligible' in result.answer.lower(),
                'reason': result.answer,
                'confidence': result.confidence_score,
                'sources': result.sources
            }
    
    async def get_class_of_trade(
        self,
        customer_info: Dict[str, Any],
        federal_db_results: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Determine class-of-trade using DDD Matrix and federal database information
        
        Args:
            customer_info: Customer details from chargeback EDI
            federal_db_results: Results from DEA/HIBCC/HRSA lookups
        
        Returns:
            COT determination with confidence and reasoning
        """
        # Build query for LLM
        query = f"""
        Determine the class-of-trade (COT) for this customer:
        
        Customer Information:
        - HIN: {customer_info.get('hin', 'N/A')}
        - DEA: {customer_info.get('dea', 'N/A')}
        - Address: {customer_info.get('address', 'N/A')}
        - Customer Type: {customer_info.get('customer_type', 'N/A')}
        
        Federal Database Results:
        - DEA Registration: {federal_db_results.get('dea', {}).get('registration_type', 'N/A')}
        - HIBCC HIN: {federal_db_results.get('hibcc', {}).get('entity_type', 'N/A')}
        - HRSA Program: {federal_db_results.get('hrsa', {}).get('program_type', 'N/A')}
        
        Please reference the DDD Matrix to determine the appropriate class-of-trade.
        Return a structured response with:
        1. Class-of-trade code
        2. Class-of-trade description
        3. Reasoning
        4. Confidence level
        """
        
        # Query KB using RAG
        result = await self.query_rule_book(
            query=query,
            rule_book_type='ddd_matrix',  # Search DDD Matrix
            extract_structured=True
        )
        
        # Parse structured response
        if result.structured_data:
            return {
                'cot_code': result.structured_data.get('cot_code', ''),
                'cot_description': result.structured_data.get('cot_description', ''),
                'reasoning': result.structured_data.get('reasoning', ''),
                'confidence': result.structured_data.get('confidence', result.confidence_score),
                'sources': result.sources
            }
        else:
            # Fallback: extract from answer
            return {
                'cot_code': 'UNKNOWN',
                'cot_description': result.answer,
                'confidence': result.confidence_score,
                'sources': result.sources
            }
    
    async def _extract_structured_data(
        self,
        query: str,
        answer: str,
        sources: List[Any]
    ) -> Optional[Dict[str, Any]]:
        """
        Extract structured data from RAG answer using LLM
        
        Args:
            query: Original query
            answer: RAG-generated answer
            sources: Source documents
        
        Returns:
            Structured data dictionary or None
        """
        try:
            # Build prompt for structured extraction
            extraction_prompt = f"""
            Extract structured data from this answer to the query.
            
            Query: {query}
            
            Answer: {answer}
            
            Please extract the key information and return it as a JSON object.
            The structure should match the type of query:
            - For eligibility queries: {{"is_eligible": bool, "reason": str, "contract_details": {{}}, "discrepancies": []}}
            - For COT queries: {{"cot_code": str, "cot_description": str, "reasoning": str, "confidence": float}}
            - For general queries: {{"key_points": [], "summary": str}}
            
            Return only valid JSON, no additional text.
            """
            
            # Use LLM to extract structured data
            if hasattr(self.llm_adapter, 'llm_service'):
                structured_text = await self.llm_adapter.llm_service.generate_completion(
                    prompt=extraction_prompt,
                    max_tokens=500,
                    temperature=0.1  # Low temperature for structured output
                )
            else:
                # Fallback: try to parse answer directly
                import json
                import re
                
                # Try to find JSON in answer
                json_match = re.search(r'\{[^{}]*\}', answer, re.DOTALL)
                if json_match:
                    structured_text = json_match.group(0)
                else:
                    return None
            
            # Parse JSON
            import json
            return json.loads(structured_text)
            
        except Exception as e:
            logger.warning(f"Failed to extract structured data: {e}")
            return None
    
    async def get_rule_book_version(
        self,
        rule_book_type: str
    ) -> Optional[Dict[str, Any]]:
        """
        Get version information for a rule book
        
        Args:
            rule_book_type: Type of rule book
        
        Returns:
            Version information or None
        """
        basket_id = self.kb_baskets.get(rule_book_type)
        if not basket_id:
            return None
        
        # Query for version metadata
        query = f"What is the current version and last update date of the {rule_book_type}?"
        
        result = await self.query_rule_book(
            query=query,
            rule_book_type=rule_book_type,
            extract_structured=False
        )
        
        return {
            'rule_book_type': rule_book_type,
            'basket_id': basket_id,
            'last_updated': result.metadata.get('last_updated') if result.metadata else None,
            'version': result.metadata.get('version') if result.metadata else None
        }
```

### Component 2: Rule Book Processor

```python
"""
Rule Book Processor for DocEX

Processes rule book documents (GPO Rosters, DDD Matrix, Eligibility Guides)
and extracts structured data using LLM.
"""

import logging
from typing import Dict, Any, Optional
from datetime import datetime

from docex.processors.base import BaseProcessor, ProcessingResult
from docex.processors.llm import BaseLLMProcessor
from docex.document import Document
from docex.services.knowledge_base_service import KnowledgeBaseService

logger = logging.getLogger(__name__)


class RuleBookProcessor(BaseLLMProcessor):
    """
    Processor for ingesting and extracting structured data from rule books
    """
    
    def can_process(self, document: Document) -> bool:
        """Check if this processor can handle the document"""
        # Check if document is a rule book based on name or metadata
        name_lower = document.name.lower()
        return any(keyword in name_lower for keyword in [
            'gpo_roster', 'gpo roster', 'ddd_matrix', 'ddd matrix',
            'eligibility_guide', 'eligibility guide', 'contract'
        ])
    
    async def _process_with_llm(self, document: Document, text: str) -> ProcessingResult:
        """
        Process rule book document with LLM
        
        Args:
            document: DocEX document
            text: Document text content
        
        Returns:
            ProcessingResult with extracted rule data
        """
        try:
            # Determine rule book type
            rule_book_type = self._detect_rule_book_type(document)
            
            # Extract structured data using LLM
            prompt_name = f'{rule_book_type}_extraction'
            
            system_prompt = self.get_system_prompt(prompt_name)
            user_prompt = self.get_user_prompt(prompt_name, content=text)
            
            # Extract using LLM
            result = await self.llm_service.extract_structured_data(
                text=text,
                system_prompt=system_prompt,
                user_prompt=user_prompt,
                return_raw_response=True
            )
            
            extracted_data = result['extracted_data']
            
            # Store extracted data as metadata
            metadata = {
                'rule_book_type': rule_book_type,
                'extracted_rules': extracted_data,
                'extraction_timestamp': datetime.now().isoformat(),
                'llm_provider': result.get('provider', 'unknown'),
                'llm_model': result.get('model', 'unknown')
            }
            
            return ProcessingResult(
                success=True,
                content=text,  # Keep original content
                metadata=metadata
            )
            
        except Exception as e:
            logger.error(f"Rule book processing failed: {e}")
            return ProcessingResult(
                success=False,
                error=f"Failed to process rule book: {str(e)}"
            )
    
    def _detect_rule_book_type(self, document: Document) -> str:
        """Detect the type of rule book from document name/metadata"""
        name_lower = document.name.lower()
        
        if 'gpo' in name_lower and 'roster' in name_lower:
            return 'gpo_roster'
        elif 'ddd' in name_lower and 'matrix' in name_lower:
            return 'ddd_matrix'
        elif 'eligibility' in name_lower:
            return 'eligibility_guide'
        else:
            return 'contract_specification'
```

### Component 3: COT Determination Processor

```python
"""
Class-of-Trade Determination Processor

Uses KB service to determine class-of-trade in chargeback workflow.
"""

import logging
from typing import Dict, Any
from datetime import datetime

from docex.processors.base import BaseProcessor, ProcessingResult
from docex.document import Document
from docex.services.knowledge_base_service import KnowledgeBaseService

logger = logging.getLogger(__name__)


class COTDeterminationProcessor(BaseProcessor):
    """
    Processor that determines class-of-trade using Knowledge Base
    """
    
    def __init__(self, config: Dict[str, Any], kb_service: KnowledgeBaseService, db=None):
        """
        Initialize processor
        
        Args:
            config: Processor configuration
            kb_service: Knowledge Base Service instance
            db: Optional database instance
        """
        super().__init__(config, db=db)
        self.kb_service = kb_service
    
    def can_process(self, document: Document) -> bool:
        """Check if this processor can handle the document"""
        # Process documents that need COT determination
        return document.document_type == 'chargeback' or 'chargeback' in document.name.lower()
    
    async def process(self, document: Document) -> ProcessingResult:
        """
        Determine class-of-trade using KB
        
        Args:
            document: Chargeback document with customer and federal DB info
        
        Returns:
            ProcessingResult with COT determination
        """
        try:
            # Extract customer info and federal DB results from document metadata
            customer_info = self._extract_customer_info(document)
            federal_db_results = self._extract_federal_db_results(document)
            
            if not customer_info:
                return ProcessingResult(
                    success=False,
                    error="Customer information not found in document"
                )
            
            # Query KB for COT determination
            cot_result = await self.kb_service.get_class_of_trade(
                customer_info=customer_info,
                federal_db_results=federal_db_results
            )
            
            # Store COT result as metadata
            document.update_metadata({
                'cot_code': cot_result['cot_code'],
                'cot_description': cot_result['cot_description'],
                'cot_reasoning': cot_result.get('reasoning', ''),
                'cot_confidence': cot_result['confidence'],
                'cot_determined_at': datetime.now().isoformat()
            })
            
            return ProcessingResult(
                success=True,
                content=document.get_content(mode='text'),
                metadata={
                    'cot_determination': cot_result,
                    'cot_code': cot_result['cot_code']
                }
            )
            
        except Exception as e:
            logger.error(f"COT determination failed: {e}")
            return ProcessingResult(
                success=False,
                error=f"Failed to determine COT: {str(e)}"
            )
    
    def _extract_customer_info(self, document: Document) -> Dict[str, Any]:
        """Extract customer information from document metadata"""
        metadata = document.metadata or {}
        
        return {
            'hin': metadata.get('hin') or metadata.get('customer_hin'),
            'dea': metadata.get('dea') or metadata.get('customer_dea'),
            'address': metadata.get('address') or metadata.get('customer_address'),
            'customer_type': metadata.get('customer_type')
        }
    
    def _extract_federal_db_results(self, document: Document) -> Dict[str, Any]:
        """Extract federal database lookup results from document metadata"""
        metadata = document.metadata or {}
        
        return {
            'dea': metadata.get('dea_lookup_result', {}),
            'hibcc': metadata.get('hibcc_lookup_result', {}),
            'hrsa': metadata.get('hrsa_lookup_result', {})
        }
```

### Component 4: Contract Eligibility Processor (Workflow Integration)

```python
"""
Contract Eligibility Processor

Uses KB service to validate contract eligibility in chargeback workflow.
"""

import logging
from typing import Dict, Any
from datetime import datetime

from docex.processors.base import BaseProcessor, ProcessingResult
from docex.document import Document
from docex.services.knowledge_base_service import KnowledgeBaseService

logger = logging.getLogger(__name__)


class ContractEligibilityProcessor(BaseProcessor):
    """
    Processor that validates contract eligibility using Knowledge Base
    """
    
    def __init__(self, config: Dict[str, Any], kb_service: KnowledgeBaseService, db=None):
        """
        Initialize processor
        
        Args:
            config: Processor configuration
            kb_service: Knowledge Base Service instance
            db: Optional database instance
        """
        super().__init__(config, db=db)
        self.kb_service = kb_service
    
    def can_process(self, document: Document) -> bool:
        """Check if this processor can handle the document"""
        # Process chargeback documents that need eligibility validation
        return document.document_type == 'chargeback' or 'chargeback' in document.name.lower()
    
    async def process(self, document: Document) -> ProcessingResult:
        """
        Validate contract eligibility using KB
        
        Args:
            document: Chargeback document
        
        Returns:
            ProcessingResult with eligibility validation
        """
        try:
            # Extract contract specifications from document metadata
            contract_spec = self._extract_contract_spec(document)
            customer_id = contract_spec.get('customer_id')
            
            if not customer_id:
                return ProcessingResult(
                    success=False,
                    error="Customer ID not found in document"
                )
            
            # Query KB for eligibility
            validation_result = await self.kb_service.validate_contract_eligibility(
                customer_id=customer_id,
                contract_spec=contract_spec
            )
            
            # Store validation result as metadata
            document.update_metadata({
                'contract_eligible': validation_result['eligible'],
                'eligibility_details': validation_result,
                'kb_query_timestamp': datetime.now().isoformat()
            })
            
            return ProcessingResult(
                success=True,
                content=document.get_content(mode='text'),
                metadata={
                    'eligibility_validation': validation_result,
                    'eligible': validation_result['eligible']
                }
            )
            
        except Exception as e:
            logger.error(f"Eligibility validation failed: {e}")
            return ProcessingResult(
                success=False,
                error=f"Failed to validate eligibility: {str(e)}"
            )
    
    def _extract_contract_spec(self, document: Document) -> Dict[str, Any]:
        """Extract contract specifications from document metadata"""
        # This would extract from document metadata or content
        # Implementation depends on chargeback document structure
        metadata = document.metadata or {}
        
        return {
            'customer_id': metadata.get('customer_id') or metadata.get('hin') or metadata.get('dea'),
            'contract_number': metadata.get('contract_number'),
            'program': metadata.get('program'),
            'eligibility_start': metadata.get('eligibility_start'),
            'eligibility_end': metadata.get('eligibility_end')
        }
```

## Usage Example: Novartis Chargeback Workflow

```python
"""
Example: Using Knowledge Base Service in Novartis Chargeback Workflow

This example demonstrates how the KB service integrates into the 8-step
chargeback process automation for Novartis MMF use case.
"""

from docex import DocEX
from docex.processors.rag.enhanced_rag_service import EnhancedRAGService, EnhancedRAGConfig
from docex.processors.llm import OpenAIAdapter
from docex.processors.vector.semantic_search_service import SemanticSearchService
from docex.services.knowledge_base_service import KnowledgeBaseService

# Initialize DocEX (Novartis environment)
docex = DocEX()

# Create KB baskets for Novartis rule books
# These baskets will store rule books from G-Drive/G-Suite
gpo_roster_basket = docex.basket('novartis_gpo_rosters')
ddd_matrix_basket = docex.basket('novartis_ddd_matrices')
eligibility_guide_basket = docex.basket('novartis_eligibility_guides')

# Ingest rule books from Novartis G-Drive
# These are the reference documents mentioned in the proposal:
# - GPO Roster (customer contract eligibility)
# - DDD Matrix (class-of-trade determination rules)
# - ICCR Eligibility Guide (eligibility verification procedures)
gpo_roster_doc = gpo_roster_basket.add('path/to/novartis_gpo_roster.xlsx')
ddd_matrix_doc = ddd_matrix_basket.add('path/to/novartis_ddd_matrix.xlsx')
eligibility_doc = eligibility_guide_basket.add('path/to/novartis_iccr_eligibility_guide.pdf')

# Initialize RAG service
semantic_search = SemanticSearchService(docex.db)
llm_adapter = OpenAIAdapter({'api_key': 'your-key'})

rag_config = EnhancedRAGConfig(
    vector_db_type='faiss',
    enable_hybrid_search=True,
    top_k_documents=5
)

rag_service = EnhancedRAGService(
    semantic_search_service=semantic_search,
    llm_adapter=llm_adapter,
    config=rag_config
)

await rag_service.initialize_vector_db()

# Initialize KB service
kb_service = KnowledgeBaseService(
    rag_service=rag_service,
    llm_adapter=llm_adapter,
    kb_baskets={
        'gpo_roster': gpo_roster_basket.id,
        'ddd_matrix': ddd_matrix_basket.id,
        'eligibility_guide': eligibility_guide_basket.id
    }
)

await kb_service.initialize()

# Ingest rule books into KB
await kb_service.ingest_rule_book('gpo_roster', gpo_roster_doc)
await kb_service.ingest_rule_book('ddd_matrix', ddd_matrix_doc)
await kb_service.ingest_rule_book('eligibility_guide', eligibility_doc)

# Example 1: Step 3 - Contract Eligibility Validation
# This is used in the 8-step chargeback workflow (Step 3)
# Query KB for contract eligibility from chargeback EDI
eligibility_result = await kb_service.validate_contract_eligibility(
    customer_id='HIN123456',  # Customer identifier from chargeback EDI
    contract_spec={
        'contract_number': 'CT-456',  # Contract from chargeback EDI
        'program': 'Medicaid',
        'eligibility_start': '2024-01-01',
        'eligibility_end': '2024-12-31'
    }
)

print(f"Step 3 Result - Eligible: {eligibility_result['eligible']}")
print(f"Reason: {eligibility_result['reason']}")
print(f"Confidence: {eligibility_result['confidence']}")
# Expected: 99.9% of cases should be eligible (as per proposal)

# Example 2: Step 6 - Class-of-Trade Determination
# This is used in the 8-step chargeback workflow (Step 6)
# Query KB for class-of-trade using DDD Matrix and federal DB results
cot_result = await kb_service.get_class_of_trade(
    customer_info={
        'hin': 'HIN123456',  # From chargeback EDI
        'dea': 'DEA123456',  # From chargeback EDI
        'address': '123 Main St',
        'customer_type': 'Hospital'
    },
    federal_db_results={
        # Results from Step 5 (Federal Database Lookup)
        'dea': {'registration_type': 'Hospital'},
        'hibcc': {'entity_type': 'Healthcare Facility'},
        'hrsa': {'program_type': '340B'}
    }
)

print(f"Step 6 Result - COT Code: {cot_result['cot_code']}")
print(f"COT Description: {cot_result['cot_description']}")
print(f"Confidence: {cot_result['confidence']}")
# This COT will be used in Step 7 (SAP Customer Creation)

# Example 3: General KB Query
# For ad-hoc queries about eligibility requirements
general_result = await kb_service.query_rule_book(
    query="What are the eligibility requirements for contract CT-456?",
    rule_book_type='gpo_roster'
)

print(f"Answer: {general_result.answer}")
print(f"Confidence: {general_result.confidence_score}")
print(f"Sources: {len(general_result.sources)} documents found")
```

## Integration with Novartis 8-Step Chargeback Workflow

```python
"""
Example: Integrating KB Service into Novartis 8-Step Chargeback Workflow

This demonstrates how the KB service integrates into the automated chargeback
workflow that processes 50-200 "Customer not found" kickouts daily from Model N.
"""

from docex.processors.kb.contract_eligibility_processor import ContractEligibilityProcessor
from docex.processors.kb.cot_determination_processor import COTDeterminationProcessor

# Initialize KB service (from previous example)
# ... (KB service setup code) ...

# Step 3: Contract Eligibility Validation (uses KB)
# This step queries GPO Roster and Eligibility Guide to validate contract eligibility
eligibility_processor = ContractEligibilityProcessor(
    config={},
    kb_service=kb_service,
    db=docex.db
)

# Step 6: Class-of-Trade Determination (uses KB)
# This step queries DDD Matrix to determine COT based on customer info and federal DB results
cot_processor = COTDeterminationProcessor(
    config={},
    kb_service=kb_service,
    db=docex.db
)

# Process chargeback kickout from Model N
# This is a "Customer not found" kickout that needs to be resolved
chargeback_basket = docex.basket('novartis_chargeback_kickouts')
chargeback_doc = chargeback_basket.add('chargeback_edi_from_model_n.txt')

# Step 1: Extract Identifiers (HIN, DEA, Address) - handled by IdentifierExtractionProcessor
# Step 2: SAP Customer Existence Check - handled by SAPCustomerCheckProcessor

# Step 3: Query Knowledge Base for Contract Eligibility
# This is where KB service is used
eligibility_result = await eligibility_processor.process(chargeback_doc)

if eligibility_result.metadata.get('eligible'):
    # Step 4: GPO Roster Validation (also uses KB)
    # Step 5: Federal Database Lookup (DEA/HIBCC/HRSA)
    
    # Step 6: Determine Class-of-Trade using KB (DDD Matrix)
    cot_result = await cot_processor.process(chargeback_doc)
    
    # Step 7: SAP Customer Creation (uses COT from Step 6)
    # Step 8: Chargeback Resolution & Compliance Documentation
else:
    # 0.1% case: Customer not eligible, route to exception queue
    print("Customer not eligible - routing to exception queue")
```

## Prompts for KB Queries

### `docex/prompts/kb/rule_extraction.yaml`

```yaml
name: rule_extraction
description: Extract structured rules from Novartis rule book documents (GPO Rosters, DDD Matrix, Eligibility Guides)
version: 1.0
project: Novartis MMF AI

system_prompt: |
  You are an expert at extracting structured business rules from Novartis pharmaceutical
  industry documents. Extract customer eligibility, contract terms, and class-of-trade
  rules from GPO Rosters, DDD Matrix, and ICCR Eligibility Guides in a structured JSON format.
  
  This data will be used to automate the chargeback process workflow for Novartis MMF team.

user_prompt_template: |
  Extract structured rules from this Novartis rule book document:
  
  {{ content }}
  
  Return a JSON object with the following structure:
  {
    "customers": [
      {
        "customer_id": "string",
        "hin": "string (HIBCC Health Industry Number)",
        "dea": "string (DEA registration number)",
        "contract_number": "string (Novartis contract identifier)",
        "eligibility_start": "string (ISO date format)",
        "eligibility_end": "string (ISO date format)",
        "program": "string (e.g., Medicaid, 340B, Commercial)",
        "gpo_name": "string (Group Purchasing Organization name)"
      }
    ],
    "cot_rules": [
      {
        "customer_type": "string (e.g., Hospital, Clinic, Pharmacy)",
        "federal_db_type": "string (DEA, HIBCC, HRSA)",
        "cot_code": "string (Class-of-Trade code)",
        "cot_description": "string (Class-of-Trade description)",
        "ddd_matrix_reference": "string (Reference to DDD Matrix rule)"
      }
    ],
    "eligibility_rules": [
      {
        "contract_number": "string",
        "eligibility_criteria": "string",
        "verification_frequency": "string",
        "iccr_reference": "string (Reference to ICCR Eligibility Guide)"
      }
    ]
  }
```

### `docex/prompts/kb/eligibility_query.yaml`

```yaml
name: eligibility_query
description: Query eligibility information from Novartis GPO Rosters and ICCR Eligibility Guides
version: 1.0
project: Novartis MMF AI

system_prompt: |
  You are an expert at determining customer contract eligibility for Novartis based on
  GPO Rosters and ICCR Eligibility Guides. This is used in Step 3 of the chargeback
  workflow automation to validate if a customer is eligible for a specific contract.
  
  Provide accurate, structured responses about eligibility status and requirements.
  Note that 99.9% of chargeback kickouts result in customer creation (eligible),
  while 0.1% are rejected due to ineligibility.

user_prompt_template: |
  Based on the following Novartis rule book documents (GPO Roster and ICCR Eligibility Guide),
  determine if the customer is eligible for the specified contract:
  
  {{ content }}
  
  Query: {{ query }}
  
  Return a structured JSON response with:
  {
    "is_eligible": boolean,
    "reason": "string (detailed explanation of eligibility determination)",
    "contract_details": {
      "contract_number": "string",
      "program": "string",
      "eligibility_start": "string",
      "eligibility_end": "string",
      "gpo_name": "string"
    },
    "discrepancies": [
      {
        "field": "string",
        "expected": "string",
        "found": "string",
        "severity": "string (high/medium/low)"
      }
    ],
    "confidence": float (0.0 to 1.0),
    "source_documents": ["string (document names used for determination)"]
  }
```

### `docex/prompts/kb/cot_determination.yaml`

```yaml
name: cot_determination
description: Determine class-of-trade using Novartis DDD Matrix and federal database results
version: 1.0
project: Novartis MMF AI

system_prompt: |
  You are an expert at determining class-of-trade (COT) for Novartis customers using
  the DDD Matrix (Distribution Data Dictionary) and federal database information.
  This is used in Step 6 of the chargeback workflow automation.
  
  The COT determination requires discretion and considers:
  - Customer type (hospital, clinic, pharmacy, etc.)
  - Federal database registration types (DEA, HIBCC, HRSA)
  - DDD Matrix rules and classifications
  - Lower-level customer distinctions

user_prompt_template: |
  Based on the following Novartis DDD Matrix and customer information, determine
  the appropriate class-of-trade (COT):
  
  DDD Matrix Content:
  {{ content }}
  
  Customer Information:
  - HIN: {{ customer_info.hin }}
  - DEA: {{ customer_info.dea }}
  - Address: {{ customer_info.address }}
  - Customer Type: {{ customer_info.customer_type }}
  
  Federal Database Results:
  - DEA Registration Type: {{ federal_db_results.dea.registration_type }}
  - HIBCC Entity Type: {{ federal_db_results.hibcc.entity_type }}
  - HRSA Program Type: {{ federal_db_results.hrsa.program_type }}
  
  Return a structured JSON response with:
  {
    "cot_code": "string (Class-of-Trade code from DDD Matrix)",
    "cot_description": "string (Full COT description)",
    "reasoning": "string (Detailed explanation of COT determination)",
    "confidence": float (0.0 to 1.0),
    "ddd_matrix_reference": "string (Specific DDD Matrix rule reference)",
    "factors_considered": [
      "string (List of factors that influenced the determination)"
    ],
    "requires_review": boolean (true if determination is ambiguous)
  }
```

## Benefits for Novartis MMF Use Cases

1. **Leverages Existing Infrastructure**: Uses existing RAG, LLM, and vector database components from DocEX
2. **Intelligent Querying**: RAG + LLM provides semantic understanding of rule books without manual lookup
3. **Structured Extraction**: LLM extracts structured data for programmatic use in automated workflows
4. **Scalable**: Vector database supports large rule book collections (GPO Rosters with 1000s of customers)
5. **Flexible**: Can query across multiple rule book types (GPO Roster, DDD Matrix, Eligibility Guide)
6. **Integrated**: Seamlessly integrates with DocEX workflow processors for 8-step chargeback automation
7. **Time Savings**: Automates manual rule book lookups, contributing to 10+ minute reduction per kickout
8. **Accuracy**: 99.9% automated resolution rate for chargeback kickouts (as per proposal goals)
9. **Compliance**: Maintains audit trail of all KB queries for SOX compliance
10. **Version Control**: Tracks changes to rule books over time (GPO Rosters updated on contract amendments)

## Implementation Steps for Novartis Project

### Phase 1A: Weeks 1-6 (Prototype Phase)

1. **Create KB Service** (`docex/services/knowledge_base_service.py`)
   - Core service wrapping EnhancedRAGService
   - Methods for contract eligibility and COT determination
   - Integration with DocEX baskets

2. **Create Rule Book Processors** (`docex/processors/kb/`)
   - RuleBookProcessor for ingesting GPO Rosters, DDD Matrix, Eligibility Guides
   - LLM-powered extraction of structured data
   - Integration with Novartis G-Drive/G-Suite

3. **Create KB Prompts** (`docex/prompts/kb/`)
   - Prompts tailored for Novartis rule book formats
   - Eligibility query prompts
   - COT determination prompts

4. **Test with Novartis Sample Data**
   - Test with sample GPO Roster from Novartis
   - Test with sample DDD Matrix
   - Validate extraction accuracy

### Phase 1A: Weeks 6-14 (Development Phase)

5. **Create Workflow Integration Processors**
   - ContractEligibilityProcessor (Step 3)
   - COTDeterminationProcessor (Step 6)
   - Integration with chargeback workflow

6. **Add KB baskets** to Novartis DocEX configuration
   - Configure baskets for GPO Rosters, DDD Matrix, Eligibility Guides
   - Set up G-Drive integration for automated updates

7. **Integrate into Chargeback Workflow**
   - Integrate Step 3 (Contract Eligibility) with KB service
   - Integrate Step 6 (COT Determination) with KB service
   - Test end-to-end workflow with real chargeback kickouts

### Phase 1B: Productionization

8. **Production Deployment**
   - Deploy KB service on Novartis cloud environment
   - Set up automated rule book update workflow
   - Monitor performance and accuracy

## Architecture Flow Diagram

```
┌─────────────────────────────────────────────────────────────────┐
│                    Knowledge Base Service Flow                   │
└─────────────────────────────────────────────────────────────────┘

Rule Book Ingestion Flow:
┌─────────────┐     ┌──────────────┐     ┌──────────────┐
│ Rule Book   │ --> │ Rule Book    │ --> │ Vector DB    │
│ Document    │     │ Processor    │     │ Indexing     │
│ (PDF/Excel) │     │ (LLM Extract)│     │ (FAISS/Pine) │
└─────────────┘     └──────────────┘     └──────────────┘
                            │
                            ▼
                    ┌──────────────┐
                    │ DocEX Basket │
                    │ (Storage)    │
                    └──────────────┘

Query Flow:
┌─────────────┐     ┌──────────────┐     ┌──────────────┐
│ User Query  │ --> │ RAG Service   │ --> │ Vector Search│
│ (Natural    │     │ (Semantic)    │     │ + Semantic    │
│ Language)   │     │               │     │ Search       │
└─────────────┘     └──────────────┘     └──────────────┘
                            │
                            ▼
                    ┌──────────────┐
                    │ LLM Adapter    │
                    │ (Answer Gen)   │
                    └──────────────┘
                            │
                            ▼
                    ┌──────────────┐
                    │ Structured   │
                    │ Data Extract │
                    └──────────────┘
```

## Data Flow Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                    KB Service Data Flow                          │
└─────────────────────────────────────────────────────────────────┘

1. Rule Book Ingestion:
   Document → RuleBookProcessor → LLM Extraction → 
   Structured Data → DocEX Metadata → Vector DB Index

2. Query Processing:
   Query → EnhancedRAGService → Hybrid Search (Vector + Semantic) →
   Relevant Documents → LLM Context → Answer Generation →
   Structured Extraction → KBQueryResult

3. Workflow Integration:
   Chargeback Doc → ContractEligibilityProcessor → 
   KB Service Query → Eligibility Result → Document Metadata
```

## Error Handling & Resilience

### Error Handling Strategy

```python
"""
Error handling patterns for KB Service
"""

class KBServiceError(Exception):
    """Base exception for KB service errors"""
    pass

class RuleBookNotFoundError(KBServiceError):
    """Raised when rule book type is not found"""
    pass

class VectorDBError(KBServiceError):
    """Raised when vector database operations fail"""
    pass

class LLMQueryError(KBServiceError):
    """Raised when LLM query fails"""
    pass

# In KnowledgeBaseService:

async def query_rule_book(
    self,
    query: str,
    rule_book_type: Optional[str] = None,
    basket_ids: Optional[List[str]] = None,
    extract_structured: bool = True,
    retry_count: int = 3
) -> KBQueryResult:
    """
    Query with retry logic and error handling
    """
    last_error = None
    
    for attempt in range(retry_count):
        try:
            # Attempt query
            result = await self._execute_query(query, rule_book_type, basket_ids, extract_structured)
            return result
            
        except VectorDBError as e:
            logger.warning(f"Vector DB error (attempt {attempt + 1}/{retry_count}): {e}")
            last_error = e
            if attempt < retry_count - 1:
                await asyncio.sleep(2 ** attempt)  # Exponential backoff
            else:
                # Fallback to semantic search only
                logger.info("Falling back to semantic search only")
                return await self._fallback_semantic_query(query, rule_book_type, basket_ids)
                
        except LLMQueryError as e:
            logger.error(f"LLM query error: {e}")
            # Return partial result without structured extraction
            return await self._partial_query_result(query, e)
            
        except Exception as e:
            logger.error(f"Unexpected error: {e}")
            last_error = e
            break
    
    # Return error result
    return KBQueryResult(
        query=query,
        answer=f"Error querying knowledge base: {str(last_error)}",
        confidence_score=0.0,
        metadata={'error': str(last_error), 'error_type': type(last_error).__name__}
    )
```

### Resilience Features

1. **Fallback Mechanisms:**
   - Vector DB failure → Fallback to semantic search only
   - LLM failure → Return retrieved documents without answer generation
   - Structured extraction failure → Return text answer only

2. **Retry Logic:**
   - Exponential backoff for transient failures
   - Configurable retry counts
   - Circuit breaker pattern for repeated failures

3. **Caching:**
   - Query result caching (TTL-based)
   - Rule book version caching
   - Structured data caching

## Performance Optimization

### 1. Vector Database Optimization

```python
# Use appropriate index type based on data size
if rule_book_count < 1000:
    index_type = 'flat'  # Exact search, fastest for small datasets
elif rule_book_count < 100000:
    index_type = 'ivf'  # Inverted file index, good balance
else:
    index_type = 'hnsw'  # Hierarchical navigable small world, best for large datasets

rag_config = EnhancedRAGConfig(
    vector_db_type='faiss',
    vector_db_config={
        'index_type': index_type,
        'dimension': 384,  # Match embedding dimension
        'metric': 'cosine'  # Cosine similarity for semantic search
    }
)
```

### 2. Batch Processing

```python
# Batch ingest multiple rule books
async def batch_ingest_rule_books(
    self,
    rule_books: List[Tuple[str, Document]]
) -> Dict[str, bool]:
    """Batch ingest for better performance"""
    results = {}
    
    # Process in batches
    batch_size = 10
    for i in range(0, len(rule_books), batch_size):
        batch = rule_books[i:i + batch_size]
        
        # Ingest batch
        tasks = [
            self.ingest_rule_book(rule_type, doc)
            for rule_type, doc in batch
        ]
        
        batch_results = await asyncio.gather(*tasks, return_exceptions=True)
        
        for (rule_type, doc), result in zip(batch, batch_results):
            results[f"{rule_type}_{doc.id}"] = (
                result if isinstance(result, bool) else False
            )
    
    return results
```

### 3. Query Optimization

```python
# Pre-filter by rule book type before vector search
async def query_rule_book_optimized(
    self,
    query: str,
    rule_book_type: Optional[str] = None
) -> KBQueryResult:
    """Optimized query with pre-filtering"""
    
    # Pre-filter documents by type if specified
    filters = {}
    if rule_book_type:
        filters['rule_book_type'] = rule_book_type
    
    # Use smaller top_k for faster retrieval
    config_override = {
        'top_k_documents': 3 if rule_book_type else 5  # Fewer docs if type specified
    }
    
    return await self.query_rule_book(
        query=query,
        rule_book_type=rule_book_type,
        extract_structured=True
    )
```

## Testing Strategy

### 1. Unit Tests

```python
"""
Unit tests for KB Service
"""

import pytest
from unittest.mock import Mock, AsyncMock, patch
from docex.services.knowledge_base_service import KnowledgeBaseService, KBQueryResult

@pytest.fixture
def mock_rag_service():
    """Mock RAG service"""
    rag = Mock()
    rag.vector_db_initialized = True
    rag.query = AsyncMock(return_value=Mock(
        answer="Test answer",
        confidence_score=0.9,
        sources=[],
        processing_time=0.5
    ))
    return rag

@pytest.fixture
def mock_llm_adapter():
    """Mock LLM adapter"""
    adapter = Mock()
    adapter.llm_service = Mock()
    adapter.llm_service.generate_completion = AsyncMock(
        return_value='{"is_eligible": true, "reason": "Found in roster"}'
    )
    return adapter

@pytest.mark.asyncio
async def test_validate_contract_eligibility(mock_rag_service, mock_llm_adapter):
    """Test contract eligibility validation"""
    kb_service = KnowledgeBaseService(
        rag_service=mock_rag_service,
        llm_adapter=mock_llm_adapter,
        kb_baskets={'gpo_roster': 'bas_123'}
    )
    
    result = await kb_service.validate_contract_eligibility(
        customer_id='HIN123',
        contract_spec={'contract_number': 'CT-456'}
    )
    
    assert result['eligible'] == True
    assert 'reason' in result
    assert result['confidence'] > 0

@pytest.mark.asyncio
async def test_get_class_of_trade(mock_rag_service, mock_llm_adapter):
    """Test COT determination"""
    kb_service = KnowledgeBaseService(
        rag_service=mock_rag_service,
        llm_adapter=mock_llm_adapter,
        kb_baskets={'ddd_matrix': 'bas_456'}
    )
    
    result = await kb_service.get_class_of_trade(
        customer_info={'hin': 'HIN123'},
        federal_db_results={'dea': {'registration_type': 'Hospital'}}
    )
    
    assert 'cot_code' in result
    assert 'cot_description' in result
    assert result['confidence'] > 0
```

### 2. Integration Tests

```python
"""
Integration tests with real DocEX infrastructure
"""

@pytest.mark.integration
async def test_end_to_end_kb_workflow():
    """Test complete KB workflow from ingestion to query"""
    
    # Setup
    docex = DocEX()
    basket = docex.basket('test_kb')
    
    # Ingest test rule book
    doc = basket.add('test_data/gpo_roster_sample.xlsx')
    
    # Initialize KB service
    kb_service = await setup_kb_service(docex)
    
    # Ingest
    success = await kb_service.ingest_rule_book('gpo_roster', doc)
    assert success == True
    
    # Query
    result = await kb_service.query_rule_book(
        query="Is customer HIN123 eligible for contract CT-456?",
        rule_book_type='gpo_roster'
    )
    
    assert result.answer is not None
    assert result.confidence_score > 0
    assert len(result.sources) > 0
```

### 3. Performance Tests

```python
"""
Performance benchmarks
"""

@pytest.mark.performance
async def test_query_performance():
    """Test query performance with large rule book collection"""
    
    kb_service = await setup_kb_service_with_large_dataset()
    
    import time
    
    # Test query latency
    start = time.time()
    result = await kb_service.query_rule_book("Test query")
    latency = time.time() - start
    
    assert latency < 2.0  # Should complete in under 2 seconds
    assert result.processing_time < 2.0
```

## Deployment Guide

### 1. Prerequisites

```bash
# Install dependencies
pip install faiss-cpu  # or faiss-gpu for GPU support
pip install pinecone-client  # if using Pinecone

# Set environment variables
export OPENAI_API_KEY=your_key  # or ANTHROPIC_API_KEY for Claude
export PINECONE_API_KEY=your_key  # if using Pinecone
```

### 2. Configuration

```python
# docex/config/kb_config.yaml

knowledge_base:
  # Vector database configuration
  vector_db:
    type: 'faiss'  # or 'pinecone'
    config:
      index_type: 'ivf'  # for medium datasets
      dimension: 384
      metric: 'cosine'
  
  # RAG configuration
  rag:
    top_k_documents: 5
    min_similarity: 0.7
    enable_hybrid_search: true
    semantic_weight: 0.7
    vector_weight: 0.3
  
  # Caching
  cache:
    enabled: true
    ttl_seconds: 3600
    max_size: 1000
  
  # Baskets
  baskets:
    gpo_roster: 'bas_gpo_roster'
    ddd_matrix: 'bas_ddd_matrix'
    eligibility_guide: 'bas_eligibility_guide'
```

### 3. Initialization Script

```python
"""
Script to initialize KB service
"""

import asyncio
import os
from docex import DocEX
from docex.services.knowledge_base_service import KnowledgeBaseService
from docex.processors.rag.enhanced_rag_service import EnhancedRAGService, EnhancedRAGConfig
from docex.processors.llm import OpenAIAdapter
from docex.processors.vector.semantic_search_service import SemanticSearchService

async def initialize_kb_service():
    """
    Initialize and configure KB service for Novartis MMF project
    
    This sets up the Knowledge Base service with Novartis-specific rule books
    from G-Drive/G-Suite, configured for the chargeback automation workflow.
    """
    
    # Initialize DocEX (Novartis environment)
    docex = DocEX()
    
    # Create KB baskets for Novartis rule books
    # These baskets will store rule books from Novartis G-Drive/G-Suite
    gpo_basket = docex.basket('novartis_gpo_rosters')
    ddd_basket = docex.basket('novartis_ddd_matrices')
    eligibility_basket = docex.basket('novartis_eligibility_guides')
    
    # Note: As per Novartis proposal, priorities are:
    # 1. API calls to Federal websites (highest priority)
    # 2. GPO Roster pulls (highest priority)
    # 3. DDD Matrix queries (high priority)
    
    # Initialize services
    semantic_search = SemanticSearchService(docex.db)
    llm_adapter = OpenAIAdapter({'api_key': os.getenv('OPENAI_API_KEY')})
    
    rag_config = EnhancedRAGConfig(
        vector_db_type='faiss',
        enable_hybrid_search=True
    )
    
    rag_service = EnhancedRAGService(
        semantic_search_service=semantic_search,
        llm_adapter=llm_adapter,
        config=rag_config
    )
    
    # Initialize vector database
    await rag_service.initialize_vector_db()
    
    # Create KB service
    kb_service = KnowledgeBaseService(
        rag_service=rag_service,
        llm_adapter=llm_adapter,
        kb_baskets={
            'gpo_roster': gpo_basket.id,
            'ddd_matrix': ddd_basket.id,
            'eligibility_guide': eligibility_basket.id
        }
    )
    
    await kb_service.initialize()
    
    print("KB Service initialized successfully for Novartis MMF project!")
    print(f"KB Baskets configured:")
    print(f"  - GPO Rosters: {gpo_basket.id}")
    print(f"  - DDD Matrices: {ddd_basket.id}")
    print(f"  - Eligibility Guides: {eligibility_basket.id}")
    
    return kb_service

if __name__ == '__main__':
    # Initialize KB service for Novartis chargeback automation
    kb_service = asyncio.run(initialize_kb_service())
    
    # Example: Ingest rule books from Novartis G-Drive
    # (This would typically be done via automated G-Drive integration)
    print("\nReady to ingest Novartis rule books from G-Drive/G-Suite")
```

## Monitoring & Observability

### 1. Metrics to Track

```python
"""
KB Service metrics
"""

class KBMetrics:
    """Metrics for KB service monitoring"""
    
    def __init__(self):
        self.query_count = 0
        self.query_latency = []
        self.cache_hits = 0
        self.cache_misses = 0
        self.vector_db_errors = 0
        self.llm_errors = 0
    
    def record_query(self, latency: float, cache_hit: bool):
        """Record query metrics"""
        self.query_count += 1
        self.query_latency.append(latency)
        if cache_hit:
            self.cache_hits += 1
        else:
            self.cache_misses += 1
    
    def get_stats(self) -> Dict[str, Any]:
        """Get current statistics"""
        avg_latency = sum(self.query_latency) / len(self.query_latency) if self.query_latency else 0
        cache_hit_rate = self.cache_hits / (self.cache_hits + self.cache_misses) if (self.cache_hits + self.cache_misses) > 0 else 0
        
        return {
            'total_queries': self.query_count,
            'avg_latency_seconds': avg_latency,
            'cache_hit_rate': cache_hit_rate,
            'vector_db_errors': self.vector_db_errors,
            'llm_errors': self.llm_errors
        }
```

### 2. Logging

```python
# Configure structured logging
import logging
import json

class KBServiceLogger:
    """Structured logger for KB service"""
    
    def __init__(self):
        self.logger = logging.getLogger('kb_service')
        handler = logging.StreamHandler()
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        handler.setFormatter(formatter)
        self.logger.addHandler(handler)
        self.logger.setLevel(logging.INFO)
    
    def log_query(self, query: str, result: KBQueryResult):
        """Log query with structured data"""
        log_data = {
            'event': 'kb_query',
            'query': query[:100],  # Truncate long queries
            'confidence': result.confidence_score,
            'num_sources': len(result.sources),
            'processing_time': result.processing_time,
            'has_structured_data': result.structured_data is not None
        }
        self.logger.info(json.dumps(log_data))
```

## Next Steps for Novartis Project

### Immediate Actions (Week 1-2)

1. **Access Novartis Rule Books**
   - Obtain sample GPO Roster from Novartis G-Drive
   - Obtain sample DDD Matrix
   - Obtain ICCR Eligibility Guide
   - Understand Novartis-specific formats and structures

2. **Set Up Development Environment**
   - Configure DocEX on Novartis cloud environment
   - Set up KB baskets for rule books
   - Configure G-Drive API access for automated updates

3. **Prototype KB Service**
   - Implement `KnowledgeBaseService` class
   - Test with sample Novartis rule books
   - Validate RAG query accuracy

### Phase 1A: Weeks 3-6 (Prototype)

4. **Create Rule Book Processors**
   - Develop processors for Novartis rule book formats
   - Test extraction accuracy with Novartis data
   - Create KB-specific prompts for Novartis use cases

5. **Initial Integration Testing**
   - Test contract eligibility queries with real Novartis contracts
   - Test COT determination with sample customer data
   - Validate against manual process results

### Phase 1A: Weeks 6-14 (Development)

6. **Workflow Integration**
   - Integrate ContractEligibilityProcessor into Step 3
   - Integrate COTDeterminationProcessor into Step 6
   - Test complete 8-step workflow with KB service

7. **User Acceptance Testing**
   - Test with Novartis ICCR team (Vanessa Zanni's team)
   - Validate time savings (target: 10+ minute reduction)
   - Validate accuracy (target: 99.9% automated resolution)

### Phase 1B: Productionization

8. **Production Deployment**
   - Deploy KB service to Novartis production environment
   - Set up automated rule book update workflow
   - Implement monitoring and alerting
   - Document operational procedures

## Success Criteria (from Novartis Proposal)

- **Time Reduction**: 10+ minute reduction per kickout (from 25 minutes to <15 minutes)
- **Automation Rate**: 99.9% automated resolution rate (0.1% exception rate)
- **Accuracy**: High accuracy in contract eligibility and COT determination
- **Reusability**: Demonstrate reusable platform components extensible to additional kickout types
- **Compliance**: Complete audit trail of all KB queries for SOX compliance

