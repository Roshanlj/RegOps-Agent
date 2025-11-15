# RegOps Copilot (MVP)

Agentic QA/QC assistant for **stability pull** workflows with flexible **multi-provider LLM support**.

- **Multi-Provider LLM**: Supports Gemini, OpenRouter, Ollama, and local LLMs with automatic failover
- Deterministic **Plan → Act → Review → Replan** loop with LLM-powered planning
- Naive **RAG** over ingested SOPs (pgvector or keyword fallback)
- Stub tool calls for **LIMS**, **Sheets**, **Jira**, **Mailer**
- **Audit log** + **metrics** + static console at `/app`
- **Offline fallback**: Works without LLM providers using deterministic planning

---

## 1) Problem this solves

Stability pulls are repetitive and compliance-sensitive. Typical steps:

1. Get the week’s **pull list** from LIMS.
2. Add rows to a **tracker** (Sheets).
3. Open a **ticket** (Jira).
4. Draft a **QA email** with the table and **citations to SOPs**.
5. Verify **window (+/-3 days)**, **two-person review**, and **required fields** before sending.

This MVP automates steps 1–4 and blocks step 5 if checks fail. Everything is logged.

---

## 2) How it works (high level)

1. **Ingest SOP** → chunk → store in Postgres (`sop_chunks`).
2. **RAG** → retrieve top-k chunks for grounding and email citations.
3. **Agent loop**
   - **Plan**: parse week from instruction and build a tool plan.
   - **Act**: execute tools; carry forward context (e.g., table rows).
   - **Review**: rule checks (citations present, window, two-person, fields).
   - **Replan**: on any failure, iterate up to a cap.
4. **Audit/Metrics**: every step and result is stored and summarized.

> LIMS here is a **stub**; real systems would replace tool functions with live integrations.

---

## 3) LLM Provider Configuration

The system supports multiple LLM providers with automatic failover. Configure providers via environment variables.

### Supported Providers

1. **Google Gemini** (Cloud)
   - Models: `gemini-1.5-pro`, `gemini-1.5-flash`, `gemini-2.0-flash-exp`
   - Requires: `GEMINI_API_KEY`

2. **OpenRouter** (Cloud)
   - Access to multiple models (Claude, GPT-4, etc.)
   - Requires: `OPENROUTER_API_KEY`

3. **Ollama** (Local)
   - Run models locally (llama3.1, mistral, etc.)
   - Requires: Ollama server running on `http://localhost:11434`

4. **Local LLM** (OpenAI-compatible)
   - LM Studio, llama.cpp, vLLM, etc.
   - Requires: `LOCAL_LLM_BASE_URL`

### Environment Variables

Copy `.env.example` to `.env` and configure:

```bash
# Primary provider (first to try)
LLM_PROVIDER=gemini

# Fallback chain (comma-separated, tried in order)
LLM_FALLBACK_CHAIN=gemini,openrouter,ollama

# Gemini configuration
GEMINI_API_KEY=your_api_key_here
GEMINI_MODEL=gemini-1.5-flash

# OpenRouter configuration
OPENROUTER_API_KEY=your_api_key_here
OPENROUTER_MODEL=anthropic/claude-3.5-sonnet

# Ollama configuration (local)
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL=llama3.1:8b

# Local LLM configuration (LM Studio, llama.cpp, etc.)
LOCAL_LLM_BASE_URL=http://localhost:1234/v1
LOCAL_LLM_MODEL=local

# Retry configuration
LLM_MAX_RETRIES=3
LLM_RETRY_DELAY=2.0
LLM_TIMEOUT=60
```

### Fallback Chain Behavior

The system automatically tries providers in order:

1. **Primary Provider**: Configured via `LLM_PROVIDER`
2. **Fallback Chain**: Tries each provider in `LLM_FALLBACK_CHAIN` order
3. **Retry Logic**: Each provider gets 3 retries with exponential backoff (2s → 4s → 8s)
4. **Rate Limit Handling**: Automatically detects HTTP 429 and retries
5. **Deterministic Fallback**: If all LLM providers fail, uses rule-based planning

**Example Flow:**
```
Request → Gemini (rate limited) → retry 2s → retry 4s → retry 8s 
       → OpenRouter (success) ✓
```

**Audit Trail**: Every request logs which provider was used for compliance tracking.

### Running Without LLM Providers

The system works without any LLM configuration:

```bash
# No LLM environment variables set
# System automatically uses deterministic fallback
docker compose up --build -d
```

The deterministic fallback uses rule-based planning for stability pull workflows.

---

## 4) Architecture

- **RAG store**: Postgres table `sop_chunks(doc_name, chunk_no, text, embedding VECTOR(384)?).`
- If `pgvector` is missing, fallback to **keyword** search via `EMBEDDINGS_OFFLINE=1`.
- **LLM Manager**: Orchestrates provider selection, retry logic, and fallback chain
- **Provider Abstraction**: Unified interface for all LLM providers

---

## 5) Quick Start

### Docker (recommended)
```bash
# 1. Configure environment (optional - works without LLM)
cp .env.example .env
# Edit .env with your API keys

# 2. Start services
docker compose up --build -d

# 3. Enable pgvector extension
docker compose exec db psql -U regops -d regops -c 'CREATE EXTENSION IF NOT EXISTS vector;'

# 4. UI console: http://localhost:8000/app/


### Local Development (without Docker)

For faster iteration during development:

```bash
# 1. Install Python 3.11+
python --version  # Verify 3.11 or higher

# 2. Create virtual environment
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Set up PostgreSQL (option A: Docker container)
docker run -d --name regops-db \
  -e POSTGRES_USER=regops \
  -e POSTGRES_PASSWORD=regops \
  -e POSTGRES_DB=regops \
  -p 5432:5432 \
  pgvector/pgvector:pg16

# Enable pgvector
docker exec regops-db psql -U regops -d regops -c 'CREATE EXTENSION IF NOT EXISTS vector;'

# 4. Set up PostgreSQL (option B: Local installation)
# Install PostgreSQL 16 with pgvector extension
# Create database: createdb -U postgres regops
# Enable extension: psql -U postgres -d regops -c 'CREATE EXTENSION IF NOT EXISTS vector;'

# 5. Configure environment
cp .env.example .env
# Edit .env with your settings:
# - PG_URL=postgresql+psycopg2://regops:regops@localhost:5432/regops
# - Add LLM provider API keys (optional)

# 6. Run development server
uvicorn backend.app:app --reload --port 8000

# 7. Access UI console
# http://localhost:8000/app/
```

### API Examples

```bash
# 1) Ingest SOP (plain text file)
curl -F "file=@data/sops/sample_sop.txt" http://localhost:8000/ingest

# 2) Ask RAG
curl -X POST http://localhost:8000/ask_rag -H "Content-Type: application/json" \
  -d '{"question":"required email content for stability pulls"}'

# 3) Run agent (week parsed from text: "week 12", "2025-W45", etc.)
curl -X POST http://localhost:8000/agent/run -H "Content-Type: application/json" \
  -d '{"instruction":"prepare stability pull list for week 12"}'

# 4) Lightweight eval
curl -X POST http://localhost:8000/eval/rag -H "Content-Type: application/json" \
  -d '{"cases":[{"question":"required email content for stability pulls","ground":"Lot Batch Expiry Storage"}]}'

# 5) Metrics / Audit
curl http://localhost:8000/metrics/summary
curl http://localhost:8000/audit/logs


---

## 6) Troubleshooting

### LLM Provider Issues

#### Problem: "No LLM providers available"

**Symptoms:**
- Agent uses deterministic fallback for all requests
- Logs show: "No LLM providers available, using deterministic fallback"

**Solutions:**
1. Check environment variables are set:
   ```bash
   # Verify .env file exists and contains API keys
   cat .env | grep API_KEY
   ```

2. Verify provider availability:
   ```bash
   # Check logs for provider initialization
   docker compose logs api | grep "Initialized provider"
   ```

3. Test provider connectivity:
   ```bash
   # For Gemini
   curl -H "Authorization: Bearer $GEMINI_API_KEY" \
     https://generativelanguage.googleapis.com/v1/models
   
   # For Ollama (local)
   curl http://localhost:11434/api/tags
   
   # For Local LLM
   curl http://localhost:1234/v1/models
   ```

#### Problem: "Rate limit exceeded" (HTTP 429)

**Symptoms:**
- Logs show: "Rate limit hit (attempt 1/3), retrying in 2s"
- Multiple retry attempts before fallback

**Solutions:**
1. **Wait for automatic retry**: System retries 3 times with exponential backoff
2. **Configure fallback chain**: Add alternative providers
   ```bash
   LLM_FALLBACK_CHAIN=gemini,openrouter,ollama
   ```
3. **Increase retry delay**:
   ```bash
   LLM_RETRY_DELAY=5.0  # Wait 5s instead of 2s
   ```
4. **Check API quota**: Verify your API key has remaining quota

#### Problem: "Provider timeout"

**Symptoms:**
- Logs show: "Timeout (attempt 1/3), retrying in 2s"
- Requests take longer than expected

**Solutions:**
1. **Increase timeout**:
   ```bash
   LLM_TIMEOUT=120  # 2 minutes instead of 60s
   ```
2. **Check network connectivity**:
   ```bash
   # Test latency to provider
   ping -c 3 generativelanguage.googleapis.com
   ```
3. **Use local provider**: Switch to Ollama or local LLM for faster response

#### Problem: Ollama not available

**Symptoms:**
- Logs show: "Provider ollama configured but not available"
- Agent skips Ollama in fallback chain

**Solutions:**
1. **Start Ollama server**:
   ```bash
   # Install Ollama: https://ollama.ai/download
   ollama serve
   ```

2. **Pull model**:
   ```bash
   ollama pull llama3.1:8b
   ```

3. **Verify Ollama is running**:
   ```bash
   curl http://localhost:11434/api/tags
   ```

4. **Check base URL**:
   ```bash
   # In .env
   OLLAMA_BASE_URL=http://localhost:11434
   ```

#### Problem: Local LLM (LM Studio) not connecting

**Symptoms:**
- Logs show: "Local LLM not available"
- Connection refused errors

**Solutions:**
1. **Start LM Studio server**:
   - Open LM Studio
   - Go to "Local Server" tab
   - Click "Start Server"
   - Note the port (usually 1234)

2. **Configure base URL**:
   ```bash
   LOCAL_LLM_BASE_URL=http://localhost:1234/v1
   ```

3. **Test endpoint**:
   ```bash
   curl http://localhost:1234/v1/models
   ```

4. **Check firewall**: Ensure port 1234 is not blocked

### Database Issues

#### Problem: "pgvector extension not found"

**Solutions:**
```bash
# Enable pgvector extension
docker compose exec db psql -U regops -d regops -c 'CREATE EXTENSION IF NOT EXISTS vector;'

# Or use keyword fallback
EMBEDDINGS_OFFLINE=1
```

#### Problem: "Connection refused" to PostgreSQL

**Solutions:**
```bash
# Check database is running
docker compose ps

# Check connection string
echo $PG_URL

# Restart database
docker compose restart db
```

### Configuration Issues

#### Problem: "Invalid provider name in LLM_PROVIDER"

**Symptoms:**
- Logs show: "Primary provider 'xyz' not configured"
- System uses first available provider

**Solutions:**
1. **Use valid provider name**:
   ```bash
   LLM_PROVIDER=gemini  # Valid: gemini, openrouter, ollama, local
   ```

2. **Check provider is configured**:
   ```bash
   # Gemini requires GEMINI_API_KEY
   # OpenRouter requires OPENROUTER_API_KEY
   # Ollama requires OLLAMA_BASE_URL or OLLAMA_MODEL
   # Local requires LOCAL_LLM_BASE_URL
   ```

#### Problem: Environment variables not loaded

**Symptoms:**
- Configuration not taking effect
- Default values used instead

**Solutions:**
1. **Docker**: Ensure `.env` file exists in project root
   ```bash
   ls -la .env
   docker compose down && docker compose up -d
   ```

2. **Local development**: Load environment manually
   ```bash
   # Option A: Use python-dotenv (automatic)
   pip install python-dotenv
   
   # Option B: Export manually
   export $(cat .env | xargs)
   ```

### Performance Issues

#### Problem: Slow agent responses

**Solutions:**
1. **Use faster model**:
   ```bash
   GEMINI_MODEL=gemini-1.5-flash  # Faster than gemini-1.5-pro
   ```

2. **Use local provider**:
   ```bash
   LLM_PROVIDER=ollama  # No network latency
   ```

3. **Reduce timeout**:
   ```bash
   LLM_TIMEOUT=30  # Fail faster, move to next provider
   ```

4. **Check database performance**:
   ```bash
   # Ensure pgvector index exists
   docker compose exec db psql -U regops -d regops -c '\d sop_chunks'
   ```

### Debugging Tips

#### Enable verbose logging

```python
# In backend/app.py or backend/llm/manager.py
import logging
logging.basicConfig(level=logging.DEBUG)
```

#### Check audit logs

```bash
# View recent agent runs
curl http://localhost:8000/audit/logs | jq '.[-10:]'

# Check which provider was used
curl http://localhost:8000/audit/logs | jq '.[] | select(.action=="agent_run") | .llm_provider'
```

#### Test provider directly

```python
# Python REPL
from backend.llm import get_manager

manager = get_manager()
print(manager.get_available_providers())

response = manager.chat(
    system="You are a helpful assistant",
    user="Say hello"
)
print(response)
print(f"Used provider: {manager.last_used_provider}")
```

### Common Error Messages

| Error | Meaning | Solution |
|-------|---------|----------|
| `AllProvidersFailedError` | All LLM providers failed | Check API keys, network, and provider status |
| `RateLimitError` | Provider rate limit hit | Wait or add fallback providers |
| `ProviderUnavailableError` | Provider not configured/reachable | Check configuration and connectivity |
| `TimeoutError` | Request exceeded timeout | Increase `LLM_TIMEOUT` or use faster provider |
| `No providers configured` | No valid provider config | Add at least one provider to `.env` |

### Getting Help

1. **Check logs**: `docker compose logs -f api`
2. **Review audit trail**: `curl http://localhost:8000/audit/logs`
3. **Test providers**: Use troubleshooting commands above
4. **Verify configuration**: `cat .env` and check for typos
5. **Check provider status**: Visit provider status pages (Gemini, OpenRouter)

---

## 7) Environment Variable Reference

### LLM Configuration

| Variable | Default | Description |
|----------|---------|-------------|
| `LLM_PROVIDER` | `gemini` | Primary provider to try first |
| `LLM_FALLBACK_CHAIN` | `gemini,openrouter,ollama` | Comma-separated fallback order |
| `LLM_MAX_RETRIES` | `3` | Max retry attempts per provider |
| `LLM_RETRY_DELAY` | `2.0` | Initial retry delay in seconds |
| `LLM_TIMEOUT` | `60` | Request timeout in seconds |

### Provider-Specific

| Variable | Required | Description |
|----------|----------|-------------|
| `GEMINI_API_KEY` | For Gemini | Google AI API key |
| `GEMINI_MODEL` | No | Model name (default: `gemini-1.5-flash`) |
| `OPENROUTER_API_KEY` | For OpenRouter | OpenRouter API key |
| `OPENROUTER_MODEL` | No | Model name (default: `anthropic/claude-3.5-sonnet`) |
| `OLLAMA_BASE_URL` | No | Ollama server URL (default: `http://localhost:11434`) |
| `OLLAMA_MODEL` | No | Model name (default: `llama3.1:8b`) |
| `LOCAL_LLM_BASE_URL` | For Local | OpenAI-compatible endpoint URL |
| `LOCAL_LLM_MODEL` | No | Model name (default: `local`) |

### Database Configuration

| Variable | Default | Description |
|----------|---------|-------------|
| `PG_URL` | `postgresql+psycopg2://regops:regops@db:5432/regops` | PostgreSQL connection string |
| `COPILOT_DB` | `data/copilot.sqlite3` | SQLite database path |
| `EMBEDDINGS_OFFLINE` | `0` | Set to `1` to disable vector embeddings |

---

## 8) License & Contributing

This is an MVP demonstration. For production use:
- Replace stub integrations (LIMS, Sheets, Jira, Mailer) with real APIs
- Add authentication and authorization
- Implement proper error handling and monitoring
- Add comprehensive test coverage
- Review and enhance compliance checks
