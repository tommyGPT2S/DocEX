"""
Tests for LLM Adapter Implementation

Tests the prompt manager, OpenAI service, and LLM processors.
"""

import pytest
import os
import json
import tempfile
from pathlib import Path
from unittest.mock import Mock, AsyncMock, patch
import yaml

from docex import DocEX
from docex.document import Document
from docex.processors.llm import (
    PromptManager,
    OpenAILLMService,
    BaseLLMProcessor,
    OpenAIAdapter
)
from docex.processors.base import ProcessingResult


class TestPromptManager:
    """Tests for PromptManager"""
    
    def test_prompt_manager_initialization(self):
        """Test PromptManager initialization"""
        manager = PromptManager()
        assert manager.prompts_dir.exists()
    
    def test_load_prompt_from_file(self):
        """Test loading a prompt from YAML file"""
        # Create temporary prompt file
        with tempfile.TemporaryDirectory() as tmpdir:
            prompt_file = Path(tmpdir) / "test_prompt.yaml"
            prompt_data = {
                'name': 'test_prompt',
                'description': 'Test prompt',
                'version': '1.0',
                'system_prompt': 'You are a test system.',
                'user_prompt_template': 'Process: {{ content }}'
            }
            
            with open(prompt_file, 'w') as f:
                yaml.dump(prompt_data, f)
            
            manager = PromptManager(prompts_dir=tmpdir)
            loaded = manager.load_prompt('test_prompt', use_cache=False)
            
            assert loaded['system_prompt'] == 'You are a test system.'
            assert loaded['user_prompt_template'] == 'Process: {{ content }}'
    
    def test_get_system_prompt(self):
        """Test getting system prompt"""
        manager = PromptManager()
        
        # Should load from default prompts directory
        system_prompt = manager.get_system_prompt('invoice_extraction')
        assert isinstance(system_prompt, str)
        assert len(system_prompt) > 0
    
    def test_get_user_prompt_with_template(self):
        """Test getting user prompt with template variables"""
        manager = PromptManager()
        
        user_prompt = manager.get_user_prompt(
            'invoice_extraction',
            content='test invoice text'
        )
        assert isinstance(user_prompt, str)
        assert 'test invoice text' in user_prompt
    
    def test_prompt_caching(self):
        """Test prompt caching"""
        manager = PromptManager()
        
        # Load prompt (should cache)
        prompt1 = manager.load_prompt('invoice_extraction')
        
        # Load again (should use cache)
        prompt2 = manager.load_prompt('invoice_extraction')
        
        assert prompt1 == prompt2
    
    def test_list_prompts(self):
        """Test listing available prompts"""
        manager = PromptManager()
        prompts = manager.list_prompts()
        
        assert isinstance(prompts, list)
        # Should have at least the default prompts
        assert len(prompts) > 0


class TestOpenAILLMService:
    """Tests for OpenAILLMService"""
    
    @pytest.mark.asyncio
    async def test_generate_completion(self):
        """Test generating text completion"""
        # Mock OpenAI client
        mock_response = Mock()
        mock_response.choices = [Mock()]
        mock_response.choices[0].message = Mock()
        mock_response.choices[0].message.content = "Test completion"
        
        mock_client = AsyncMock()
        mock_client.chat.completions.create = AsyncMock(return_value=mock_response)
        
        service = OpenAILLMService(api_key='test-key', model='gpt-4o')
        service.client = mock_client
        
        result = await service.generate_completion(
            prompt="Test prompt",
            system_prompt="You are a test system"
        )
        
        assert result == "Test completion"
        mock_client.chat.completions.create.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_generate_embedding(self):
        """Test generating embedding"""
        # Mock OpenAI client
        mock_response = Mock()
        mock_response.data = [Mock()]
        mock_response.data[0].embedding = [0.1, 0.2, 0.3]
        
        mock_client = AsyncMock()
        mock_client.embeddings.create = AsyncMock(return_value=mock_response)
        
        service = OpenAILLMService(api_key='test-key', model='gpt-4o')
        service.client = mock_client
        
        result = await service.generate_embedding("Test text")
        
        assert result == [0.1, 0.2, 0.3]
        mock_client.embeddings.create.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_extract_structured_data(self):
        """Test extracting structured data"""
        # Mock OpenAI client
        mock_response = Mock()
        mock_response.choices = [Mock()]
        mock_response.choices[0].message = Mock()
        mock_response.choices[0].message.content = '{"key": "value"}'
        mock_response.usage = None
        
        mock_client = AsyncMock()
        mock_client.chat.completions.create = AsyncMock(return_value=mock_response)
        
        service = OpenAILLMService(api_key='test-key', model='gpt-4o')
        service.client = mock_client
        
        result = await service.extract_structured_data(
            text="Test text",
            system_prompt="Extract data"
        )
        
        assert 'extracted_data' in result
        assert result['extracted_data']['key'] == 'value'


class TestBaseLLMProcessor:
    """Tests for BaseLLMProcessor"""
    
    def test_base_processor_initialization(self):
        """Test BaseLLMProcessor initialization"""
        class TestProcessor(BaseLLMProcessor):
            def _initialize_llm_service(self, config):
                return Mock()
            
            def can_process(self, document):
                return True
            
            async def _process_with_llm(self, document, text):
                return ProcessingResult(success=True, content=text)
        
        processor = TestProcessor({'test': 'config'})
        assert processor.llm_service is not None
        assert processor.prompt_manager is not None
    
    def test_get_document_text(self):
        """Test getting text from document"""
        class TestProcessor(BaseLLMProcessor):
            def _initialize_llm_service(self, config):
                return Mock()
            
            def can_process(self, document):
                return True
            
            async def _process_with_llm(self, document, text):
                return ProcessingResult(success=True)
        
        processor = TestProcessor({})
        
        # Mock document
        mock_document = Mock(spec=Document)
        mock_document.get_content = Mock(return_value="Test content")
        
        text = processor.get_document_text(mock_document)
        assert text == "Test content"
    
    @pytest.mark.asyncio
    async def test_process_document(self):
        """Test processing a document"""
        class TestProcessor(BaseLLMProcessor):
            def _initialize_llm_service(self, config):
                return Mock()
            
            def can_process(self, document):
                return True
            
            async def _process_with_llm(self, document, text):
                return ProcessingResult(
                    success=True,
                    content=text,
                    metadata={'test': 'value'}
                )
        
        processor = TestProcessor({})
        
        # Mock document
        mock_document = Mock(spec=Document)
        mock_document.id = 'test-id'
        mock_document.document_type = 'test'
        mock_document.get_content = Mock(return_value="Test content")
        mock_document.get_metadata = Mock(return_value={})
        
        # Mock _record_operation
        processor._record_operation = Mock()
        
        # Mock MetadataService - patch where it's imported
        with patch('docex.services.metadata_service.MetadataService') as mock_service_class:
            mock_metadata_service = Mock()
            mock_service_class.return_value = mock_metadata_service
            
            result = await processor.process(mock_document)
            
            assert result.success is True
            assert result.content == "Test content"
            processor._record_operation.assert_called()
            mock_metadata_service.update_metadata.assert_called()


class TestOpenAIAdapter:
    """Tests for OpenAIAdapter"""
    
    def test_adapter_initialization(self):
        """Test OpenAIAdapter initialization"""
        with patch.dict(os.environ, {'OPENAI_API_KEY': 'test-key'}):
            adapter = OpenAIAdapter({
                'api_key': 'test-key',
                'model': 'gpt-4o'
            })
            
            assert adapter.llm_service is not None
            assert adapter.prompt_manager is not None
    
    def test_adapter_initialization_without_key(self):
        """Test OpenAIAdapter initialization without API key"""
        with patch.dict(os.environ, {}, clear=True):
            with pytest.raises(ValueError, match="OpenAI API key is required"):
                OpenAIAdapter({})
    
    @pytest.mark.asyncio
    async def test_process_with_prompt(self):
        """Test processing document with external prompt"""
        # Mock OpenAI service
        mock_service = AsyncMock()
        mock_service.model = 'gpt-4o'
        mock_service.extract_structured_data = AsyncMock(return_value={
            'extracted_data': {'key': 'value'},
            'raw_response': {}
        })
        
        with patch.dict(os.environ, {'OPENAI_API_KEY': 'test-key'}):
            adapter = OpenAIAdapter({
                'api_key': 'test-key',
                'prompt_name': 'invoice_extraction'
            })
            adapter.llm_service = mock_service
            
            # Mock document
            mock_document = Mock(spec=Document)
            mock_document.id = 'test-id'
            mock_document.document_type = 'invoice'
            mock_document.get_content = Mock(return_value="Invoice text")
            mock_document.get_metadata = Mock(return_value={})
            
            # Mock _record_operation
            adapter._record_operation = Mock()
            
            # Test _process_with_llm directly (it doesn't use MetadataService)
            result = await adapter._process_with_llm(mock_document, "Invoice text")
            
            assert result.success is True
            assert result.content['key'] == 'value'
            mock_service.extract_structured_data.assert_called_once()


class TestIntegration:
    """Integration tests with DocEX"""
    
    @pytest.mark.asyncio
    async def test_integration_with_docex(self):
        """Test LLM adapter integration with DocEX"""
        # Skip if no OpenAI API key
        if not os.getenv('OPENAI_API_KEY'):
            pytest.skip("OPENAI_API_KEY not set")
        
        # Initialize DocEX
        docEX = DocEX()
        basket = docEX.basket('test_llm')
        
        # Create a test document
        test_file = Path(tempfile.gettempdir()) / "test_llm.txt"
        test_file.write_text("This is a test document for LLM processing.")
        
        try:
            # Add document to basket
            document = basket.add(
                str(test_file),
                metadata={
                    'biz_doc_type': 'test',
                    'processing_status': 'pending'
                }
            )
            
            # Initialize adapter
            adapter = OpenAIAdapter({
                'api_key': os.getenv('OPENAI_API_KEY'),
                'model': 'gpt-4o',
                'prompt_name': 'generic_extraction',
                'generate_summary': False,
                'generate_embedding': False,
                'return_raw_response': False
            })
            
            # Process document
            result = await adapter.process(document)
            
            # Verify result
            assert result.success is True
            
            # Check metadata was updated
            metadata = document.get_metadata()
            assert 'llm_provider' in metadata
            assert metadata['llm_provider'] == 'openai'
            
        finally:
            # Cleanup
            if test_file.exists():
                test_file.unlink()

