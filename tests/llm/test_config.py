"""
Unit tests for LLM configuration system

Tests cover:
- Loading configuration from environment variables
- Configuration validation
- Default values
- Invalid configuration handling
"""

import pytest
import os
from unittest.mock import patch

from backend.llm.config import RetryConfig, ProviderConfig, LLMConfig


# ============================================================================
# RetryConfig Tests
# ============================================================================

class TestRetryConfig:
    """Tests for RetryConfig dataclass"""
    
    def test_default_values(self):
        """Test RetryConfig uses correct default values"""
        config = RetryConfig()
        
        assert config.max_retries == 3
        assert config.initial_delay == 2.0
        assert config.timeout == 60
    
    def test_custom_values(self):
        """Test RetryConfig accepts custom values"""
        config = RetryConfig(max_retries=5, initial_delay=1.0, timeout=120)
        
        assert config.max_retries == 5
        assert config.initial_delay == 1.0
        assert config.timeout == 120
    
    def test_from_env_with_all_variables(self):
        """Test loading RetryConfig from environment variables"""
        env_vars = {
            'LLM_MAX_RETRIES': '5',
            'LLM_RETRY_DELAY': '3.0',
            'LLM_TIMEOUT': '90'
        }
        
        with patch.dict(os.environ, env_vars, clear=False):
            config = RetryConfig.from_env()
            
            assert config.max_retries == 5
            assert config.initial_delay == 3.0
            assert config.timeout == 90
    
    def test_from_env_with_defaults(self):
        """Test RetryConfig.from_env uses defaults when env vars not set"""
        # Use empty dict to ensure no relevant env vars are set
        with patch.dict(os.environ, {}, clear=True):
            config = RetryConfig.from_env()
            
            assert config.max_retries == 3
            assert config.initial_delay == 2.0
            assert config.timeout == 60
    
    def test_from_env_partial_configuration(self):
        """Test RetryConfig.from_env with only some env vars set"""
        env_vars = {
            'LLM_MAX_RETRIES': '10'
        }
        
        with patch.dict(os.environ, env_vars, clear=True):
            config = RetryConfig.from_env()
            
            assert config.max_retries == 10
            assert config.initial_delay == 2.0  # Default
            assert config.timeout == 60  # Default


# ============================================================================
# ProviderConfig Tests
# ============================================================================

class TestProviderConfig:
    """Tests for ProviderConfig dataclass"""
    
    def test_minimal_configuration(self):
        """Test ProviderConfig with only name"""
        config = ProviderConfig(name='test')
        
        assert config.name == 'test'
        assert config.api_key is None
        assert config.model is None
        assert config.base_url is None
        assert config.extra == {}
    
    def test_full_configuration(self):
        """Test ProviderConfig with all fields"""
        config = ProviderConfig(
            name='gemini',
            api_key='test-key',
            model='gemini-1.5-flash',
            base_url='https://api.example.com',
            extra={'custom': 'value'}
        )
        
        assert config.name == 'gemini'
        assert config.api_key == 'test-key'
        assert config.model == 'gemini-1.5-flash'
        assert config.base_url == 'https://api.example.com'
        assert config.extra == {'custom': 'value'}
    
    def test_extra_defaults_to_empty_dict(self):
        """Test extra field defaults to empty dict"""
        config = ProviderConfig(name='test')
        
        assert isinstance(config.extra, dict)
        assert len(config.extra) == 0


# ============================================================================
# LLMConfig Tests
# ============================================================================

class TestLLMConfig:
    """Tests for LLMConfig loading and validation"""
    
    def test_from_env_gemini_only(self):
        """Test loading configuration with only Gemini provider"""
        env_vars = {
            'LLM_PROVIDER': 'gemini',
            'GEMINI_API_KEY': 'test-gemini-key',
            'GEMINI_MODEL': 'gemini-1.5-pro'
        }
        
        with patch.dict(os.environ, env_vars, clear=True):
            config = LLMConfig.from_env()
            
            assert config.primary_provider == 'gemini'
            assert 'gemini' in config.providers
            assert config.providers['gemini'].api_key == 'test-gemini-key'
            assert config.providers['gemini'].model == 'gemini-1.5-pro'
    
    def test_from_env_gemini_default_model(self):
        """Test Gemini uses default model when not specified"""
        env_vars = {
            'GEMINI_API_KEY': 'test-key'
        }
        
        with patch.dict(os.environ, env_vars, clear=True):
            config = LLMConfig.from_env()
            
            assert config.providers['gemini'].model == 'gemini-1.5-flash'
    
    def test_from_env_openrouter_only(self):
        """Test loading configuration with only OpenRouter provider"""
        env_vars = {
            'LLM_PROVIDER': 'openrouter',
            'OPENROUTER_API_KEY': 'test-openrouter-key',
            'OPENROUTER_MODEL': 'anthropic/claude-3.5-sonnet'
        }
        
        with patch.dict(os.environ, env_vars, clear=True):
            config = LLMConfig.from_env()
            
            assert config.primary_provider == 'openrouter'
            assert 'openrouter' in config.providers
            assert config.providers['openrouter'].api_key == 'test-openrouter-key'
            assert config.providers['openrouter'].model == 'anthropic/claude-3.5-sonnet'
    
    def test_from_env_openrouter_default_model(self):
        """Test OpenRouter uses default model when not specified"""
        env_vars = {
            'OPENROUTER_API_KEY': 'test-key'
        }
        
        with patch.dict(os.environ, env_vars, clear=True):
            config = LLMConfig.from_env()
            
            assert config.providers['openrouter'].model == 'anthropic/claude-3.5-sonnet'
    
    def test_from_env_ollama_with_base_url(self):
        """Test loading Ollama configuration with base URL"""
        env_vars = {
            'OLLAMA_BASE_URL': 'http://localhost:11434',
            'OLLAMA_MODEL': 'llama3.1:8b'
        }
        
        with patch.dict(os.environ, env_vars, clear=True):
            config = LLMConfig.from_env()
            
            assert 'ollama' in config.providers
            assert config.providers['ollama'].base_url == 'http://localhost:11434'
            assert config.providers['ollama'].model == 'llama3.1:8b'
    
    def test_from_env_ollama_with_model_only(self):
        """Test loading Ollama configuration with only model specified"""
        env_vars = {
            'OLLAMA_MODEL': 'mistral:7b'
        }
        
        with patch.dict(os.environ, env_vars, clear=True):
            config = LLMConfig.from_env()
            
            assert 'ollama' in config.providers
            assert config.providers['ollama'].base_url == 'http://localhost:11434'  # Default
            assert config.providers['ollama'].model == 'mistral:7b'
    
    def test_from_env_ollama_defaults(self):
        """Test Ollama uses default values when only base URL specified"""
        env_vars = {
            'OLLAMA_BASE_URL': 'http://custom:11434'
        }
        
        with patch.dict(os.environ, env_vars, clear=True):
            config = LLMConfig.from_env()
            
            assert config.providers['ollama'].model == 'llama3.1:8b'
    
    def test_from_env_local_llm(self):
        """Test loading local LLM configuration"""
        env_vars = {
            'LOCAL_LLM_BASE_URL': 'http://localhost:1234',
            'LOCAL_LLM_MODEL': 'custom-model'
        }
        
        with patch.dict(os.environ, env_vars, clear=True):
            config = LLMConfig.from_env()
            
            assert 'local' in config.providers
            assert config.providers['local'].base_url == 'http://localhost:1234'
            assert config.providers['local'].model == 'custom-model'
    
    def test_from_env_local_llm_default_model(self):
        """Test local LLM uses default model when not specified"""
        env_vars = {
            'LOCAL_LLM_BASE_URL': 'http://localhost:1234'
        }
        
        with patch.dict(os.environ, env_vars, clear=True):
            config = LLMConfig.from_env()
            
            assert config.providers['local'].model == 'local'
    
    def test_from_env_multiple_providers(self):
        """Test loading configuration with multiple providers"""
        env_vars = {
            'LLM_PROVIDER': 'gemini',
            'GEMINI_API_KEY': 'gemini-key',
            'OPENROUTER_API_KEY': 'openrouter-key',
            'OLLAMA_BASE_URL': 'http://localhost:11434',
            'LOCAL_LLM_BASE_URL': 'http://localhost:1234'
        }
        
        with patch.dict(os.environ, env_vars, clear=True):
            config = LLMConfig.from_env()
            
            assert len(config.providers) == 4
            assert 'gemini' in config.providers
            assert 'openrouter' in config.providers
            assert 'ollama' in config.providers
            assert 'local' in config.providers
    
    def test_from_env_default_primary_provider(self):
        """Test default primary provider is gemini"""
        with patch.dict(os.environ, {}, clear=True):
            config = LLMConfig.from_env()
            
            assert config.primary_provider == 'gemini'
    
    def test_from_env_custom_primary_provider(self):
        """Test custom primary provider from environment"""
        env_vars = {
            'LLM_PROVIDER': 'openrouter',
            'OPENROUTER_API_KEY': 'test-key'
        }
        
        with patch.dict(os.environ, env_vars, clear=True):
            config = LLMConfig.from_env()
            
            assert config.primary_provider == 'openrouter'
    
    def test_from_env_default_fallback_chain(self):
        """Test default fallback chain"""
        with patch.dict(os.environ, {}, clear=True):
            config = LLMConfig.from_env()
            
            assert config.fallback_chain == ['gemini', 'openrouter', 'ollama']
    
    def test_from_env_custom_fallback_chain(self):
        """Test custom fallback chain from environment"""
        env_vars = {
            'LLM_FALLBACK_CHAIN': 'openrouter,gemini,local'
        }
        
        with patch.dict(os.environ, env_vars, clear=True):
            config = LLMConfig.from_env()
            
            assert config.fallback_chain == ['openrouter', 'gemini', 'local']
    
    def test_from_env_fallback_chain_with_spaces(self):
        """Test fallback chain handles spaces in comma-separated list"""
        env_vars = {
            'LLM_FALLBACK_CHAIN': 'gemini , openrouter , ollama'
        }
        
        with patch.dict(os.environ, env_vars, clear=True):
            config = LLMConfig.from_env()
            
            assert config.fallback_chain == ['gemini', 'openrouter', 'ollama']
    
    def test_from_env_no_providers_configured(self):
        """Test configuration when no providers are configured"""
        with patch.dict(os.environ, {}, clear=True):
            config = LLMConfig.from_env()
            
            assert len(config.providers) == 0
    
    def test_from_env_includes_retry_config(self):
        """Test configuration includes retry config"""
        env_vars = {
            'LLM_MAX_RETRIES': '5',
            'LLM_TIMEOUT': '120'
        }
        
        with patch.dict(os.environ, env_vars, clear=True):
            config = LLMConfig.from_env()
            
            assert config.retry_config.max_retries == 5
            assert config.retry_config.timeout == 120


# ============================================================================
# Configuration Validation Tests
# ============================================================================

class TestLLMConfigValidation:
    """Tests for LLMConfig.validate() method"""
    
    def test_validate_no_providers(self):
        """Test validation warns when no providers configured"""
        config = LLMConfig(
            primary_provider='gemini',
            fallback_chain=['gemini'],
            providers={},
            retry_config=RetryConfig()
        )
        
        warnings = config.validate()
        
        assert len(warnings) > 0
        assert any('No LLM providers configured' in w for w in warnings)
    
    def test_validate_primary_not_configured(self):
        """Test validation warns when primary provider not configured"""
        config = LLMConfig(
            primary_provider='gemini',
            fallback_chain=['openrouter'],
            providers={
                'openrouter': ProviderConfig(name='openrouter', api_key='test-key')
            },
            retry_config=RetryConfig()
        )
        
        warnings = config.validate()
        
        assert len(warnings) > 0
        assert any('Primary provider' in w and 'not configured' in w for w in warnings)
    
    def test_validate_fallback_provider_not_configured(self):
        """Test validation warns when fallback provider not configured"""
        config = LLMConfig(
            primary_provider='gemini',
            fallback_chain=['gemini', 'openrouter', 'ollama'],
            providers={
                'gemini': ProviderConfig(name='gemini', api_key='test-key')
            },
            retry_config=RetryConfig()
        )
        
        warnings = config.validate()
        
        assert len(warnings) >= 2
        assert any('openrouter' in w and 'not configured' in w for w in warnings)
        assert any('ollama' in w and 'not configured' in w for w in warnings)
    
    def test_validate_invalid_max_retries(self):
        """Test validation corrects invalid max_retries"""
        config = LLMConfig(
            primary_provider='gemini',
            fallback_chain=['gemini'],
            providers={
                'gemini': ProviderConfig(name='gemini', api_key='test-key')
            },
            retry_config=RetryConfig(max_retries=0)
        )
        
        warnings = config.validate()
        
        assert len(warnings) > 0
        assert any('LLM_MAX_RETRIES must be positive' in w for w in warnings)
        assert config.retry_config.max_retries == 3  # Corrected to default
    
    def test_validate_negative_max_retries(self):
        """Test validation corrects negative max_retries"""
        config = LLMConfig(
            primary_provider='gemini',
            fallback_chain=['gemini'],
            providers={
                'gemini': ProviderConfig(name='gemini', api_key='test-key')
            },
            retry_config=RetryConfig(max_retries=-1)
        )
        
        warnings = config.validate()
        
        assert any('LLM_MAX_RETRIES must be positive' in w for w in warnings)
        assert config.retry_config.max_retries == 3
    
    def test_validate_invalid_timeout(self):
        """Test validation corrects invalid timeout"""
        config = LLMConfig(
            primary_provider='gemini',
            fallback_chain=['gemini'],
            providers={
                'gemini': ProviderConfig(name='gemini', api_key='test-key')
            },
            retry_config=RetryConfig(timeout=0)
        )
        
        warnings = config.validate()
        
        assert len(warnings) > 0
        assert any('LLM_TIMEOUT must be positive' in w for w in warnings)
        assert config.retry_config.timeout == 60  # Corrected to default
    
    def test_validate_negative_timeout(self):
        """Test validation corrects negative timeout"""
        config = LLMConfig(
            primary_provider='gemini',
            fallback_chain=['gemini'],
            providers={
                'gemini': ProviderConfig(name='gemini', api_key='test-key')
            },
            retry_config=RetryConfig(timeout=-10)
        )
        
        warnings = config.validate()
        
        assert any('LLM_TIMEOUT must be positive' in w for w in warnings)
        assert config.retry_config.timeout == 60
    
    def test_validate_valid_configuration(self):
        """Test validation returns no warnings for valid configuration"""
        config = LLMConfig(
            primary_provider='gemini',
            fallback_chain=['gemini', 'openrouter'],
            providers={
                'gemini': ProviderConfig(name='gemini', api_key='test-key'),
                'openrouter': ProviderConfig(name='openrouter', api_key='test-key')
            },
            retry_config=RetryConfig(max_retries=3, timeout=60)
        )
        
        warnings = config.validate()
        
        assert len(warnings) == 0
    
    def test_validate_multiple_warnings(self):
        """Test validation can return multiple warnings"""
        config = LLMConfig(
            primary_provider='gemini',
            fallback_chain=['gemini', 'openrouter'],
            providers={},
            retry_config=RetryConfig(max_retries=0, timeout=-1)
        )
        
        warnings = config.validate()
        
        # Should have warnings for: no providers, invalid retries, invalid timeout
        assert len(warnings) >= 3
    
    def test_validate_partial_fallback_chain(self):
        """Test validation with some fallback providers configured"""
        config = LLMConfig(
            primary_provider='gemini',
            fallback_chain=['gemini', 'openrouter', 'ollama'],
            providers={
                'gemini': ProviderConfig(name='gemini', api_key='test-key'),
                'openrouter': ProviderConfig(name='openrouter', api_key='test-key')
            },
            retry_config=RetryConfig()
        )
        
        warnings = config.validate()
        
        # Should only warn about ollama
        assert len(warnings) == 1
        assert 'ollama' in warnings[0]
        assert 'not configured' in warnings[0]


# ============================================================================
# Integration Tests
# ============================================================================

class TestConfigurationIntegration:
    """Integration tests for full configuration workflow"""
    
    def test_full_configuration_workflow(self):
        """Test complete workflow: load from env, validate, use"""
        env_vars = {
            'LLM_PROVIDER': 'gemini',
            'LLM_FALLBACK_CHAIN': 'gemini,openrouter',
            'GEMINI_API_KEY': 'test-gemini-key',
            'GEMINI_MODEL': 'gemini-1.5-flash',
            'OPENROUTER_API_KEY': 'test-openrouter-key',
            'LLM_MAX_RETRIES': '5',
            'LLM_TIMEOUT': '90'
        }
        
        with patch.dict(os.environ, env_vars, clear=True):
            # Load configuration
            config = LLMConfig.from_env()
            
            # Validate
            warnings = config.validate()
            assert len(warnings) == 0
            
            # Verify configuration
            assert config.primary_provider == 'gemini'
            assert config.fallback_chain == ['gemini', 'openrouter']
            assert len(config.providers) == 2
            assert config.retry_config.max_retries == 5
            assert config.retry_config.timeout == 90
    
    def test_configuration_with_validation_corrections(self):
        """Test configuration that requires validation corrections"""
        env_vars = {
            'GEMINI_API_KEY': 'test-key',
            'LLM_MAX_RETRIES': '0',
            'LLM_TIMEOUT': '-1'
        }
        
        with patch.dict(os.environ, env_vars, clear=True):
            # Load configuration
            config = LLMConfig.from_env()
            
            # Validate (should correct invalid values)
            warnings = config.validate()
            assert len(warnings) >= 2
            
            # Verify corrections applied
            assert config.retry_config.max_retries == 3
            assert config.retry_config.timeout == 60
    
    def test_minimal_valid_configuration(self):
        """Test minimal valid configuration"""
        env_vars = {
            'GEMINI_API_KEY': 'test-key'
        }
        
        with patch.dict(os.environ, env_vars, clear=True):
            config = LLMConfig.from_env()
            warnings = config.validate()
            
            # Should have warnings about fallback chain but still usable
            assert 'gemini' in config.providers
            assert config.retry_config.max_retries > 0
            assert config.retry_config.timeout > 0
