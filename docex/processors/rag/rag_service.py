"""
RAG (Retrieval-Augmented Generation) Service for DocEX

Provides comprehensive RAG capabilities by combining:
1. Vector search (FAISS, Pinecone) for document retrieval
2. LLM processing for answer generation
3. DocEX document management for context
"""

import logging
import asyncio
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime
from dataclasses import dataclass

from docex.processors.llm import BaseLLMProcessor
from docex.processors.vector.semantic_search_service import SemanticSearchService, SemanticSearchResult

logger = logging.getLogger(__name__)


@dataclass
class RAGResult:
    """Result from RAG query containing answer and source documents"""
    
    query: str
    answer: str
    sources: List[SemanticSearchResult]
    confidence_score: float
    metadata: Dict[str, Any]
    processing_time: float
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization"""
        return {
            'query': self.query,
            'answer': self.answer,
            'sources': [source.to_dict() for source in self.sources],
            'confidence_score': self.confidence_score,
            'metadata': self.metadata,
            'processing_time': self.processing_time
        }


class RAGService:
    """
    Retrieval-Augmented Generation service built on DocEX infrastructure
    
    Combines semantic search with LLM generation to provide accurate,
    source-backed answers to queries about document collections.
    """
    
    def __init__(
        self,
        semantic_search_service: SemanticSearchService,
        llm_adapter: BaseLLMProcessor,
        config: Optional[Dict[str, Any]] = None
    ):
        """
        Initialize RAG service
        
        Args:
            semantic_search_service: Configured semantic search service
            llm_adapter: LLM adapter for answer generation
            config: Optional configuration with:
                - max_context_tokens: Max tokens for context (default: 4000)
                - top_k_documents: Number of documents to retrieve (default: 5)
                - min_similarity: Minimum similarity score (default: 0.7)
                - answer_style: 'concise', 'detailed', 'bullet_points' (default: 'detailed')
                - include_citations: Whether to include source citations (default: True)
        """
        self.semantic_search = semantic_search_service
        self.llm_adapter = llm_adapter
        
        # Default configuration
        default_config = {
            'max_context_tokens': 4000,
            'top_k_documents': 5,
            'min_similarity': 0.7,
            'answer_style': 'detailed',
            'include_citations': True,
            'temperature': 0.3,  # Lower temperature for more focused answers
            'max_answer_tokens': 500
        }
        
        self.config = {**default_config, **(config or {})}
        
        logger.info(f"RAG service initialized with config: {self.config}")
    
    async def query(
        self,
        question: str,
        basket_id: Optional[str] = None,
        filters: Optional[Dict[str, Any]] = None,
        context_override: Optional[Dict[str, Any]] = None
    ) -> RAGResult:
        """
        Process RAG query and generate answer
        
        Args:
            question: User's question
            basket_id: Optional basket ID to limit search scope
            filters: Optional metadata filters
            context_override: Override default configuration for this query
            
        Returns:
            RAGResult with answer and source documents
        """
        start_time = asyncio.get_event_loop().time()
        
        # Merge context override with default config
        query_config = {**self.config, **(context_override or {})}
        
        logger.info(f"Processing RAG query: {question[:100]}...")
        
        try:
            # Step 1: Retrieve relevant documents
            search_results = await self._retrieve_documents(
                question, 
                basket_id, 
                filters, 
                query_config
            )
            
            if not search_results:
                return RAGResult(
                    query=question,
                    answer="I couldn't find any relevant documents to answer your question.",
                    sources=[],
                    confidence_score=0.0,
                    metadata={'no_sources_found': True},
                    processing_time=asyncio.get_event_loop().time() - start_time
                )
            
            # Step 2: Generate context from documents
            context = self._build_context(search_results, query_config)
            
            # Step 3: Generate answer using LLM
            answer, confidence = await self._generate_answer(
                question, 
                context, 
                search_results, 
                query_config
            )
            
            processing_time = asyncio.get_event_loop().time() - start_time
            
            result = RAGResult(
                query=question,
                answer=answer,
                sources=search_results,
                confidence_score=confidence,
                metadata={
                    'num_sources': len(search_results),
                    'context_tokens': self._estimate_tokens(context),
                    'answer_style': query_config['answer_style'],
                    'llm_adapter': self.llm_adapter.__class__.__name__
                },
                processing_time=processing_time
            )
            
            logger.info(f"RAG query completed in {processing_time:.2f}s, confidence: {confidence:.2f}")
            return result
            
        except Exception as e:
            logger.error(f"RAG query failed: {e}", exc_info=True)
            return RAGResult(
                query=question,
                answer=f"An error occurred while processing your question: {str(e)}",
                sources=[],
                confidence_score=0.0,
                metadata={'error': str(e)},
                processing_time=asyncio.get_event_loop().time() - start_time
            )
    
    async def _retrieve_documents(
        self,
        question: str,
        basket_id: Optional[str],
        filters: Optional[Dict[str, Any]],
        config: Dict[str, Any]
    ) -> List[SemanticSearchResult]:
        """Retrieve relevant documents using semantic search"""
        
        logger.info(f"Retrieving documents for: {question[:50]}...")
        
        search_results = await self.semantic_search.search(
            query=question,
            top_k=config['top_k_documents'],
            basket_id=basket_id,
            filters=filters,
            min_similarity=config['min_similarity']
        )
        
        logger.info(f"Retrieved {len(search_results)} relevant documents")
        return search_results
    
    def _build_context(
        self,
        search_results: List[SemanticSearchResult],
        config: Dict[str, Any]
    ) -> str:
        """Build context string from search results"""
        
        context_parts = []
        total_tokens = 0
        max_tokens = config['max_context_tokens']
        
        for i, result in enumerate(search_results):
            doc = result.document
            
            # Create document header with metadata
            doc_header = f"Document {i+1} (Similarity: {result.similarity_score:.2f}):"
            if hasattr(doc, 'name') and doc.name:
                doc_header += f" {doc.name}"
            
            # Get document content
            content = getattr(doc, 'content', '') or str(doc)
            
            # Estimate tokens (rough approximation: 1 token ≈ 4 characters)
            estimated_tokens = len(content) // 4
            
            if total_tokens + estimated_tokens > max_tokens:
                # Truncate content to fit within token limit
                remaining_chars = (max_tokens - total_tokens) * 4
                if remaining_chars > 100:  # Only include if meaningful content fits
                    content = content[:remaining_chars] + "... [truncated]"
                else:
                    break
            
            context_parts.append(f"{doc_header}\n{content}")
            total_tokens += estimated_tokens
            
            if total_tokens >= max_tokens:
                break
        
        return "\n\n".join(context_parts)
    
    async def _generate_answer(
        self,
        question: str,
        context: str,
        sources: List[SemanticSearchResult],
        config: Dict[str, Any]
    ) -> Tuple[str, float]:
        """Generate answer using LLM with retrieved context"""
        
        # Build prompt based on answer style
        prompt = self._build_answer_prompt(question, context, config)
        
        logger.info("Generating answer with LLM...")
        
        try:
            # Generate answer using LLM through DocEX architecture
            # DocBasket integration ensures proper tracking and storage patterns
            from docex.docbasket import DocBasket
            
            # Create a temporary RAG processing basket for LLM operations
            # This maintains DocEX's document management patterns while enabling RAG
            basket = DocBasket(id=1, name="rag_processing_basket", description="Temporary basket for RAG LLM processing")
            
            # Support multiple LLM adapter patterns:
            # 1. Service-based adapters (OpenAI, Claude with dedicated services)
            # 2. Direct generation adapters (OllamaAdapter with generate method)  
            # 3. DocBasket-integrated adapters (standard DocEX pattern)
            if hasattr(self.llm_adapter, 'llm_service'):
                # Service-based LLM adapters (OpenAI, Claude)
                answer = await self.llm_adapter.llm_service.generate_completion(
                    prompt=prompt,
                    max_tokens=config['max_answer_tokens'],
                    temperature=config['temperature']
                )
            elif hasattr(self.llm_adapter, 'generate'):
                # Direct generation adapters (OllamaAdapter)
                # These provide streamlined access to local/custom LLMs
                answer = await self.llm_adapter.generate(
                    prompt,
                    max_tokens=config['max_answer_tokens'],
                    temperature=config['temperature']
                )
                if not answer:
                    answer = "Failed to generate answer"
            else:
                # Standard DocEX pattern - process through DocBasket
                # This path supports traditional DocEX LLM adapters that expect
                # full document basket context and processing workflows
                result = await self.llm_adapter.process(
                    basket,
                    options={
                        'prompt': prompt,
                        'max_tokens': config['max_answer_tokens'],
                        'temperature': config['temperature']
                    }
                )
                answer = result.data if result.success else "Failed to generate answer"
            
            # Estimate confidence based on source similarity scores
            confidence = self._calculate_confidence(sources, answer)
            
            # Add citations if requested
            if config['include_citations'] and sources:
                answer = self._add_citations(answer, sources)
            
            return answer, confidence
            
        except Exception as e:
            logger.error(f"Failed to generate answer: {e}")
            return f"Error generating answer: {str(e)}", 0.0
    
    def _build_answer_prompt(
        self,
        question: str,
        context: str,
        config: Dict[str, Any]
    ) -> str:
        """Build prompt for answer generation"""
        
        style_instructions = {
            'concise': "Provide a brief, direct answer in 1-2 sentences.",
            'detailed': "Provide a comprehensive answer with explanations and details.",
            'bullet_points': "Provide the answer as a structured list of bullet points."
        }
        
        style_instruction = style_instructions.get(
            config['answer_style'], 
            style_instructions['detailed']
        )
        
        citation_instruction = ""
        if config['include_citations']:
            citation_instruction = "\nWhen referencing information, include the document number in your answer (e.g., 'According to Document 1...')."
        
        prompt = f"""Based on the following documents, answer the user's question.

QUESTION: {question}

CONTEXT DOCUMENTS:
{context}

INSTRUCTIONS:
- Answer based only on the information provided in the documents above
- If the documents don't contain enough information to answer the question, say so
- {style_instruction}
- Be accurate and cite your sources{citation_instruction}

ANSWER:"""
        
        return prompt
    
    def _calculate_confidence(
        self,
        sources: List[SemanticSearchResult],
        answer: str
    ) -> float:
        """Calculate confidence score for the answer"""
        
        if not sources:
            return 0.0
        
        # Base confidence on average similarity score of sources
        avg_similarity = sum(source.similarity_score for source in sources) / len(sources)
        
        # Adjust based on number of sources and answer quality indicators
        source_factor = min(len(sources) / 3, 1.0)  # More sources = higher confidence (up to 3)
        
        # Check for quality indicators in answer
        quality_factor = 1.0
        if "I don't know" in answer or "not enough information" in answer:
            quality_factor = 0.3
        elif "based on" in answer.lower() or "according to" in answer.lower():
            quality_factor = 1.2
        
        confidence = avg_similarity * source_factor * quality_factor
        return min(confidence, 1.0)  # Cap at 1.0
    
    def _add_citations(
        self,
        answer: str,
        sources: List[SemanticSearchResult]
    ) -> str:
        """Add source citations to the answer"""
        
        citations = []
        for i, source in enumerate(sources):
            doc = source.document
            doc_name = getattr(doc, 'name', f'Document {i+1}')
            citations.append(f"{i+1}. {doc_name} (Similarity: {source.similarity_score:.2f})")
        
        citation_text = "\n\nSources:\n" + "\n".join(citations)
        return answer + citation_text
    
    def _estimate_tokens(self, text: str) -> int:
        """Rough token estimation (1 token ≈ 4 characters)"""
        return len(text) // 4


class AdvancedRAGService(RAGService):
    """
    Advanced RAG service with additional features:
    - Multi-turn conversations
    - Query expansion
    - Answer refinement
    """
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.conversation_history: List[Dict[str, Any]] = []
    
    async def conversational_query(
        self,
        question: str,
        conversation_id: Optional[str] = None,
        **kwargs
    ) -> RAGResult:
        """
        Process query with conversation context
        
        Args:
            question: Current question
            conversation_id: Optional conversation ID to maintain context
            **kwargs: Additional arguments passed to query method
            
        Returns:
            RAGResult with conversational context
        """
        
        # Expand query with conversation context if available
        expanded_question = await self._expand_query_with_context(question, conversation_id)
        
        # Process expanded query
        result = await self.query(expanded_question, **kwargs)
        
        # Store in conversation history
        self._store_conversation_turn(question, result, conversation_id)
        
        return result
    
    async def _expand_query_with_context(
        self,
        question: str,
        conversation_id: Optional[str]
    ) -> str:
        """Expand query using conversation context"""
        
        if not conversation_id:
            return question
        
        # Get recent conversation history
        recent_history = [
            turn for turn in self.conversation_history[-5:]  # Last 5 turns
            if turn.get('conversation_id') == conversation_id
        ]
        
        if not recent_history:
            return question
        
        # Build context from recent history
        context_parts = []
        for turn in recent_history:
            context_parts.append(f"Q: {turn['question']}")
            context_parts.append(f"A: {turn['answer'][:200]}...")  # Truncate for context
        
        context = "\n".join(context_parts)
        
        # Use LLM to expand/clarify the current question
        expansion_prompt = f"""Given this conversation history:

{context}

Current question: {question}

Rewrite the current question to be more specific and complete, incorporating relevant context from the conversation. If the question is already clear and complete, return it unchanged.

Rewritten question:"""
        
        try:
            if hasattr(self.llm_adapter, 'llm_service'):
                expanded = await self.llm_adapter.llm_service.generate_completion(
                    prompt=expansion_prompt,
                    max_tokens=100,
                    temperature=0.3
                )
                return expanded.strip() if expanded else question
        except Exception as e:
            logger.warning(f"Query expansion failed: {e}")
        
        return question
    
    def _store_conversation_turn(
        self,
        question: str,
        result: RAGResult,
        conversation_id: Optional[str]
    ):
        """Store conversation turn in history"""
        
        turn = {
            'timestamp': datetime.now().isoformat(),
            'conversation_id': conversation_id,
            'question': question,
            'answer': result.answer,
            'confidence': result.confidence_score,
            'source_count': len(result.sources)
        }
        
        self.conversation_history.append(turn)
        
        # Keep only last 50 turns to prevent memory issues
        if len(self.conversation_history) > 50:
            self.conversation_history = self.conversation_history[-50:]