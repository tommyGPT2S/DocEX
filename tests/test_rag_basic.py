"""
Test RAG functionality with basic components
"""

import asyncio
import pytest
import logging
from unittest.mock import Mock, AsyncMock, MagicMock

# Set up basic logging for testing
logging.basicConfig(level=logging.INFO)


@pytest.mark.asyncio
async def test_basic_rag_service():
    """Test basic RAG service functionality"""
    
    # Import modules
    from docex.processors.rag.rag_service import RAGService, RAGResult
    from docex.processors.vector.semantic_search_service import SemanticSearchResult
    from docex.document import Document
    
    # Mock semantic search service
    mock_semantic_search = Mock()
    
    # Create mock document
    mock_doc = Document()
    mock_doc.name = "Test Document"
    mock_doc.content = "This is a test document about Python programming."
    mock_doc.metadata = {'category': 'test'}
    
    # Create mock search result
    mock_search_result = SemanticSearchResult(
        document=mock_doc,
        similarity_score=0.85,
        metadata={'test': True}
    )
    
    # Mock the search method
    mock_semantic_search.search = AsyncMock(return_value=[mock_search_result])
    
    # Mock LLM adapter
    mock_llm_adapter = Mock()
    mock_llm_adapter.__class__.__name__ = "MockLLMAdapter"
    
    # Mock LLM service
    mock_llm_service = Mock()
    mock_llm_service.generate_completion = AsyncMock(
        return_value="Python is a programming language known for its simplicity."
    )
    mock_llm_adapter.llm_service = mock_llm_service
    
    # Create RAG service
    rag_config = {
        'max_context_tokens': 1000,
        'top_k_documents': 3,
        'min_similarity': 0.7,
        'answer_style': 'detailed',
        'include_citations': True
    }
    
    rag_service = RAGService(
        semantic_search_service=mock_semantic_search,
        llm_adapter=mock_llm_adapter,
        config=rag_config
    )
    
    # Test query
    result = await rag_service.query(
        question="What is Python?",
        basket_id="test_basket"
    )
    
    # Verify result
    assert isinstance(result, RAGResult)
    assert result.query == "What is Python?"
    assert len(result.sources) == 1
    assert result.sources[0].document.name == "Test Document"
    assert result.confidence_score > 0
    
    # Verify semantic search was called
    mock_semantic_search.search.assert_called_once()
    
    # Verify LLM was called
    mock_llm_service.generate_completion.assert_called_once()
    
    print("✅ Basic RAG service test passed")


@pytest.mark.asyncio  
async def test_vector_database_factory():
    """Test vector database factory"""
    
    try:
        from docex.processors.rag.vector_databases import VectorDatabaseFactory, FAISSVectorDatabase
        
        # Test FAISS database creation
        faiss_config = {
            'dimension': 384,
            'index_type': 'flat',
            'metric': 'cosine'
        }
        
        faiss_db = VectorDatabaseFactory.create_database('faiss', faiss_config)
        assert isinstance(faiss_db, FAISSVectorDatabase)
        
        print("✅ Vector database factory test passed")
        
    except ImportError as e:
        print(f"⚠️  Vector database test skipped (missing dependency): {e}")


@pytest.mark.asyncio
async def test_enhanced_rag_config():
    """Test enhanced RAG configuration"""
    
    from docex.processors.rag.enhanced_rag_service import EnhancedRAGConfig
    
    # Test default configuration
    config = EnhancedRAGConfig()
    assert config.vector_db_type == 'faiss'
    assert config.enable_hybrid_search is True
    assert config.semantic_weight == 0.7
    assert config.vector_weight == 0.3
    
    # Test custom configuration
    custom_config = EnhancedRAGConfig(
        vector_db_type='pinecone',
        enable_hybrid_search=False,
        semantic_weight=0.5,
        vector_weight=0.5,
        vector_db_config={'api_key': 'test_key'}
    )
    
    assert custom_config.vector_db_type == 'pinecone'
    assert custom_config.enable_hybrid_search is False
    assert custom_config.vector_db_config == {'api_key': 'test_key'}
    
    print("✅ Enhanced RAG config test passed")


@pytest.mark.asyncio
async def test_rag_result_serialization():
    """Test RAG result serialization"""
    
    from docex.processors.rag.rag_service import RAGResult
    from docex.processors.vector.semantic_search_service import SemanticSearchResult  
    from docex.document import Document
    
    # Create mock document and search result
    doc = Document()
    doc.name = "Test Doc"
    doc.content = "Test content"
    
    search_result = SemanticSearchResult(
        document=doc,
        similarity_score=0.9,
        metadata={}
    )
    
    # Create RAG result
    rag_result = RAGResult(
        query="Test question",
        answer="Test answer",
        sources=[search_result],
        confidence_score=0.85,
        metadata={'test': 'value'},
        processing_time=1.5
    )
    
    # Test serialization
    result_dict = rag_result.to_dict()
    
    assert result_dict['query'] == "Test question"
    assert result_dict['answer'] == "Test answer"
    assert result_dict['confidence_score'] == 0.85
    assert len(result_dict['sources']) == 1
    
    print("✅ RAG result serialization test passed")


async def run_all_tests():
    """Run all RAG tests"""
    
    print("🧪 Running RAG Tests")
    print("=" * 40)
    
    try:
        await test_basic_rag_service()
        await test_vector_database_factory()
        await test_enhanced_rag_config()
        await test_rag_result_serialization()
        
        print("\n🎉 All RAG tests passed successfully!")
        
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(run_all_tests())