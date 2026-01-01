"""
Helper functions for creating tenant-aware baskets with application name support.

This module provides utilities for creating baskets with proper S3 path structure:
{application_name}/{tenant_id}/{document_type}_{stage}/documents/{document_id}.{ext}
"""

from typing import Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from docex import DocEX
    from docex.docbasket import DocBasket

from docex.config.docex_config import DocEXConfig
from .s3_prefix_builder import build_s3_prefix, parse_basket_name


def create_tenant_basket(
    docEX: "DocEX",
    document_type: str,
    stage: str,
    description: Optional[str] = None,
    bucket: Optional[str] = None,
    region: Optional[str] = None,
    path_namespace: Optional[str] = None
) -> "DocBasket":
    """
    Create a tenant-aware basket with proper S3 path structure.
    
    Basket naming: {tenant_id}_{document_type}_{stage}
    S3 Path: {tenant_id}/{path_namespace}/{prefix}/{basket_friendly_name}_{last_4_of_basket_id}/
    
    Tenant ID is FIRST in the path for better tenant isolation.
    
    Args:
        docEX: DocEX instance with user_context containing tenant_id
        document_type: Type of document (e.g., "invoice", "purchase_order")
        stage: Processing stage (e.g., "raw", "ready_to_pay")
        description: Optional basket description
        bucket: Optional S3 bucket name (defaults to config)
        region: Optional AWS region (defaults to config)
        path_namespace: Optional path namespace (defaults to config.path_namespace, can override)
        
    Returns:
        Created DocBasket instance
        
    Example:
        basket = create_tenant_basket(docEX, "invoice", "raw")
        # Creates basket: "test-tenant-001_invoice_raw"
        # S3 prefix: "test-tenant-001/acme-corp/production/invoice_raw/" (if path_namespace and prefix set)
        # S3 prefix: "test-tenant-001/acme-corp/invoice_raw/" (if only path_namespace set)
        # S3 prefix: "test-tenant-001/invoice_raw/" (if neither set)
        # Note: Actual basket path will be: {friendly_name}_{last_4_of_basket_id}/
    """
    if not docEX.user_context or not docEX.user_context.tenant_id:
        raise ValueError("DocEX instance must have user_context with tenant_id")
    
    tenant_id = docEX.user_context.tenant_id
    basket_name = f"{tenant_id}_{document_type}_{stage}"
    
    if description is None:
        description = f"{document_type} documents in {stage} stage"
    
    # Get configuration
    config = DocEXConfig()
    
    # Get path_namespace from parameter, config, or None
    if path_namespace is None:
        path_namespace = config.get('storage.s3.path_namespace')
        # Convert empty string to None
        if path_namespace == '':
            path_namespace = None
    
    # Get bucket and region from config if not provided
    if bucket is None:
        bucket = config.get('storage.s3.bucket')
    if region is None:
        region = config.get('storage.s3.region', 'us-east-1')
    
    if not bucket:
        raise ValueError(
            "S3 bucket must be specified either in storage_config or config.yaml"
        )
    
    # Build S3 prefix with path namespace
    prefix = build_s3_prefix(tenant_id, document_type, stage, path_namespace)
    
    # Create basket with tenant-aware S3 prefix
    basket = docEX.create_basket(
        basket_name,
        description=description,
        storage_config={
            'type': 's3',
            's3': {
                'bucket': bucket,
                'region': region,
                'prefix': prefix
            }
        }
    )
    
    return basket


def get_path_namespace_from_config() -> Optional[str]:
    """
    Get path namespace from DocEX configuration.
    
    Returns:
        Path namespace if configured, None otherwise
    """
    config = DocEXConfig()
    path_namespace = config.get('storage.s3.path_namespace')
    return path_namespace if path_namespace else None
