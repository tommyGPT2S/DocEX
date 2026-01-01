# Installing Dependencies for DocEX 3.0 Testing

## Required Packages

Both `boto3` and `moto` are required for testing S3 storage functionality:

- **boto3**: AWS SDK for Python (for S3 storage)
- **moto**: Mock AWS services for testing

## Installation

### Option 1: Install from requirements.txt

```bash
# Activate your virtual environment
source venv/bin/activate

# Install all dependencies
pip install -r requirements.txt
```

### Option 2: Install only boto3 and moto

```bash
# Activate your virtual environment
source venv/bin/activate

# Install boto3 and moto
pip install boto3>=1.26.0 moto>=4.0.0
```

### Option 3: Verify Installation

```bash
# Activate your virtual environment
source venv/bin/activate

# Check if installed
python3 -c "import boto3; print('boto3 version:', boto3.__version__)"
python3 -c "import moto; print('moto version:', moto.__version__)"
```

## Current Status

Both packages are already listed in `requirements.txt`:
- `boto3>=1.26.0`
- `moto>=4.0.0`

## After Installation

Once installed, you can run the test suite:

```bash
# Run simple tests
python3 test_docex3_simple.py

# Run full test suite (when available)
pytest tests/test_docex3_multitenancy.py -v
```

## Testing S3 Storage

With `moto` installed, you can test S3 storage without actual AWS credentials:

```python
from moto import mock_s3
import boto3

@mock_s3
def test_s3_storage():
    # Create mock S3 bucket
    s3 = boto3.client('s3', region_name='us-east-1')
    s3.create_bucket(Bucket='test-bucket')
    
    # Test S3 storage
    from docex.storage.s3_storage import S3Storage
    storage = S3Storage({
        'bucket': 'test-bucket',
        'region': 'us-east-1'
    })
    
    # Test operations
    storage.save('test.txt', b'Hello World')
    content = storage.load('test.txt')
    assert content == b'Hello World'
```

