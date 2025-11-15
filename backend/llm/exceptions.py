"""Custom exception classes for LLM provider errors"""


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
