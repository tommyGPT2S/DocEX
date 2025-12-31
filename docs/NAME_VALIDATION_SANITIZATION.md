# Name Validation and Sanitization

## Overview

DocEX now includes automatic validation and sanitization of basket names and filenames to ensure they are safe for filesystem and S3 storage. This prevents issues with special characters, spaces, and other problematic characters.

## 🎯 Key Features

- **Automatic Sanitization**: Names are automatically cleaned during basket and document creation
- **Filesystem Safe**: All names are compatible with filesystems and S3
- **Validation Functions**: Check names before creation
- **Configurable**: Customize sanitization rules if needed

## 📋 Sanitization Rules

### Characters Replaced/Removed
- **Spaces** → `_` (underscores)
- **Special Characters** → `_` (e.g., `< > : " | ? *`)
- **Multiple Underscores** → Single `_`
- **Leading/Trailing** → Removed (underscores and dots)

### Length Limits
- **Basket Names**: 80 characters maximum
- **Filenames**: 80 characters maximum
- **Fallback Names**: Used for empty/invalid names

### Safe Character Set
- Alphanumeric: `A-Z a-z 0-9`
- Underscore: `_`
- Hyphen: `-`
- Dot: `.` (for filenames)

## 🔧 Usage Examples

### Basket Name Sanitization

```python
from docex.utils import sanitize_basket_name

# Examples of sanitization
sanitize_basket_name("Test Basket With Spaces")      # → "Test_Basket_With_Spaces"
sanitize_basket_name("basket:with<special>chars")    # → "basket_with_special_chars"
sanitize_basket_name("normal_basket_name")           # → "normal_basket_name" (unchanged)
sanitize_basket_name("")                             # → "unnamed_basket"
```

### Filename Sanitization

```python
from docex.utils import sanitize_filename

# Examples of sanitization
sanitize_filename("Invoice January 2024")            # → "Invoice_January_2024"
sanitize_filename("contract:Q1|2024")                # → "contract_Q1_2024"
sanitize_filename("receipt march 2024")              # → "receipt_march_2024"
```

### Validation Functions

```python
from docex.utils import validate_basket_name, validate_filename

# Check if names are valid (will be auto-sanitized if not)
is_valid, sanitized = validate_basket_name("My Basket Name")
# is_valid: False, sanitized: "My_Basket_Name"

is_valid, sanitized = validate_basket_name("my_clean_basket")
# is_valid: True, sanitized: "my_clean_basket"
```

## 🔄 Automatic Application

### Basket Creation

Basket names are automatically sanitized when created:

```python
# This basket name will be sanitized
docEX.create_basket("Test Basket With Spaces")  # → "Test_Basket_With_Spaces"
```

**Log Output:**
```
INFO: Basket name sanitized: 'Test Basket With Spaces' -> 'Test_Basket_With_Spaces'
```

### Document Storage

Document filenames are automatically sanitized:

```python
# File: "Invoice January 2024.pdf"
basket.add("Invoice January 2024.pdf")
# Stored as: "Invoice_January_2024__doc_abc123.pdf"
```

## 📁 S3 Path Examples

### Before Sanitization
```
s3://bucket/llamasee-dp-dev/tenant_test-001/Test Basket With Spaces/documents/Invoice January 2024__doc_abc123.pdf
```
❌ **Problems**: Spaces in basket name and filename

### After Sanitization
```
s3://bucket/llamasee-dp-dev/tenant_test-001/Test_Basket_With_Spaces/documents/Invoice_January_2024__doc_abc123.pdf
```
✅ **Safe**: All characters are filesystem-compatible

## 🛡️ Security Benefits

### Prevents Issues With:
- **Filesystem Operations**: No invalid characters for OS operations
- **S3 Keys**: Safe for AWS S3 object keys
- **URLs**: Safe for web-based access
- **Database Storage**: Safe for metadata storage

### Protection Against:
- **Directory Traversal**: Special characters removed
- **Command Injection**: Sanitized input
- **Path Manipulation**: Controlled character set

## ⚙️ Configuration

### Default Behavior
- **Automatic**: Sanitization happens automatically
- **Logging**: Changes are logged for visibility
- **Backward Compatible**: Existing valid names unchanged

### Custom Sanitization (Advanced)

You can create custom sanitization rules:

```python
from docex.utils.s3_prefix_builder import sanitize_name

# Custom sanitization with different rules
def custom_sanitize(name: str) -> str:
    # Your custom logic here
    return sanitize_name(name).upper()  # Example: force uppercase

# Use in custom document processing
custom_name = custom_sanitize("my document name")
```

## 🧪 Testing

### Run Sanitization Tests

```bash
python test_name_sanitization.py
```

### Test Basket Creation

```python
# Test automatic sanitization
basket = docEX.create_basket("Test Basket With Spaces")
print(basket.name)  # → "Test_Basket_With_Spaces"
```

## 📊 Test Results

```
Basket Name Sanitization Examples:
  "Test Basket With Spaces" -> "Test_Basket_With_Spaces" ⚠️  Sanitized
  "basket:with<special>chars" -> "basket_with_special_chars" ⚠️  Sanitized
  "normal_basket_name" -> "normal_basket_name" ✅ Valid
  "basket with /slashes\\and\\backslashes" -> "basket_with_slashes_nd_ackslashes" ⚠️  Sanitized
  "" -> "unnamed" ⚠️  Sanitized to: unnamed_basket

Filename Sanitization Examples:
  "Invoice January 2024" -> "Invoice_January_2024"
  "contract:Q1|2024" -> "contract_Q1_2024"
  "receipt_march_2024" -> "receipt_march_2024"
  "file with spaces and symbols @#$%" -> "file_with_spaces_and_symbols"
```

## 🚀 Benefits Summary

✅ **Automatic**: No manual intervention required
✅ **Safe**: Prevents filesystem and S3 issues
✅ **Consistent**: Standardized naming across the system
✅ **Logged**: Changes are visible in logs
✅ **Configurable**: Can be customized if needed
✅ **Backward Compatible**: Existing valid names work unchanged

## 🔗 Related Documentation

- `S3_READABLE_PATHS_DESIGN.md` - Document path structure
- `S3_TENANT_CONFIGURATION_GUIDE.md` - Tenant configuration
- `S3_BUCKET_NAMING_RECOMMENDATIONS.md` - Bucket naming best practices
