"""
Configuration system for LLM providers
"""

from dataclasses import dataclass, field
from typing import List, Optional, Dict
import os


@dataclass
class RetryConfig:
    """Retry behavior configuration"""
    max_retries: int = 3
    initial_delay: float = 2.0  # seconds
    timeout: int = 60  # seconds
    
    @classmethod
    def from_env(cls) -> 'RetryConfig':
        """Load retry configuration from environment variables"""
        return cls(
            max_retries=int(os.getenv('LLM_MAX_RETRIES', '3')),
            initial_delay=float(os.getenv('LLM_RETRY_DELAY', '2.0')),
            timeout=int(os.getenv('LLM_TIMEOUT', '60'))
        )


@dataclass
class ProviderConfig:
    """Individual provider configuration"""
    name: str
    api_key: Optional[str] = None
    model: Optional[str] = None
    base_url: Optional[str] = None
    extra: Dict = field(default_factory=dict)  # Provider-specific settings


@dataclass
class LLMConfig:
    """Complete LLM system configuration"""
    primary_provider: str
    fallback_chain: List[str]
    providers: Dict[str, ProviderConfig]
    retry_config: RetryConfig
    
    @classmethod
    def from_env(cls) -> 'LLMConfig':
        """Load configuration from environment variables"""
        import logging
        logger = logging.getLogger("regops.llm.config")
        
        logger.info("Loading LLM configuration from environment variables")
        
        primary = os.getenv('LLM_PROVIDER', 'gemini')
        fallback_str = os.getenv('LLM_FALLBACK_CHAIN', 'gemini,openrouter,ollama')
        fallback_chain = [p.strip() for p in fallback_str.split(',')]
        
        logger.info(f"Primary provider: {primary}")
        logger.info(f"Fallback chain: {fallback_chain}")
        
        providers = {}
        
        # Gemini configuration
        if os.getenv('GEMINI_API_KEY'):
            model = os.getenv('GEMINI_MODEL', 'gemini-1.5-flash')
            providers['gemini'] = ProviderConfig(
                name='gemini',
                api_key=os.getenv('GEMINI_API_KEY'),
                model=model
            )
            logger.info(f"Configured Gemini provider with model: {model}")
        
        # OpenRouter configuration
        if os.getenv('OPENROUTER_API_KEY'):
            model = os.getenv('OPENROUTER_MODEL', 'anthropic/claude-3.5-sonnet')
            providers['openrouter'] = ProviderConfig(
                name='openrouter',
                api_key=os.getenv('OPENROUTER_API_KEY'),
                model=model
            )
            logger.info(f"Configured OpenRouter provider with model: {model}")
        
        # Ollama configuration
        if os.getenv('OLLAMA_BASE_URL') or os.getenv('OLLAMA_MODEL'):
            base_url = os.getenv('OLLAMA_BASE_URL', 'http://localhost:11434')
            model = os.getenv('OLLAMA_MODEL', 'llama3.1:8b')
            providers['ollama'] = ProviderConfig(
                name='ollama',
                base_url=base_url,
                model=model
            )
            logger.info(f"Configured Ollama provider at {base_url} with model: {model}")
        
        # Local LLM configuration (OpenAI-compatible)
        if os.getenv('LOCAL_LLM_BASE_URL'):
            base_url = os.getenv('LOCAL_LLM_BASE_URL')
            model = os.getenv('LOCAL_LLM_MODEL', 'local')
            providers['local'] = ProviderConfig(
                name='local',
                base_url=base_url,
                model=model
            )
            logger.info(f"Configured local LLM provider at {base_url} with model: {model}")
        
        if not providers:
            logger.warning("No LLM providers configured via environment variables")
        
        retry_config = RetryConfig.from_env()
        logger.info(
            f"Retry configuration: max_retries={retry_config.max_retries}, "
            f"initial_delay={retry_config.initial_delay}s, timeout={retry_config.timeout}s"
        )
        
        return cls(
            primary_provider=primary,
            fallback_chain=fallback_chain,
            providers=providers,
            retry_config=retry_config
        )
    
    def validate(self) -> List[str]:
        """
        Validate configuration and return list of warnings
        
        Returns:
            List of warning messages (empty if valid)
        """
        import logging
        logger = logging.getLogger("regops.llm.config")
        
        warnings = []
        
        if not self.providers:
            warning = "No LLM providers configured - system will use deterministic fallback only"
            warnings.append(warning)
            logger.error(warning)
        
        if self.primary_provider not in self.providers:
            warning = f"Primary provider '{self.primary_provider}' not configured - will use first available provider"
            warnings.append(warning)
            logger.warning(warning)
        
        for provider_name in self.fallback_chain:
            if provider_name not in self.providers:
                warning = f"Fallback provider '{provider_name}' not configured - will be skipped in fallback chain"
                warnings.append(warning)
                logger.warning(warning)
        
        if self.retry_config.max_retries < 1:
            warning = "LLM_MAX_RETRIES must be positive, using default: 3"
            warnings.append(warning)
            logger.warning(warning)
            self.retry_config.max_retries = 3
        
        if self.retry_config.timeout < 1:
            warning = "LLM_TIMEOUT must be positive, using default: 60"
            warnings.append(warning)
            logger.warning(warning)
            self.retry_config.timeout = 60
        
        if not warnings:
            logger.info("LLM configuration validated successfully")
        else:
            logger.warning(f"LLM configuration validation completed with {len(warnings)} warning(s)")
        
        return warnings
