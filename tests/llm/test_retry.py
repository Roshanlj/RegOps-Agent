"""
Unit tests for retry logic with exponential backoff

Tests cover:
- Exponential backoff timing
- Max retries exceeded
- No retry on non-retryable errors
"""

import pytest
import time
from unittest.mock import Mock, patch

from backend.llm.retry import with_exponential_backoff
from backend.llm.exceptions import (
    RateLimitError,
    TimeoutError,
    ProviderUnavailableError
)


# ============================================================================
# Exponential Backoff Tests
# ============================================================================

class TestExponentialBackoff:
    """Tests for exponential backoff retry decorator"""
    
    def test_success_no_retry(self):
        """Test successful function call requires no retry"""
        mock_func = Mock(return_value="success")
        
        @with_exponential_backoff(max_retries=3, initial_delay=1.0)
        def test_func():
            return mock_func()
        
        result = test_func()
        
        assert result == "success"
        assert mock_func.call_count == 1
    
    def test_rate_limit_retry_success(self):
        """Test retry on rate limit error with eventual success"""
        mock_func = Mock(side_effect=[
            RateLimitError("Rate limit 1"),
            RateLimitError("Rate limit 2"),
            "success"
        ])
        
        @with_exponential_backoff(max_retries=3, initial_delay=0.1)
        def test_func():
            return mock_func()
        
        result = test_func()
        
        assert result == "success"
        assert mock_func.call_count == 3
    
    def test_timeout_retry_success(self):
        """Test retry on timeout error with eventual success"""
        mock_func = Mock(side_effect=[
            TimeoutError("Timeout 1"),
            TimeoutError("Timeout 2"),
            "success"
        ])
        
        @with_exponential_backoff(max_retries=3, initial_delay=0.1)
        def test_func():
            return mock_func()
        
        result = test_func()
        
        assert result == "success"
        assert mock_func.call_count == 3
    
    def test_max_retries_exceeded_rate_limit(self):
        """Test RateLimitError raised when max retries exceeded"""
        mock_func = Mock(side_effect=RateLimitError("Rate limit"))
        
        @with_exponential_backoff(max_retries=3, initial_delay=0.1)
        def test_func():
            return mock_func()
        
        with pytest.raises(RateLimitError, match="Rate limit"):
            test_func()
        
        assert mock_func.call_count == 3
    
    def test_max_retries_exceeded_timeout(self):
        """Test TimeoutError raised when max retries exceeded"""
        mock_func = Mock(side_effect=TimeoutError("Timeout"))
        
        @with_exponential_backoff(max_retries=3, initial_delay=0.1)
        def test_func():
            return mock_func()
        
        with pytest.raises(TimeoutError, match="Timeout"):
            test_func()
        
        assert mock_func.call_count == 3
    
    def test_no_retry_on_provider_unavailable(self):
        """Test no retry on ProviderUnavailableError"""
        mock_func = Mock(side_effect=ProviderUnavailableError("Provider down"))
        
        @with_exponential_backoff(max_retries=3, initial_delay=0.1)
        def test_func():
            return mock_func()
        
        with pytest.raises(ProviderUnavailableError, match="Provider down"):
            test_func()
        
        # Should fail immediately without retry
        assert mock_func.call_count == 1
    
    def test_no_retry_on_generic_exception(self):
        """Test no retry on generic exceptions"""
        mock_func = Mock(side_effect=ValueError("Invalid value"))
        
        @with_exponential_backoff(max_retries=3, initial_delay=0.1)
        def test_func():
            return mock_func()
        
        with pytest.raises(ValueError, match="Invalid value"):
            test_func()
        
        # Should fail immediately without retry
        assert mock_func.call_count == 1
    
    @patch('backend.llm.retry.time.sleep')
    def test_exponential_backoff_timing(self, mock_sleep):
        """Test exponential backoff applies correct delays"""
        mock_func = Mock(side_effect=[
            RateLimitError("Rate limit 1"),
            RateLimitError("Rate limit 2"),
            "success"
        ])
        
        @with_exponential_backoff(max_retries=3, initial_delay=2.0, backoff_factor=2.0)
        def test_func():
            return mock_func()
        
        result = test_func()
        
        assert result == "success"
        # Verify sleep was called with exponential delays
        assert mock_sleep.call_count == 2
        assert mock_sleep.call_args_list[0][0][0] == 2.0  # First retry: 2s
        assert mock_sleep.call_args_list[1][0][0] == 4.0  # Second retry: 4s
    
    @patch('backend.llm.retry.time.sleep')
    def test_exponential_backoff_three_retries(self, mock_sleep):
        """Test exponential backoff with three retries (2s, 4s, 8s)"""
        mock_func = Mock(side_effect=[
            RateLimitError("Rate limit 1"),
            RateLimitError("Rate limit 2"),
            RateLimitError("Rate limit 3"),
            "success"
        ])
        
        @with_exponential_backoff(max_retries=4, initial_delay=2.0, backoff_factor=2.0)
        def test_func():
            return mock_func()
        
        result = test_func()
        
        assert result == "success"
        # Verify exponential delays: 2s, 4s, 8s
        assert mock_sleep.call_count == 3
        assert mock_sleep.call_args_list[0][0][0] == 2.0
        assert mock_sleep.call_args_list[1][0][0] == 4.0
        assert mock_sleep.call_args_list[2][0][0] == 8.0
    
    @patch('backend.llm.retry.time.sleep')
    def test_custom_backoff_factor(self, mock_sleep):
        """Test custom backoff factor"""
        mock_func = Mock(side_effect=[
            RateLimitError("Rate limit 1"),
            RateLimitError("Rate limit 2"),
            "success"
        ])
        
        @with_exponential_backoff(max_retries=3, initial_delay=1.0, backoff_factor=3.0)
        def test_func():
            return mock_func()
        
        result = test_func()
        
        assert result == "success"
        # Verify custom backoff: 1s, 3s
        assert mock_sleep.call_count == 2
        assert mock_sleep.call_args_list[0][0][0] == 1.0
        assert mock_sleep.call_args_list[1][0][0] == 3.0
    
    def test_retry_with_function_arguments(self):
        """Test retry decorator works with function arguments"""
        mock_func = Mock(side_effect=[
            RateLimitError("Rate limit"),
            "success"
        ])
        
        @with_exponential_backoff(max_retries=3, initial_delay=0.1)
        def test_func(arg1, arg2, kwarg1=None):
            return mock_func(arg1, arg2, kwarg1=kwarg1)
        
        result = test_func("value1", "value2", kwarg1="kwvalue")
        
        assert result == "success"
        assert mock_func.call_count == 2
        # Verify arguments passed correctly
        mock_func.assert_called_with("value1", "value2", kwarg1="kwvalue")
    
    def test_retry_preserves_function_metadata(self):
        """Test decorator preserves original function metadata"""
        @with_exponential_backoff(max_retries=3, initial_delay=0.1)
        def test_func():
            """Test function docstring"""
            return "success"
        
        assert test_func.__name__ == "test_func"
        assert test_func.__doc__ == "Test function docstring"
    
    def test_mixed_errors_retry_only_retryable(self):
        """Test retry only occurs for retryable errors"""
        mock_func = Mock(side_effect=[
            RateLimitError("Rate limit"),
            TimeoutError("Timeout"),
            "success"
        ])
        
        @with_exponential_backoff(max_retries=3, initial_delay=0.1)
        def test_func():
            return mock_func()
        
        result = test_func()
        
        assert result == "success"
        assert mock_func.call_count == 3
    
    def test_rate_limit_then_non_retryable_error(self):
        """Test non-retryable error after rate limit stops retry"""
        mock_func = Mock(side_effect=[
            RateLimitError("Rate limit"),
            ProviderUnavailableError("Provider down")
        ])
        
        @with_exponential_backoff(max_retries=3, initial_delay=0.1)
        def test_func():
            return mock_func()
        
        with pytest.raises(ProviderUnavailableError, match="Provider down"):
            test_func()
        
        # Should have retried after rate limit, then failed on provider error
        assert mock_func.call_count == 2
    
    @patch('backend.llm.retry.time.sleep')
    def test_timeout_exponential_backoff(self, mock_sleep):
        """Test timeout errors also use exponential backoff"""
        mock_func = Mock(side_effect=[
            TimeoutError("Timeout 1"),
            TimeoutError("Timeout 2"),
            "success"
        ])
        
        @with_exponential_backoff(max_retries=3, initial_delay=2.0, backoff_factor=2.0)
        def test_func():
            return mock_func()
        
        result = test_func()
        
        assert result == "success"
        # Verify exponential delays for timeouts
        assert mock_sleep.call_count == 2
        assert mock_sleep.call_args_list[0][0][0] == 2.0
        assert mock_sleep.call_args_list[1][0][0] == 4.0
    
    def test_single_retry_configuration(self):
        """Test configuration with single retry"""
        mock_func = Mock(side_effect=[
            RateLimitError("Rate limit")
        ])
        
        @with_exponential_backoff(max_retries=1, initial_delay=0.1)
        def test_func():
            return mock_func()
        
        # With max_retries=1, it will try once and fail
        with pytest.raises(RateLimitError, match="Rate limit"):
            test_func()
        
        assert mock_func.call_count == 1  # Only one attempt with max_retries=1
    
    def test_zero_initial_delay(self):
        """Test retry with zero initial delay"""
        mock_func = Mock(side_effect=[
            RateLimitError("Rate limit"),
            "success"
        ])
        
        @with_exponential_backoff(max_retries=2, initial_delay=0.0)
        def test_func():
            return mock_func()
        
        start_time = time.time()
        result = test_func()
        elapsed = time.time() - start_time
        
        assert result == "success"
        assert mock_func.call_count == 2
        # Should complete quickly with no delay
        assert elapsed < 0.5
