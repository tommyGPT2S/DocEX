"""
Tests for Claude and Local LLM Adapters

Tests for the new LLM adapters: Claude (Anthropic) and Local LLM (Ollama).
"""

import pytest
import os
import json
import tempfile
from pathlib import Path
from unittest.mock import Mock, AsyncMock, patch, MagicMock
import yaml

from docex import DocEX
from docex.document import Document
from docex.processors.llm import (
    ClaudeAdapter,
    ClaudeLLMService,
    LocalLLMAdapter,
    LocalLLMService
)
from docex.processors.base import ProcessingResult


class TestClaudeLLMService:
    """Tests for ClaudeLLMService"""
    
    def test_service_initialization(self):
        """Test Claude service initialization"""
        service = ClaudeLLMService(api_key="test-key", model="claude-3-5-sonnet-20241022")
        assert service.model == "claude-3-5-sonnet-20241022"
        assert service.client is not None
    
    @pytest.mark.asyncio
    async def test_generate_completion(self):
        """Test completion generation"""
        service = ClaudeLLMService(api_key="test-key")
        
        # Mock the client
        mock_response = MagicMock()
        mock_response.content = [MagicMock(text="Test response")]
        service.client.messages.create = MagicMock(return_value=mock_response)
        
        result = await service.generate_completion(
            prompt="Test prompt",
            system_prompt="Test system"
        )
        
        assert result == "Test response"
        service.client.messages.create.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_generate_embedding(self):
        """Test embedding generation (should return None)"""
        service = ClaudeLLMService(api_key="test-key")
        
        result = await service.generate_embedding("Test text")
        assert result is None
    
    @pytest.mark.asyncio
    async def test_extract_structured_data(self):
        """Test structured data extraction"""
        service = ClaudeLLMService(api_key="test-key")
        
        # Mock the completion
        service.generate_completion = AsyncMock(return_value='{"key": "value"}')
        
        result = await service.extract_structured_data(
            text="Test text",
            system_prompt="Extract data",
            user_prompt="Extract: {content}"
        )
        
        assert result["extracted_data"]["key"] == "value"
        assert result["provider"] == "anthropic"


class TestLocalLLMService:
    """Tests for LocalLLMService"""
    
    def test_service_initialization(self):
        """Test Local LLM service initialization"""
        service = LocalLLMService(base_url="http://test:11434", model="test-model")
        assert service.base_url == "http://test:11434"
        assert service.model == "test-model"
    
    @pytest.mark.asyncio
    async def test_generate_completion(self):
        """Test completion generation"""
        service = LocalLLMService()
        
        # Mock the HTTP request
        with patch('aiohttp.ClientSession.post') as mock_post:
            mock_response = AsyncMock()
            mock_response.status = 200
            mock_response.json = AsyncMock(return_value={"response": "Test response"})
            mock_post.return_value.__aenter__.return_value = mock_response
            
            result = await service.generate_completion("Test prompt")
            assert result == "Test response"
    
    @pytest.mark.asyncio
    async def test_generate_embedding(self):
        """Test embedding generation"""
        service = LocalLLMService()
        
        # Mock the HTTP request
        with patch('aiohttp.ClientSession.post') as mock_post:
            mock_response = AsyncMock()
            mock_response.status = 200
            mock_response.json = AsyncMock(return_value={"embedding": [0.1, 0.2, 0.3]})
            mock_post.return_value.__aenter__.return_value = mock_response
            
            result = await service.generate_embedding("Test text")
            assert result == [0.1, 0.2, 0.3]
    
    @pytest.mark.asyncio
    async def test_check_model_availability(self):
        """Test model availability check"""
        service = LocalLLMService(model="test-model")
        
        # Mock the HTTP request
        with patch('aiohttp.ClientSession.get') as mock_get:
            mock_response = AsyncMock()
            mock_response.status = 200
            mock_response.json = AsyncMock(return_value={
                "models": [{"name": "test-model"}, {"name": "other-model"}]
            })
            mock_get.return_value.__aenter__.return_value = mock_response
            
            result = await service.check_model_availability()
            assert result is True


class TestClaudeAdapter:
    """Tests for ClaudeAdapter"""
    
    def test_adapter_initialization(self):
        """Test Claude adapter initialization"""
        with patch.dict(os.environ, {'ANTHROPIC_API_KEY': 'test-key'}):
            adapter = ClaudeAdapter({
                'api_key': 'test-key',
                'model': 'claude-3-5-sonnet-20241022'
            })
            
            assert adapter.llm_service is not None
            assert adapter.prompt_manager is not None
    
    def test_adapter_initialization_without_key(self):
        """Test Claude adapter initialization without API key"""
        with patch.dict(os.environ, {}, clear=True):
            with pytest.raises(ValueError, match="Anthropic API key is required"):
                ClaudeAdapter({})
    
    @pytest.mark.asyncio
    async def test_process_with_prompt(self):
        """Test processing document with external prompt"""
        with patch.dict(os.environ, {'ANTHROPIC_API_KEY': 'test-key'}):
            adapter = ClaudeAdapter({
                'api_key': 'test-key',
                'prompt_name': 'test_prompt'
            })
            
            # Mock the LLM service
            adapter.llm_service.extract_structured_data = AsyncMock(return_value={
                'extracted_data': {'test_field': 'test_value'},
                'model': 'claude-3-5-sonnet-20241022',
                'raw_response': {'completion': 'test'}
            })
            
            # Mock prompt manager
            adapter.get_system_prompt = Mock(return_value="System prompt")
            adapter.get_user_prompt = Mock(return_value="User prompt")
            
            # Create test document
            docex = DocEX()
            basket = docex.basket('test')
            
            with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
                f.write("Test document content")
                temp_path = f.name
            
            try:
                document = basket.add(temp_path)
                result = await adapter.process(document)
                
                assert result.success is True
                assert result.content['test_field'] == 'test_value'
                
                # Check metadata
                metadata = document.get_metadata()
                assert metadata.get('llm_provider') == 'anthropic'
                assert metadata.get('test_field') == 'test_value'
                
            finally:
                os.unlink(temp_path)


class TestLocalLLMAdapter:
    """Tests for LocalLLMAdapter"""
    
    def test_adapter_initialization(self):
        """Test Local LLM adapter initialization"""
        adapter = LocalLLMAdapter({
            'base_url': 'http://test:11434',
            'model': 'test-model'
        })
        
        assert adapter.llm_service is not None
        assert adapter.prompt_manager is not None
    
    @pytest.mark.asyncio
    async def test_process_with_model_check(self):
        """Test processing with model availability check"""
        adapter = LocalLLMAdapter({
            'base_url': 'http://test:11434',
            'model': 'test-model',
            'prompt_name': 'test_prompt'
        })
        
        # Mock model availability and processing
        adapter.llm_service.check_model_availability = AsyncMock(return_value=True)
        adapter.llm_service.extract_structured_data = AsyncMock(return_value={
            'extracted_data': {'test_field': 'test_value'},
            'model': 'test-model',
            'raw_response': {'completion': 'test'}
        })
        
        # Mock prompt manager
        adapter.get_system_prompt = Mock(return_value="System prompt")
        adapter.get_user_prompt = Mock(return_value="User prompt")
        
        # Create test document
        docex = DocEX()
        basket = docex.basket('test')
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
            f.write("Test document content")
            temp_path = f.name
        
        try:
            document = basket.add(temp_path)
            result = await adapter.process(document)
            
            assert result.success is True
            assert result.content['test_field'] == 'test_value'
            
            # Check that model availability was checked
            adapter.llm_service.check_model_availability.assert_called_once()
            
        finally:
            os.unlink(temp_path)
    
    @pytest.mark.asyncio
    async def test_process_with_model_pull(self):
        """Test processing with model pull"""
        adapter = LocalLLMAdapter({
            'model': 'missing-model'
        })
        
        # Mock model not available, but pull succeeds
        adapter.llm_service.check_model_availability = AsyncMock(return_value=False)
        adapter.llm_service.pull_model = AsyncMock(return_value=True)
        adapter.llm_service.extract_structured_data = AsyncMock(return_value={
            'extracted_data': {'test': 'data'},
            'model': 'missing-model',
            'raw_response': {}
        })
        
        adapter.get_system_prompt = Mock(return_value="System prompt")
        adapter.get_user_prompt = Mock(return_value="User prompt")
        
        # Create test document
        docex = DocEX()
        basket = docex.basket('test')
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
            f.write("Test content")
            temp_path = f.name
        
        try:
            document = basket.add(temp_path)
            result = await adapter.process(document)
            
            assert result.success is True
            
            # Check that model was pulled
            adapter.llm_service.pull_model.assert_called_once()
            
        finally:
            os.unlink(temp_path)


class TestIntegration:
    """Integration tests with DocEX"""
    
    @pytest.mark.asyncio
    async def test_claude_integration(self):
        """Test Claude adapter integration with DocEX"""
        with patch.dict(os.environ, {'ANTHROPIC_API_KEY': 'test-key'}):
            docex = DocEX()
            basket = docex.basket('claude_integration_test')
            
            # Mock the adapter for integration test
            with patch('docex.processors.llm.ClaudeAdapter._process_with_llm') as mock_process:
                mock_process.return_value = ProcessingResult(
                    success=True,
                    content={'extracted': 'data'},
                    metadata={'llm_provider': 'anthropic'}
                )
                
                adapter = ClaudeAdapter({'api_key': 'test-key'})
                
                # Create and process document
                with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
                    f.write("Integration test content")
                    temp_path = f.name
                
                try:
                    document = basket.add(temp_path)
                    result = await adapter.process(document)
                    
                    assert result.success is True
                    assert result.content['extracted'] == 'data'
                    
                finally:
                    os.unlink(temp_path)
    
    @pytest.mark.asyncio
    async def test_local_llm_integration(self):
        """Test Local LLM adapter integration with DocEX"""
        docex = DocEX()
        basket = docex.basket('local_llm_integration_test')
        
        # Mock the adapter for integration test
        with patch('docex.processors.llm.LocalLLMAdapter._process_with_llm') as mock_process:
            mock_process.return_value = ProcessingResult(
                success=True,
                content={'extracted': 'data'},
                metadata={'llm_provider': 'local_llm'}
            )
            
            adapter = LocalLLMAdapter({'model': 'test-model'})
            
            # Create and process document
            with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
                f.write("Integration test content")
                temp_path = f.name
            
            try:
                document = basket.add(temp_path)
                result = await adapter.process(document)
                
                assert result.success is True
                assert result.content['extracted'] == 'data'
                
            finally:
                os.unlink(temp_path)