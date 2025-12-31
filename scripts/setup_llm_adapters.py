#!/usr/bin/env python3
"""
Setup Script for DocEX LLM Adapters

This script helps set up the environment for using the new LLM adapters.
"""

import os
import sys
import subprocess
import platform
from pathlib import Path


def print_header(title):
    """Print a formatted header"""
    print("\n" + "=" * 60)
    print(f" {title}")
    print("=" * 60)


def check_python_version():
    """Check if Python version is compatible"""
    version = sys.version_info
    if version.major < 3 or (version.major == 3 and version.minor < 8):
        print("❌ Python 3.8+ is required")
        return False
    print(f"✅ Python {version.major}.{version.minor}.{version.micro}")
    return True


def install_package(package):
    """Install a Python package"""
    try:
        subprocess.check_call([sys.executable, "-m", "pip", "install", package])
        return True
    except subprocess.CalledProcessError:
        return False


def check_and_install_dependencies():
    """Check and install required dependencies"""
    print_header("Checking Dependencies")
    
    dependencies = {
        "anthropic>=0.34.0": "Claude adapter",
        "aiohttp>=3.9.0": "Local LLM adapter",
        "openai>=1.0.0": "OpenAI adapter (existing)"
    }
    
    for package, description in dependencies.items():
        try:
            # Extract package name
            package_name = package.split(">=")[0].split("==")[0]
            __import__(package_name)
            print(f"✅ {package_name} - {description}")
        except ImportError:
            print(f"⚠️  {package_name} not found, installing...")
            if install_package(package):
                print(f"✅ {package_name} installed successfully")
            else:
                print(f"❌ Failed to install {package_name}")


def check_environment_variables():
    """Check for required environment variables"""
    print_header("Environment Variables")
    
    env_vars = {
        "OPENAI_API_KEY": "OpenAI adapter",
        "ANTHROPIC_API_KEY": "Claude adapter"
    }
    
    for var, description in env_vars.items():
        if os.getenv(var):
            print(f"✅ {var} - {description}")
        else:
            print(f"⚠️  {var} not set - {description}")


def check_ollama():
    """Check if Ollama is installed and running"""
    print_header("Ollama Setup (Local LLM)")
    
    try:
        # Check if ollama command exists
        result = subprocess.run(
            ["ollama", "--version"], 
            capture_output=True, 
            text=True
        )
        if result.returncode == 0:
            print("✅ Ollama is installed")
            
            # Check if server is running
            try:
                import aiohttp
                import asyncio
                
                async def check_server():
                    try:
                        async with aiohttp.ClientSession() as session:
                            async with session.get("http://localhost:11434/api/tags") as resp:
                                if resp.status == 200:
                                    return True
                    except:
                        return False
                    return False
                
                if asyncio.run(check_server()):
                    print("✅ Ollama server is running")
                    
                    # List available models
                    result = subprocess.run(
                        ["ollama", "list"], 
                        capture_output=True, 
                        text=True
                    )
                    if result.returncode == 0:
                        models = [line.split()[0] for line in result.stdout.strip().split('\n')[1:] if line.strip()]
                        if models:
                            print(f"✅ Available models: {', '.join(models)}")
                        else:
                            print("⚠️  No models installed")
                else:
                    print("⚠️  Ollama server is not running")
                    print("   Start with: ollama serve")
                    
            except ImportError:
                print("⚠️  Cannot check server status (aiohttp not available)")
                
        else:
            print("❌ Ollama is not installed")
            
    except FileNotFoundError:
        print("❌ Ollama is not installed")
        print("   Install from: https://ollama.ai/")


def create_example_env_file():
    """Create an example .env file"""
    print_header("Environment File Setup")
    
    env_file = Path(".env")
    
    if env_file.exists():
        print("✅ .env file already exists")
        return
    
    env_content = """# DocEX LLM Adapters Environment Variables

# OpenAI API Key (for OpenAI adapter)
# Get from: https://platform.openai.com/api-keys
OPENAI_API_KEY=your-openai-api-key-here

# Anthropic API Key (for Claude adapter)
# Get from: https://console.anthropic.com/
ANTHROPIC_API_KEY=your-anthropic-api-key-here

# Local LLM Settings (for Ollama)
# These are the default values, change if needed
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL=llama3.2
"""
    
    try:
        env_file.write_text(env_content)
        print("✅ Created example .env file")
        print("   Edit .env file with your API keys")
    except Exception as e:
        print(f"❌ Failed to create .env file: {e}")


def print_usage_examples():
    """Print usage examples"""
    print_header("Usage Examples")
    
    print("1. OpenAI Adapter:")
    print("   from docex.processors.llm import OpenAIAdapter")
    
    print("\n2. Claude Adapter:")
    print("   from docex.processors.llm import ClaudeAdapter")
    
    print("\n3. Local LLM Adapter:")
    print("   from docex.processors.llm import LocalLLMAdapter")
    
    print("\n4. Run examples:")
    print("   python examples/test_claude_adapter.py")
    print("   python examples/test_local_llm_adapter.py")


def print_next_steps():
    """Print next steps"""
    print_header("Next Steps")
    
    print("1. Set your API keys in .env file:")
    print("   - OpenAI: https://platform.openai.com/api-keys")
    print("   - Anthropic: https://console.anthropic.com/")
    
    print("\n2. For local LLM (optional):")
    print("   - Install Ollama: https://ollama.ai/")
    print("   - Start server: ollama serve")
    print("   - Pull models: ollama pull llama3.2")
    
    print("\n3. Run example scripts:")
    print("   - python examples/test_claude_adapter.py")
    print("   - python examples/test_local_llm_adapter.py")
    
    print("\n4. Read documentation:")
    print("   - docs/LLM_ADAPTERS_GUIDE.md")


def main():
    """Main setup function"""
    print("🚀 DocEX LLM Adapters Setup")
    
    if not check_python_version():
        sys.exit(1)
    
    check_and_install_dependencies()
    check_environment_variables()
    check_ollama()
    create_example_env_file()
    print_usage_examples()
    print_next_steps()
    
    print("\n🎉 Setup completed!")


if __name__ == "__main__":
    main()