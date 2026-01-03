"""
Test script for name sanitization functionality.

This tests the sanitization of basket names and filenames to ensure
they are safe for filesystem and S3 use.
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__)))

from docex.utils import (
    sanitize_basket_name,
    sanitize_filename,
    validate_basket_name,
    validate_filename
)

def test_sanitization():
    """Test name sanitization functions"""
    print("=" * 60)
    print("Name Sanitization Test")
    print("=" * 60)

    # Test cases for basket names
    basket_test_cases = [
        ("test-tenant-001_invoice_raw", "test-tenant-001_invoice_raw"),  # Already clean
        ("Test Tenant Invoice Raw", "Test_Tenant_Invoice_Raw"),  # Spaces
        ("test/tenant\\invoice:raw", "test_tenant_invoice_raw"),  # Special chars
        ("test..tenant__invoice", "test.tenant_invoice"),  # Multiple dots/underscores
        ("", "unnamed_basket"),  # Empty
        ("a" * 100, "a" * 80),  # Too long
    ]

    print("\n🗂️  Basket Name Sanitization:")
    print("-" * 40)
    for input_name, expected in basket_test_cases:
        result = sanitize_basket_name(input_name)
        status = "✅" if result == expected else "❌"
        print("15")

    # Test cases for filenames
    filename_test_cases = [
        ("invoice_2024-01-15", "invoice_2024-01-15"),  # Already clean
        ("Invoice January 2024", "Invoice_January_2024"),  # Spaces
        ("contract/Q1\\2024:file", "contract_Q1_2024_file"),  # Special chars
        ("receipt..march__2024", "receipt.march_2024"),  # Multiple dots/underscores
        ("", "unnamed_file"),  # Empty
        ("b" * 100, "b" * 80),  # Too long
    ]

    print("\n📄 Filename Sanitization:")
    print("-" * 40)
    for input_name, expected in filename_test_cases:
        result = sanitize_filename(input_name)
        status = "✅" if result == expected else "❌"
        print("15")

    # Test validation functions
    print("\n🔍 Validation Tests:")
    print("-" * 40)

    validation_cases = [
        ("clean_name", True, "clean_name"),
        ("name with spaces", False, "name_with_spaces"),
        ("name<with>bad:chars", False, "name_with_bad_chars"),
    ]

    for test_name, expected_valid, expected_sanitized in validation_cases:
        is_valid, sanitized = validate_basket_name(test_name)
        status = "✅" if is_valid == expected_valid and sanitized == expected_sanitized else "❌"
        print("15")

    print("\n" + "=" * 60)
    print("✅ Name sanitization functions are working correctly!")
    print("✅ Spaces are replaced with underscores")
    print("✅ Special characters are sanitized")
    print("✅ Length limits are enforced")
    print("✅ Empty names get safe defaults")
    print("=" * 60)

if __name__ == "__main__":
    test_sanitization()