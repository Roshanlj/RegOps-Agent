# LLM System Logging Implementation

## Overview

Comprehensive logging has been implemented throughout the LLM system to provide visibility into provider operations, configuration, retries, and fallback behavior. All logging follows Python's standard logging module with appropriate log levels.

## Log Levels and Usage

### INFO Level
Used for normal operational events that indicate successful operations:

- **Configuration Loading**: When configuration is loaded from environment variables
- **Provider Initialization**: When providers are successfully initialized
- **Provider Attempts**: When attempting to use a provider
- **Provider Success**: When a provider successfully returns a response
- **Fallback Transitions**: When falling back from one provider to another
- **Retry Attempts**: When retrying after backoff delay

### WARNING Level
Used for potentially problematic situations that don't prevent operation:

- **Configuration Warnings**: Missing or misconfigured providers
- **Invalid Configuration Values**: Out-of-range retry/timeout values
- **Provider Unavailable**: When a configured provider is not available
- **Rate Limits**: When a provider returns a rate limit error
- **Timeouts**: When a request times out
- **Provider Failures**: When a provider fails with an error
- **Retry Attempts**: When applying exponential backoff

### ERROR Level
Used for error conditions that prevent normal operation:

- **No Providers Configured**: When no LLM providers are available
- **All Providers Failed**: When all providers in the chain fail
- **Configuration Load Failure**: When configuration cannot be loaded
- **Provider Initialization Failure**: When a provider fails to initialize
- **Max Retries Exhausted**: When retry limit is reached

### DEBUG Level
Used for detailed diagnostic information:

- **Configuration Already Loaded**: When skipping reload
- **Skipping Unconfigured Provider**: When a provider in chain is not configured
- **Manager Singleton Access**: When returning existing manager instance

## Logging by Component

### 1. Configuration System (`backend/llm/config.py`)

**Logger Name**: `regops.llm.config`

**Key Log Messages**:
```python
# INFO: Configuration loading
"Loading LLM configuration from environment variables"
"Primary provider: {provider_name}"
"Fallback chain: {chain_list}"
"Configured {provider} provider with model: {model}"
"Retry configuration: max_retries={n}, initial_delay={s}s, timeout={s}s"
"LLM configuration validated successfully"

# WARNING: Configuration issues
"No LLM providers configured via environment variables"
"Primary provider '{name}' not configured - will use first available provider"
"Fallback provider '{name}' not configured - will be skipped in fallback chain"
"LLM_MAX_RETRIES must be positive, using default: 3"
"LLM_TIMEOUT must be positive, using default: 60"
"LLM configuration validation completed with {n} warning(s)"

# ERROR: Critical configuration issues
"No LLM providers configured - system will use deterministic fallback only"
```

### 2. LLM Manager (`backend/llm/manager.py`)

**Logger Name**: `regops.llm.manager`

**Key Log Messages**:
```python
# INFO: Manager operations
"Initializing LLM providers from configuration: {provider_list}"
"Attempting to initialize provider: {name}"
"Successfully initialized and verified provider: {name}"
"LLM Manager initialized with {n} available provider(s): {list}"
"Starting LLM request with provider chain: {chain}"
"Attempting provider: {name} (attempt {n}/{total})"
"Falling back from {prev_provider} to {next_provider}"
"Successfully received response from provider: {name}"

# WARNING: Provider issues
"Provider {name} is configured but not available. Check configuration and connectivity."
"Unknown provider type in configuration: {name}"
"Skipping unconfigured provider in chain: {name}"
"Provider {name} failed with error: {error_type}: {error_msg}"

# ERROR: Critical failures
"Failed to initialize provider {name}: {error_type}: {error_msg}"
"No LLM providers successfully initialized. System will use deterministic fallback only."
"All LLM providers failed after attempting: {attempted_list}. Deterministic fallback will be used. Last error: {error}"
```

### 3. Retry Logic (`backend/llm/retry.py`)

**Logger Name**: `regops.llm.retry`

**Key Log Messages**:
```python
# WARNING: Retry events
"Rate limit encountered (attempt {n}/{max}). Applying exponential backoff: waiting {delay}s before retry. Error: {error}"
"Request timeout (attempt {n}/{max}). Applying exponential backoff: waiting {delay}s before retry. Error: {error}"

# INFO: Retry progress
"Retrying after rate limit backoff (attempt {n}/{max})"
"Retrying after timeout (attempt {n}/{max})"

# ERROR: Retry exhaustion
"Max retries ({n}) exhausted after repeated rate limits. Last error: {error}"
"Max retries ({n}) exhausted after repeated timeouts. Last error: {error}"
```

### 4. Module Initialization (`backend/llm/__init__.py`)

**Logger Name**: `regops.llm`

**Key Log Messages**:
```python
# INFO: Module initialization
"Loading LLM system configuration from environment"
"LLM configuration loaded and validated successfully"
"Creating LLM manager singleton instance"
"LLM manager singleton created and ready for use"

# WARNING: Initialization issues
"Configuration loaded with {n} warning(s)"
"  - {warning_message}"
"LLM configuration validation failed on module import: {error}. Manager will attempt to load configuration on first use."

# DEBUG: Singleton management
"Configuration already loaded, skipping reload"
"Returning existing LLM manager singleton instance"
```

## Example Log Output

### Successful Request with Fallback

```
INFO     | regops.llm.manager        | Starting LLM request with provider chain: ['gemini', 'openrouter']
INFO     | regops.llm.manager        | Attempting provider: gemini (attempt 1/2)
WARNING  | regops.llm.retry          | Rate limit encountered (attempt 1/3). Applying exponential backoff: waiting 2.0s before retry. Error: Gemini rate limit
INFO     | regops.llm.retry          | Retrying after rate limit backoff (attempt 2/3)
WARNING  | regops.llm.retry          | Rate limit encountered (attempt 2/3). Applying exponential backoff: waiting 4.0s before retry. Error: Gemini rate limit
INFO     | regops.llm.retry          | Retrying after rate limit backoff (attempt 3/3)
ERROR    | regops.llm.retry          | Max retries (3) exhausted after repeated rate limits. Last error: Gemini rate limit
WARNING  | regops.llm.manager        | Provider gemini failed with error: RateLimitError: Gemini rate limit
INFO     | regops.llm.manager        | Falling back from gemini to openrouter
INFO     | regops.llm.manager        | Attempting provider: openrouter (attempt 2/2)
INFO     | regops.llm.manager        | Successfully received response from provider: openrouter
```

### All Providers Failed

```
INFO     | regops.llm.manager        | Starting LLM request with provider chain: ['gemini', 'openrouter']
INFO     | regops.llm.manager        | Attempting provider: gemini (attempt 1/2)
WARNING  | regops.llm.manager        | Provider gemini failed with error: ProviderUnavailableError: Gemini error
INFO     | regops.llm.manager        | Falling back from gemini to openrouter
INFO     | regops.llm.manager        | Attempting provider: openrouter (attempt 2/2)
WARNING  | regops.llm.manager        | Provider openrouter failed with error: ProviderUnavailableError: OpenRouter error
ERROR    | regops.llm.manager        | All LLM providers failed after attempting: ['gemini', 'openrouter']. Deterministic fallback will be used. Last error: ProviderUnavailableError: OpenRouter error
```

## Requirements Coverage

This implementation satisfies all requirements from task 11:

✅ **8.1**: INFO-level logging for provider attempts and successes in LLMManager
✅ **8.2**: WARNING-level logging for rate limits, retries, and unavailable providers  
✅ **8.3**: ERROR-level logging for all providers failed and configuration errors
✅ **8.4**: Logging for fallback transitions between providers
✅ **8.5**: Logging for deterministic fallback usage (when all providers fail)

## Integration with Agent System

When integrated with the agent system (tasks 12-15), the logging will provide:

1. **Audit Trail**: Which LLM provider was used for each agent action
2. **Debugging**: Detailed error messages when LLM requests fail
3. **Monitoring**: Visibility into rate limits and provider availability
4. **Compliance**: Complete record of fallback behavior and deterministic usage

## Testing

Run the verification script to see logging in action:

```bash
python verify_logging.py
```

This demonstrates:
- Configuration loading with various scenarios
- Warning messages for missing/invalid configuration
- Error messages for critical issues
- Detailed context in all log messages
