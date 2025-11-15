"""
LLM Manager with automatic fallback chain
"""

import logging
from typing import Optional, List, Dict

from .config import LLMConfig
from .provider import LLMProvider
from .retry import with_exponential_backoff
from .exceptions import AllProvidersFailedError

logger = logging.getLogger("regops.llm.manager")


class LLMManager:
    """Manages multiple LLM providers with automatic fallback"""
    
    def __init__(self, config: LLMConfig):
        self.config = config
        self.providers: Dict[str, LLMProvider] = {}
        self._init_providers()
        self._last_used_provider: Optional[str] = None
    
    def _init_providers(self):
        """Initialize all configured providers"""
        from .providers.gemini import GeminiProvider
        from .providers.openrouter import OpenRouterProvider
        from .providers.ollama import OllamaProvider
        from .providers.local import LocalLLMProvider
        
        provider_classes = {
            'gemini': GeminiProvider,
            'openrouter': OpenRouterProvider,
            'ollama': OllamaProvider,
            'local': LocalLLMProvider
        }
        
        logger.info(f"Initializing LLM providers from configuration: {list(self.config.providers.keys())}")
        
        for name, provider_config in self.config.providers.items():
            if name in provider_classes:
                try:
                    logger.info(f"Attempting to initialize provider: {name}")
                    provider = provider_classes[name](provider_config.__dict__)
                    if provider.is_available():
                        self.providers[name] = provider
                        logger.info(f"Successfully initialized and verified provider: {name}")
                    else:
                        logger.warning(
                            f"Provider {name} is configured but not available. "
                            f"Check configuration and connectivity."
                        )
                except Exception as e:
                    logger.error(
                        f"Failed to initialize provider {name}: {type(e).__name__}: {e}",
                        exc_info=True
                    )
            else:
                logger.warning(f"Unknown provider type in configuration: {name}")
        
        if not self.providers:
            logger.error("No LLM providers successfully initialized. System will use deterministic fallback only.")
        else:
            logger.info(f"LLM Manager initialized with {len(self.providers)} available provider(s): {list(self.providers.keys())}")
    
    def chat(self, system: str, user: str, **kwargs) -> str:
        """
        Execute chat with automatic fallback through provider chain
        
        Args:
            system: System prompt
            user: User prompt
            **kwargs: Additional parameters (temperature, max_tokens, etc.)
        
        Returns:
            LLM response string
        
        Raises:
            AllProvidersFailedError: If all providers in chain fail
        """
        # Build ordered list of providers to try
        providers_to_try = self._get_provider_chain()
        
        if not providers_to_try:
            logger.warning("No LLM providers available, deterministic fallback will be used")
            raise AllProvidersFailedError("No providers configured")
        
        logger.info(f"Starting LLM request with provider chain: {providers_to_try}")
        
        last_error = None
        attempted_providers = []
        
        for idx, provider_name in enumerate(providers_to_try):
            provider = self.providers.get(provider_name)
            if not provider:
                logger.warning(f"Skipping unconfigured provider in chain: {provider_name}")
                continue
            
            # Log fallback transition if not the first provider
            if idx > 0:
                logger.info(f"Falling back from {attempted_providers[-1]} to {provider_name}")
            
            attempted_providers.append(provider_name)
            
            try:
                logger.info(f"Attempting provider: {provider_name} (attempt {idx + 1}/{len(providers_to_try)})")
                response = self._try_provider_with_retry(provider, system, user, **kwargs)
                self._last_used_provider = provider_name
                logger.info(f"Successfully received response from provider: {provider_name}")
                return response
                
            except Exception as e:
                last_error = e
                logger.warning(f"Provider {provider_name} failed with error: {type(e).__name__}: {e}")
                # Continue to next provider in chain
        
        # All providers failed
        logger.error(
            f"All LLM providers failed after attempting: {attempted_providers}. "
            f"Deterministic fallback will be used. Last error: {type(last_error).__name__}: {last_error}"
        )
        raise AllProvidersFailedError(f"All providers failed. Last error: {last_error}")
    
    def _get_provider_chain(self) -> List[str]:
        """Get ordered list of providers to try"""
        chain = []
        
        # Start with primary provider if available
        if self.config.primary_provider in self.providers:
            chain.append(self.config.primary_provider)
        
        # Add fallback chain, avoiding duplicates
        for provider_name in self.config.fallback_chain:
            if provider_name not in chain and provider_name in self.providers:
                chain.append(provider_name)
        
        return chain
    
    def _try_provider_with_retry(
        self, 
        provider: LLMProvider, 
        system: str, 
        user: str, 
        **kwargs
    ) -> str:
        """Try a single provider with retry logic"""
        retry_config = self.config.retry_config
        
        @with_exponential_backoff(
            max_retries=retry_config.max_retries,
            initial_delay=retry_config.initial_delay
        )
        def _call():
            return provider.chat(system, user, timeout=retry_config.timeout, **kwargs)
        
        return _call()
    
    @property
    def last_used_provider(self) -> Optional[str]:
        """Get the name of the last successfully used provider"""
        return self._last_used_provider
    
    def get_available_providers(self) -> List[str]:
        """Get list of currently available provider names"""
        return list(self.providers.keys())
