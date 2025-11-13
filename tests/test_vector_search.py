"""
Tests for vector indexing and semantic search
"""

import pytest
import asyncio
from unittest.mock import Mock, patch, MagicMock
from docex.processors.vector import VectorIndexingProcessor, SemanticSearchService
from docex.processors.llm import OpenAIAdapter
from docex import DocEX
from docex.document import Document


class TestVectorIndexingProcessor:
    """Tests for VectorIndexingProcessor"""
    
    @pytest.fixture
    def mock_llm_adapter(self):
        """Create a mock LLM adapter"""
        async def mock_generate_embedding(text):
            return [0.1] * 1536
        
        adapter = Mock(spec=OpenAIAdapter)
        adapter.llm_service = Mock()
        adapter.llm_service.generate_embedding = mock_generate_embedding
        return adapter
    
    @pytest.fixture
    def processor_config(self, mock_llm_adapter):
        """Create processor configuration"""
        return {
            'llm_adapter': mock_llm_adapter,
            'vector_db_type': 'memory',
            'store_in_metadata': True
        }
    
    @pytest.fixture
    def processor(self, processor_config):
        """Create processor instance"""
        return VectorIndexingProcessor(processor_config)
    
    @pytest.fixture
    def mock_document(self):
        """Create a mock document"""
        doc = Mock(spec=Document)
        doc.id = 'doc_test_123'
        doc.basket_id = 'basket_test_123'
        doc.document_type = 'file'
        doc.get_metadata_dict = Mock(return_value={})
        return doc
    
    def test_initialization(self, processor):
        """Test processor initialization"""
        assert processor.vector_db_type == 'memory'
        assert processor.store_in_metadata is True
        assert processor.vector_db is not None
    
    def test_can_process(self, processor, mock_document):
        """Test can_process method"""
        # Should process documents that aren't already indexed
        assert processor.can_process(mock_document) is True
        
        # Should skip if already indexed
        mock_document.get_metadata_dict = Mock(return_value={'vector_indexed': True})
        assert processor.can_process(mock_document) is False
    
    @pytest.mark.asyncio
    async def test_process_document(self, processor, mock_document):
        """Test processing a document"""
        # Mock get_document_text
        processor.get_document_text = Mock(return_value="Test document content")
        
        # Mock the database operations to avoid needing real document
        with patch.object(processor, '_record_operation') as mock_record:
            # Mock metadata service (it's imported inside the method)
            with patch('docex.services.metadata_service.MetadataService') as mock_meta:
                mock_service = Mock()
                mock_meta.return_value = mock_service
                
                result = await processor.process(mock_document)
                
                assert result.success is True
                assert 'vector_indexed' in result.metadata
                # Extract value from DocumentMetadata object if needed
                vector_indexed = result.metadata['vector_indexed']
                if hasattr(vector_indexed, 'extra') and 'value' in vector_indexed.extra:
                    assert vector_indexed.extra['value'] is True
                else:
                    assert vector_indexed is True
                mock_service.update_metadata.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_process_no_text(self, processor, mock_document):
        """Test processing document with no text"""
        processor.get_document_text = Mock(return_value="")
        
        # Mock the database operations to avoid needing real document
        with patch.object(processor, '_record_operation') as mock_record:
            result = await processor.process(mock_document)
            
            assert result.success is False
            assert "No text content" in result.error


class TestSemanticSearchService:
    """Tests for SemanticSearchService"""
    
    @pytest.fixture
    def mock_doc_ex(self):
        """Create a mock DocEX instance"""
        return Mock(spec=DocEX)
    
    @pytest.fixture
    def mock_llm_adapter(self):
        """Create a mock LLM adapter"""
        async def mock_generate_embedding(text):
            return [0.1] * 1536
        
        adapter = Mock()
        adapter.llm_service = Mock()
        adapter.llm_service.generate_embedding = mock_generate_embedding
        return adapter
    
    @pytest.fixture
    def search_service(self, mock_doc_ex, mock_llm_adapter):
        """Create search service instance"""
        return SemanticSearchService(
            doc_ex=mock_doc_ex,
            llm_adapter=mock_llm_adapter,
            vector_db_type='memory',
            vector_db_config={'vectors': {}}
        )
    
    def test_initialization(self, search_service):
        """Test service initialization"""
        assert search_service.vector_db_type == 'memory'
        assert search_service.vector_db is not None
    
    def test_cosine_similarity(self, search_service):
        """Test cosine similarity calculation"""
        vec1 = [1.0, 0.0, 0.0]
        vec2 = [1.0, 0.0, 0.0]
        
        similarity = search_service._cosine_similarity(vec1, vec2)
        assert similarity == pytest.approx(1.0, abs=0.001)
        
        # Orthogonal vectors
        vec3 = [0.0, 1.0, 0.0]
        similarity = search_service._cosine_similarity(vec1, vec3)
        assert similarity == pytest.approx(0.0, abs=0.001)
    
    @pytest.mark.asyncio
    async def test_search_memory(self, search_service):
        """Test semantic search with memory database"""
        # Add some test vectors
        search_service.vector_db['vectors'] = {
            'doc1': {
                'embedding': [1.0, 0.0, 0.0],
                'document_id': 'doc1',
                'basket_id': 'basket1',
                'document_type': 'file',
                'metadata': {}
            },
            'doc2': {
                'embedding': [0.0, 1.0, 0.0],
                'document_id': 'doc2',
                'basket_id': 'basket1',
                'document_type': 'file',
                'metadata': {}
            }
        }
        
        # Mock document retrieval
        mock_doc = Mock(spec=Document)
        mock_doc.id = 'doc1'
        mock_doc.name = 'test.txt'
        mock_doc.get_metadata_dict = Mock(return_value={})
        
        search_service._find_basket_for_document = Mock(return_value=Mock(
            get_document=Mock(return_value=mock_doc)
        ))
        
        # Search with query embedding similar to doc1
        query_embedding = [0.9, 0.1, 0.0]
        results = await search_service._search_memory(
            query_embedding,
            top_k=2,
            basket_id='basket1'
        )
        
        assert len(results) > 0
        assert results[0]['document_id'] == 'doc1'  # Should be most similar
        assert results[0]['similarity'] > 0.5
    
    @pytest.mark.asyncio
    async def test_search_empty(self, search_service):
        """Test search with empty database"""
        search_service.vector_db['vectors'] = {}
        
        results = await search_service._search_memory(
            [0.1] * 1536,
            top_k=10
        )
        
        assert len(results) == 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

