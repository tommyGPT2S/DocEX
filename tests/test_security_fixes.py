"""
Security Test Cases for DocEX

Tests for SQL injection and path traversal vulnerabilities fixes.
"""

import os
import pytest
import tempfile
import shutil
from pathlib import Path
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from io import BytesIO
import json

from docex.storage.filesystem_storage import FileSystemStorage
from docex.processors.vector.semantic_search_service import SemanticSearchService
from docex import DocEX
from docex.processors.llm import BaseLLMProcessor


class TestPathTraversalProtection:
    """Test path traversal protection in FileSystemStorage"""
    
    def setup_method(self):
        """Set up test environment"""
        self.test_dir = Path(tempfile.mkdtemp())
        self.storage = FileSystemStorage({
            'path': str(self.test_dir)
        })
    
    def teardown_method(self):
        """Clean up test environment"""
        if self.test_dir.exists():
            shutil.rmtree(self.test_dir)
    
    def test_get_path_blocks_relative_path_traversal(self):
        """Test that get_path() blocks ../ path traversal"""
        # Test various path traversal attempts
        malicious_paths = [
            '../etc/passwd',
            '../../etc/passwd',
            '../../../etc/passwd',
            '..\\..\\etc\\passwd',  # Windows style
            '../' * 10 + 'etc/passwd',
            'valid/path/../../etc/passwd',
            'valid/../etc/passwd',
        ]
        
        for malicious_path in malicious_paths:
            with pytest.raises(ValueError, match="path traversal detected"):
                self.storage.get_path(malicious_path)
    
    def test_get_path_blocks_absolute_paths(self):
        """Test that get_path() blocks absolute paths"""
        if os.name == 'nt':  # Windows
            malicious_paths = ['C:\\Windows\\System32', 'C:/Windows/System32']
        else:  # Unix-like
            malicious_paths = ['/etc/passwd', '/root/.ssh/id_rsa', '/usr/bin']
        
        for malicious_path in malicious_paths:
            with pytest.raises(ValueError, match="path traversal detected"):
                self.storage.get_path(malicious_path)
    
    def test_get_path_allows_valid_paths(self):
        """Test that get_path() allows valid relative paths"""
        valid_paths = [
            'document.pdf',
            'folder/document.pdf',
            'folder/subfolder/document.pdf',
            '2024/01/document.pdf',
        ]
        
        for valid_path in valid_paths:
            result = self.storage.get_path(valid_path)
            assert result.is_absolute()
            assert str(self.test_dir) in str(result)
    
    def test_get_path_blocks_empty_key(self):
        """Test that get_path() blocks empty keys"""
        with pytest.raises(ValueError, match="cannot be empty"):
            self.storage.get_path('')
    
    def test_get_full_path_blocks_path_traversal(self):
        """Test that _get_full_path() blocks path traversal"""
        malicious_paths = [
            '../etc/passwd',
            '../../etc/passwd',
            '/etc/passwd',
        ]
        
        for malicious_path in malicious_paths:
            with pytest.raises(ValueError, match="path traversal detected"):
                self.storage._get_full_path(malicious_path)
    
    def test_get_full_path_blocks_empty_path(self):
        """Test that _get_full_path() blocks empty paths"""
        with pytest.raises(ValueError, match="cannot be empty"):
            self.storage._get_full_path('')
    
    def test_save_blocks_symlink_attacks(self):
        """Test that save() blocks symlink attacks"""
        if not hasattr(os, 'symlink'):  # Skip on Windows
            pytest.skip("Symlinks not supported on this platform")
        
        # Create a symlink pointing to a file outside storage
        target_file = self.test_dir.parent / 'target.txt'
        target_file.write_text('sensitive data')
        
        symlink_path = self.test_dir / 'symlink.txt'
        os.symlink(target_file, symlink_path)
        
        # Try to save to a path that would resolve to a symlink
        # The path resolution will detect it's outside storage directory
        content = BytesIO(b'test content')
        with pytest.raises(ValueError, match="path outside storage directory"):
            self.storage.save('symlink.txt', content)
    
    def test_save_prevents_path_traversal(self):
        """Test that save() prevents path traversal"""
        content = BytesIO(b'test content')
        
        with pytest.raises(ValueError, match="path traversal detected"):
            self.storage.save('../etc/passwd', content)
    
    def test_store_prevents_path_traversal(self):
        """Test that store() prevents path traversal"""
        # Create a valid source file
        source_file = self.test_dir / 'source.txt'
        source_file.write_text('test content')
        
        # Try to store with path traversal
        with pytest.raises(ValueError, match="path traversal detected"):
            self.storage.store(str(source_file), '../etc/passwd')
    
    def test_store_blocks_symlink_attacks(self):
        """Test that store() blocks symlink attacks"""
        if not hasattr(os, 'symlink'):  # Skip on Windows
            pytest.skip("Symlinks not supported on this platform")
        
        # Create a valid source file
        source_file = self.test_dir / 'source.txt'
        source_file.write_text('test content')
        
        # Create a symlink pointing to a file outside storage
        target_file = self.test_dir.parent / 'target.txt'
        target_file.write_text('sensitive data')
        
        symlink_path = self.test_dir / 'symlink.txt'
        os.symlink(target_file, symlink_path)
        
        # The path resolution will detect it's outside storage directory
        with pytest.raises(ValueError, match="path outside storage directory"):
            self.storage.store(str(source_file), 'symlink.txt')
    
    def test_load_prevents_path_traversal(self):
        """Test that load() prevents path traversal"""
        with pytest.raises(ValueError, match="path traversal detected"):
            self.storage.load('../etc/passwd')
    
    def test_delete_prevents_path_traversal(self):
        """Test that delete() prevents path traversal"""
        with pytest.raises(ValueError, match="path traversal detected"):
            self.storage.delete('../etc/passwd')
    
    def test_path_normalization_works(self):
        """Test that path normalization works correctly"""
        # Paths with .. are blocked for security, but we can test that
        # valid paths normalize correctly
        path1 = self.storage.get_path('folder/subfolder/document.pdf')
        path2 = self.storage.get_path('folder//subfolder/document.pdf')  # Double slash
        
        # Both should resolve to the same path
        assert path1.resolve() == path2.resolve()
        
        # Test that .. is blocked
        with pytest.raises(ValueError, match="path traversal detected"):
            self.storage.get_path('folder/../document.pdf')


class TestSQLInjectionProtection:
    """Test SQL injection protection in SemanticSearchService"""
    
    def setup_method(self):
        """Set up test environment"""
        # Create mock DocEX and LLM adapter
        self.mock_doc_ex = Mock(spec=DocEX)
        self.mock_llm_adapter = Mock(spec=BaseLLMProcessor)
        self.mock_llm_service = Mock()
        self.mock_llm_service.generate_embedding = AsyncMock(return_value=[0.1, 0.2, 0.3])
        self.mock_llm_adapter.llm_service = self.mock_llm_service
        
        # Create service with memory vector DB for testing
        self.service = SemanticSearchService(
            doc_ex=self.mock_doc_ex,
            llm_adapter=self.mock_llm_adapter,
            vector_db_type='memory',
            vector_db_config={'vectors': {}}
        )
    
    @pytest.mark.asyncio
    async def test_sql_injection_in_embedding_values(self):
        """Test that malicious embedding values are validated"""
        # Try to inject SQL in embedding values
        malicious_embeddings = [
            ["1'; DROP TABLE document; --"],
            ["1", "'; DELETE FROM document; --"],
            [1, 2, "'; UPDATE document SET id='hacked'; --"],
        ]
        
        for malicious_embedding in malicious_embeddings:
            # This should fail validation before reaching SQL
            with pytest.raises(ValueError, match="Invalid embedding values"):
                await self.service._search_pgvector(
                    query_embedding=malicious_embedding,
                    top_k=10
                )
    
    @pytest.mark.asyncio
    async def test_sql_injection_in_basket_id(self):
        """Test that malicious basket_id values are validated and parameterized"""
        # Mock database session
        mock_db = Mock()
        mock_session = Mock()
        mock_db.session = Mock(return_value=mock_session)
        
        # Create service with pgvector
        service = SemanticSearchService(
            doc_ex=self.mock_doc_ex,
            llm_adapter=self.mock_llm_adapter,
            vector_db_type='pgvector',
            vector_db_config={}
        )
        service.vector_db = {'type': 'pgvector', 'db': mock_db}
        
        # Mock execute to capture the query
        executed_queries = []
        def capture_execute(query, params=None):
            executed_queries.append((str(query), params))
            return Mock(fetchall=Mock(return_value=[]))
        
        mock_session.execute = Mock(side_effect=capture_execute)
        mock_session.__enter__ = Mock(return_value=mock_session)
        mock_session.__exit__ = Mock(return_value=False)
        
        # Try SQL injection in basket_id
        malicious_basket_ids = [
            "'; DROP TABLE document; --",
            "' OR '1'='1",
            "1'; DELETE FROM document; --",
            "1' UNION SELECT * FROM document--",
        ]
        
        for malicious_id in malicious_basket_ids:
            executed_queries.clear()
            
            with pytest.raises(ValueError, match="Invalid basket_id"):
                await service._search_pgvector(
                    query_embedding=[0.1, 0.2, 0.3],
                    top_k=10,
                    basket_id=malicious_id
                )
    
    @pytest.mark.asyncio
    async def test_parameterized_queries_used(self):
        """Test that parameterized queries are used instead of string interpolation"""
        # Mock database session
        mock_db = Mock()
        mock_session = Mock()
        mock_db.session = Mock(return_value=mock_session)
        
        # Create service with pgvector
        service = SemanticSearchService(
            doc_ex=self.mock_doc_ex,
            llm_adapter=self.mock_llm_adapter,
            vector_db_type='pgvector',
            vector_db_config={}
        )
        service.vector_db = {'type': 'pgvector', 'db': mock_db}
        
        # Mock execute to capture the query
        executed_queries = []
        def capture_execute(query, params=None):
            executed_queries.append((str(query), params or {}))
            result = Mock()
            result.fetchall = Mock(return_value=[])
            return result
        
        mock_session.execute = Mock(side_effect=capture_execute)
        mock_session.__enter__ = Mock(return_value=mock_session)
        mock_session.__exit__ = Mock(return_value=False)
        mock_session.execute.return_value.scalar = Mock(return_value='public')
        
        # Execute a search
        await service._search_pgvector(
            query_embedding=[0.1, 0.2, 0.3],
            top_k=10,
            basket_id='valid_basket_id'
        )
        
        # Verify parameterized query was used
        assert len(executed_queries) > 0
        
        # Check that parameters are passed separately (not interpolated)
        for query_str, params in executed_queries:
            # Query should contain parameter placeholders
            assert ':embedding_json' in query_str or ':basket_id' in query_str or ':limit' in query_str
            # Parameters should be in params dict, not in query string
            if params:
                for param_name in params.keys():
                    # Parameter value should not appear as string in query
                    param_value = str(params[param_name])
                    # Check that the actual value is not directly in the query (except as placeholder)
                    assert f"'{param_value}'" not in query_str or param_name in ['embedding_json']
    
    @pytest.mark.asyncio
    async def test_top_k_validation(self):
        """Test that top_k values are validated"""
        mock_db = Mock()
        mock_session = Mock()
        mock_db.session = Mock(return_value=mock_session)
        
        service = SemanticSearchService(
            doc_ex=self.mock_doc_ex,
            llm_adapter=self.mock_llm_adapter,
            vector_db_type='pgvector',
            vector_db_config={}
        )
        service.vector_db = {'type': 'pgvector', 'db': mock_db}
        
        # Test invalid top_k values
        invalid_top_k_values = [
            -1,
            0,
            10001,
            999999,
        ]
        
        for invalid_top_k in invalid_top_k_values:
            with pytest.raises(ValueError, match="Invalid top_k value"):
                await service._search_pgvector(
                    query_embedding=[0.1, 0.2, 0.3],
                    top_k=invalid_top_k
                )
    
    @pytest.mark.asyncio
    async def test_embedding_validation(self):
        """Test that embedding values are validated"""
        mock_db = Mock()
        mock_session = Mock()
        mock_db.session = Mock(return_value=mock_session)
        
        service = SemanticSearchService(
            doc_ex=self.mock_doc_ex,
            llm_adapter=self.mock_llm_adapter,
            vector_db_type='pgvector',
            vector_db_config={}
        )
        service.vector_db = {'type': 'pgvector', 'db': mock_db}
        
        # Test invalid embeddings
        invalid_embeddings = [
            None,
            [],
            "not a list",
            ["not", "numeric", "values"],
            [None, None, None],
        ]
        
        for invalid_embedding in invalid_embeddings:
            with pytest.raises(ValueError):
                await service._search_pgvector(
                    query_embedding=invalid_embedding,
                    top_k=10
                )
    
    @pytest.mark.asyncio
    async def test_schema_name_validation(self):
        """Test that schema names are validated to prevent injection"""
        mock_db = Mock()
        mock_session = Mock()
        mock_db.session = Mock(return_value=mock_session)
        
        service = SemanticSearchService(
            doc_ex=self.mock_doc_ex,
            llm_adapter=self.mock_llm_adapter,
            vector_db_type='pgvector',
            vector_db_config={}
        )
        service.vector_db = {'type': 'pgvector', 'db': mock_db}
        
        # Mock schema name with injection attempt
        malicious_schema = "public'; DROP TABLE document; --"
        mock_session.execute.return_value.scalar = Mock(return_value=malicious_schema)
        
        with pytest.raises(ValueError, match="Invalid schema name"):
            await service._search_pgvector(
                query_embedding=[0.1, 0.2, 0.3],
                top_k=10
            )


class TestSecurityIntegration:
    """Integration tests for security fixes"""
    
    def setup_method(self):
        """Set up test environment"""
        self.test_dir = Path(tempfile.mkdtemp())
        
        # Set up DocEX
        DocEX.setup(
            database={
                'type': 'sqlite',
                'sqlite': {'path': str(self.test_dir / 'docex.db')}
            },
            storage={
                'type': 'filesystem',
                'path': str(self.test_dir / 'storage')
            }
        )
        
        self.docex = DocEX()
    
    def teardown_method(self):
        """Clean up test environment"""
        if self.test_dir.exists():
            shutil.rmtree(self.test_dir)
    
    def test_path_traversal_in_real_workflow(self):
        """Test path traversal protection in real DocEX workflow"""
        basket = self.docex.basket('test_basket')
        
        # Create a test file
        test_file = self.test_dir / 'test.txt'
        test_file.write_text('test content')
        
        # Try to add file with path traversal - should be blocked by storage layer
        with pytest.raises(ValueError, match="path traversal detected"):
            # This would go through storage.store() which uses _get_full_path()
            storage = self.docex._storage
            storage.store(str(test_file), '../etc/passwd')
    
    def test_valid_paths_work_correctly(self):
        """Test that valid paths work correctly after security fixes"""
        basket = self.docex.basket('test_basket')
        
        # Create a test file
        test_file = self.test_dir / 'test.txt'
        test_file.write_text('test content')
        
        # Add file with valid path - should work
        doc = basket.add(str(test_file), name='test.txt')
        assert doc is not None
        assert doc.name == 'test.txt'


if __name__ == '__main__':
    pytest.main([__file__, '-v'])

