# Testing ID-Centric Operations

## Quick Test

Run the test script in your virtual environment:

```bash
# Activate venv
source venv/bin/activate

# Run the test
python test_id_centric_operations.py
```

## What the Test Verifies

1. **DocEXPathBuilder** - Builds full paths from `basket_id` and `document_id`
2. **S3Storage** - Accepts full paths without interpretation
3. **Filesystem paths** - Works correctly with ID-based path building
4. **Path resolver relationship** - DocEXPathBuilder uses DocEXPathResolver correctly

## Expected Output

```
============================================================
ID-Centric Operations Test Suite
============================================================
============================================================
TEST 1: DocEXPathBuilder - Building paths from IDs
============================================================
✅ Built full path from IDs: acme-corp/production/acme/invoices_a1b2/invoice_001_c3d4e5.pdf
✅ Path structure is correct

============================================================
TEST 2: S3Storage - Accepts full paths (no interpretation)
============================================================
✅ Saved to full path: acme-corp/production/acme/invoices_a1b2/invoice_001_c3d4e5.pdf
✅ Retrieved from exact path: acme-corp/production/acme/invoices_a1b2/invoice_001_c3d4e5.pdf
✅ Path exists check passed
✅ Loaded content matches
✅ Delete operation succeeded
✅ Path correctly deleted

============================================================
TEST 3: DocEXPathBuilder - Filesystem paths
============================================================
✅ Built filesystem path from IDs: storage/test-org/acme/invoices_a1b2/invoice_001_c3d4e5.pdf
✅ Filesystem path structure is correct

============================================================
TEST 4: DocEXPathBuilder uses DocEXPathResolver
============================================================
✅ DocEXPathBuilder has path_resolver
✅ Resolved tenant prefix: acme-corp/production/acme/

============================================================
✅ ALL TESTS PASSED
============================================================
```

## Integration Test

You can also test with a real DocBasket operation:

```python
from docex import DocEX
from docex.context import UserContext
from pathlib import Path
import tempfile

# Setup
user_context = UserContext(user_id="test_user", tenant_id="acme")
docex = DocEX(user_context=user_context)

# Create basket (returns basket_id)
basket = docex.create_basket("test_basket", "Test basket")

# Add document (returns document_id)
with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
    f.write("Test content")
    temp_path = Path(f.name)

doc = basket.add(str(temp_path))
document_id = doc.id

# Get document by document_id
retrieved_doc = basket.get_document(document_id)
print(f"Retrieved document: {retrieved_doc.id}")

# Delete document by document_id
basket.delete_document(document_id)
print(f"Deleted document: {document_id}")

# All operations centered around IDs!
```

## Key Points Verified

✅ **Users work with IDs only**: `basket_id` and `document_id`  
✅ **Paths built internally**: `DocEXPathBuilder` builds full paths from IDs  
✅ **S3Storage accepts full paths**: No prefix interpretation  
✅ **Consistent path structure**: All paths follow the same pattern  

