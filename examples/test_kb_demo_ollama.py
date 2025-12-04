"""
Test KB Service Demo with Ollama

This script checks if Ollama is available and runs the KB service demo.
If Ollama is not available, it provides setup instructions.
"""

import asyncio
import subprocess
import sys
from pathlib import Path

async def check_ollama():
    """Check if Ollama is available"""
    print("🔍 Checking Ollama availability...")
    
    # Check if Ollama command exists
    try:
        result = subprocess.run(
            ['ollama', '--version'],
            capture_output=True,
            text=True,
            timeout=5
        )
        if result.returncode == 0:
            print(f"✅ Ollama found: {result.stdout.strip()}")
            return True
    except (FileNotFoundError, subprocess.TimeoutExpired):
        pass
    
    # Check if Ollama service is running
    try:
        import aiohttp
        async with aiohttp.ClientSession() as session:
            async with session.get('http://localhost:11434/api/tags', timeout=aiohttp.ClientTimeout(total=2)) as response:
                if response.status == 200:
                    print("✅ Ollama service is running")
                    return True
    except Exception:
        pass
    
    print("❌ Ollama is not available")
    return False

def print_ollama_setup_instructions():
    """Print instructions for setting up Ollama"""
    print("\n" + "=" * 70)
    print("OLLAMA SETUP INSTRUCTIONS")
    print("=" * 70)
    print()
    print("To run this demo with Ollama, you need to:")
    print()
    print("1. Install Ollama:")
    print("   Visit: https://ollama.ai")
    print("   Or install via Homebrew (macOS):")
    print("   $ brew install ollama")
    print()
    print("2. Start Ollama service:")
    print("   $ ollama serve")
    print()
    print("3. Pull a model (in a separate terminal):")
    print("   $ ollama pull llama3.2")
    print("   Or try: llama3.1, mistral, phi3")
    print()
    print("4. Verify Ollama is running:")
    print("   $ curl http://localhost:11434/api/tags")
    print()
    print("5. Run this demo again:")
    print("   $ python examples/test_kb_demo_ollama.py")
    print()
    print("=" * 70)
    print()

async def run_demo():
    """Run the KB service demo"""
    print("\n🚀 Starting KB Service Demo with Ollama...")
    print("=" * 70)
    print()
    
    # Import and run the demo
    try:
        import sys
        from pathlib import Path
        # Add parent directory to path for imports
        parent_dir = Path(__file__).parent.parent
        if str(parent_dir) not in sys.path:
            sys.path.insert(0, str(parent_dir))
        
        from examples.kb_service_demo import KBDemo
        
        demo = KBDemo()
        await demo.run_demo()
        
    except Exception as e:
        print(f"\n❌ Demo failed: {e}")
        print("\nTroubleshooting:")
        print("1. Make sure Ollama is running: ollama serve")
        print("2. Make sure a model is pulled: ollama pull llama3.2")
        print("3. Check Ollama logs for errors")
        raise

async def main():
    """Main entry point"""
    print("Knowledge Base Service Demo - Ollama Test")
    print("=" * 70)
    print()
    
    # Check if Ollama is available
    ollama_available = await check_ollama()
    
    if not ollama_available:
        print_ollama_setup_instructions()
        print("\n⚠️  Demo cannot run without Ollama.")
        print("Please set up Ollama and try again.")
        sys.exit(1)
    
    # Run the demo
    try:
        await run_demo()
    except KeyboardInterrupt:
        print("\n\n⚠️  Demo interrupted by user")
        sys.exit(0)
    except Exception as e:
        print(f"\n\n❌ Demo failed with error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main())

