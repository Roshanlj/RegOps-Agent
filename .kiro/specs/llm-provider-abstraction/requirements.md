# Requirements Document

## Introduction

This document specifies the requirements for transforming RegOps Copilot from a fallback-based system to a truly agentic system with flexible, multi-provider LLM integration. The system shall support multiple LLM providers (cloud and local) with intelligent failover, automatic rate limit handling, and easy configuration through environment variables. This enhancement enables local development without Docker while maintaining production deployment capabilities.

## Glossary

- **LLM Provider**: A service or system that provides Large Language Model inference capabilities (e.g., Google Gemini, OpenRouter, Ollama)
- **Primary Provider**: The first LLM provider attempted for each request, configured via environment variables
- **Fallback Chain**: An ordered sequence of LLM providers to attempt when the primary provider fails
- **Rate Limit**: A restriction imposed by an LLM provider on the number of requests within a time period (typically indicated by HTTP 429 status)
- **Provider Manager**: The system component responsible for coordinating LLM provider selection and fallback logic
- **Deterministic Fallback**: The existing rule-based system that operates without LLM inference
- **Cloud Provider**: An LLM provider accessed via internet API (e.g., Gemini, OpenRouter)
- **Local Provider**: An LLM provider running on localhost (e.g., Ollama, LM Studio)
- **Exponential Backoff**: A retry strategy where wait time doubles after each failed attempt
- **RegOps Copilot**: The agentic QA/QC assistant system being enhanced

## Requirements

### Requirement 1: Multi-Provider Support

**User Story:** As a developer, I want to configure multiple LLM providers, so that I can choose the best provider for my deployment environment and budget constraints.

#### Acceptance Criteria

1. THE RegOps Copilot SHALL support Google Gemini as a cloud provider with models gemini-1.5-pro, gemini-1.5-flash, and gemini-2.0-flash-exp
2. THE RegOps Copilot SHALL support OpenRouter as a cloud provider with configurable model selection
3. THE RegOps Copilot SHALL support Ollama as a local provider with configurable base URL and model
4. THE RegOps Copilot SHALL support LM Studio as a local provider through OpenAI-compatible API endpoints
5. THE RegOps Copilot SHALL support any OpenAI-compatible API endpoint as a local provider with configurable base URL

### Requirement 2: Environment-Based Configuration

**User Story:** As a system administrator, I want to configure LLM providers through environment variables, so that I can deploy the system across different environments without code changes.

#### Acceptance Criteria

1. WHEN the environment variable LLM_PROVIDER is set, THE RegOps Copilot SHALL use the specified provider as the primary provider
2. WHEN the environment variable GEMINI_API_KEY is set, THE RegOps Copilot SHALL configure the Gemini provider with the provided API key
3. WHEN the environment variable OPENROUTER_API_KEY is set, THE RegOps Copilot SHALL configure the OpenRouter provider with the provided API key
4. WHEN the environment variable LLM_FALLBACK_CHAIN is set, THE RegOps Copilot SHALL attempt providers in the specified comma-separated order
5. WHEN the environment variable LLM_FALLBACK_CHAIN is not set, THE RegOps Copilot SHALL use the default fallback chain of gemini, openrouter, and ollama
6. WHEN the environment variable LOCAL_LLM_BASE_URL is set, THE RegOps Copilot SHALL configure the local provider with the specified endpoint URL
7. WHEN the environment variable LLM_MAX_RETRIES is set, THE RegOps Copilot SHALL retry failed requests up to the specified number of times
8. WHEN the environment variable LLM_TIMEOUT is set, THE RegOps Copilot SHALL terminate requests that exceed the specified timeout in seconds

### Requirement 3: Intelligent Fallback Chain

**User Story:** As a developer, I want automatic provider failover, so that my application continues functioning when the primary provider is unavailable or rate-limited.

#### Acceptance Criteria

1. WHEN the primary provider returns an HTTP 429 status code, THE RegOps Copilot SHALL attempt the next provider in the fallback chain within 2 seconds
2. WHEN the primary provider times out, THE RegOps Copilot SHALL attempt the next provider in the fallback chain
3. WHEN the primary provider returns an error response, THE RegOps Copilot SHALL attempt the next provider in the fallback chain
4. WHEN all providers in the fallback chain fail, THE RegOps Copilot SHALL use the deterministic fallback system
5. THE RegOps Copilot SHALL complete each fallback attempt within the configured timeout period before proceeding to the next provider

### Requirement 4: Rate Limit Handling

**User Story:** As a developer, I want automatic rate limit detection and retry logic, so that temporary rate limits do not cause immediate failures.

#### Acceptance Criteria

1. WHEN a provider returns an HTTP 429 status code, THE RegOps Copilot SHALL detect the rate limit condition
2. WHEN a rate limit is detected on the first retry, THE RegOps Copilot SHALL wait 2 seconds before retrying
3. WHEN a rate limit is detected on the second retry, THE RegOps Copilot SHALL wait 4 seconds before retrying
4. WHEN a rate limit is detected on the third retry, THE RegOps Copilot SHALL wait 8 seconds before retrying
5. WHEN the maximum retry count is reached for a provider, THE RegOps Copilot SHALL proceed to the next provider in the fallback chain

### Requirement 5: Provider Abstraction Interface

**User Story:** As a developer, I want a unified interface for all LLM providers, so that I can add new providers without modifying existing code.

#### Acceptance Criteria

1. THE RegOps Copilot SHALL define a base LLMProvider interface with a chat method accepting system prompt and user prompt parameters
2. THE RegOps Copilot SHALL define a base LLMProvider interface with an is_available method returning boolean availability status
3. THE RegOps Copilot SHALL define a base LLMProvider interface with a name property returning the provider identifier string
4. THE RegOps Copilot SHALL implement the LLMProvider interface for each supported provider
5. THE RegOps Copilot SHALL allow provider implementations to accept provider-specific configuration parameters

### Requirement 6: Local Development Support

**User Story:** As a developer, I want to run the agent system locally without Docker, so that I can iterate quickly during development.

#### Acceptance Criteria

1. WHEN the developer installs Python dependencies from requirements.txt, THE RegOps Copilot SHALL run without Docker containers
2. WHEN the developer configures environment variables in a .env file, THE RegOps Copilot SHALL load the configuration on startup
3. WHEN the developer starts the uvicorn server locally, THE RegOps Copilot SHALL accept API requests on port 8000
4. WHEN the developer uses a local PostgreSQL instance, THE RegOps Copilot SHALL connect using the PG_URL environment variable
5. WHEN the developer uses a Docker PostgreSQL container, THE RegOps Copilot SHALL connect to the container from the host system

### Requirement 7: Provider Manager

**User Story:** As a system component, I want a centralized provider manager, so that provider selection and fallback logic is consistent across all agent operations.

#### Acceptance Criteria

1. THE RegOps Copilot SHALL implement a Provider Manager component that initializes all configured providers on startup
2. WHEN a chat request is received, THE Provider Manager SHALL attempt the primary provider first
3. WHEN a provider fails, THE Provider Manager SHALL log the failure reason and attempt the next provider
4. WHEN all providers fail, THE Provider Manager SHALL raise an AllProvidersFailedError exception
5. THE Provider Manager SHALL track which provider successfully handled each request for audit logging

### Requirement 8: Error Handling and Logging

**User Story:** As a system administrator, I want comprehensive error logging, so that I can diagnose provider failures and rate limit issues.

#### Acceptance Criteria

1. WHEN a provider attempt begins, THE RegOps Copilot SHALL log the provider name at INFO level
2. WHEN a rate limit is detected, THE RegOps Copilot SHALL log the provider name and retry delay at WARNING level
3. WHEN a provider fails, THE RegOps Copilot SHALL log the provider name and error message at WARNING level
4. WHEN fallback to the next provider occurs, THE RegOps Copilot SHALL log both provider names at INFO level
5. WHEN all providers fail and deterministic fallback is used, THE RegOps Copilot SHALL log the fallback event at WARNING level
6. THE RegOps Copilot SHALL define custom exception classes for RateLimitError, ProviderUnavailableError, AllProvidersFailedError, and TimeoutError

### Requirement 9: Backward Compatibility

**User Story:** As a system maintainer, I want the new LLM system to maintain backward compatibility, so that existing functionality continues working without modification.

#### Acceptance Criteria

1. WHEN all LLM providers fail, THE RegOps Copilot SHALL execute the existing deterministic fallback logic
2. WHEN the EMBEDDINGS_OFFLINE environment variable is set to 1, THE RegOps Copilot SHALL use keyword-based search instead of vector embeddings
3. THE RegOps Copilot SHALL maintain all existing API endpoints with unchanged request and response formats
4. THE RegOps Copilot SHALL continue logging all actions to the audit table with the same schema
5. THE RegOps Copilot SHALL maintain compatibility with the existing Docker deployment configuration

### Requirement 10: Provider Availability Detection

**User Story:** As a developer, I want automatic provider availability detection, so that unavailable providers are skipped without causing delays.

#### Acceptance Criteria

1. WHEN a provider is initialized, THE RegOps Copilot SHALL check if required configuration parameters are present
2. WHEN a local provider is configured, THE RegOps Copilot SHALL verify the endpoint is reachable before marking it available
3. WHEN a provider is marked unavailable, THE RegOps Copilot SHALL skip it in the fallback chain
4. WHEN a cloud provider lacks an API key, THE RegOps Copilot SHALL mark it as unavailable
5. THE RegOps Copilot SHALL complete availability checks within 2 seconds per provider

### Requirement 11: Configuration Validation

**User Story:** As a system administrator, I want configuration validation on startup, so that I can identify misconfiguration before deployment.

#### Acceptance Criteria

1. WHEN the RegOps Copilot starts, THE system SHALL validate that at least one provider is configured and available
2. WHEN an invalid provider name is specified in LLM_PROVIDER, THE RegOps Copilot SHALL log a warning and use the first available provider
3. WHEN an invalid model name is specified, THE RegOps Copilot SHALL log a warning and use the provider default model
4. WHEN LLM_MAX_RETRIES is set to a non-positive integer, THE RegOps Copilot SHALL use the default value of 3
5. WHEN LLM_TIMEOUT is set to a non-positive integer, THE RegOps Copilot SHALL use the default value of 60 seconds

### Requirement 12: Audit Trail Enhancement

**User Story:** As a compliance officer, I want audit logs to include which LLM provider was used, so that I can track provider usage for compliance and cost analysis.

#### Acceptance Criteria

1. WHEN an agent action completes successfully, THE RegOps Copilot SHALL record the provider name in the audit log
2. WHEN an agent action uses deterministic fallback, THE RegOps Copilot SHALL record "deterministic" as the provider name
3. WHEN multiple providers are attempted, THE RegOps Copilot SHALL record only the successful provider name
4. THE RegOps Copilot SHALL maintain the existing audit log schema with provider information added as a new field
5. THE RegOps Copilot SHALL ensure audit log entries include timestamp, actor, action, payload, and provider name
