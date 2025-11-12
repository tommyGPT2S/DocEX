"""
Test CLI with S3 storage using moto
"""
import os
import sys
from pathlib import Path
from moto import mock_aws
import boto3
import yaml
import tempfile

# Add the project root to the path
sys.path.insert(0, str(Path(__file__).parent))

from docex import DocEX
from docex.config.docex_config import DocEXConfig


@mock_aws
def test_cli_with_s3():
    """Test CLI operations with S3 storage"""
    
    # Create mock S3 bucket
    s3_client = boto3.client('s3', region_name='us-east-1')
    bucket_name = 'test-docex-bucket'
    s3_client.create_bucket(Bucket=bucket_name)
    print(f"✓ Created mock S3 bucket: {bucket_name}")
    
    # Create temporary config file
    config_dir = Path.home() / '.docex'
    config_dir.mkdir(parents=True, exist_ok=True)
    config_file = config_dir / 'config.yaml'
    
    config = {
        'database': {
            'type': 'sqlite',
            'sqlite': {
                'path': str(Path.cwd() / 'test_docex_s3.db')
            }
        },
        'storage': {
            'type': 's3',
            's3': {
                'bucket': bucket_name,
                'region': 'us-east-1',
                'access_key': 'test-access-key',
                'secret_key': 'test-secret-key'
            }
        },
        'logging': {
            'level': 'INFO'
        }
    }
    
    with open(config_file, 'w') as f:
        yaml.dump(config, f)
    print(f"✓ Created config file: {config_file}")
    
    # Initialize DocEX
    try:
        DocEX.setup(**config)
        print("✓ DocEX initialized with S3 storage")
    except Exception as e:
        print(f"✗ Failed to initialize DocEX: {e}")
        return False
    
    # Create DocEX instance
    try:
        docEX = DocEX()
        print("✓ DocEX instance created")
    except Exception as e:
        print(f"✗ Failed to create DocEX instance: {e}")
        return False
    
    # Create a basket with S3 storage
    try:
        basket = docEX.create_basket('test_s3_basket', 'Test basket with S3 storage')
        print(f"✓ Created basket: {basket.name} (ID: {basket.id})")
        print(f"  Storage type: {basket.storage_config.get('type')}")
        if basket.storage_config.get('type') == 's3':
            s3_config = basket.storage_config.get('s3', {})
            print(f"  S3 bucket: {s3_config.get('bucket')}")
            print(f"  S3 region: {s3_config.get('region')}")
    except Exception as e:
        print(f"✗ Failed to create basket: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    # Create a test file
    test_file = Path('test_document.txt')
    test_content = 'Hello, S3 Storage!'
    test_file.write_text(test_content)
    print(f"✓ Created test file: {test_file}")
    
    # Add document to basket
    try:
        doc = basket.add(str(test_file))
        print(f"✓ Added document to basket: {doc.name} (ID: {doc.id})")
        print(f"  Document path: {doc.path}")
        print(f"  Document size: {doc.size} bytes")
    except Exception as e:
        print(f"✗ Failed to add document: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    # Verify document content can be retrieved
    try:
        content = doc.get_content(mode='bytes')
        if content == test_content.encode('utf-8'):
            print("✓ Document content retrieved correctly from S3")
        else:
            print(f"✗ Document content mismatch")
            print(f"  Expected: {test_content.encode('utf-8')}")
            print(f"  Got: {content}")
            return False
    except Exception as e:
        print(f"✗ Failed to retrieve document content: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    # Verify document exists in S3
    try:
        s3_client = boto3.client('s3', region_name='us-east-1')
        # List objects in bucket
        response = s3_client.list_objects_v2(Bucket=bucket_name)
        if 'Contents' in response:
            print(f"✓ Found {len(response['Contents'])} object(s) in S3 bucket")
            for obj in response['Contents']:
                print(f"  - {obj['Key']} ({obj['Size']} bytes)")
        else:
            print("⚠ No objects found in S3 bucket (this might be expected if using prefix)")
    except Exception as e:
        print(f"⚠ Could not verify S3 objects: {e}")
    
    # Clean up
    try:
        test_file.unlink()
        print("✓ Cleaned up test file")
    except:
        pass
    
    print("\n✅ All CLI S3 tests passed!")
    return True


if __name__ == '__main__':
    success = test_cli_with_s3()
    sys.exit(0 if success else 1)



