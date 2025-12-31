"""
Utility for building S3 prefixes with application name support.

This module provides functions to construct S3 prefixes following the pattern:
{application_name}/{tenant_id}/{document_type}_{stage}/

If application_name is not provided, uses: {tenant_id}/{document_type}_{stage}/
"""

from typing import Optional


def build_s3_prefix(
    tenant_id: str,
    document_type: str,
    stage: str,
    application_name: Optional[str] = None
) -> str:
    """
    Build S3 prefix with optional application name.
    
    Args:
        tenant_id: Tenant identifier
        document_type: Document type (e.g., "invoice", "purchase_order")
        stage: Processing stage (e.g., "raw", "ready_to_pay")
        application_name: Optional application name (e.g., "llamasee-dp-dev")
        
    Returns:
        S3 prefix string with trailing slash
        
    Examples:
        >>> build_s3_prefix("test-tenant-001", "invoice", "raw")
        'tenant_test-tenant-001/invoice_raw/'
        
        >>> build_s3_prefix("test-tenant-001", "invoice", "raw", "llamasee-dp-dev")
        'llamasee-dp-dev/tenant_test-tenant-001/invoice_raw/'
    """
    if application_name:
        prefix = f"{application_name}/tenant_{tenant_id}/{document_type}_{stage}/"
    else:
        prefix = f"tenant_{tenant_id}/{document_type}_{stage}/"
    
    return prefix


def parse_basket_name(basket_name: str) -> tuple[str, str, str]:
    """
    Parse basket name to extract tenant_id, document_type, and stage.
    
    Basket name format: {tenant_id}_{document_type}_{stage}
    
    Args:
        basket_name: Basket name to parse
        
    Returns:
        Tuple of (tenant_id, document_type, stage)
        
    Examples:
        >>> parse_basket_name("test-tenant-001_invoice_raw")
        ('test-tenant-001', 'invoice', 'raw')
        
        >>> parse_basket_name("test-tenant-001_invoice_ready_to_pay")
        ('test-tenant-001', 'invoice', 'ready_to_pay')
    """
    parts = basket_name.split('_', 1)
    if len(parts) != 2:
        raise ValueError(
            f"Invalid basket name format: {basket_name}. "
            f"Expected: {{tenant_id}}_{{document_type}}_{{stage}}"
        )
    
    tenant_id = parts[0]
    rest = parts[1]
    
    # Find the last underscore to split document_type and stage
    # Handle cases like "invoice_ready_to_pay" where stage has underscores
    last_underscore = rest.rfind('_')
    if last_underscore > 0:
        document_type = rest[:last_underscore]
        stage = rest[last_underscore + 1:]
    else:
        # No underscore in rest, treat entire rest as document_type
        document_type = rest
        stage = ""
    
    return tenant_id, document_type, stage


def build_s3_prefix_from_basket_name(
    basket_name: str,
    application_name: Optional[str] = None
) -> str:
    """
    Build S3 prefix from basket name with optional application name.
    
    Args:
        basket_name: Basket name in format {tenant_id}_{document_type}_{stage}
        application_name: Optional application name
        
    Returns:
        S3 prefix string with trailing slash
        
    Examples:
        >>> build_s3_prefix_from_basket_name("test-tenant-001_invoice_raw")
        'tenant_test-tenant-001/invoice_raw/'
        
        >>> build_s3_prefix_from_basket_name(
        ...     "test-tenant-001_invoice_raw",
        ...     "llamasee-dp-dev"
        ... )
        'llamasee-dp-dev/tenant_test-tenant-001/invoice_raw/'
    """
    tenant_id, document_type, stage = parse_basket_name(basket_name)
    return build_s3_prefix(tenant_id, document_type, stage, application_name)
