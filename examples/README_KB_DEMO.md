# Knowledge Base Service Demo

## Overview

This demo demonstrates the Knowledge Base Service implementation following the `KB_Implementation_Proposal.html` specifications. It shows:

1. Rule book ingestion (GPO Roster, DDD Matrix, Eligibility Guide)
2. KB service initialization with RAG
3. Natural language querying
4. Workflow integration (Steps 3, 4, 6 of chargeback process)
5. Structured data extraction

## Prerequisites

### Option 1: Ollama (Recommended for Demo)

1. **Install Ollama:**
   ```bash
   # macOS
   brew install ollama
   
   # Or download from https://ollama.ai
   ```

2. **Start Ollama service:**
   ```bash
   ollama serve
   ```

3. **Pull a model (in a separate terminal):**
   ```bash
   ollama pull llama3.2
   # Or try: llama3.1, mistral, phi3
   ```

4. **Verify Ollama is running:**
   ```bash
   curl http://localhost:11434/api/tags
   ```

### Option 2: OpenAI or Claude

Set environment variables:
```bash
export OPENAI_API_KEY="your-key-here"
# OR
export ANTHROPIC_API_KEY="your-key-here"
```

## Running the Demo

### Quick Test (with Ollama check)

```bash
python3 examples/test_kb_demo_ollama.py
```

This script will:
- Check if Ollama is available
- Provide setup instructions if not
- Run the demo if available

### Direct Demo

```bash
python3 examples/kb_service_demo.py
```

The demo will automatically:
- Try Ollama first (if available)
- Fall back to OpenAI (if API key set)
- Fall back to Claude (if API key set)

## What the Demo Shows

### 1. Setup Phase
- Creates DocBasket for rule books
- Initializes LLM adapter (Ollama/OpenAI/Claude)
- Initializes semantic search service
- Initializes Enhanced RAG service
- Initializes Knowledge Base Service

### 2. Rule Book Ingestion
Ingests three sample rule books:
- **GPO Roster**: Customer contract eligibility information
- **DDD Matrix**: Class-of-trade determination rules
- **Eligibility Guide**: Eligibility verification procedures

### 3. Query Demonstrations
- Natural language queries
- Contract eligibility validation (Step 3)
- GPO Roster validation (Step 4)
- Class-of-trade determination (Step 6)

### 4. Workflow Integration
- ContractEligibilityProcessor (Step 3)
- COTDeterminationProcessor (Step 6)

### 5. Version Tracking
- Rule book version information

## Sample Data

The demo uses generic sample company names:
- **Sample Hospital A** (Customer ID: HOSP-A-001)
- **Sample Medical Center B** (Customer ID: MED-B-002)
- **Sample Health Network C** (Customer ID: NET-C-003)

GPO Names:
- **Healthcare Alliance Group** (Contract IDs: HAG-2024-001, HAG-2024-002)
- **HealthTrust Purchasing Network** (Contract ID: HTPN-2024-045)

## Expected Output

The demo will show:
```
🚀 Knowledge Base Service Demo
======================================================================
Following KB_Implementation_Proposal.html specifications
======================================================================

📁 Step 1: Creating DocBasket for rule books...
✅ Created basket: sample_company_kb_rule_books

🤖 Step 2: Initializing LLM adapter...
  Using Local LLM adapter (Ollama)...
  ✅ Ollama adapter initialized
✅ LLM adapter initialized: LocalLLMAdapter

🔍 Step 3: Initializing semantic search service...
✅ Semantic search service initialized

🧠 Step 4: Initializing Enhanced RAG service...
✅ Enhanced RAG service initialized

📚 Step 5: Initializing Knowledge Base Service...
✅ Knowledge Base Service initialized

📥 Ingesting Sample Rule Books
======================================================================

📄 Processing GPO_Roster_Sample.txt (gpo_roster)...
  ✅ Extracted structured data: X items
  ✅ Ingested into Knowledge Base

[... continues with queries and workflow demonstrations ...]
```

## Troubleshooting

### Ollama Not Found
- Install Ollama: `brew install ollama` (macOS) or visit https://ollama.ai
- Start service: `ollama serve`
- Pull model: `ollama pull llama3.2`

### Ollama Service Not Running
- Check if service is running: `curl http://localhost:11434/api/tags`
- Start service: `ollama serve`
- Check logs for errors

### Model Not Available
- Pull the model: `ollama pull llama3.2`
- Try alternative models: `llama3.1`, `mistral`, `phi3`
- Update model name in demo if needed

### Semantic Search Issues
- If using Ollama, semantic search uses local embeddings (may be less accurate)
- For better results, set `OPENAI_API_KEY` to use OpenAI embeddings

### Import Errors
- Make sure you're in the DocEX root directory
- Install dependencies: `pip install -r requirements.txt`
- Check Python path includes DocEX

## Next Steps

After running the demo successfully:

1. **Test with Real Data**: Replace sample rule books with actual documents
2. **Customize Queries**: Modify queries to match your use case
3. **Integrate Workflow**: Connect to your chargeback workflow
4. **Production Setup**: Configure production vector database (Pinecone)
5. **Monitoring**: Set up logging and monitoring

## Files

- `examples/kb_service_demo.py` - Main demo script
- `examples/test_kb_demo_ollama.py` - Test script with Ollama check
- `docex/services/knowledge_base_service.py` - KB Service implementation
- `docex/processors/kb/` - Rule book processors
- `docex/prompts/` - KB-specific prompts

## References

- `KB_Implementation_Proposal.html` - Full implementation proposal
- `docex/services/README_KB_SERVICE.md` - KB Service documentation

