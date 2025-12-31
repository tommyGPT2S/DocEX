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
    application_name: Optional[str] = None
) -> "DocBasket":
    """
    Create a tenant-aware basket with proper S3 path structure.
    
    Basket naming: {tenant_id}_{document_type}_{stage}
    S3 Path: {application_name}/tenant_{tenant_id}/{document_type}_{stage}/
    
    Args:
        docEX: DocEX instance with user_context containing tenant_id
        document_type: Type of document (e.g., "invoice", "purchase_order")
        stage: Processing stage (e.g., "raw", "ready_to_pay")
        description: Optional basket description
        bucket: Optional S3 bucket name (defaults to config)
        region: Optional AWS region (defaults to config)
        application_name: Optional application name (defaults to config, can override)
        
    Returns:
        Created DocBasket instance
        
    Example:
        basket = create_tenant_basket(docEX, "invoice", "raw")
        # Creates basket: "test-tenant-001_invoice_raw"
        # S3 prefix: "llamasee-dp-dev/tenant_test-tenant-001/invoice_raw/" (if app_name set)
        # S3 prefix: "tenant_test-tenant-001/invoice_raw/" (if app_name not set)
    """
    if not docEX.user_context or not docEX.user_context.tenant_id:
        raise ValueError("DocEX instance must have user_context with tenant_id")
    
    tenant_id = docEX.user_context.tenant_id
    basket_name = f"{tenant_id}_{document_type}_{stage}"
    
    if description is None:
        description = f"{document_type} documents in {stage} stage"
    
    # Get configuration
    config = DocEXConfig()
    
    # Get application_name from parameter, config, or None
    if application_name is None:
        application_name = config.get('storage.s3.application_name')
        # Convert empty string to None
        if application_name == '':
            application_name = None
    
    # Get bucket and region from config if not provided
    if bucket is None:
        bucket = config.get('storage.s3.bucket')
    if region is None:
        region = config.get('storage.s3.region', 'us-east-1')
    
    if not bucket:
        raise ValueError(
            "S3 bucket must be specified either in storage_config or config.yaml"
        )
    
    # Build S3 prefix with application name
    prefix = build_s3_prefix(tenant_id, document_type, stage, application_name)
    
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


def get_application_name_from_config() -> Optional[str]:
    """
    Get application name from DocEX configuration.
    
    Returns:
        Application name if configured, None otherwise
    """
    config = DocEXConfig()
    app_name = config.get('storage.s3.application_name')
    return app_name if app_name else None
