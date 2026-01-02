"""
Path Builder for DocEX Storage

This module provides a centralized class for building full storage paths
from basket_id and document_id. All path interpretation and building logic
is centralized here, ensuring S3Storage and other storage backends receive
fully resolved paths without needing to interpret them.

User operations center around basket_id and document_id - paths are internal
implementation details handled by this class.
"""

import logging
from typing import Optional, Dict, Any
from pathlib import Path

from docex.config.path_resolver import DocEXPathResolver
from docex.config.docex_config import DocEXConfig

logger = logging.getLogger(__name__)


class DocEXPathBuilder:
    """
    Centralized path builder for DocEX storage operations.
    
    This class is responsible for building full storage paths from basket_id
    and document_id. All path building logic is centralized here to ensure:
    1. S3Storage receives full paths (no interpretation needed)
    2. Path structure is consistent across all storage backends
    3. Users only work with basket_id and document_id (paths are internal)
    
    Usage:
        builder = DocEXPathBuilder()
        full_path = builder.build_document_path(
            basket_id="bas_123",
            document_id="doc_456",
            basket_name="invoices",
            document_name="invoice_001",
            file_ext=".pdf",
            tenant_id="acme"
        )
        # Returns: "acme-corp/production/acme/invoices_a1b2/invoice_001_c3d4e5.pdf"
    """
    
    def __init__(self, config: Optional[DocEXConfig] = None):
        """
        Initialize path builder.
        
        Args:
            config: Optional DocEXConfig instance (defaults to singleton)
        """
        self.config = config or DocEXConfig()
        self.path_resolver = DocEXPathResolver(self.config)
    
    def build_basket_path(
        self, 
        basket_id: str, 
        basket_name: str, 
        tenant_id: Optional[str] = None,
        existing_prefix: Optional[str] = None,
        storage_type: Optional[str] = None
    ) -> str:
        """
        Build storage path for a basket.
        
        For S3: Returns full S3 key prefix including tenant, namespace, and basket
        For filesystem: Returns RELATIVE path (relative to base_path) - FileSystemStorage will combine with base_path
        
        Args:
            basket_id: Basket ID (e.g., "bas_1234567890abcdef")
            basket_name: Basket friendly name (e.g., "invoices")
            tenant_id: Optional tenant ID (required for multi-tenant)
            existing_prefix: Optional existing prefix from storage_config (avoids duplication)
                            If provided and contains basket path, use it instead of building from scratch
            storage_type: Optional storage type override (e.g., 's3', 'filesystem')
                          If not provided, uses config's storage type
            
        Returns:
            Basket path:
            - S3: Full prefix (e.g., "acme_corp/finance_dept/test-env/invoices_a1b2")
            - Filesystem: Relative path (e.g., "acme_corp/invoices_a1b2") - relative to base_path
        """
        if storage_type is None:
            storage_type = self.config.get('storage', {}).get('type', 'filesystem')
        
        if storage_type == 's3':
            if not tenant_id:
                raise ValueError("tenant_id is required for S3 basket path building")
            
            # Check if existing_prefix already contains the basket path
            if existing_prefix:
                from docex.utils.s3_prefix_builder import sanitize_basket_name
                basket_id_suffix = basket_id.replace('bas_', '')[-4:] if basket_id.startswith('bas_') else basket_id[-4:]
                sanitized_name = sanitize_basket_name(basket_name)
                expected_basket_path = f"{sanitized_name}_{basket_id_suffix}"
                
                # If existing prefix contains the basket path, use it
                if expected_basket_path in existing_prefix:
                    logger.debug(f"Using existing prefix with basket path: {existing_prefix}")
                    return existing_prefix.rstrip('/')
            
            # Build full S3 prefix from scratch: {tenant_id}/{path_namespace}/{prefix}/{basket_friendly_name}_{last_4}/
            basket_prefix = self.path_resolver.resolve_s3_basket_prefix(
                tenant_id=tenant_id,
                basket_id=basket_id,
                basket_name=basket_name
            )
            return basket_prefix.rstrip('/')  # Return without trailing slash for consistency
        else:
            # Filesystem storage
            # Return RELATIVE path (relative to base_path) for FileSystemStorage
            # FileSystemStorage expects relative paths and will combine with base_path
            if tenant_id:
                # Build: {tenant_id}/{basket_friendly_name}_{last_4}/
                from docex.utils.s3_prefix_builder import sanitize_basket_name
                basket_id_suffix = basket_id.replace('bas_', '')[-4:] if basket_id.startswith('bas_') else basket_id[-4:]
                friendly_name = sanitize_basket_name(basket_name)
                basket_path_segment = f"{friendly_name}_{basket_id_suffix}"
                # Return relative path: tenant_id/basket_path_segment
                return f"{tenant_id}/{basket_path_segment}"
            else:
                # Non-multi-tenant: {basket_id}/
                return basket_id
    
    def build_document_path(
        self,
        basket_id: str,
        document_id: str,
        basket_name: str,
        document_name: str,
        file_ext: str = '',
        tenant_id: Optional[str] = None,
        existing_prefix: Optional[str] = None,
        storage_type: Optional[str] = None
    ) -> str:
        """
        Build storage path for a document using three-part S3 path structure.
        
        Three-Part Structure:
        - Part A: Config prefix (tenant_id, path_namespace, prefix) - from configuration
        - Part B: Basket path (basket_friendly_name + last_4_of_basket_id) - basket-specific
        - Part C: Document path (document_friendly_name + last_6_of_document_id + ext) - document-specific
        
        Full path = Part A + Part B + Part C
        
        This method constructs the complete path including all three parts.
        If existing_prefix is provided and contains Part A + Part B, it uses that directly.
        
        Args:
            basket_id: Basket ID (e.g., "bas_1234567890abcdef")
            document_id: Document ID (e.g., "doc_9876543210fedcba")
            basket_name: Basket friendly name (e.g., "invoices")
            document_name: Document friendly name (e.g., "invoice_001")
            file_ext: File extension (e.g., ".pdf")
            tenant_id: Optional tenant ID (required for multi-tenant)
            existing_prefix: Optional existing prefix from storage_config (Part A + Part B)
                            If provided and contains basket path, use it instead of building from scratch
            storage_type: Optional storage type override (e.g., 's3', 'filesystem')
                          If not provided, uses config's storage type
            
        Returns:
            Document path:
            - S3: Full S3 key (Part A + Part B + Part C)
                  Example: "acme_corp/finance_dept/production/invoice_raw_2c03/invoice_001_585d29.pdf"
            - Filesystem: Relative path (Part B + Part C) - relative to base_path
                  Example: "acme_corp/invoice_raw_2c03/invoice_001_585d29.pdf"
        """
        if storage_type is None:
            storage_type = self.config.get('storage', {}).get('type', 'filesystem')
        
        # For S3, if existing_prefix is provided and contains the basket path, use it directly
        # This avoids rebuilding the path and prevents duplication
        if storage_type == 's3' and existing_prefix:
            # Check if existing_prefix already contains the basket path
            from docex.utils.s3_prefix_builder import sanitize_basket_name
            basket_id_suffix = basket_id.replace('bas_', '')[-4:] if basket_id.startswith('bas_') else basket_id[-4:]
            sanitized_name = sanitize_basket_name(basket_name)
            expected_basket_path = f"{sanitized_name}_{basket_id_suffix}"
            
            # If existing_prefix contains the basket path, use it directly
            # existing_prefix format: {tenant_id}/{path_namespace}/{prefix}/{basket_friendly_name}_{last_4}
            if expected_basket_path in existing_prefix:
                # Build document filename: {friendly_name}_{last_6_of_doc_id}.{ext}
                doc_id_suffix = document_id.replace('doc_', '')[-6:] if document_id.startswith('doc_') else document_id[-6:]
                document_filename = f"{document_name}_{doc_id_suffix}{file_ext}"
                # Use existing_prefix directly (it already includes tenant_id, path_namespace, prefix, and basket path)
                # No need to rebuild - just append document filename
                return f"{existing_prefix.rstrip('/')}/{document_filename}"
        
        # Build basket path first (pass existing_prefix and storage_type to avoid duplication)
        basket_path = self.build_basket_path(basket_id, basket_name, tenant_id, existing_prefix, storage_type)
        
        # Build document filename: {friendly_name}_{last_6_of_doc_id}.{ext}
        doc_id_suffix = document_id.replace('doc_', '')[-6:] if document_id.startswith('doc_') else document_id[-6:]
        document_filename = f"{document_name}_{doc_id_suffix}{file_ext}"
        
        if storage_type == 's3':
            # For S3, combine basket prefix with document filename
            # basket_path is already the full prefix (e.g., "acme_corp/finance_dept/production/invoices_a1b2")
            return f"{basket_path}/{document_filename}"
        else:
            # For filesystem, combine basket directory with document filename
            # basket_path is already relative (e.g., "acme_corp/invoices_a1b2")
            # Return relative path: basket_path/document_filename
            return f"{basket_path}/{document_filename}"
    
    def parse_path_to_ids(self, full_path: str, storage_type: Optional[str] = None) -> Dict[str, Optional[str]]:
        """
        Parse a full storage path back to basket_id and document_id.
        
        This is used internally by DocEX to retrieve documents by path.
        Users should never need to call this - they work with IDs only.
        
        Args:
            full_path: Full storage path
            storage_type: Optional storage type (defaults to config)
            
        Returns:
            Dictionary with 'basket_id', 'document_id', 'tenant_id' if parseable
        """
        if storage_type is None:
            storage_type = self.config.get('storage', {}).get('type', 'filesystem')
        
        # This is a reverse operation - extract IDs from path
        # Implementation depends on path structure
        # For now, return None for all - this should be implemented based on
        # the actual path structure used
        logger.warning("parse_path_to_ids not yet implemented - paths should be stored in DB metadata")
        return {
            'basket_id': None,
            'document_id': None,
            'tenant_id': None
        }

