---
title: Multi-Provider LLM Integration with Intelligent Fallback
status: draft
created: 2025-11-16
---

# Multi-Provider LLM Integration with Intelligent Fallback

## Overview

Transform RegOps Copilot from fallback-based to truly agentic by implementing a flexible, multi-provider LLM system with automatic failover and rate limit handling.

## Goals

1. **Provider Agnostic**: Support multiple LLM providers through unified interface
2. **Intelligent Fallback**: Automatic provider switching on rate limits or failures
3. **Easy Configuration**: Environment-based provider setup
4. **Local Development**: Run agents without Docker for rapid iteration
5. **Production Ready**: Maintain Docker deployment capability

## Requirements

### Supported LLM Providers

#### Cloud Providers
- **Google Gemini** (primary)
  - Models: gemini-1.5-pro, gemini-1.5-flash, gemini-2.0-flash-exp
  - API: Google AI Studio / Vertex AI
  - Rate limits: Handle 429 errors

- **OpenRouter** (secondary fallback)
  - Models: Configurable (anthropic/claude, google/gemini, meta-llama, etc.)
  - API: OpenRouter unified endpoint
  - Rate limits: Handle 429 errors

#### Local Providers (tertiary fallback)
- **Ollama** (http://localhost:11434)
- **LM Studio** (http://localhost:1234/v1)
- **llama.cpp server** (configurable port)
- **Any OpenAI-compatible API** (custom endpoint)

### Configuration System

Environment variables for provider configuration:

```bash
# Primary Provider
LLM_PROVIDER=gemini  # gemini|openrouter|openai|ollama|local
LLM_API_KEY=your_key_here
LLM_MODEL=gemini-1.5-flash

# Gemini Specific
GEMINI_API_KEY=your_gemini_key
GEMINI_MODEL=gemini-1.5-flash

# OpenRouter Specific
OPENROUTER_API_KEY=your_openrouter_key
OPENROUTER_MODEL=anthropic/claude-3.5-sonnet

# Local LLM
LOCAL_LLM_BASE_URL=http://localhost:1234/v1
LOCAL_LLM_MODEL=llama-3.1-8b

# Ollama Specific
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL=llama3.1:8b

# Fallback Chain (comma-separated)
LLM_FALLBACK_CHAIN=gemini,openrouter,ollama
# If not set, defaults to: gemini -> openrouter -> local/ollama

# Retry Configuration
LLM_MAX_RETRIES=3
LLM_RETRY_DELAY=2  # seconds
LLM_TIMEOUT=60  # seconds
```

### Retry & Fallback Logic

#### Retry Strategy
1. **Exponential Backoff**: 2s, 4s, 8s delays
2. **Rate Limit Detection**: Catch 429 status codes
3. **Timeout Handling**: Configurable timeout per request
4. **Max Retries**: Configurable per provider (default: 3)

#### Fallback Chain
```
Request → Primary Provider (Gemini)
    ↓ (on rate limit/error)
Secondary Provider (OpenRouter)
    ↓ (on rate limit/error)
Tertiary Provider (Ollama/Local)
    ↓ (on failure)
Deterministic Fallback (existing rule-based)
```

### Architecture Changes

#### New Module: `backend/llm/`

```
backend/llm/
├── __init__.py           # Public API
├── provider.py           # Base provider interface
├── providers/
│   ├── __init__.py
│   ├── gemini.py         # Google Gemini implementation
│   ├── openrouter.py     # OpenRouter implementation
│   ├── openai.py         # OpenAI-compatible (local LLMs)
│   └── ollama.py         # Ollama-specific implementation
├── manager.py            # Provider manager with fallback logic
├── retry.py              # Retry decorator and utilities
└── config.py             # Configuration loader
```

#### Provider Interface

```python
from abc import ABC, abstractmethod
from typing import Optional, Dict, Any

class LLMProvider(ABC):
    """Base interface for all LLM providers"""
    
    @abstractmethod
    def chat(self, system: str, user: str, **kwargs) -> str:
        """Send chat completion request"""
        pass
    
    @abstractmethod
    def is_available(self) -> bool:
        """Check if provider is configured and reachable"""
        pass
    
    @property
    @abstractmethod
    def name(self) -> str:
        """Provider name for logging"""
        pass
    
    @property
    @abstractmethod
    def supports_streaming(self) -> bool:
        """Whether provider supports streaming responses"""
        pass
```

#### Manager with Fallback

```python
class LLMManager:
    """Manages multiple providers with automatic fallback"""
    
    def __init__(self, config: LLMConfig):
        self.providers = self._init_providers(config)
        self.fallback_chain = config.fallback_chain
        self.retry_config = config.retry_config
    
    def chat(self, system: str, user: str, **kwargs) -> str:
        """
        Execute chat with automatic fallback
        Returns: LLM response string
        Raises: AllProvidersFailedError if all providers fail
        """
        pass
    
    def _try_provider(self, provider: LLMProvider, 
                      system: str, user: str, **kwargs) -> Optional[str]:
        """Try single provider with retry logic"""
        pass
```

### Integration Points

#### Update `backend/agents/llm.py`

Replace current implementation with new provider system:

```python
from backend.llm import LLMManager, load_config

# Initialize once at module level
_manager = None

def get_manager() -> LLMManager:
    global _manager
    if _manager is None:
        config = load_config()
        _manager = LLMManager(config)
    return _manager

def plan_for(instruction: str, state) -> list[dict]:
    """Generate plan using LLM with fallback to deterministic"""
    manager = get_manager()
    
    try:
        # Try LLM providers
        response = manager.chat(
            system=_get_planning_prompt(),
            user=f'Instruction: "{instruction}"\nReturn JSON only.',
            temperature=0
        )
        return _parse_plan_response(response)
    except AllProvidersFailedError:
        # Fall back to deterministic planning
        return _deterministic_plan(instruction)
```

#### Update `backend/agents/planner.py`

Remove hardcoded logic, rely on LLM manager:

```python
# This file can be simplified or removed
# Planning logic moves to llm.py with LLM manager
```

### Error Handling

#### Custom Exceptions

```python
class LLMError(Exception):
    """Base exception for LLM operations"""
    pass

class RateLimitError(LLMError):
    """Rate limit exceeded"""
    pass

class ProviderUnavailableError(LLMError):
    """Provider not configured or unreachable"""
    pass

class AllProvidersFailedError(LLMError):
    """All providers in fallback chain failed"""
    pass

class TimeoutError(LLMError):
    """Request timeout"""
    pass
```

#### Logging Strategy

```python
import logging

logger = logging.getLogger("regops.llm")

# Log provider attempts
logger.info(f"Attempting provider: {provider.name}")

# Log rate limits
logger.warning(f"Rate limit hit on {provider.name}, trying next provider")

# Log fallbacks
logger.info(f"Falling back to {next_provider.name}")

# Log final fallback
logger.warning("All LLM providers failed, using deterministic fallback")
```

### Testing Strategy

#### Unit Tests

```python
# tests/llm/test_providers.py
def test_gemini_provider_chat()
def test_openrouter_provider_chat()
def test_ollama_provider_availability()

# tests/llm/test_manager.py
def test_fallback_chain()
def test_retry_on_rate_limit()
def test_all_providers_fail()

# tests/llm/test_retry.py
def test_exponential_backoff()
def test_max_retries()
```

#### Integration Tests

```python
# tests/integration/test_agent_with_llm.py
def test_agent_run_with_gemini()
def test_agent_run_with_fallback()
def test_agent_run_offline_mode()
```

### Local Development Setup

#### Without Docker

```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Set up environment
cp .env.example .env
# Edit .env with your API keys

# 3. Start PostgreSQL (if using vector search)
# Option A: Local PostgreSQL
psql -c "CREATE DATABASE regops;"
psql -d regops -c "CREATE EXTENSION vector;"

# Option B: Docker PostgreSQL only
docker run -d -p 5432:5432 \
  -e POSTGRES_USER=regops \
  -e POSTGRES_PASSWORD=regops \
  -e POSTGRES_DB=regops \
  pgvector/pgvector:pg16

# 4. Run development server
python -m uvicorn backend.app:app --reload --port 8000

# 5. Test agent
curl -X POST http://localhost:8000/agent/run \
  -H "Content-Type: application/json" \
  -d '{"instruction":"prepare stability pull list for week 12"}'
```

#### Environment File Template

```bash
# .env.example

# === LLM Configuration ===
LLM_PROVIDER=gemini
LLM_FALLBACK_CHAIN=gemini,openrouter,ollama

# Gemini
GEMINI_API_KEY=your_gemini_api_key_here
GEMINI_MODEL=gemini-1.5-flash

# OpenRouter (fallback)
OPENROUTER_API_KEY=your_openrouter_key_here
OPENROUTER_MODEL=anthropic/claude-3.5-sonnet

# Local LLM (tertiary fallback)
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL=llama3.1:8b

# Retry Configuration
LLM_MAX_RETRIES=3
LLM_RETRY_DELAY=2
LLM_TIMEOUT=60

# === Database Configuration ===
PG_URL=postgresql+psycopg2://regops:regops@localhost:5432/regops
COPILOT_DB=data/copilot.sqlite3

# === Feature Flags ===
EMBEDDINGS_OFFLINE=0  # Set to 1 to disable vector embeddings
```

### Dependencies to Add

```txt
# requirements.txt additions

# Google Gemini
google-generativeai>=0.3.0

# OpenRouter (uses requests, already included)

# Ollama client
ollama>=0.1.0  # optional, can use requests

# Retry utilities
tenacity>=8.2.0

# Better environment management
python-dotenv>=1.0.0
```

### Migration Path

#### Phase 1: Core Infrastructure
- [ ] Create `backend/llm/` module structure
- [ ] Implement base `LLMProvider` interface
- [ ] Implement `LLMConfig` loader
- [ ] Implement retry decorator with exponential backoff

#### Phase 2: Provider Implementations
- [ ] Implement `GeminiProvider`
- [ ] Implement `OpenRouterProvider`
- [ ] Implement `OpenAICompatibleProvider` (for local LLMs)
- [ ] Implement `OllamaProvider`

#### Phase 3: Manager & Fallback
- [ ] Implement `LLMManager` with fallback chain
- [ ] Add rate limit detection and handling
- [ ] Add comprehensive logging
- [ ] Add metrics tracking (provider usage, failures)

#### Phase 4: Integration
- [ ] Update `backend/agents/llm.py` to use new system
- [ ] Update `backend/agents/graph.py` if needed
- [ ] Add environment variable validation
- [ ] Create `.env.example` template

#### Phase 5: Testing & Documentation
- [ ] Write unit tests for all providers
- [ ] Write integration tests for agent workflows
- [ ] Update README with new configuration
- [ ] Add troubleshooting guide
- [ ] Test local development setup (non-Docker)

#### Phase 6: Docker Integration
- [ ] Update Dockerfile with new dependencies
- [ ] Update docker-compose.yml with env vars
- [ ] Test Docker deployment
- [ ] Document Docker + LLM setup

### Success Criteria

- [ ] Can run agents locally without Docker
- [ ] Gemini API integration works with real API key
- [ ] OpenRouter fallback works on Gemini rate limit
- [ ] Local LLM fallback works when cloud providers fail
- [ ] Deterministic fallback still works when all LLMs unavailable
- [ ] Rate limit retry logic prevents immediate failures
- [ ] Configuration via environment variables only
- [ ] Comprehensive logging for debugging
- [ ] All existing tests pass
- [ ] New provider tests achieve >80% coverage

### Future Enhancements

- [ ] Streaming support for real-time responses
- [ ] Cost tracking per provider
- [ ] Provider health monitoring dashboard
- [ ] A/B testing between providers
- [ ] Caching layer for repeated queries
- [ ] Fine-tuned models for specific tasks
- [ ] Multi-modal support (images, documents)

## Notes

- Maintain backward compatibility with existing deterministic fallback
- Ensure audit logs capture which provider was used
- Consider adding provider selection to UI console
- Document rate limits for each provider
- Add cost estimation for cloud providers

## References

- Google Gemini API: https://ai.google.dev/docs
- OpenRouter API: https://openrouter.ai/docs
- Ollama API: https://github.com/ollama/ollama/blob/main/docs/api.md
- OpenAI API Spec: https://platform.openai.com/docs/api-reference
