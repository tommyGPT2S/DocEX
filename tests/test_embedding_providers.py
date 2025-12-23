"""
Test Embedding Providers

Simple script to test which embedding providers are available
"""

import os
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def test_openai():
    """Test OpenAI embedding availability"""
    try:
        import openai
        if os.getenv('OPENAI_API_KEY'):
            client = openai.OpenAI()
            # Test a simple embedding
            response = client.embeddings.create(
                input=["test"],
                model="text-embedding-3-small"
            )
            return True, f"OpenAI available (dimension: {len(response.data[0].embedding)})"
        else:
            return False, "OpenAI available but no API key set"
    except ImportError:
        return False, "OpenAI library not installed (pip install openai)"
    except Exception as e:
        return False, f"OpenAI error: {e}"

def test_ollama():
    """Test Ollama embedding availability"""
    try:
        import ollama
        # Test if Ollama service is running
        ollama.list()  # This will raise an exception if Ollama is not running
        
        # Try to use an embedding model
        model_name = "nomic-embed-text"
        try:
            response = ollama.embeddings(model=model_name, prompt="test")
            dimension = len(response.get('embedding', []))
            return True, f"Ollama available with {model_name} (dimension: {dimension})"
        except Exception:
            # Try to pull the model
            try:
                logger.info(f"Pulling {model_name}...")
                ollama.pull(model_name)
                response = ollama.embeddings(model=model_name, prompt="test")
                dimension = len(response.get('embedding', []))
                return True, f"Ollama available with {model_name} (dimension: {dimension}, just pulled)"
            except Exception as pull_error:
                return False, f"Ollama running but failed to use/pull {model_name}: {pull_error}"
        
    except ImportError:
        return False, "Ollama library not installed (pip install ollama)"
    except Exception as e:
        return False, f"Ollama not running or error: {e}"

def main():
    """Test all embedding providers"""
    print("🔍 Testing Embedding Providers")
    print("=" * 50)
    
    # Test OpenAI
    openai_available, openai_msg = test_openai()
    status = "✅" if openai_available else "❌"
    print(f"{status} OpenAI: {openai_msg}")
    
    # Test Ollama
    ollama_available, ollama_msg = test_ollama()
    status = "✅" if ollama_available else "❌"
    print(f"{status} Ollama: {ollama_msg}")
    
    # Recommendations
    print("\n📋 Recommendations:")
    if openai_available:
        print("• OpenAI embeddings are ready to use")
    elif not openai_available and "API key" not in openai_msg:
        print("• Install OpenAI: pip install openai")
        print("• Set OPENAI_API_KEY environment variable")
    
    if ollama_available:
        print("• Ollama embeddings are ready to use")
    elif "not installed" in ollama_msg:
        print("• Install Ollama: pip install ollama")
        print("• Install Ollama service: https://ollama.com/download")
    elif "not running" in ollama_msg:
        print("• Start Ollama service: ollama serve")
        print("• Or install Ollama: https://ollama.com/download")
    
    if not openai_available and not ollama_available:
        print("• Mock embeddings will be used for demo")
    
    print("\n🚀 Ready to run FAISS example!")

if __name__ == "__main__":
    main()