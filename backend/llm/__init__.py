"""
LLM Provider Abstraction Layer

This module provides a unified interface for multiple LLM providers with
automatic failover, rate limit handling, and retry logic.

Usage:
    from backend.llm import get_manager
    
    manager = get_manager()
    response = manager.chat(
        system="You are a helpful assistant",
        user="What is the capital of France?"
    )
"""

import logging

from .config import LLMConfig, ProviderConfig, RetryConfig
from .provider import LLMProvider
from .manager import LLMManager
from .exceptions import (
    LLMError,
    RateLimitError,
    ProviderUnavailableError,
    AllProvidersFailedError,
    TimeoutError
)

__all__ = [
    'get_manager',
    'LLMConfig',
    'ProviderConfig',
    'RetryConfig',
    'LLMProvider',
    'LLMManager',
    'LLMError',
    'RateLimitError',
    'ProviderUnavailableError',
    'AllProvidersFailedError',
    'TimeoutError',
]

# Module logger
logger = logging.getLogger("regops.llm")

# Singleton instance
_manager_instance = None
_config_loaded = False


def _load_and_validate_config() -> LLMConfig:
    """
    Load configuration from environment and validate
    
    Returns:
        Validated LLMConfig instance
    """
    global _config_loaded
    
    if _config_loaded:
        logger.debug("Configuration already loaded, skipping reload")
        return None
    
    try:
        logger.info("Loading LLM system configuration from environment")
        config = LLMConfig.from_env()
        warnings = config.validate()
        
        if warnings:
            logger.warning(f"Configuration loaded with {len(warnings)} warning(s)")
            for warning in warnings:
                logger.warning(f"  - {warning}")
        
        _config_loaded = True
        logger.info("LLM configuration loaded and validated successfully")
        return config
        
    except Exception as e:
        logger.error(f"Failed to load LLM configuration: {type(e).__name__}: {e}", exc_info=True)
        raise


def get_manager() -> LLMManager:
    """
    Get singleton LLM manager instance
    
    Lazily initializes the manager on first call with configuration
    loaded from environment variables. Subsequent calls return the
    same instance.
    
    Returns:
        Configured LLMManager instance
        
    Raises:
        Exception: If configuration loading or manager initialization fails
    """
    global _manager_instance
    
    if _manager_instance is None:
        logger.info("Creating LLM manager singleton instance")
        config = _load_and_validate_config()
        _manager_instance = LLMManager(config)
        logger.info("LLM manager singleton created and ready for use")
    else:
        logger.debug("Returning existing LLM manager singleton instance")
    
    return _manager_instance


# Module-level initialization: Load and validate configuration on first import
# This ensures configuration errors are caught early
try:
    _load_and_validate_config()
except Exception as e:
    logger.warning(
        f"LLM configuration validation failed on module import: {e}. "
        "Manager will attempt to load configuration on first use."
    )
