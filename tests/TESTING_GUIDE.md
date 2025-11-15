# Testing Guide for RegOps Copilot LLM System

## Overview

This guide covers the testing infrastructure for the multi-provider LLM integration system.

## Test Structure

```
tests/
├── __init__.py                 # Test package initialization
├── llm/
│   ├── __init__.py            # LLM tests package
│   ├── test_providers.py      # Provider unit tests (COMPLETED)
│   └── README.md              # LLM tests documentation
└── TESTING_GUIDE.md           # This file
```

## Completed Tests

### Task 20: Provider Unit Tests ✅

**File**: `tests/llm/test_providers.py`

Comprehensive unit tests for all LLM provider implementations:

#### Test Classes
1. **TestGeminiProvider** (9 tests)
   - Initialization with/without API key
   - Successful chat completion
   - Rate limit detection (429, quota errors)
   - Timeout detection
   - Generic error handling
   - Availability checking

2. **TestOpenRouterProvider** (8 tests)
   - Initialization and defaults
   - Successful chat completion
   - HTTP 429 rate limit detection
   - Timeout handling
   - HTTP error handling
   - Availability checking

3. **TestOllamaProvider** (9 tests)
   - Initialization with defaults
   - Successful chat completion
   - Availability checking with 2s timeout
   - Availability result caching
   - Timeout and error handling

4. **TestLocalLLMProvider** (10 tests)
   - Initialization with defaults
   - Successful chat completion
   - Base URL validation
   - Availability checking with 2s timeout
   - Availability result caching
   - Timeout and error handling

**Total**: 36 unit tests covering all provider implementations

#### Requirements Satisfied
- ✅ Requirement 1.1: Gemini provider chat and error handling
- ✅ Requirement 1.2: OpenRouter rate limit detection
- ✅ Requirement 1.3: Ollama availability check
- ✅ Requirement 1.4: LM Studio support
- ✅ Requirement 1.5: Generic local provider support
- ✅ Requirement 4.1: Rate limit detection

## Pending Tests

### Task 21: Manager and Retry Logic Tests
**File**: `tests/llm/test_manager.py` (NOT YET IMPLEMENTED)
- Fallback chain execution
- All providers failed scenario
- Last provider tracking
- Skipping unavailable providers
- Exponential backoff timing
- Max retries exceeded
- No retry on non-retryable errors

### Task 22: Configuration Tests
**File**: `tests/llm/test_config.py` (NOT YET IMPLEMENTED)
- Loading configuration from environment
- Configuration validation
- Default values
- Invalid configuration handling

### Task 23: Integration Tests
**File**: `tests/integration/test_agent_with_llm.py` (NOT YET IMPLEMENTED)
- Full agent run with Gemini (requires API key)
- Agent fallback when primary provider fails
- Agent with no LLM providers (deterministic fallback)

## Running Tests

### Prerequisites

Install test dependencies:
```bash
pip install pytest pytest-mock
```

Or update from requirements.txt:
```bash
pip install -r requirements.txt
```

### Run All Tests

```bash
pytest tests/ -v
```

### Run Provider Tests Only

```bash
pytest tests/llm/test_providers.py -v
```

### Run Specific Test Class

```bash
pytest tests/llm/test_providers.py::TestGeminiProvider -v
```

### Run Specific Test

```bash
pytest tests/llm/test_providers.py::TestGeminiProvider::test_chat_rate_limit_error -v
```

### Run with Coverage

```bash
pytest tests/ --cov=backend.llm --cov-report=html
```

## Test Design Principles

### 1. Isolation
- Each test is independent
- No shared state between tests
- All external dependencies are mocked

### 2. Mocking Strategy
- All HTTP requests are mocked using `unittest.mock`
- No real API calls in unit tests
- No API keys required for unit tests
- Fast, deterministic test execution

### 3. Test Naming
- Descriptive names: `test_<what>_<condition>`
- Example: `test_chat_rate_limit_error`
- Clear intent from the name alone

### 4. Coverage Focus
- Happy path (successful operations)
- Error conditions (rate limits, timeouts, failures)
- Edge cases (missing config, unavailable services)
- Caching behavior (where applicable)

## Continuous Integration

### GitHub Actions (Example)

```yaml
name: Tests

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      - uses: actions/setup-python@v2
        with:
          python-version: '3.11'
      - run: pip install -r requirements.txt
      - run: pytest tests/ -v
```

## Debugging Failed Tests

### Verbose Output
```bash
pytest tests/llm/test_providers.py -vv
```

### Show Print Statements
```bash
pytest tests/llm/test_providers.py -s
```

### Stop on First Failure
```bash
pytest tests/llm/test_providers.py -x
```

### Run Last Failed Tests
```bash
pytest tests/llm/test_providers.py --lf
```

## Best Practices

1. **Write tests first** (TDD) or immediately after implementation
2. **Keep tests simple** - one assertion per test when possible
3. **Mock external dependencies** - no network calls in unit tests
4. **Use descriptive names** - test name should explain what it tests
5. **Test error paths** - don't just test the happy path
6. **Keep tests fast** - unit tests should run in milliseconds
7. **Maintain test independence** - tests should not depend on each other

## Resources

- [pytest Documentation](https://docs.pytest.org/)
- [unittest.mock Documentation](https://docs.python.org/3/library/unittest.mock.html)
- [Testing Best Practices](https://docs.python-guide.org/writing/tests/)
