"""
Path Helper for DocBasket

This module provides path building and resolution utilities for DocBasket.
All path-related operations are centralized here for better maintainability.
"""

from typing import Optional, Dict, Any
from pathlib import Path
import logging

from docex.storage.path_builder import DocEXPathBuilder
from docex.utils.file_utils import get_content_type
from docex.utils.s3_prefix_builder import sanitize_basket_name, sanitize_filename

logger = logging.getLogger(__name__)


class DocBasketPathHelper:
    """
    Helper class for path building and resolution in DocBasket.
    
    This class encapsulates all path-related operations to keep the main
    DocBasket class focused on basket-level operations.
    """
    
    def __init__(self, basket: 'DocBasket'):
        """
        Initialize path helper with reference to parent basket.
        
        Args:
            basket: DocBasket instance that owns this helper
        """
        self.basket = basket
        self.path_builder = DocEXPathBuilder()
    
    def get_content_type(self, file_path: Path) -> str:
        """
        Get content type (MIME type) for a file.
        
        Args:
            file_path: Path to the file
            
        Returns:
            Content type string
        """
        return get_content_type(file_path)
    
    def extract_tenant_id(self) -> Optional[str]:
        """
        Extract tenant_id from database instance or basket name.
        
        Priority:
        1. Database instance tenant_id (most reliable for multi-tenant setups)
        2. Basket name format: {tenant_id}_{document_type}_{stage} (legacy support)
        
        Returns:
            Tenant ID if found, None otherwise
        """
        # First, try to get tenant_id from database instance (most reliable)
        # The database instance is tenant-aware when created by DocEX with UserContext
        if self.basket.db and hasattr(self.basket.db, 'tenant_id') and self.basket.db.tenant_id:
            return self.basket.db.tenant_id
        
        # Fallback: Try to extract from basket name (legacy support)
        # Basket name format: {tenant_id}_{document_type}_{stage}
        basket_name_parts = self.basket.name.split('_', 1)
        if len(basket_name_parts) == 2:
            return basket_name_parts[0]
        
        return None
    
    def get_readable_document_name(
        self, 
        document: Any, 
        file_path: Optional[str] = None, 
        metadata: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Get a readable document name, sanitized for filesystem use.
        
        Priority order:
        1. original_filename from provided metadata
        2. original_filename from document metadata
        3. document.name (if not a temp path)
        4. file_path stem
        5. document.name (even if temp)
        6. Fallback: document_{id}
        
        Args:
            document: Document model instance or Document wrapper
            file_path: Optional file path to extract name from
            metadata: Optional metadata dictionary
            
        Returns:
            Sanitized document name (without extension)
        """
        # First priority: Check for original filename in provided metadata
        if metadata:
            original_filename = metadata.get('original_filename')
            if original_filename:
                name = Path(original_filename).stem
                return sanitize_filename(name)

        # Second priority: Check for original filename in document metadata (if Document wrapper)
        if hasattr(document, 'get_metadata'):
            try:
                doc_metadata = document.get_metadata()
                original_filename = doc_metadata.get('original_filename')
                if original_filename:
                    name = Path(original_filename).stem
                    return sanitize_filename(name)
            except Exception:
                # Metadata access might fail if session is closed
                pass

        # Third priority: Check if document model has a proper name set (from metadata during creation)
        if hasattr(document, 'name') and document.name and not document.name.startswith('/tmp/'):
            # If document.name looks like a proper filename (not a temp path), use it
            name = Path(document.name).stem
            # Avoid using temp filenames that might have been set during creation
            if not name.startswith('temp') and not name.startswith('tmp'):
                return sanitize_filename(name)

        # Fourth priority: Use provided file_path (for new uploads)
        if file_path:
            # Use original filename (without extension)
            name = Path(file_path).stem
            return sanitize_filename(name)

        # Fifth priority: Fallback to document name even if it looks like a temp file
        if hasattr(document, 'name') and document.name:
            name = Path(document.name).stem
            return sanitize_filename(name)

        # Final fallback
        doc_id = document.id if hasattr(document, 'id') else 'unknown'
        return f"document_{doc_id[:8]}"
    
    def build_document_path(
        self, 
        document: Any, 
        file_path: Optional[str] = None, 
        metadata: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Build full document path using DocEXPathBuilder or existing storage config prefix.
        
        This method builds complete storage paths from basket_id and document_id.
        For S3, if the basket's storage config already has a prefix, use that to avoid duplication.
        All path building logic is centralized in DocEXPathBuilder to ensure:
        1. S3Storage receives full paths (no interpretation needed)
        2. Users work with IDs only (paths are internal)
        3. Consistent path structure across all storage backends
        
        Args:
            document: Document model instance with id attribute
            file_path: Optional file path to extract extension from
            metadata: Optional metadata for document name resolution
            
        Returns:
            Full document path (ready for storage backend)
        """
        # Get readable document name
        document_name = self.get_readable_document_name(document, file_path, metadata)
        
        # Extract file extension
        # Priority: 1) file_path, 2) document.name (if document has name attribute)
        if file_path:
            file_ext = Path(file_path).suffix
        elif hasattr(document, 'name') and document.name:
            file_ext = Path(document.name).suffix
        else:
            file_ext = ''
        
        # Use property to get storage type (validates it exists and is valid)
        storage_type = self.basket.storage_type
        
        # Get tenant_id (required for multi-tenant path building)
        tenant_id = self.extract_tenant_id()
        
        # For S3, check if storage config already has a prefix with basket path
        # If so, pass it to path builder to avoid duplication
        existing_prefix = None
        if storage_type == 's3':
            existing_prefix = self.basket.storage_config.get('s3', {}).get('prefix', '')
            if existing_prefix:
                # Check if prefix already includes the basket path
                # Basket path format: {basket_friendly_name}_{last_4_of_basket_id}
                basket_id_suffix = self.basket.id.replace('bas_', '')[-4:] if self.basket.id.startswith('bas_') else self.basket.id[-4:]
                sanitized_name = sanitize_basket_name(self.basket.name)
                expected_basket_path = f"{sanitized_name}_{basket_id_suffix}"
                
                if expected_basket_path not in existing_prefix:
                    # Prefix doesn't include basket path - don't use it
                    existing_prefix = None
        
        # Build full path using DocEXPathBuilder
        # Pass existing_prefix and storage_type to avoid duplication if storage_config already has basket path
        # This ensures all paths are built from IDs and are complete (no interpretation needed)
        full_path = self.path_builder.build_document_path(
            basket_id=self.basket.id,
            document_id=document.id,
            basket_name=self.basket.name,
            document_name=document_name,
            file_ext=file_ext,
            tenant_id=tenant_id,
            existing_prefix=existing_prefix,
            storage_type=storage_type  # Use basket's storage type
        )
        
        return full_path
    
    def parse_tenant_basket_name(self) -> tuple[str, str]:
        """
        Parse basket name to extract tenant_id and basket_name.

        Basket name format: {tenant_id}_{basket_name}
        Example: "test-tenant-003_resume_raw" -> ("test-tenant-003", "resume_raw")

        Returns:
            Tuple of (tenant_id, basket_name)
        """
        # Split on first underscore to separate tenant from basket
        parts = self.basket.name.split('_', 1)
        if len(parts) == 2:
            tenant_id, basket_name = parts
            return tenant_id, basket_name
        else:
            # Fallback if parsing fails
            logger.warning(f"Unable to parse tenant from basket name: {self.basket.name}")
            return "unknown_tenant", self.basket.name

