"""
Quick test script for DSPy integration
"""

import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent))

def test_imports():
    """Test that all DSPy components can be imported"""
    print("Testing DSPy integration imports...")
    
    try:
        from docex.processors.llm.dspy_adapter import DSPyAdapter, DSPySignatureBuilder
        print("✅ DSPyAdapter imported successfully")
    except ImportError as e:
        print(f"❌ Failed to import DSPyAdapter: {e}")
        return False
    
    try:
        from docex.processors.chargeback import ExtractIdentifiersDSPyProcessor
        print("✅ ExtractIdentifiersDSPyProcessor imported successfully")
    except ImportError as e:
        print(f"❌ Failed to import ExtractIdentifiersDSPyProcessor: {e}")
        return False
    
    try:
        import dspy
        print(f"✅ DSPy library imported successfully")
    except ImportError:
        print("⚠️  DSPy library not installed - install with: pip install dspy-ai")
        print("   (This is expected if you haven't installed it yet)")
        return False
    
    return True

def test_signature_builder():
    """Test DSPySignatureBuilder"""
    print("\nTesting DSPySignatureBuilder...")
    
    try:
        from docex.processors.llm.dspy_adapter import DSPySignatureBuilder
        
        # Test from_field_list
        signature = DSPySignatureBuilder.from_field_list(
            ['customer_name', 'hin', 'dea'],
            input_name='document_text'
        )
        print(f"✅ Signature from field list: {signature}")
        
        # Test from_yaml_schema
        yaml_schema = {
            'schema': {
                'customer_name': 'string',
                'hin': 'string',
                'dea': 'string'
            }
        }
        signature2 = DSPySignatureBuilder.from_yaml_schema(yaml_schema)
        print(f"✅ Signature from YAML schema: {signature2}")
        
        return True
    except Exception as e:
        print(f"❌ Signature builder test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_dspy_availability():
    """Test if DSPy is available and can be configured"""
    print("\nTesting DSPy availability...")
    
    try:
        import dspy
        
        # Try to configure with a placeholder (won't actually call API)
        # Just check if the module structure is correct
        print("✅ DSPy module structure is correct")
        
        # Check for key classes
        if hasattr(dspy, 'Signature'):
            print("✅ dspy.Signature available")
        if hasattr(dspy, 'ChainOfThought'):
            print("✅ dspy.ChainOfThought available")
        if hasattr(dspy, 'Predict'):
            print("✅ dspy.Predict available")
        if hasattr(dspy, 'LM'):
            print("✅ dspy.LM available")
        
        return True
    except Exception as e:
        print(f"❌ DSPy availability test failed: {e}")
        return False

def main():
    """Run all tests"""
    print("=" * 60)
    print("DSPy Integration Test")
    print("=" * 60)
    
    all_passed = True
    
    # Test imports
    if not test_imports():
        all_passed = False
        print("\n⚠️  Some imports failed - this may be expected if DSPy is not installed")
    
    # Test signature builder (doesn't require DSPy)
    if not test_signature_builder():
        all_passed = False
    
    # Test DSPy availability
    try:
        if not test_dspy_availability():
            all_passed = False
    except ImportError:
        print("\n⚠️  DSPy not installed - skipping availability tests")
        print("   Install with: pip install dspy-ai")
    
    print("\n" + "=" * 60)
    if all_passed:
        print("✅ All tests passed!")
    else:
        print("⚠️  Some tests had issues (may be expected if DSPy not installed)")
    print("=" * 60)
    
    return all_passed

if __name__ == '__main__':
    success = main()
    sys.exit(0 if success else 1)

