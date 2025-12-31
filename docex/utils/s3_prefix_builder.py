"""
Utility for building S3 prefixes with application name support.

This module provides functions to construct S3 prefixes following the pattern:
{application_name}/{tenant_id}/{document_type}_{stage}/

If application_name is not provided, uses: {tenant_id}/{document_type}_{stage}/
"""

from typing import Optional
import re


def sanitize_name(name: str, max_length: int = 100) -> str:
    """
    Sanitize a name for safe use in filenames and paths.

    Args:
        name: Name to sanitize
        max_length: Maximum allowed length

    Returns:
        Sanitized name safe for filesystem use
    """
    if not name:
        return "unnamed"

    # Replace spaces with underscores
    name = name.replace(' ', '_')

    # Remove/replace unsafe characters (keep alphanumeric, underscore, hyphen, dot)
    name = re.sub(r'[^\w\-_.]', '_', name)

    # Remove multiple consecutive underscores
    name = re.sub(r'_+', '_', name)

    # Remove leading/trailing underscores and dots
    name = name.strip('_.')

    # Ensure not empty after sanitization
    if not name:
        return "unnamed"

    # Limit length
    return name[:max_length] if len(name) > max_length else name


def sanitize_basket_name(basket_name: str) -> str:
    """
    Sanitize basket name for filesystem and database use.

    Basket names should be safe for:
    - Database storage
    - Filesystem directories
    - S3 keys
    - URL paths

    Args:
        basket_name: Raw basket name

    Returns:
        Sanitized basket name
    """
    return sanitize_name(basket_name, max_length=80)


def sanitize_filename(filename: str) -> str:
    """
    Sanitize filename for filesystem and S3 use.

    Args:
        filename: Raw filename (without extension)

    Returns:
        Sanitized filename safe for filesystem use
    """
    return sanitize_name(filename, max_length=80)


def validate_basket_name(basket_name: str) -> tuple[bool, str]:
    """
    Validate a basket name for safety and compliance.

    Args:
        basket_name: Basket name to validate

    Returns:
        Tuple of (is_valid, sanitized_name)
    """
    if not basket_name or not basket_name.strip():
        return False, "unnamed_basket"

    # Check length
    if len(basket_name) > 80:
        return False, sanitize_basket_name(basket_name)

    # Check for obviously problematic characters
    if re.search(r'[<>|:*?"\x00-\x1f]', basket_name):
        return False, sanitize_basket_name(basket_name)

    # Check if it would be changed by sanitization
    sanitized = sanitize_basket_name(basket_name)
    if sanitized != basket_name:
        return False, sanitized

    return True, basket_name


def validate_filename(filename: str) -> tuple[bool, str]:
    """
    Validate a filename for safety and compliance.

    Args:
        filename: Filename to validate (without extension)

    Returns:
        Tuple of (is_valid, sanitized_name)
    """
    if not filename or not filename.strip():
        return False, "unnamed_file"

    # Check length
    if len(filename) > 80:
        return False, sanitize_filename(filename)

    # Check if it would be changed by sanitization
    sanitized = sanitize_filename(filename)
    if sanitized != filename:
        return False, sanitized

    return True, filename


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
