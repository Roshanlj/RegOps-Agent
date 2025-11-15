# LLM Provider Tests

This directory contains unit tests for the LLM provider implementations.

## Test Coverage

### `test_providers.py`

Comprehensive unit tests for all LLM providers with mocked external API calls.

#### Gemini Provider Tests
- ✅ Initialization with and without API key
- ✅ Successful chat completion
- ✅ Error handling when not configured
- ✅ Rate limit detection (HTTP 429)
- ✅ Quota error detection (treated as rate limit)
- ✅ Timeout error detection
- ✅ Generic error handling
- ✅ Availability checking

#### OpenRouter Provider Tests
- ✅ Initialization with default model
- ✅ Successful chat completion
- ✅ Error handling when not configured
- ✅ HTTP 429 rate limit detection
- ✅ Timeout error detection
- ✅ HTTP error handling
- ✅ Availability checking

#### Ollama Provider Tests
- ✅ Initialization with defaults
- ✅ Successful chat completion
- ✅ Error handling when not available
- ✅ Timeout error detection
- ✅ Generic error handling
- ✅ Availability check with 2-second timeout
- ✅ Availability result caching
- ✅ Timeout handling in availability check

#### Local LLM Provider Tests
- ✅ Initialization with default model
- ✅ Successful chat completion
- ✅ Error handling when base URL not configured
- ✅ Error handling when not available
- ✅ Timeout error detection
- ✅ HTTP error handling
- ✅ Availability check with 2-second timeout
- ✅ Availability result caching
- ✅ Timeout handling in availability check

## Requirements Covered

This test suite satisfies the following requirements from the specification:

- **Requirement 1.1**: Gemini provider support with error handling
- **Requirement 1.2**: OpenRouter provider support with rate limit detection
- **Requirement 1.3**: Ollama provider support with availability checking
- **Requirement 1.4**: LM Studio support through OpenAI-compatible API
- **Requirement 1.5**: Generic OpenAI-compatible local provider support
- **Requirement 4.1**: Rate limit detection (HTTP 429)

## Running the Tests

### Using pytest directly

```bash
pytest tests/llm/test_providers.py -v
```

### Using the test runner script

```bash
python run_tests.py
```

### Running specific test classes

```bash
# Test only Gemini provider
pytest tests/llm/test_providers.py::TestGeminiProvider -v

# Test only OpenRouter provider
pytest tests/llm/test_providers.py::TestOpenRouterProvider -v

# Test only Ollama provider
pytest tests/llm/test_providers.py::TestOllamaProvider -v

# Test only Local LLM provider
pytest tests/llm/test_providers.py::TestLocalLLMProvider -v
```

### Running specific tests

```bash
# Test Gemini rate limit detection
pytest tests/llm/test_providers.py::TestGeminiProvider::test_chat_rate_limit_error -v

# Test OpenRouter HTTP 429 detection
pytest tests/llm/test_providers.py::TestOpenRouterProvider::test_chat_rate_limit_429 -v

# Test Ollama availability check
pytest tests/llm/test_providers.py::TestOllamaProvider::test_is_available_success -v

# Test Local provider timeout handling
pytest tests/llm/test_providers.py::TestLocalLLMProvider::test_chat_timeout -v
```

## Test Design

### Mocking Strategy

All external API calls are mocked using `unittest.mock` to ensure:
- Tests run without network access
- Tests are fast and deterministic
- No API keys or external services required
- Consistent behavior across environments

### Test Structure

Each provider test class follows the same pattern:
1. **Initialization tests**: Verify correct configuration handling
2. **Success path tests**: Verify normal operation with mocked responses
3. **Error handling tests**: Verify proper exception raising for various error conditions
4. **Availability tests**: Verify provider availability detection logic

### Key Testing Principles

- **Isolation**: Each test is independent and doesn't affect others
- **Clarity**: Test names clearly describe what is being tested
- **Coverage**: All critical paths and error conditions are tested
- **Maintainability**: Tests use consistent patterns and are easy to update

## Dependencies

The tests require:
- `pytest>=7.4.0` - Test framework
- `pytest-mock>=3.12.0` - Enhanced mocking support (optional, using unittest.mock)

Install with:
```bash
pip install pytest pytest-mock
```

## Future Enhancements

Potential additions to the test suite:
- Integration tests with real API calls (requires API keys)
- Performance tests for timeout behavior
- Concurrent request handling tests
- Streaming response tests (when implemented)
