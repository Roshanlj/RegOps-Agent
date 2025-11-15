"""
Retry logic with exponential backoff
"""

import time
import logging
from functools import wraps
from typing import Callable, TypeVar

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
                            f"Rate limit encountered (attempt {attempt + 1}/{max_retries}). "
                            f"Applying exponential backoff: waiting {delay}s before retry. "
                            f"Error: {e}"
                        )
                        time.sleep(delay)
                        delay *= backoff_factor
                        logger.info(f"Retrying after rate limit backoff (attempt {attempt + 2}/{max_retries})")
                    else:
                        logger.error(
                            f"Max retries ({max_retries}) exhausted after repeated rate limits. "
                            f"Last error: {e}"
                        )
                        raise
                except TimeoutError as e:
                    last_exception = e
                    if attempt < max_retries - 1:
                        logger.warning(
                            f"Request timeout (attempt {attempt + 1}/{max_retries}). "
                            f"Applying exponential backoff: waiting {delay}s before retry. "
                            f"Error: {e}"
                        )
                        time.sleep(delay)
                        delay *= backoff_factor
                        logger.info(f"Retrying after timeout (attempt {attempt + 2}/{max_retries})")
                    else:
                        logger.error(
                            f"Max retries ({max_retries}) exhausted after repeated timeouts. "
                            f"Last error: {e}"
                        )
                        raise
            
            # Should not reach here, but just in case
            if last_exception:
                raise last_exception
            
        return wrapper
    return decorator
