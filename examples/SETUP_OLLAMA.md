# Setting Up Ollama for KB Service Demo

## Option 1: Install Homebrew First (Recommended)

If you don't have Homebrew installed:

```bash
# Install Homebrew
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"

# Then install Ollama
brew install ollama
```

## Option 2: Install Ollama Directly (Without Homebrew)

You can install Ollama directly on macOS:

```bash
# Download and install Ollama
curl -fsSL https://ollama.ai/install.sh | sh
```

Or download the installer manually:
1. Visit: https://ollama.ai/download
2. Download the macOS installer
3. Run the installer

## Option 3: Use OpenAI or Claude Instead

If you prefer not to install Ollama, you can use OpenAI or Claude API keys:

### Using OpenAI:
```bash
export OPENAI_API_KEY="your-openai-api-key-here"
python3 examples/kb_service_demo.py
```

### Using Claude:
```bash
export ANTHROPIC_API_KEY="your-anthropic-api-key-here"
python3 examples/kb_service_demo.py
```

## After Installing Ollama

1. **Start Ollama service:**
   ```bash
   ollama serve
   ```
   (Keep this running in a terminal)

2. **Pull a model (in a new terminal):**
   ```bash
   ollama pull llama3.2
   ```
   
   Or try other models:
   ```bash
   ollama pull llama3.1
   ollama pull mistral
   ollama pull phi3
   ```

3. **Verify Ollama is running:**
   ```bash
   curl http://localhost:11434/api/tags
   ```
   
   You should see a JSON response with available models.

4. **Run the demo:**
   ```bash
   python3 examples/test_kb_demo_ollama.py
   ```
   
   Or directly:
   ```bash
   python3 examples/kb_service_demo.py
   ```

## Quick Start (If You Have Homebrew)

```bash
# Install Homebrew (if not installed)
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"

# Install Ollama
brew install ollama

# Start Ollama (in background or separate terminal)
ollama serve &

# Pull a model
ollama pull llama3.2

# Run the demo
python3 examples/kb_service_demo.py
```

## Troubleshooting

### "command not found: brew"
- Install Homebrew first (see Option 1 above)
- Or use Option 2 to install Ollama directly

### "command not found: ollama"
- Make sure Ollama is installed
- Check if it's in your PATH: `which ollama`
- Restart your terminal after installation

### "Connection refused" when starting Ollama
- Make sure Ollama service is running: `ollama serve`
- Check if port 11434 is available: `lsof -i :11434`

### Model not found
- Pull the model first: `ollama pull llama3.2`
- List available models: `ollama list`

## Alternative: Use API Keys

If you don't want to install Ollama, the demo will automatically fall back to:
1. OpenAI (if `OPENAI_API_KEY` is set)
2. Claude (if `ANTHROPIC_API_KEY` is set)

Just set the environment variable and run the demo - no installation needed!

