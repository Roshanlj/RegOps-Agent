# Design Document: Multi-Provider LLM Integration

## Overview

This design document describes the architecture for transforming RegOps Copilot from a single-provider fallback system to a flexible multi-provider LLM system with intelligent failover. The system will support cloud providers (Google Gemini, OpenRouter) and local providers (Ollama, LM Studio, llama.cpp) with automatic rate limit handling, exponential backoff retry logic, and seamless fallback to deterministic planning when all LLM providers fail.

### Design Goals

1. **Provider Agnostic**: Unified interface for all LLM providers
2. **Resilient**: Automatic failover on rate limits, timeouts, and errors
3. **Configurable**: Environment-based configuration without code changes
4. **Observable**: Comprehensive logging and audit trails
5. **Backward Compatible**: Maintains existing deterministic fallback
6. **Developer Friendly**: Supports local development without Docker

### Key Design Principles

- **Fail Fast, Fallback Gracefully**: Quick provider availability checks, smooth transitions
- **Single Responsibility**: Each provider handles only its own API integration
- **Configuration Over Code**: All provider settings via environment variables
- **Explicit Over Implicit**: Clear logging of provider attempts and failures

## Architecture

### High-Level Component Diagram

```mermaid
graph TB
    API[FastAPI Endpoints] --> Graph[LangGraph Agent]
    Graph --> LLMManager[LLM Manager]
    LLMManager --> Config[Configuration Loader]
    LLMManager --> Retry[Retry Logic]
    LLMManager --> GeminiProvider[Gemini Provider]
    LLMManager --> OpenRouterProvider[OpenRouter Provider]
    LLMManager --> OllamaProvider[Ollama Provider]
    LLMManager --> LocalProvider[Local LLM Provider]
    LLMManager --> Deterministic[Deterministic Fallback]
    
    GeminiProvider --> GeminiAPI[Google AI API]
    OpenRouterProvider --> OpenRouterAPI[OpenRouter API]
    OllamaProvider --> OllamaAPI[Ollama Server]
    LocalProvider --> LocalAPI[LM Studio / llama.cpp]
    
    LLMManager --> AuditLog[Audit Logger]
    LLMManager --> Metrics[Metrics Tracker]
```

### Module Structure


```
backend/llm/
├── __init__.py              # Public API exports
├── config.py                # Configuration loader and validation
├── provider.py              # Base provider interface (ABC)
├── manager.py               # Provider manager with fallback logic
├── retry.py                 # Retry decorator and utilities
├── exceptions.py            # Custom exception classes
└── providers/
    ├── __init__.py
    ├── gemini.py            # Google Gemini implementation
    ├── openrouter.py        # OpenRouter implementation
    ├── ollama.py            # Ollama implementation
    └── local.py             # OpenAI-compatible local LLMs
```

### Data Flow

```mermaid
sequenceDiagram
    participant Agent as LangGraph Agent
    participant Manager as LLM Manager
    participant Primary as Primary Provider
    participant Secondary as Secondary Provider
    participant Fallback as Deterministic Fallback
    participant Audit as Audit Log

    Agent->>Manager: chat(system, user)
    Manager->>Primary: chat(system, user)
    
    alt Success
        Primary-->>Manager: response
        Manager->>Audit: log(provider=primary, success=true)
        Manager-->>Agent: response
    else Rate Limit (429)
        Primary-->>Manager: RateLimitError
        Manager->>Manager: exponential backoff retry
        Primary-->>Manager: RateLimitError (max retries)
        Manager->>Secondary: chat(system, user)
        Secondary-->>Manager: response
        Manager->>Audit: log(provider=secondary, success=true)
        Manager-->>Agent: response
    else All Providers Fail
        Secondary-->>Manager: Error
        Manager->>Fallback: deterministic_plan()
        Fallback-->>Manager: plan
        Manager->>Audit: log(provider=deterministic, success=true)
        Manager-->>Agent: plan
    end
```

## Components and Interfaces

### 1. Base Provider Interface

**File**: `backend/llm/provider.py`

**Purpose**: Abstract base class defining the contract for all LLM providers.



**Interface Definition**:

```python
from abc import ABC, abstractmethod
from typing import Optional, Dict, Any

class LLMProvider(ABC):
    """Base interface for all LLM providers"""
    
    def __init__(self, config: Dict[str, Any]):
        """Initialize provider with configuration"""
        self.config = config
    
    @abstractmethod
    def chat(self, system: str, user: str, **kwargs) -> str:
        """
        Send chat completion request
        
        Args:
            system: System prompt
            user: User prompt
            **kwargs: Provider-specific parameters (temperature, max_tokens, etc.)
            
        Returns:
            Response text from LLM
            
        Raises:
            RateLimitError: When rate limit is hit (HTTP 429)
            ProviderUnavailableError: When provider is not reachable
            TimeoutError: When request exceeds timeout
        """
        pass
    
    @abstractmethod
    def is_available(self) -> bool:
        """
        Check if provider is configured and reachable
        
        Returns:
            True if provider can be used, False otherwise
        """
        pass
    
    @property
    @abstractmethod
    def name(self) -> str:
        """Provider name for logging (e.g., 'gemini', 'openrouter')"""
        pass
    
    @property
    def supports_streaming(self) -> bool:
        """Whether provider supports streaming responses (future enhancement)"""
        return False
```

**Design Rationale**:
- ABC ensures all providers implement required methods
- `chat()` method provides unified interface regardless of underlying API
- `is_available()` enables fast-fail for misconfigured providers
- `name` property used for logging and audit trails
- `supports_streaming` reserved for future streaming support

### 2. Configuration System

**File**: `backend/llm/config.py`

**Purpose**: Load and validate LLM configuration from environment variables.



**Configuration Schema**:

```python
from dataclasses import dataclass
from typing import List, Optional
import os

@dataclass
class RetryConfig:
    """Retry behavior configuration"""
    max_retries: int = 3
    initial_delay: float = 2.0  # seconds
    timeout: int = 60  # seconds
    
    @classmethod
    def from_env(cls) -> 'RetryConfig':
        return cls(
            max_retries=int(os.getenv('LLM_MAX_RETRIES', '3')),
            initial_delay=float(os.getenv('LLM_RETRY_DELAY', '2.0')),
            timeout=int(os.getenv('LLM_TIMEOUT', '60'))
        )

@dataclass
class ProviderConfig:
    """Individual provider configuration"""
    name: str
    api_key: Optional[str] = None
    model: Optional[str] = None
    base_url: Optional[str] = None
    extra: dict = None  # Provider-specific settings
    
    def __post_init__(self):
        if self.extra is None:
            self.extra = {}

@dataclass
class LLMConfig:
    """Complete LLM system configuration"""
    primary_provider: str
    fallback_chain: List[str]
    providers: dict[str, ProviderConfig]
    retry_config: RetryConfig
    
    @classmethod
    def from_env(cls) -> 'LLMConfig':
        """Load configuration from environment variables"""
        primary = os.getenv('LLM_PROVIDER', 'gemini')
        fallback_str = os.getenv('LLM_FALLBACK_CHAIN', 'gemini,openrouter,ollama')
        fallback_chain = [p.strip() for p in fallback_str.split(',')]
        
        providers = {}
        
        # Gemini configuration
        if os.getenv('GEMINI_API_KEY'):
            providers['gemini'] = ProviderConfig(
                name='gemini',
                api_key=os.getenv('GEMINI_API_KEY'),
                model=os.getenv('GEMINI_MODEL', 'gemini-1.5-flash')
            )
        
        # OpenRouter configuration
        if os.getenv('OPENROUTER_API_KEY'):
            providers['openrouter'] = ProviderConfig(
                name='openrouter',
                api_key=os.getenv('OPENROUTER_API_KEY'),
                model=os.getenv('OPENROUTER_MODEL', 'anthropic/claude-3.5-sonnet')
            )
        
        # Ollama configuration
        if os.getenv('OLLAMA_BASE_URL') or os.getenv('OLLAMA_MODEL'):
            providers['ollama'] = ProviderConfig(
                name='ollama',
                base_url=os.getenv('OLLAMA_BASE_URL', 'http://localhost:11434'),
                model=os.getenv('OLLAMA_MODEL', 'llama3.1:8b')
            )
        
        # Local LLM configuration (OpenAI-compatible)
        if os.getenv('LOCAL_LLM_BASE_URL'):
            providers['local'] = ProviderConfig(
                name='local',
                base_url=os.getenv('LOCAL_LLM_BASE_URL'),
                model=os.getenv('LOCAL_LLM_MODEL', 'local')
            )
        
        return cls(
            primary_provider=primary,
            fallback_chain=fallback_chain,
            providers=providers,
            retry_config=RetryConfig.from_env()
        )
    
    def validate(self) -> List[str]:
        """
        Validate configuration and return list of warnings
        
        Returns:
            List of warning messages (empty if valid)
        """
        warnings = []
        
        if not self.providers:
            warnings.append("No LLM providers configured")
        
        if self.primary_provider not in self.providers:
            warnings.append(f"Primary provider '{self.primary_provider}' not configured")
        
        for provider_name in self.fallback_chain:
            if provider_name not in self.providers:
                warnings.append(f"Fallback provider '{provider_name}' not configured")
        
        if self.retry_config.max_retries < 1:
            warnings.append("LLM_MAX_RETRIES must be positive, using default: 3")
            self.retry_config.max_retries = 3
        
        if self.retry_config.timeout < 1:
            warnings.append("LLM_TIMEOUT must be positive, using default: 60")
            self.retry_config.timeout = 60
        
        return warnings
```

**Design Rationale**:
- Dataclasses provide clean, type-safe configuration objects
- `from_env()` centralizes environment variable parsing
- `validate()` catches configuration errors at startup
- Separate `RetryConfig` allows independent retry tuning per use case

### 3. Provider Implementations

#### 3.1 Gemini Provider

**File**: `backend/llm/providers/gemini.py`



**Implementation Strategy**:

```python
import google.generativeai as genai
from ..provider import LLMProvider
from ..exceptions import RateLimitError, ProviderUnavailableError, TimeoutError

class GeminiProvider(LLMProvider):
    """Google Gemini provider implementation"""
    
    def __init__(self, config):
        super().__init__(config)
        self.api_key = config.get('api_key')
        self.model_name = config.get('model', 'gemini-1.5-flash')
        self._client = None
        
        if self.api_key:
            genai.configure(api_key=self.api_key)
            self._client = genai.GenerativeModel(self.model_name)
    
    def chat(self, system: str, user: str, **kwargs) -> str:
        if not self._client:
            raise ProviderUnavailableError("Gemini not configured")
        
        try:
            # Gemini uses system instruction in model config
            prompt = f"{system}\n\n{user}"
            response = self._client.generate_content(
                prompt,
                generation_config={
                    'temperature': kwargs.get('temperature', 0),
                    'max_output_tokens': kwargs.get('max_tokens', 2048)
                }
            )
            return response.text
        except Exception as e:
            error_str = str(e).lower()
            if '429' in error_str or 'rate limit' in error_str:
                raise RateLimitError(f"Gemini rate limit: {e}")
            elif 'timeout' in error_str:
                raise TimeoutError(f"Gemini timeout: {e}")
            else:
                raise ProviderUnavailableError(f"Gemini error: {e}")
    
    def is_available(self) -> bool:
        return self._client is not None and self.api_key is not None
    
    @property
    def name(self) -> str:
        return 'gemini'
```

**Key Features**:
- Uses official `google-generativeai` SDK
- Maps generic parameters to Gemini-specific config
- Detects rate limits from error messages
- Fast availability check (no network call)

#### 3.2 OpenRouter Provider

**File**: `backend/llm/providers/openrouter.py`

**Implementation Strategy**:

```python
import requests
from ..provider import LLMProvider
from ..exceptions import RateLimitError, ProviderUnavailableError, TimeoutError

class OpenRouterProvider(LLMProvider):
    """OpenRouter provider implementation"""
    
    BASE_URL = "https://openrouter.ai/api/v1"
    
    def __init__(self, config):
        super().__init__(config)
        self.api_key = config.get('api_key')
        self.model = config.get('model', 'anthropic/claude-3.5-sonnet')
    
    def chat(self, system: str, user: str, **kwargs) -> str:
        if not self.api_key:
            raise ProviderUnavailableError("OpenRouter not configured")
        
        headers = {
            'Authorization': f'Bearer {self.api_key}',
            'Content-Type': 'application/json'
        }
        
        payload = {
            'model': self.model,
            'messages': [
                {'role': 'system', 'content': system},
                {'role': 'user', 'content': user}
            ],
            'temperature': kwargs.get('temperature', 0)
        }
        
        try:
            response = requests.post(
                f"{self.BASE_URL}/chat/completions",
                headers=headers,
                json=payload,
                timeout=kwargs.get('timeout', 60)
            )
            
            if response.status_code == 429:
                raise RateLimitError("OpenRouter rate limit exceeded")
            
            response.raise_for_status()
            return response.json()['choices'][0]['message']['content']
            
        except requests.Timeout:
            raise TimeoutError("OpenRouter request timeout")
        except RateLimitError:
            raise
        except Exception as e:
            raise ProviderUnavailableError(f"OpenRouter error: {e}")
    
    def is_available(self) -> bool:
        return self.api_key is not None
    
    @property
    def name(self) -> str:
        return 'openrouter'
```

**Key Features**:
- OpenAI-compatible API format
- Explicit HTTP 429 detection
- Timeout handling via requests library
- No external SDK dependency

#### 3.3 Ollama Provider

**File**: `backend/llm/providers/ollama.py`



**Implementation Strategy**:

```python
import requests
from ..provider import LLMProvider
from ..exceptions import ProviderUnavailableError, TimeoutError

class OllamaProvider(LLMProvider):
    """Ollama local LLM provider"""
    
    def __init__(self, config):
        super().__init__(config)
        self.base_url = config.get('base_url', 'http://localhost:11434')
        self.model = config.get('model', 'llama3.1:8b')
        self._available = None  # Cache availability check
    
    def chat(self, system: str, user: str, **kwargs) -> str:
        if not self.is_available():
            raise ProviderUnavailableError("Ollama not available")
        
        payload = {
            'model': self.model,
            'messages': [
                {'role': 'system', 'content': system},
                {'role': 'user', 'content': user}
            ],
            'stream': False,
            'options': {
                'temperature': kwargs.get('temperature', 0)
            }
        }
        
        try:
            response = requests.post(
                f"{self.base_url}/api/chat",
                json=payload,
                timeout=kwargs.get('timeout', 60)
            )
            response.raise_for_status()
            return response.json()['message']['content']
            
        except requests.Timeout:
            raise TimeoutError("Ollama request timeout")
        except Exception as e:
            raise ProviderUnavailableError(f"Ollama error: {e}")
    
    def is_available(self) -> bool:
        if self._available is not None:
            return self._available
        
        try:
            response = requests.get(f"{self.base_url}/api/tags", timeout=2)
            self._available = response.status_code == 200
        except:
            self._available = False
        
        return self._available
    
    @property
    def name(self) -> str:
        return 'ollama'
```

**Key Features**:
- Ollama-specific API format (`/api/chat`)
- Availability check with 2-second timeout
- Cached availability to avoid repeated checks
- No rate limits (local deployment)

#### 3.4 Local LLM Provider (OpenAI-compatible)

**File**: `backend/llm/providers/local.py`

**Implementation Strategy**:

```python
import requests
from ..provider import LLMProvider
from ..exceptions import ProviderUnavailableError, TimeoutError

class LocalLLMProvider(LLMProvider):
    """OpenAI-compatible local LLM provider (LM Studio, llama.cpp, etc.)"""
    
    def __init__(self, config):
        super().__init__(config)
        self.base_url = config.get('base_url')
        self.model = config.get('model', 'local')
        self._available = None
    
    def chat(self, system: str, user: str, **kwargs) -> str:
        if not self.base_url:
            raise ProviderUnavailableError("Local LLM base URL not configured")
        
        if not self.is_available():
            raise ProviderUnavailableError("Local LLM not available")
        
        payload = {
            'model': self.model,
            'messages': [
                {'role': 'system', 'content': system},
                {'role': 'user', 'content': user}
            ],
            'temperature': kwargs.get('temperature', 0)
        }
        
        try:
            response = requests.post(
                f"{self.base_url}/chat/completions",
                json=payload,
                timeout=kwargs.get('timeout', 60)
            )
            response.raise_for_status()
            return response.json()['choices'][0]['message']['content']
            
        except requests.Timeout:
            raise TimeoutError("Local LLM request timeout")
        except Exception as e:
            raise ProviderUnavailableError(f"Local LLM error: {e}")
    
    def is_available(self) -> bool:
        if self._available is not None:
            return self._available
        
        if not self.base_url:
            return False
        
        try:
            response = requests.get(f"{self.base_url}/models", timeout=2)
            self._available = response.status_code == 200
        except:
            self._available = False
        
        return self._available
    
    @property
    def name(self) -> str:
        return 'local'
```

**Key Features**:
- OpenAI-compatible API format
- Works with LM Studio, llama.cpp server, vLLM, etc.
- Availability check via `/models` endpoint
- Configurable base URL for flexibility

### 4. Retry Logic

**File**: `backend/llm/retry.py`



**Implementation Strategy**:

```python
import time
import logging
from functools import wraps
from typing import Callable, TypeVar, Any
from .exceptions import RateLimitError, TimeoutError

logger = logging.getLogger("regops.llm.retry")

T = TypeVar('T')

def with_exponential_backoff(
    max_retries: int = 3,
    initial_delay: float = 2.0,
    backoff_factor: float = 2.0
) -> Callable:
    """
    Decorator for exponential backoff retry logic
    
    Args:
        max_retries: Maximum number of retry attempts
        initial_delay: Initial delay in seconds
        backoff_factor: Multiplier for each retry (default: 2.0 for exponential)
    
    Returns:
        Decorated function with retry logic
    """
    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @wraps(func)
        def wrapper(*args, **kwargs) -> T:
            delay = initial_delay
            last_exception = None
            
            for attempt in range(max_retries):
                try:
                    return func(*args, **kwargs)
                except RateLimitError as e:
                    last_exception = e
                    if attempt < max_retries - 1:
                        logger.warning(
                            f"Rate limit hit (attempt {attempt + 1}/{max_retries}), "
                            f"retrying in {delay}s: {e}"
                        )
                        time.sleep(delay)
                        delay *= backoff_factor
                    else:
                        logger.error(f"Max retries reached after rate limits: {e}")
                        raise
                except TimeoutError as e:
                    last_exception = e
                    if attempt < max_retries - 1:
                        logger.warning(
                            f"Timeout (attempt {attempt + 1}/{max_retries}), "
                            f"retrying in {delay}s: {e}"
                        )
                        time.sleep(delay)
                        delay *= backoff_factor
                    else:
                        logger.error(f"Max retries reached after timeouts: {e}")
                        raise
            
            # Should not reach here, but just in case
            if last_exception:
                raise last_exception
            
        return wrapper
    return decorator
```

**Design Rationale**:
- Decorator pattern allows easy application to any function
- Exponential backoff: 2s → 4s → 8s (configurable)
- Only retries on `RateLimitError` and `TimeoutError`
- Other exceptions propagate immediately
- Comprehensive logging for debugging

### 5. LLM Manager

**File**: `backend/llm/manager.py`

**Purpose**: Orchestrates provider selection, fallback chain, and deterministic fallback.



**Implementation Strategy**:

```python
import logging
from typing import Optional, List, Dict, Any
from .config import LLMConfig
from .provider import LLMProvider
from .retry import with_exponential_backoff
from .exceptions import AllProvidersFailedError, ProviderUnavailableError

logger = logging.getLogger("regops.llm.manager")

class LLMManager:
    """Manages multiple LLM providers with automatic fallback"""
    
    def __init__(self, config: LLMConfig):
        self.config = config
        self.providers: Dict[str, LLMProvider] = {}
        self._init_providers()
        self._last_used_provider: Optional[str] = None
    
    def _init_providers(self):
        """Initialize all configured providers"""
        from .providers.gemini import GeminiProvider
        from .providers.openrouter import OpenRouterProvider
        from .providers.ollama import OllamaProvider
        from .providers.local import LocalLLMProvider
        
        provider_classes = {
            'gemini': GeminiProvider,
            'openrouter': OpenRouterProvider,
            'ollama': OllamaProvider,
            'local': LocalLLMProvider
        }
        
        for name, provider_config in self.config.providers.items():
            if name in provider_classes:
                try:
                    provider = provider_classes[name](provider_config.__dict__)
                    if provider.is_available():
                        self.providers[name] = provider
                        logger.info(f"Initialized provider: {name}")
                    else:
                        logger.warning(f"Provider {name} configured but not available")
                except Exception as e:
                    logger.error(f"Failed to initialize provider {name}: {e}")
    
    def chat(self, system: str, user: str, **kwargs) -> str:
        """
        Execute chat with automatic fallback through provider chain
        
        Args:
            system: System prompt
            user: User prompt
            **kwargs: Additional parameters (temperature, max_tokens, etc.)
        
        Returns:
            LLM response string
        
        Raises:
            AllProvidersFailedError: If all providers in chain fail
        """
        # Build ordered list of providers to try
        providers_to_try = self._get_provider_chain()
        
        if not providers_to_try:
            logger.warning("No LLM providers available, using deterministic fallback")
            raise AllProvidersFailedError("No providers configured")
        
        last_error = None
        
        for provider_name in providers_to_try:
            provider = self.providers.get(provider_name)
            if not provider:
                logger.debug(f"Skipping unconfigured provider: {provider_name}")
                continue
            
            try:
                logger.info(f"Attempting provider: {provider_name}")
                response = self._try_provider_with_retry(provider, system, user, **kwargs)
                self._last_used_provider = provider_name
                logger.info(f"Successfully used provider: {provider_name}")
                return response
                
            except Exception as e:
                last_error = e
                logger.warning(f"Provider {provider_name} failed: {e}")
                continue
        
        # All providers failed
        logger.error("All LLM providers failed")
        raise AllProvidersFailedError(f"All providers failed. Last error: {last_error}")
    
    def _get_provider_chain(self) -> List[str]:
        """Get ordered list of providers to try"""
        chain = []
        
        # Start with primary provider if available
        if self.config.primary_provider in self.providers:
            chain.append(self.config.primary_provider)
        
        # Add fallback chain, avoiding duplicates
        for provider_name in self.config.fallback_chain:
            if provider_name not in chain and provider_name in self.providers:
                chain.append(provider_name)
        
        return chain
    
    def _try_provider_with_retry(
        self, 
        provider: LLMProvider, 
        system: str, 
        user: str, 
        **kwargs
    ) -> str:
        """Try a single provider with retry logic"""
        retry_config = self.config.retry_config
        
        @with_exponential_backoff(
            max_retries=retry_config.max_retries,
            initial_delay=retry_config.initial_delay
        )
        def _call():
            return provider.chat(system, user, timeout=retry_config.timeout, **kwargs)
        
        return _call()
    
    @property
    def last_used_provider(self) -> Optional[str]:
        """Get the name of the last successfully used provider"""
        return self._last_used_provider
    
    def get_available_providers(self) -> List[str]:
        """Get list of currently available provider names"""
        return list(self.providers.keys())
```

**Key Features**:
- Initializes all providers on startup
- Skips unavailable providers automatically
- Applies retry logic per provider
- Tracks last successful provider for audit logs
- Raises `AllProvidersFailedError` when all fail

### 6. Exception Hierarchy

**File**: `backend/llm/exceptions.py`

**Implementation**:

```python
class LLMError(Exception):
    """Base exception for all LLM-related errors"""
    pass

class RateLimitError(LLMError):
    """Raised when provider rate limit is exceeded (HTTP 429)"""
    pass

class ProviderUnavailableError(LLMError):
    """Raised when provider is not configured or unreachable"""
    pass

class AllProvidersFailedError(LLMError):
    """Raised when all providers in fallback chain fail"""
    pass

class TimeoutError(LLMError):
    """Raised when request exceeds configured timeout"""
    pass
```

**Design Rationale**:
- Clear exception hierarchy for specific error handling
- Inherits from base `LLMError` for catch-all handling
- Enables different retry strategies per exception type

## Data Models

### Configuration Models

Already defined in Components section (see `config.py`).

### Audit Log Extension

**Current Schema** (in `backend/db.py`):
```sql
CREATE TABLE IF NOT EXISTS audit (
    id INTEGER PRIMARY KEY,
    ts TEXT,
    actor TEXT,
    action TEXT,
    payload TEXT
)
```

**Extended Schema**:
```sql
CREATE TABLE IF NOT EXISTS audit (
    id INTEGER PRIMARY KEY,
    ts TEXT,
    actor TEXT,
    action TEXT,
    payload TEXT,
    llm_provider TEXT  -- NEW: tracks which provider was used
)
```

**Migration Strategy**:
- Add column with `ALTER TABLE` if not exists
- Default to NULL for existing rows
- Populate for new agent runs

## Error Handling

### Error Flow Diagram



```mermaid
graph TD
    Start[LLM Request] --> TryPrimary[Try Primary Provider]
    TryPrimary --> CheckError{Error Type?}
    
    CheckError -->|Rate Limit| Retry[Exponential Backoff Retry]
    CheckError -->|Timeout| Retry
    CheckError -->|Other Error| NextProvider[Try Next Provider]
    CheckError -->|Success| Return[Return Response]
    
    Retry --> MaxRetries{Max Retries?}
    MaxRetries -->|No| TryPrimary
    MaxRetries -->|Yes| NextProvider
    
    NextProvider --> MoreProviders{More Providers?}
    MoreProviders -->|Yes| TryPrimary
    MoreProviders -->|No| Deterministic[Deterministic Fallback]
    
    Deterministic --> Return
    Return --> End[End]
```

### Error Handling Strategy

1. **Rate Limits (HTTP 429)**:
   - Retry with exponential backoff (2s, 4s, 8s)
   - After max retries, move to next provider
   - Log each retry attempt

2. **Timeouts**:
   - Retry with exponential backoff
   - After max retries, move to next provider
   - Configurable timeout per request

3. **Provider Unavailable**:
   - Skip to next provider immediately
   - No retries (fast-fail)
   - Log warning

4. **All Providers Failed**:
   - Fall back to deterministic planning
   - Log error with details
   - Continue execution (graceful degradation)

5. **Configuration Errors**:
   - Validate on startup
   - Log warnings for misconfiguration
   - Use sensible defaults where possible

### Logging Strategy

**Log Levels**:
- `INFO`: Provider attempts, successes, fallbacks
- `WARNING`: Rate limits, retries, unavailable providers
- `ERROR`: All providers failed, configuration errors

**Log Format**:
```python
logger.info(f"Attempting provider: {provider_name}")
logger.warning(f"Rate limit hit on {provider_name}, retrying in {delay}s")
logger.info(f"Falling back to {next_provider}")
logger.error(f"All LLM providers failed: {error}")
logger.warning(f"Using deterministic fallback")
```

## Testing Strategy

### Unit Tests

**File**: `tests/llm/test_providers.py`

```python
def test_gemini_provider_chat():
    """Test Gemini provider chat functionality"""
    # Mock genai.GenerativeModel
    # Verify correct API calls
    # Test error handling

def test_openrouter_rate_limit():
    """Test OpenRouter rate limit detection"""
    # Mock requests.post to return 429
    # Verify RateLimitError is raised

def test_ollama_availability():
    """Test Ollama availability check"""
    # Mock requests.get to /api/tags
    # Verify availability detection

def test_local_provider_timeout():
    """Test local provider timeout handling"""
    # Mock requests.post with timeout
    # Verify TimeoutError is raised
```

**File**: `tests/llm/test_manager.py`

```python
def test_manager_fallback_chain():
    """Test manager tries providers in order"""
    # Mock multiple providers
    # First fails, second succeeds
    # Verify correct order

def test_manager_all_providers_fail():
    """Test AllProvidersFailedError when all fail"""
    # Mock all providers to fail
    # Verify exception is raised

def test_manager_tracks_last_provider():
    """Test manager tracks successful provider"""
    # Execute chat
    # Verify last_used_provider is set

def test_manager_skips_unavailable():
    """Test manager skips unavailable providers"""
    # Configure provider but mark unavailable
    # Verify it's skipped in chain
```

**File**: `tests/llm/test_retry.py`

```python
def test_exponential_backoff():
    """Test exponential backoff timing"""
    # Mock function that fails twice then succeeds
    # Verify delays: 2s, 4s

def test_max_retries_exceeded():
    """Test exception after max retries"""
    # Mock function that always fails
    # Verify exception after 3 attempts

def test_no_retry_on_other_errors():
    """Test immediate failure on non-retryable errors"""
    # Mock function that raises ProviderUnavailableError
    # Verify no retries
```

**File**: `tests/llm/test_config.py`

```python
def test_config_from_env():
    """Test configuration loading from environment"""
    # Set environment variables
    # Load config
    # Verify correct values

def test_config_validation():
    """Test configuration validation"""
    # Create invalid config
    # Verify warnings are returned

def test_config_defaults():
    """Test default values"""
    # Load config with minimal env vars
    # Verify defaults are applied
```

### Integration Tests

**File**: `tests/integration/test_agent_with_llm.py`

```python
def test_agent_run_with_gemini():
    """Test full agent run with Gemini provider"""
    # Requires GEMINI_API_KEY
    # Execute agent with real API
    # Verify plan generation

def test_agent_run_with_fallback():
    """Test agent falls back when primary fails"""
    # Configure primary to fail
    # Verify secondary is used

def test_agent_run_offline_mode():
    """Test agent with no LLM providers"""
    # No API keys configured
    # Verify deterministic fallback works
```

### Test Coverage Goals

- Unit tests: >90% coverage
- Integration tests: Critical paths covered
- Mock external APIs in unit tests
- Use real APIs in integration tests (optional, requires keys)

## Integration with Existing System

### Changes to `backend/agents/llm.py`

**Before**:
```python
def plan_for(instruction: str, state) -> list[dict]:
    if BASE:
        try:
            return _llm_plan(instruction)
        except Exception:
            pass
    # deterministic fallback
    return _deterministic_plan(instruction)
```

**After**:
```python
from backend.llm import get_manager
from backend.llm.exceptions import AllProvidersFailedError

def plan_for(instruction: str, state) -> list[dict]:
    """Generate plan using LLM with fallback to deterministic"""
    try:
        manager = get_manager()
        response = manager.chat(
            system=_get_planning_prompt(),
            user=f'Instruction: "{instruction}"\nReturn JSON only.',
            temperature=0
        )
        plan = _parse_plan_response(response)
        return plan
    except AllProvidersFailedError:
        # Fall back to deterministic planning
        return _deterministic_plan(instruction, state)

def _get_planning_prompt() -> str:
    return (
        "You output ONLY JSON with a 'plan' array of tool steps.\n"
        "Tools: lims.create_pull_list{week}, sheets.append_rows{}, "
        "jira.create_issue{summary,labels,idem_key}, "
        "mailer.draft_email{to,subject,body}. "
        "Include week, idem_key='stability-week-<week>'."
    )

def _parse_plan_response(response: str) -> list[dict]:
    import json, re
    txt = re.sub(r"^```json|```$", "", response, flags=re.I|re.M).strip()
    return json.loads(txt)["plan"]

def _deterministic_plan(instruction: str, state) -> list[dict]:
    w = _extract_week(instruction)
    idem = f"stability-week-{w}"
    return [
        {"tool":"lims.create_pull_list","args":{"week": w}},
        {"tool":"sheets.append_rows"},
        {"tool":"jira.create_issue","args":{
            "summary": f"Weekly stability pulls prepared (W{w})",
            "labels":["stability",f"week{w}"],
            "idem_key": idem
        }},
        {"tool":"mailer.draft_email","args":{
            "to":["qa@example.com"],
            "subject": f"Week {w} stability pull list",
            "body":"See table below"
        }}
    ]
```

### Changes to `backend/agents/graph.py`

**Minimal changes required**:
- Import updated `plan_for` function
- No changes to graph structure
- Audit logging enhanced to capture provider

**Enhanced Audit Logging**:
```python
def node_plan(state: State) -> State:
    state = dict(state)
    plan = plan_for(state["instruction"], state)
    
    # Track which provider was used
    from backend.llm import get_manager
    manager = get_manager()
    state["llm_provider"] = manager.last_used_provider or "deterministic"
    
    validated = []
    for step in plan:
        action = step["tool"]
        args = validate_action(action, step.get("args", {}))
        validated.append({"tool": action, "args": args})
    state["plan"] = validated
    return state
```

### Changes to `backend/app.py`

**Enhanced Audit Logging**:
```python
@app.post("/agent/run")
def agent_run(req: AgentReq):
    out = GRAPH.invoke({"instruction": req.instruction})
    
    # Include provider in audit log
    db.add_audit(
        "AGENT",
        "run_graph",
        {
            "instruction": req.instruction,
            "review": out.get("review", {}),
            "iter": out.get("iter", 0),
            "llm_provider": out.get("llm_provider", "unknown")
        }
    )
    return out
```

### Changes to `backend/db.py`

**Add Provider Column**:
```python
def init_db():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    
    # Existing tables...
    
    # Add llm_provider column if not exists
    try:
        c.execute("ALTER TABLE audit ADD COLUMN llm_provider TEXT")
    except sqlite3.OperationalError:
        pass  # Column already exists
    
    conn.commit()
    conn.close()

def add_audit(actor: str, action: str, payload: dict, provider: str = None):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute(
        "INSERT INTO audit (ts, actor, action, payload, llm_provider) VALUES (?, ?, ?, ?, ?)",
        (datetime.now().isoformat(), actor, action, json.dumps(payload), provider)
    )
    conn.commit()
    conn.close()
```

## Deployment Considerations

### Environment Variables

**Production `.env` Example**:
```bash
# Primary: Gemini
LLM_PROVIDER=gemini
GEMINI_API_KEY=your_production_key
GEMINI_MODEL=gemini-1.5-flash

# Fallback: OpenRouter
OPENROUTER_API_KEY=your_openrouter_key
OPENROUTER_MODEL=anthropic/claude-3.5-sonnet

# Fallback chain
LLM_FALLBACK_CHAIN=gemini,openrouter

# Retry configuration
LLM_MAX_RETRIES=3
LLM_RETRY_DELAY=2
LLM_TIMEOUT=60

# Database
PG_URL=postgresql+psycopg2://regops:regops@db:5432/regops
COPILOT_DB=data/copilot.sqlite3
```

**Local Development `.env` Example**:
```bash
# Local: Ollama
LLM_PROVIDER=ollama
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL=llama3.1:8b

# Fallback: Gemini (for testing)
GEMINI_API_KEY=your_dev_key
GEMINI_MODEL=gemini-1.5-flash

# Fallback chain
LLM_FALLBACK_CHAIN=ollama,gemini

# Database (local PostgreSQL)
PG_URL=postgresql+psycopg2://regops:regops@localhost:5432/regops
COPILOT_DB=data/copilot.sqlite3
```

### Docker Configuration

**Updated `docker-compose.yml`**:
```yaml
version: '3.8'

services:
  api:
    build: .
    ports:
      - "8000:8000"
    environment:
      - LLM_PROVIDER=${LLM_PROVIDER:-gemini}
      - GEMINI_API_KEY=${GEMINI_API_KEY}
      - GEMINI_MODEL=${GEMINI_MODEL:-gemini-1.5-flash}
      - OPENROUTER_API_KEY=${OPENROUTER_API_KEY}
      - OPENROUTER_MODEL=${OPENROUTER_MODEL}
      - LLM_FALLBACK_CHAIN=${LLM_FALLBACK_CHAIN:-gemini,openrouter}
      - LLM_MAX_RETRIES=${LLM_MAX_RETRIES:-3}
      - LLM_TIMEOUT=${LLM_TIMEOUT:-60}
      - PG_URL=postgresql+psycopg2://regops:regops@db:5432/regops
      - COPILOT_DB=data/copilot.sqlite3
    volumes:
      - ./data:/app/data
    depends_on:
      - db

  db:
    image: pgvector/pgvector:pg16
    environment:
      - POSTGRES_USER=regops
      - POSTGRES_PASSWORD=regops
      - POSTGRES_DB=regops
    ports:
      - "5432:5432"
    volumes:
      - pgdata:/var/lib/postgresql/data

volumes:
  pgdata:
```

### Dependency Updates

**Updated `requirements.txt`**:
```txt
# Existing dependencies
fastapi==0.115.5
uvicorn[standard]==0.32.0
pydantic==2.9.2
python-multipart==0.0.17
psycopg2-binary==2.9.10
sqlalchemy==2.0.36
pgvector==0.2.5
sentence-transformers==3.2.1
langgraph==0.2.35
jinja2==3.1.4
ragas==0.1.9

# New dependencies for LLM providers
google-generativeai>=0.3.0
python-dotenv>=1.0.0
requests>=2.31.0  # Already included, but ensure version
```

## Performance Considerations

### Latency

- **Provider Availability Check**: <2s per provider
- **Retry Delays**: 2s, 4s, 8s (exponential backoff)
- **Timeout**: 60s default (configurable)
- **Total Max Latency**: ~180s worst case (3 providers × 3 retries × 20s avg)

### Optimization Strategies

1. **Parallel Availability Checks**: Check all providers concurrently on startup
2. **Provider Caching**: Cache availability status for 5 minutes
3. **Fast-Fail**: Skip unavailable providers immediately
4. **Timeout Tuning**: Adjust per environment (local: 30s, cloud: 60s)

### Resource Usage

- **Memory**: Minimal overhead (~10MB for provider objects)
- **Network**: Only active provider makes requests
- **CPU**: Negligible (mostly I/O bound)

## Security Considerations

### API Key Management

- **Never commit API keys**: Use `.env` files (gitignored)
- **Environment variables only**: No hardcoded keys
- **Separate keys per environment**: Dev, staging, production
- **Rotate keys regularly**: Follow provider best practices

### Request Validation

- **Input sanitization**: Validate prompts before sending
- **Output validation**: Parse and validate LLM responses
- **Error message sanitization**: Don't expose API keys in logs

### Audit Trail

- **Log provider usage**: Track which provider handled each request
- **Log failures**: Record why providers failed (without sensitive data)
- **Compliance**: Maintain audit logs for regulatory requirements

## Future Enhancements

### Phase 2 Features

1. **Streaming Support**: Real-time response streaming
2. **Cost Tracking**: Monitor API costs per provider
3. **A/B Testing**: Compare provider quality
4. **Caching Layer**: Cache repeated queries
5. **Provider Health Dashboard**: Monitor provider status
6. **Fine-tuned Models**: Custom models for specific tasks
7. **Multi-modal Support**: Images, documents, audio

### Scalability

- **Connection Pooling**: Reuse HTTP connections
- **Rate Limit Prediction**: Proactive provider switching
- **Load Balancing**: Distribute requests across providers
- **Circuit Breaker**: Temporarily disable failing providers

## Success Metrics

### Functional Metrics

- [ ] All providers initialize successfully
- [ ] Fallback chain works correctly
- [ ] Rate limit retry logic prevents immediate failures
- [ ] Deterministic fallback still works
- [ ] Audit logs capture provider information

### Performance Metrics

- [ ] Provider availability check <2s
- [ ] Average request latency <5s (cloud providers)
- [ ] Average request latency <2s (local providers)
- [ ] Fallback transition <1s

### Quality Metrics

- [ ] Unit test coverage >90%
- [ ] Integration tests pass with real APIs
- [ ] No regressions in existing functionality
- [ ] Documentation complete and accurate

## References

- [Google Gemini API Documentation](https://ai.google.dev/docs)
- [OpenRouter API Documentation](https://openrouter.ai/docs)
- [Ollama API Documentation](https://github.com/ollama/ollama/blob/main/docs/api.md)
- [OpenAI API Specification](https://platform.openai.com/docs/api-reference)
- [LangGraph Documentation](https://langchain-ai.github.io/langgraph/)
- [FastAPI Documentation](https://fastapi.tiangolo.com/)
