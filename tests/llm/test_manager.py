"""
Unit tests for LLM Manager with fallback chain logic

Tests cover:
- Fallback chain execution
- All providers failed scenario
- Last provider tracking
- Skipping unavailable providers
"""

import pytest
from unittest.mock import Mock, patch

from backend.llm.manager import LLMManager
from backend.llm.config import LLMConfig, ProviderConfig, RetryConfig
from backend.llm.exceptions import (
    AllProvidersFailedError,
    RateLimitError,
    ProviderUnavailableError,
    TimeoutError
)


# ============================================================================
# Test Fixtures
# ============================================================================

@pytest.fixture
def basic_config():
    """Create a basic LLM configuration for testing"""
    return LLMConfig(
        primary_provider='gemini',
        fallback_chain=['gemini', 'openrouter', 'ollama'],
        providers={
            'gemini': ProviderConfig(name='gemini', api_key='test-gemini-key'),
            'openrouter': ProviderConfig(name='openrouter', api_key='test-openrouter-key'),
            'ollama': ProviderConfig(name='ollama', base_url='http://localhost:11434')
        },
        retry_config=RetryConfig(max_retries=3, initial_delay=2.0, timeout=60)
    )


@pytest.fixture
def single_provider_config():
    """Create a configuration with only one provider"""
    return LLMConfig(
        primary_provider='gemini',
        fallback_chain=['gemini'],
        providers={
            'gemini': ProviderConfig(name='gemini', api_key='test-key')
        },
        retry_config=RetryConfig(max_retries=3, initial_delay=2.0, timeout=60)
    )


@pytest.fixture
def empty_config():
    """Create a configuration with no providers"""
    return LLMConfig(
        primary_provider='gemini',
        fallback_chain=[],
        providers={},
        retry_config=RetryConfig(max_retries=3, initial_delay=2.0, timeout=60)
    )


# ============================================================================
# LLM Manager Tests
# ============================================================================

class TestLLMManager:
    """Tests for LLM Manager fallback chain logic"""
    
    def test_init_all_providers_available(self, basic_config):
        """Test manager initialization when all providers are available"""
        with patch('backend.llm.manager.GeminiProvider') as mock_gemini, \
             patch('backend.llm.manager.OpenRouterProvider') as mock_openrouter, \
             patch('backend.llm.manager.OllamaProvider') as mock_ollama:
            
            # Setup mocks
            mock_gemini_instance = Mock()
            mock_gemini_instance.is_available.return_value = True
            mock_gemini.return_value = mock_gemini_instance
            
            mock_openrouter_instance = Mock()
            mock_openrouter_instance.is_available.return_value = True
            mock_openrouter.return_value = mock_openrouter_instance
            
            mock_ollama_instance = Mock()
            mock_ollama_instance.is_available.return_value = True
            mock_ollama.return_value = mock_ollama_instance
            
            # Create manager
            manager = LLMManager(basic_config)
            
            # Verify all providers initialized
            assert len(manager.providers) == 3
            assert 'gemini' in manager.providers
            assert 'openrouter' in manager.providers
            assert 'ollama' in manager.providers
    
    def test_init_skip_unavailable_providers(self, basic_config):
        """Test manager skips providers that are not available"""
        with patch('backend.llm.manager.GeminiProvider') as mock_gemini, \
             patch('backend.llm.manager.OpenRouterProvider') as mock_openrouter:
            
            # Gemini available
            mock_gemini_instance = Mock()
            mock_gemini_instance.is_available.return_value = True
            mock_gemini.return_value = mock_gemini_instance
            
            # OpenRouter not available
            mock_openrouter_instance = Mock()
            mock_openrouter_instance.is_available.return_value = False
            mock_openrouter.return_value = mock_openrouter_instance
            
            # Create manager
            manager = LLMManager(basic_config)
            
            # Verify only available providers are initialized
            assert 'gemini' in manager.providers
            assert 'openrouter' not in manager.providers
    
    def test_init_provider_initialization_error(self, basic_config):
        """Test manager handles provider initialization errors gracefully"""
        with patch('backend.llm.manager.GeminiProvider') as mock_gemini:
            # Gemini raises error during initialization
            mock_gemini.side_effect = Exception("Initialization failed")
            
            # Create manager - should not crash
            manager = LLMManager(basic_config)
            
            # Verify provider not added
            assert 'gemini' not in manager.providers
    
    def test_chat_success_primary_provider(self, single_provider_config):
        """Test successful chat using primary provider"""
        with patch('backend.llm.manager.GeminiProvider') as mock_gemini:
            # Setup mock
            mock_provider = Mock()
            mock_provider.is_available.return_value = True
            mock_provider.chat.return_value = "Response from Gemini"
            mock_gemini.return_value = mock_provider
            
            # Create manager and call chat
            manager = LLMManager(single_provider_config)
            response = manager.chat("System prompt", "User prompt")
            
            # Verify response and provider tracking
            assert response == "Response from Gemini"
            assert manager.last_used_provider == 'gemini'
            mock_provider.chat.assert_called_once()
    
    def test_chat_fallback_on_rate_limit(self, basic_config):
        """Test fallback to secondary provider when primary hits rate limit"""
        with patch('backend.llm.manager.GeminiProvider') as mock_gemini, \
             patch('backend.llm.manager.OpenRouterProvider') as mock_openrouter:
            
            # Gemini fails with rate limit
            mock_gemini_instance = Mock()
            mock_gemini_instance.is_available.return_value = True
            mock_gemini_instance.chat.side_effect = RateLimitError("Rate limit exceeded")
            mock_gemini.return_value = mock_gemini_instance
            
            # OpenRouter succeeds
            mock_openrouter_instance = Mock()
            mock_openrouter_instance.is_available.return_value = True
            mock_openrouter_instance.chat.return_value = "Response from OpenRouter"
            mock_openrouter.return_value = mock_openrouter_instance
            
            # Create manager and call chat
            manager = LLMManager(basic_config)
            response = manager.chat("System prompt", "User prompt")
            
            # Verify fallback occurred
            assert response == "Response from OpenRouter"
            assert manager.last_used_provider == 'openrouter'
            assert mock_gemini_instance.chat.call_count == 3  # 3 retries
            mock_openrouter_instance.chat.assert_called_once()
    
    def test_chat_fallback_on_timeout(self, basic_config):
        """Test fallback to secondary provider when primary times out"""
        with patch('backend.llm.manager.GeminiProvider') as mock_gemini, \
             patch('backend.llm.manager.OpenRouterProvider') as mock_openrouter:
            
            # Gemini times out
            mock_gemini_instance = Mock()
            mock_gemini_instance.is_available.return_value = True
            mock_gemini_instance.chat.side_effect = TimeoutError("Request timeout")
            mock_gemini.return_value = mock_gemini_instance
            
            # OpenRouter succeeds
            mock_openrouter_instance = Mock()
            mock_openrouter_instance.is_available.return_value = True
            mock_openrouter_instance.chat.return_value = "Response from OpenRouter"
            mock_openrouter.return_value = mock_openrouter_instance
            
            # Create manager and call chat
            manager = LLMManager(basic_config)
            response = manager.chat("System prompt", "User prompt")
            
            # Verify fallback occurred
            assert response == "Response from OpenRouter"
            assert manager.last_used_provider == 'openrouter'
    
    def test_chat_fallback_on_provider_unavailable(self, basic_config):
        """Test fallback when primary provider becomes unavailable"""
        with patch('backend.llm.manager.GeminiProvider') as mock_gemini, \
             patch('backend.llm.manager.OpenRouterProvider') as mock_openrouter:
            
            # Gemini unavailable
            mock_gemini_instance = Mock()
            mock_gemini_instance.is_available.return_value = True
            mock_gemini_instance.chat.side_effect = ProviderUnavailableError("Provider down")
            mock_gemini.return_value = mock_gemini_instance
            
            # OpenRouter succeeds
            mock_openrouter_instance = Mock()
            mock_openrouter_instance.is_available.return_value = True
            mock_openrouter_instance.chat.return_value = "Response from OpenRouter"
            mock_openrouter.return_value = mock_openrouter_instance
            
            # Create manager and call chat
            manager = LLMManager(basic_config)
            response = manager.chat("System prompt", "User prompt")
            
            # Verify fallback occurred
            assert response == "Response from OpenRouter"
            assert manager.last_used_provider == 'openrouter'
    
    def test_chat_all_providers_fail(self, basic_config):
        """Test AllProvidersFailedError when all providers in chain fail"""
        with patch('backend.llm.manager.GeminiProvider') as mock_gemini, \
             patch('backend.llm.manager.OpenRouterProvider') as mock_openrouter, \
             patch('backend.llm.manager.OllamaProvider') as mock_ollama:
            
            # All providers fail
            mock_gemini_instance = Mock()
            mock_gemini_instance.is_available.return_value = True
            mock_gemini_instance.chat.side_effect = RateLimitError("Rate limit")
            mock_gemini.return_value = mock_gemini_instance
            
            mock_openrouter_instance = Mock()
            mock_openrouter_instance.is_available.return_value = True
            mock_openrouter_instance.chat.side_effect = TimeoutError("Timeout")
            mock_openrouter.return_value = mock_openrouter_instance
            
            mock_ollama_instance = Mock()
            mock_ollama_instance.is_available.return_value = True
            mock_ollama_instance.chat.side_effect = ProviderUnavailableError("Not available")
            mock_ollama.return_value = mock_ollama_instance
            
            # Create manager and call chat
            manager = LLMManager(basic_config)
            
            with pytest.raises(AllProvidersFailedError, match="All providers failed"):
                manager.chat("System prompt", "User prompt")
            
            # Verify all providers were attempted
            assert mock_gemini_instance.chat.call_count == 3  # With retries
            assert mock_openrouter_instance.chat.call_count == 3  # With retries
            mock_ollama_instance.chat.assert_called_once()  # No retry for ProviderUnavailableError
    
    def test_chat_no_providers_configured(self, empty_config):
        """Test AllProvidersFailedError when no providers are configured"""
        with patch('backend.llm.manager.GeminiProvider'), \
             patch('backend.llm.manager.OpenRouterProvider'), \
             patch('backend.llm.manager.OllamaProvider'), \
             patch('backend.llm.manager.LocalLLMProvider'):
            
            manager = LLMManager(empty_config)
            
            with pytest.raises(AllProvidersFailedError, match="No providers configured"):
                manager.chat("System prompt", "User prompt")
    
    def test_get_provider_chain_primary_first(self, basic_config):
        """Test provider chain starts with primary provider"""
        with patch('backend.llm.manager.GeminiProvider') as mock_gemini, \
             patch('backend.llm.manager.OpenRouterProvider') as mock_openrouter:
            
            # Setup mocks
            mock_gemini_instance = Mock()
            mock_gemini_instance.is_available.return_value = True
            mock_gemini.return_value = mock_gemini_instance
            
            mock_openrouter_instance = Mock()
            mock_openrouter_instance.is_available.return_value = True
            mock_openrouter.return_value = mock_openrouter_instance
            
            # Create manager
            manager = LLMManager(basic_config)
            chain = manager._get_provider_chain()
            
            # Verify primary is first
            assert chain[0] == 'gemini'
            assert 'openrouter' in chain
    
    def test_get_provider_chain_no_duplicates(self):
        """Test provider chain contains no duplicates"""
        # Config with duplicate in fallback chain
        config = LLMConfig(
            primary_provider='gemini',
            fallback_chain=['gemini', 'openrouter', 'gemini'],  # Duplicate
            providers={
                'gemini': ProviderConfig(name='gemini', api_key='test-key'),
                'openrouter': ProviderConfig(name='openrouter', api_key='test-key')
            },
            retry_config=RetryConfig()
        )
        
        with patch('backend.llm.manager.GeminiProvider') as mock_gemini, \
             patch('backend.llm.manager.OpenRouterProvider') as mock_openrouter:
            
            # Setup mocks
            mock_gemini_instance = Mock()
            mock_gemini_instance.is_available.return_value = True
            mock_gemini.return_value = mock_gemini_instance
            
            mock_openrouter_instance = Mock()
            mock_openrouter_instance.is_available.return_value = True
            mock_openrouter.return_value = mock_openrouter_instance
            
            # Create manager
            manager = LLMManager(config)
            chain = manager._get_provider_chain()
            
            # Verify no duplicates
            assert len(chain) == len(set(chain))
            assert chain.count('gemini') == 1
    
    def test_get_provider_chain_skips_unconfigured(self):
        """Test provider chain skips providers not in initialized providers"""
        # Config references provider that won't be initialized
        config = LLMConfig(
            primary_provider='gemini',
            fallback_chain=['gemini', 'openrouter'],  # openrouter not configured
            providers={
                'gemini': ProviderConfig(name='gemini', api_key='test-key')
            },
            retry_config=RetryConfig()
        )
        
        with patch('backend.llm.manager.GeminiProvider') as mock_gemini:
            # Setup mock
            mock_gemini_instance = Mock()
            mock_gemini_instance.is_available.return_value = True
            mock_gemini.return_value = mock_gemini_instance
            
            # Create manager
            manager = LLMManager(config)
            chain = manager._get_provider_chain()
            
            # Verify only configured provider in chain
            assert chain == ['gemini']
            assert 'openrouter' not in chain
    
    def test_last_used_provider_tracking(self, single_provider_config):
        """Test last_used_provider is correctly tracked"""
        with patch('backend.llm.manager.GeminiProvider') as mock_gemini:
            # Setup mock
            mock_provider = Mock()
            mock_provider.is_available.return_value = True
            mock_provider.chat.return_value = "Response"
            mock_gemini.return_value = mock_provider
            
            # Create manager
            manager = LLMManager(single_provider_config)
            
            # Initially None
            assert manager.last_used_provider is None
            
            # After successful chat
            manager.chat("System", "User")
            assert manager.last_used_provider == 'gemini'
    
    def test_last_used_provider_updates_on_fallback(self, basic_config):
        """Test last_used_provider updates when fallback occurs"""
        with patch('backend.llm.manager.GeminiProvider') as mock_gemini, \
             patch('backend.llm.manager.OpenRouterProvider') as mock_openrouter:
            
            # Gemini fails
            mock_gemini_instance = Mock()
            mock_gemini_instance.is_available.return_value = True
            mock_gemini_instance.chat.side_effect = RateLimitError("Rate limit")
            mock_gemini.return_value = mock_gemini_instance
            
            # OpenRouter succeeds
            mock_openrouter_instance = Mock()
            mock_openrouter_instance.is_available.return_value = True
            mock_openrouter_instance.chat.return_value = "Response"
            mock_openrouter.return_value = mock_openrouter_instance
            
            # Create manager and call chat
            manager = LLMManager(basic_config)
            manager.chat("System", "User")
            
            # Verify last used provider is the successful one
            assert manager.last_used_provider == 'openrouter'
    
    def test_get_available_providers(self, single_provider_config):
        """Test get_available_providers returns list of initialized providers"""
        with patch('backend.llm.manager.GeminiProvider') as mock_gemini:
            # Setup mock
            mock_provider = Mock()
            mock_provider.is_available.return_value = True
            mock_gemini.return_value = mock_provider
            
            # Create manager
            manager = LLMManager(single_provider_config)
            available = manager.get_available_providers()
            
            # Verify
            assert 'gemini' in available
            assert len(available) == 1
    
    def test_get_available_providers_multiple(self, basic_config):
        """Test get_available_providers with multiple providers"""
        with patch('backend.llm.manager.GeminiProvider') as mock_gemini, \
             patch('backend.llm.manager.OpenRouterProvider') as mock_openrouter:
            
            # Setup mocks
            mock_gemini_instance = Mock()
            mock_gemini_instance.is_available.return_value = True
            mock_gemini.return_value = mock_gemini_instance
            
            mock_openrouter_instance = Mock()
            mock_openrouter_instance.is_available.return_value = True
            mock_openrouter.return_value = mock_openrouter_instance
            
            # Create manager
            manager = LLMManager(basic_config)
            available = manager.get_available_providers()
            
            # Verify
            assert 'gemini' in available
            assert 'openrouter' in available
    
    def test_chat_passes_kwargs_to_provider(self, single_provider_config):
        """Test chat passes additional kwargs to provider"""
        with patch('backend.llm.manager.GeminiProvider') as mock_gemini:
            # Setup mock
            mock_provider = Mock()
            mock_provider.is_available.return_value = True
            mock_provider.chat.return_value = "Response"
            mock_gemini.return_value = mock_provider
            
            # Create manager and call chat with kwargs
            manager = LLMManager(single_provider_config)
            manager.chat("System", "User", temperature=0.8, max_tokens=1000)
            
            # Verify kwargs passed through
            call_kwargs = mock_provider.chat.call_args[1]
            assert call_kwargs['temperature'] == 0.8
            assert call_kwargs['max_tokens'] == 1000
            assert 'timeout' in call_kwargs  # Added by retry logic
    
    def test_chat_applies_timeout_from_config(self, single_provider_config):
        """Test chat applies timeout from retry config"""
        with patch('backend.llm.manager.GeminiProvider') as mock_gemini:
            # Setup mock
            mock_provider = Mock()
            mock_provider.is_available.return_value = True
            mock_provider.chat.return_value = "Response"
            mock_gemini.return_value = mock_provider
            
            # Create manager with custom timeout
            single_provider_config.retry_config.timeout = 120
            manager = LLMManager(single_provider_config)
            manager.chat("System", "User")
            
            # Verify timeout passed
            call_kwargs = mock_provider.chat.call_args[1]
            assert call_kwargs['timeout'] == 120
