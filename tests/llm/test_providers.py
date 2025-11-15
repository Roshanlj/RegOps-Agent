"""
Unit tests for LLM provider implementations

Tests cover:
- Gemini provider chat and error handling
- OpenRouter rate limit detection
- Ollama availability check
- Local provider timeout handling
- All external API calls are mocked
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
import requests

from backend.llm.providers.gemini import GeminiProvider
from backend.llm.providers.openrouter import OpenRouterProvider
from backend.llm.providers.ollama import OllamaProvider
from backend.llm.providers.local import LocalLLMProvider
from backend.llm.exceptions import (
    RateLimitError,
    ProviderUnavailableError,
    TimeoutError
)


# ============================================================================
# Gemini Provider Tests
# ============================================================================

class TestGeminiProvider:
    """Tests for Google Gemini provider"""
    
    def test_init_with_api_key(self):
        """Test Gemini provider initialization with API key"""
        with patch('backend.llm.providers.gemini.genai') as mock_genai:
            config = {'api_key': 'test-key', 'model': 'gemini-1.5-flash'}
            provider = GeminiProvider(config)
            
            assert provider.api_key == 'test-key'
            assert provider.model_name == 'gemini-1.5-flash'
            assert provider.name == 'gemini'
            mock_genai.configure.assert_called_once_with(api_key='test-key')
    
    def test_init_without_api_key(self):
        """Test Gemini provider initialization without API key"""
        config = {}
        provider = GeminiProvider(config)
        
        assert provider.api_key is None
        assert provider._client is None
        assert not provider.is_available()
    
    def test_chat_success(self):
        """Test successful chat completion with Gemini"""
        with patch('backend.llm.providers.gemini.genai') as mock_genai:
            # Setup mock
            mock_response = Mock()
            mock_response.text = "This is a test response"
            mock_client = Mock()
            mock_client.generate_content.return_value = mock_response
            mock_genai.GenerativeModel.return_value = mock_client
            
            # Create provider and call chat
            config = {'api_key': 'test-key'}
            provider = GeminiProvider(config)
            
            result = provider.chat("System prompt", "User prompt", temperature=0.5)
            
            assert result == "This is a test response"
            mock_client.generate_content.assert_called_once()
            call_args = mock_client.generate_content.call_args
            assert "System prompt" in call_args[0][0]
            assert "User prompt" in call_args[0][0]
    
    def test_chat_not_configured(self):
        """Test chat raises error when not configured"""
        config = {}
        provider = GeminiProvider(config)
        
        with pytest.raises(ProviderUnavailableError, match="Gemini not configured"):
            provider.chat("System", "User")
    
    def test_chat_rate_limit_error(self):
        """Test chat detects rate limit errors (HTTP 429)"""
        with patch('backend.llm.providers.gemini.genai') as mock_genai:
            mock_client = Mock()
            mock_client.generate_content.side_effect = Exception("Error 429: Rate limit exceeded")
            mock_genai.GenerativeModel.return_value = mock_client
            
            config = {'api_key': 'test-key'}
            provider = GeminiProvider(config)
            
            with pytest.raises(RateLimitError, match="Gemini rate limit"):
                provider.chat("System", "User")
    
    def test_chat_quota_error(self):
        """Test chat detects quota errors as rate limits"""
        with patch('backend.llm.providers.gemini.genai') as mock_genai:
            mock_client = Mock()
            mock_client.generate_content.side_effect = Exception("Quota exceeded for this model")
            mock_genai.GenerativeModel.return_value = mock_client
            
            config = {'api_key': 'test-key'}
            provider = GeminiProvider(config)
            
            with pytest.raises(RateLimitError, match="Gemini rate limit"):
                provider.chat("System", "User")
    
    def test_chat_timeout_error(self):
        """Test chat detects timeout errors"""
        with patch('backend.llm.providers.gemini.genai') as mock_genai:
            mock_client = Mock()
            mock_client.generate_content.side_effect = Exception("Request timed out")
            mock_genai.GenerativeModel.return_value = mock_client
            
            config = {'api_key': 'test-key'}
            provider = GeminiProvider(config)
            
            with pytest.raises(TimeoutError, match="Gemini timeout"):
                provider.chat("System", "User")
    
    def test_chat_generic_error(self):
        """Test chat handles generic errors"""
        with patch('backend.llm.providers.gemini.genai') as mock_genai:
            mock_client = Mock()
            mock_client.generate_content.side_effect = Exception("Unknown error")
            mock_genai.GenerativeModel.return_value = mock_client
            
            config = {'api_key': 'test-key'}
            provider = GeminiProvider(config)
            
            with pytest.raises(ProviderUnavailableError, match="Gemini error"):
                provider.chat("System", "User")
    
    def test_is_available_with_key(self):
        """Test is_available returns True when configured"""
        with patch('backend.llm.providers.gemini.genai'):
            config = {'api_key': 'test-key'}
            provider = GeminiProvider(config)
            
            assert provider.is_available()
    
    def test_is_available_without_key(self):
        """Test is_available returns False when not configured"""
        config = {}
        provider = GeminiProvider(config)
        
        assert not provider.is_available()


# ============================================================================
# OpenRouter Provider Tests
# ============================================================================

class TestOpenRouterProvider:
    """Tests for OpenRouter provider"""
    
    def test_init(self):
        """Test OpenRouter provider initialization"""
        config = {'api_key': 'test-key', 'model': 'anthropic/claude-3.5-sonnet'}
        provider = OpenRouterProvider(config)
        
        assert provider.api_key == 'test-key'
        assert provider.model == 'anthropic/claude-3.5-sonnet'
        assert provider.name == 'openrouter'
    
    def test_init_default_model(self):
        """Test OpenRouter uses default model when not specified"""
        config = {'api_key': 'test-key'}
        provider = OpenRouterProvider(config)
        
        assert provider.model == 'anthropic/claude-3.5-sonnet'
    
    @patch('backend.llm.providers.openrouter.requests.post')
    def test_chat_success(self, mock_post):
        """Test successful chat completion with OpenRouter"""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'choices': [{'message': {'content': 'Test response'}}]
        }
        mock_post.return_value = mock_response
        
        config = {'api_key': 'test-key'}
        provider = OpenRouterProvider(config)
        
        result = provider.chat("System prompt", "User prompt", temperature=0.7)
        
        assert result == 'Test response'
        mock_post.assert_called_once()
        call_kwargs = mock_post.call_args[1]
        assert call_kwargs['json']['messages'][0]['role'] == 'system'
        assert call_kwargs['json']['messages'][1]['role'] == 'user'
        assert call_kwargs['json']['temperature'] == 0.7
    
    def test_chat_not_configured(self):
        """Test chat raises error when API key not configured"""
        config = {}
        provider = OpenRouterProvider(config)
        
        with pytest.raises(ProviderUnavailableError, match="OpenRouter not configured"):
            provider.chat("System", "User")
    
    @patch('backend.llm.providers.openrouter.requests.post')
    def test_chat_rate_limit_429(self, mock_post):
        """Test chat detects HTTP 429 rate limit"""
        mock_response = Mock()
        mock_response.status_code = 429
        mock_post.return_value = mock_response
        
        config = {'api_key': 'test-key'}
        provider = OpenRouterProvider(config)
        
        with pytest.raises(RateLimitError, match="OpenRouter rate limit exceeded"):
            provider.chat("System", "User")
    
    @patch('backend.llm.providers.openrouter.requests.post')
    def test_chat_timeout(self, mock_post):
        """Test chat detects timeout errors"""
        mock_post.side_effect = requests.Timeout("Connection timeout")
        
        config = {'api_key': 'test-key'}
        provider = OpenRouterProvider(config)
        
        with pytest.raises(TimeoutError, match="OpenRouter request timeout"):
            provider.chat("System", "User")
    
    @patch('backend.llm.providers.openrouter.requests.post')
    def test_chat_http_error(self, mock_post):
        """Test chat handles HTTP errors"""
        mock_response = Mock()
        mock_response.status_code = 500
        mock_response.raise_for_status.side_effect = requests.HTTPError("Server error")
        mock_post.return_value = mock_response
        
        config = {'api_key': 'test-key'}
        provider = OpenRouterProvider(config)
        
        with pytest.raises(ProviderUnavailableError, match="OpenRouter error"):
            provider.chat("System", "User")
    
    def test_is_available_with_key(self):
        """Test is_available returns True when API key configured"""
        config = {'api_key': 'test-key'}
        provider = OpenRouterProvider(config)
        
        assert provider.is_available()
    
    def test_is_available_without_key(self):
        """Test is_available returns False when no API key"""
        config = {}
        provider = OpenRouterProvider(config)
        
        assert not provider.is_available()


# ============================================================================
# Ollama Provider Tests
# ============================================================================

class TestOllamaProvider:
    """Tests for Ollama local provider"""
    
    def test_init(self):
        """Test Ollama provider initialization"""
        config = {'base_url': 'http://localhost:11434', 'model': 'llama3.1:8b'}
        provider = OllamaProvider(config)
        
        assert provider.base_url == 'http://localhost:11434'
        assert provider.model == 'llama3.1:8b'
        assert provider.name == 'ollama'
        assert provider._available is None
    
    def test_init_defaults(self):
        """Test Ollama uses default values"""
        config = {}
        provider = OllamaProvider(config)
        
        assert provider.base_url == 'http://localhost:11434'
        assert provider.model == 'llama3.1:8b'
    
    @patch('backend.llm.providers.ollama.requests.get')
    @patch('backend.llm.providers.ollama.requests.post')
    def test_chat_success(self, mock_post, mock_get):
        """Test successful chat with Ollama"""
        # Mock availability check
        mock_get_response = Mock()
        mock_get_response.status_code = 200
        mock_get.return_value = mock_get_response
        
        # Mock chat response
        mock_post_response = Mock()
        mock_post_response.json.return_value = {
            'message': {'content': 'Ollama response'}
        }
        mock_post.return_value = mock_post_response
        
        config = {'base_url': 'http://localhost:11434'}
        provider = OllamaProvider(config)
        
        result = provider.chat("System prompt", "User prompt", temperature=0.3)
        
        assert result == 'Ollama response'
        mock_post.assert_called_once()
        call_kwargs = mock_post.call_args[1]
        assert call_kwargs['json']['model'] == 'llama3.1:8b'
        assert call_kwargs['json']['stream'] is False
        assert call_kwargs['json']['options']['temperature'] == 0.3
    
    @patch('backend.llm.providers.ollama.requests.get')
    def test_chat_not_available(self, mock_get):
        """Test chat raises error when Ollama not available"""
        mock_get.side_effect = requests.ConnectionError("Connection refused")
        
        config = {}
        provider = OllamaProvider(config)
        
        with pytest.raises(ProviderUnavailableError, match="Ollama not available"):
            provider.chat("System", "User")
    
    @patch('backend.llm.providers.ollama.requests.get')
    @patch('backend.llm.providers.ollama.requests.post')
    def test_chat_timeout(self, mock_post, mock_get):
        """Test chat detects timeout errors"""
        # Mock availability check
        mock_get_response = Mock()
        mock_get_response.status_code = 200
        mock_get.return_value = mock_get_response
        
        # Mock timeout
        mock_post.side_effect = requests.Timeout("Request timeout")
        
        config = {}
        provider = OllamaProvider(config)
        
        with pytest.raises(TimeoutError, match="Ollama request timeout"):
            provider.chat("System", "User")
    
    @patch('backend.llm.providers.ollama.requests.get')
    @patch('backend.llm.providers.ollama.requests.post')
    def test_chat_error(self, mock_post, mock_get):
        """Test chat handles generic errors"""
        # Mock availability check
        mock_get_response = Mock()
        mock_get_response.status_code = 200
        mock_get.return_value = mock_get_response
        
        # Mock error
        mock_post.side_effect = Exception("Model not found")
        
        config = {}
        provider = OllamaProvider(config)
        
        with pytest.raises(ProviderUnavailableError, match="Ollama error"):
            provider.chat("System", "User")
    
    @patch('backend.llm.providers.ollama.requests.get')
    def test_is_available_success(self, mock_get):
        """Test is_available returns True when Ollama is reachable"""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_get.return_value = mock_response
        
        config = {}
        provider = OllamaProvider(config)
        
        assert provider.is_available()
        mock_get.assert_called_once_with('http://localhost:11434/api/tags', timeout=2)
    
    @patch('backend.llm.providers.ollama.requests.get')
    def test_is_available_failure(self, mock_get):
        """Test is_available returns False when Ollama not reachable"""
        mock_get.side_effect = requests.ConnectionError("Connection refused")
        
        config = {}
        provider = OllamaProvider(config)
        
        assert not provider.is_available()
    
    @patch('backend.llm.providers.ollama.requests.get')
    def test_is_available_caching(self, mock_get):
        """Test is_available caches result to avoid repeated checks"""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_get.return_value = mock_response
        
        config = {}
        provider = OllamaProvider(config)
        
        # First call should make request
        assert provider.is_available()
        assert mock_get.call_count == 1
        
        # Second call should use cache
        assert provider.is_available()
        assert mock_get.call_count == 1  # No additional call
    
    @patch('backend.llm.providers.ollama.requests.get')
    def test_is_available_timeout(self, mock_get):
        """Test is_available uses 2-second timeout"""
        mock_get.side_effect = requests.Timeout("Timeout")
        
        config = {}
        provider = OllamaProvider(config)
        
        assert not provider.is_available()
        mock_get.assert_called_once_with('http://localhost:11434/api/tags', timeout=2)


# ============================================================================
# Local LLM Provider Tests
# ============================================================================

class TestLocalLLMProvider:
    """Tests for OpenAI-compatible local LLM provider"""
    
    def test_init(self):
        """Test local provider initialization"""
        config = {'base_url': 'http://localhost:1234', 'model': 'custom-model'}
        provider = LocalLLMProvider(config)
        
        assert provider.base_url == 'http://localhost:1234'
        assert provider.model == 'custom-model'
        assert provider.name == 'local'
        assert provider._available is None
    
    def test_init_default_model(self):
        """Test local provider uses default model"""
        config = {'base_url': 'http://localhost:1234'}
        provider = LocalLLMProvider(config)
        
        assert provider.model == 'local'
    
    @patch('backend.llm.providers.local.requests.get')
    @patch('backend.llm.providers.local.requests.post')
    def test_chat_success(self, mock_post, mock_get):
        """Test successful chat with local LLM"""
        # Mock availability check
        mock_get_response = Mock()
        mock_get_response.status_code = 200
        mock_get.return_value = mock_get_response
        
        # Mock chat response
        mock_post_response = Mock()
        mock_post_response.json.return_value = {
            'choices': [{'message': {'content': 'Local LLM response'}}]
        }
        mock_post.return_value = mock_post_response
        
        config = {'base_url': 'http://localhost:1234'}
        provider = LocalLLMProvider(config)
        
        result = provider.chat("System prompt", "User prompt", temperature=0.5)
        
        assert result == 'Local LLM response'
        mock_post.assert_called_once()
        call_kwargs = mock_post.call_args[1]
        assert call_kwargs['json']['messages'][0]['content'] == 'System prompt'
        assert call_kwargs['json']['messages'][1]['content'] == 'User prompt'
        assert call_kwargs['json']['temperature'] == 0.5
    
    def test_chat_no_base_url(self):
        """Test chat raises error when base URL not configured"""
        config = {}
        provider = LocalLLMProvider(config)
        
        with pytest.raises(ProviderUnavailableError, match="Local LLM base URL not configured"):
            provider.chat("System", "User")
    
    @patch('backend.llm.providers.local.requests.get')
    def test_chat_not_available(self, mock_get):
        """Test chat raises error when local LLM not available"""
        mock_get.side_effect = requests.ConnectionError("Connection refused")
        
        config = {'base_url': 'http://localhost:1234'}
        provider = LocalLLMProvider(config)
        
        with pytest.raises(ProviderUnavailableError, match="Local LLM not available"):
            provider.chat("System", "User")
    
    @patch('backend.llm.providers.local.requests.get')
    @patch('backend.llm.providers.local.requests.post')
    def test_chat_timeout(self, mock_post, mock_get):
        """Test chat detects timeout errors"""
        # Mock availability check
        mock_get_response = Mock()
        mock_get_response.status_code = 200
        mock_get.return_value = mock_get_response
        
        # Mock timeout
        mock_post.side_effect = requests.Timeout("Request timeout")
        
        config = {'base_url': 'http://localhost:1234'}
        provider = LocalLLMProvider(config)
        
        with pytest.raises(TimeoutError, match="Local LLM request timeout"):
            provider.chat("System", "User", timeout=30)
    
    @patch('backend.llm.providers.local.requests.get')
    @patch('backend.llm.providers.local.requests.post')
    def test_chat_http_error(self, mock_post, mock_get):
        """Test chat handles HTTP errors"""
        # Mock availability check
        mock_get_response = Mock()
        mock_get_response.status_code = 200
        mock_get.return_value = mock_get_response
        
        # Mock HTTP error
        mock_post_response = Mock()
        mock_post_response.raise_for_status.side_effect = requests.HTTPError("500 Server Error")
        mock_post.return_value = mock_post_response
        
        config = {'base_url': 'http://localhost:1234'}
        provider = LocalLLMProvider(config)
        
        with pytest.raises(ProviderUnavailableError, match="Local LLM error"):
            provider.chat("System", "User")
    
    @patch('backend.llm.providers.local.requests.get')
    def test_is_available_success(self, mock_get):
        """Test is_available returns True when local LLM is reachable"""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_get.return_value = mock_response
        
        config = {'base_url': 'http://localhost:1234'}
        provider = LocalLLMProvider(config)
        
        assert provider.is_available()
        mock_get.assert_called_once_with('http://localhost:1234/models', timeout=2)
    
    @patch('backend.llm.providers.local.requests.get')
    def test_is_available_failure(self, mock_get):
        """Test is_available returns False when not reachable"""
        mock_get.side_effect = requests.ConnectionError("Connection refused")
        
        config = {'base_url': 'http://localhost:1234'}
        provider = LocalLLMProvider(config)
        
        assert not provider.is_available()
    
    def test_is_available_no_base_url(self):
        """Test is_available returns False when no base URL"""
        config = {}
        provider = LocalLLMProvider(config)
        
        assert not provider.is_available()
    
    @patch('backend.llm.providers.local.requests.get')
    def test_is_available_caching(self, mock_get):
        """Test is_available caches result"""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_get.return_value = mock_response
        
        config = {'base_url': 'http://localhost:1234'}
        provider = LocalLLMProvider(config)
        
        # First call
        assert provider.is_available()
        assert mock_get.call_count == 1
        
        # Second call should use cache
        assert provider.is_available()
        assert mock_get.call_count == 1
    
    @patch('backend.llm.providers.local.requests.get')
    def test_is_available_timeout_handling(self, mock_get):
        """Test is_available handles timeout gracefully"""
        mock_get.side_effect = requests.Timeout("Timeout")
        
        config = {'base_url': 'http://localhost:1234'}
        provider = LocalLLMProvider(config)
        
        assert not provider.is_available()
        mock_get.assert_called_once_with('http://localhost:1234/models', timeout=2)
