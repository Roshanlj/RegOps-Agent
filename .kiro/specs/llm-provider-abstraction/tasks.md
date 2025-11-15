# Implementation Plan

- [x] 1. Create core LLM infrastructure





  - Create `backend/llm/` directory structure with `__init__.py`, `config.py`, `provider.py`, `manager.py`, `retry.py`, `exceptions.py`
  - Create `backend/llm/providers/` subdirectory with `__init__.py`
  - _Requirements: 5.1, 5.2, 5.3, 5.4, 5.5_

- [x] 2. Implement exception hierarchy and base provider interface





  - Write custom exception classes in `backend/llm/exceptions.py`: `LLMError`, `RateLimitError`, `ProviderUnavailableError`, `AllProvidersFailedError`, `TimeoutError`
  - Implement abstract `LLMProvider` base class in `backend/llm/provider.py` with `chat()`, `is_available()`, `name` property, and `supports_streaming` property
  - _Requirements: 5.1, 5.2, 5.3, 8.6_

- [x] 3. Implement configuration system





  - Write `RetryConfig` dataclass in `backend/llm/config.py` with `from_env()` class method
  - Write `ProviderConfig` dataclass in `backend/llm/config.py`
  - Write `LLMConfig` dataclass in `backend/llm/config.py` with `from_env()` and `validate()` methods
  - Implement environment variable parsing for all provider configurations (Gemini, OpenRouter, Ollama, Local)
  - _Requirements: 2.1, 2.2, 2.3, 2.4, 2.5, 2.6, 2.7, 2.8, 11.1, 11.2, 11.3, 11.4, 11.5_

- [x] 4. Implement retry logic with exponential backoff





  - Write `with_exponential_backoff` decorator in `backend/llm/retry.py`
  - Implement exponential backoff timing: 2s, 4s, 8s delays
  - Add retry logic for `RateLimitError` and `TimeoutError` only
  - Add comprehensive logging for retry attempts
  - _Requirements: 4.2, 4.3, 4.4, 4.5, 8.2_

- [x] 5. Implement Gemini provider





  - Write `GeminiProvider` class in `backend/llm/providers/gemini.py` implementing `LLMProvider` interface
  - Implement `chat()` method using `google-generativeai` SDK
  - Implement `is_available()` method checking for API key
  - Add rate limit detection from error messages (HTTP 429)
  - Add timeout detection and error mapping to custom exceptions
  - _Requirements: 1.1, 4.1, 5.4, 10.4_

- [x] 6. Implement OpenRouter provider





  - Write `OpenRouterProvider` class in `backend/llm/providers/openrouter.py` implementing `LLMProvider` interface
  - Implement `chat()` method using requests library with OpenAI-compatible format
  - Implement `is_available()` method checking for API key
  - Add explicit HTTP 429 status code detection for rate limits
  - Add timeout handling via requests timeout parameter
  - _Requirements: 1.2, 4.1, 5.4, 10.4_

- [x] 7. Implement Ollama provider





  - Write `OllamaProvider` class in `backend/llm/providers/ollama.py` implementing `LLMProvider` interface
  - Implement `chat()` method using Ollama-specific API format (`/api/chat`)
  - Implement `is_available()` method with network check to `/api/tags` endpoint (2-second timeout)
  - Add availability caching to avoid repeated network checks
  - _Requirements: 1.3, 5.4, 10.1, 10.2, 10.3, 10.5_

- [x] 8. Implement local LLM provider for OpenAI-compatible endpoints





  - Write `LocalLLMProvider` class in `backend/llm/providers/local.py` implementing `LLMProvider` interface
  - Implement `chat()` method using OpenAI-compatible API format
  - Implement `is_available()` method with network check to `/models` endpoint (2-second timeout)
  - Add configurable base URL support for LM Studio, llama.cpp, vLLM, etc.
  - _Requirements: 1.4, 1.5, 5.4, 10.1, 10.2, 10.3_

- [x] 9. Implement LLM manager with fallback chain





  - Write `LLMManager` class in `backend/llm/manager.py`
  - Implement `_init_providers()` method to initialize all configured providers
  - Implement `chat()` method with automatic fallback through provider chain
  - Implement `_get_provider_chain()` method to build ordered provider list
  - Implement `_try_provider_with_retry()` method applying retry decorator
  - Add `last_used_provider` property for audit logging
  - Add `get_available_providers()` method
  - _Requirements: 3.1, 3.2, 3.3, 3.4, 3.5, 7.1, 7.2, 7.3, 7.4, 7.5_

- [x] 10. Implement public API and module initialization





  - Write `backend/llm/__init__.py` with public exports: `get_manager()`, `LLMConfig`, `LLMProvider`, exception classes
  - Implement singleton pattern for `LLMManager` instance
  - Add module-level configuration loading and validation on first import
  - _Requirements: 7.1, 11.1_

- [x] 11. Add comprehensive logging throughout LLM system





  - Add INFO-level logging for provider attempts and successes in `LLMManager`
  - Add WARNING-level logging for rate limits, retries, and unavailable providers
  - Add ERROR-level logging for all providers failed and configuration errors
  - Add logging for fallback transitions between providers
  - Add logging for deterministic fallback usage
  - _Requirements: 8.1, 8.2, 8.3, 8.4, 8.5_

- [x] 12. Update agent LLM integration





  - Refactor `backend/agents/llm.py` to use new `LLMManager` via `get_manager()`
  - Update `plan_for()` function to call `manager.chat()` with system and user prompts
  - Implement `_get_planning_prompt()` helper function
  - Implement `_parse_plan_response()` helper function for JSON parsing
  - Keep existing `_deterministic_plan()` as fallback when `AllProvidersFailedError` is raised
  - Keep existing `_extract_week()` helper function
  - _Requirements: 9.1, 9.2, 9.3_

- [x] 13. Enhance agent graph with provider tracking





  - Update `node_plan()` in `backend/agents/graph.py` to capture `llm_provider` from manager
  - Add `llm_provider` to state dictionary after plan generation
  - _Requirements: 7.5, 12.1, 12.2, 12.3_

- [x] 14. Update database schema for audit trail




  - Add `llm_provider` column to `audit` table in `backend/db.py` using `ALTER TABLE` with error handling
  - Update `add_audit()` function signature to accept optional `provider` parameter
  - Update `add_audit()` INSERT statement to include `llm_provider` column
  - Call `init_db()` migration on module import
  - _Requirements: 12.1, 12.2, 12.3, 12.4, 12.5_

- [x] 15. Update API endpoints with provider audit logging





  - Update `/agent/run` endpoint in `backend/app.py` to extract `llm_provider` from graph output
  - Pass `llm_provider` to `db.add_audit()` call in `/agent/run` endpoint
  - _Requirements: 12.1, 12.2, 12.3, 12.5_

- [x] 16. Update dependencies





  - Add `google-generativeai>=0.3.0` to `requirements.txt`
  - Add `python-dotenv>=1.0.0` to `requirements.txt`
  - Verify `requests>=2.31.0` is present in `requirements.txt`
  - _Requirements: 1.1, 1.2, 2.2, 2.3_

- [x] 17. Create environment configuration template





  - Create `.env.example` file with all LLM configuration variables documented
  - Include examples for Gemini, OpenRouter, Ollama, and local LLM configurations
  - Include retry configuration variables
  - Include database configuration variables
  - Add comments explaining each variable
  - _Requirements: 2.1, 2.2, 2.3, 2.4, 2.5, 2.6, 2.7, 2.8, 6.2_

- [x] 18. Update Docker configuration





  - Update `docker-compose.yml` to pass LLM environment variables to API service
  - Add environment variable mappings for all LLM providers
  - Add environment variable mappings for retry configuration
  - Ensure `.env` file is loaded by docker-compose
  - _Requirements: 9.4, 9.5_

- [x] 19. Update documentation





  - Update `README.md` with LLM provider configuration instructions
  - Add section on local development setup without Docker
  - Add section on environment variable configuration
  - Add troubleshooting guide for common provider issues
  - Document fallback chain behavior
  - _Requirements: 6.1, 6.2, 6.3, 6.4, 6.5_

- [x] 20. Write unit tests for providers





  - Write tests in `tests/llm/test_providers.py` for Gemini provider chat and error handling
  - Write tests for OpenRouter rate limit detection
  - Write tests for Ollama availability check
  - Write tests for local provider timeout handling
  - Mock external API calls in all provider tests
  - _Requirements: 1.1, 1.2, 1.3, 1.4, 1.5, 4.1_

- [x] 21. Write unit tests for manager and retry logic





  - Write tests in `tests/llm/test_manager.py` for fallback chain execution
  - Write tests for all providers failed scenario
  - Write tests for last provider tracking
  - Write tests for skipping unavailable providers
  - Write tests in `tests/llm/test_retry.py` for exponential backoff timing
  - Write tests for max retries exceeded
  - Write tests for no retry on non-retryable errors
  - _Requirements: 3.1, 3.2, 3.3, 3.4, 4.2, 4.3, 4.4, 4.5_

- [x] 22. Write unit tests for configuration





  - Write tests in `tests/llm/test_config.py` for loading configuration from environment
  - Write tests for configuration validation
  - Write tests for default values
  - Write tests for invalid configuration handling
  - _Requirements: 2.1, 2.2, 2.3, 2.4, 2.5, 2.6, 2.7, 2.8, 11.1, 11.2, 11.3, 11.4, 11.5_

- [x] 23. Write integration tests






  - Write tests in `tests/integration/test_agent_with_llm.py` for full agent run with Gemini (requires API key)
  - Write tests for agent fallback when primary provider fails
  - Write tests for agent with no LLM providers (deterministic fallback)
  - _Requirements: 9.1, 9.2, 9.3, 9.4, 9.5_
