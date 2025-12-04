# Installing Homebrew on macOS

## Step-by-Step Installation

### Step 1: Open Terminal
Open the Terminal app on your Mac (Applications > Utilities > Terminal, or press `Cmd + Space` and type "Terminal")

### Step 2: Install Homebrew
Copy and paste this command into your terminal:

```bash
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
```

### Step 3: Follow the Prompts
- The installer will ask for your **administrator password** (the password you use to log into your Mac)
- Type your password and press Enter (you won't see the password as you type - this is normal)
- The installation will take a few minutes
- You may see messages about installing Xcode Command Line Tools - this is normal

### Step 4: Add Homebrew to Your PATH
After installation, Homebrew will show you commands to run. They will look something like:

**For Apple Silicon Macs (M1/M2/M3):**
```bash
echo 'eval "$(/opt/homebrew/bin/brew shellenv)"' >> ~/.zprofile
eval "$(/opt/homebrew/bin/brew shellenv)"
```

**For Intel Macs:**
```bash
echo 'eval "$(/usr/local/bin/brew shellenv)"' >> ~/.zprofile
eval "$(/usr/local/bin/brew shellenv)"
```

**Copy and paste the commands that Homebrew shows you** - they will be specific to your system.

### Step 5: Verify Installation
Test that Homebrew is installed:

```bash
brew --version
```

You should see something like: `Homebrew 4.x.x`

### Step 6: Install Ollama
Once Homebrew is installed, install Ollama:

```bash
brew install ollama
```

### Step 7: Start Ollama
Start the Ollama service:

```bash
ollama serve
```

Keep this terminal window open. Open a **new terminal window** for the next steps.

### Step 8: Pull a Model
In the new terminal window, pull a model:

```bash
ollama pull llama3.2
```

This will download the model (may take a few minutes depending on your internet speed).

### Step 9: Verify Ollama is Running
Test that Ollama is working:

```bash
curl http://localhost:11434/api/tags
```

You should see a JSON response with your models.

### Step 10: Run the KB Demo
Now you can run the Knowledge Base demo:

```bash
cd /Users/mrahman/repos/DocEX
python3 examples/kb_service_demo.py
```

## Troubleshooting

### "Permission denied" errors
- Make sure you're using your administrator password
- You may need to run: `sudo chown -R $(whoami) /opt/homebrew` (for Apple Silicon) or `/usr/local` (for Intel)

### "Command not found: brew" after installation
- Make sure you ran the PATH commands from Step 4
- Try restarting your terminal
- Check: `echo $PATH` should include `/opt/homebrew/bin` or `/usr/local/bin`

### Homebrew installation hangs or is slow
- This is normal - it can take 5-15 minutes
- Make sure you have a stable internet connection
- Don't interrupt the installation

### Need help?
- Homebrew documentation: https://docs.brew.sh
- Homebrew troubleshooting: https://docs.brew.sh/Troubleshooting

## Quick Reference

After Homebrew is installed, here's the quick workflow:

```bash
# Install Ollama
brew install ollama

# Terminal 1: Start Ollama service
ollama serve

# Terminal 2: Pull model and run demo
ollama pull llama3.2
cd /Users/mrahman/repos/DocEX
python3 examples/kb_service_demo.py
```

