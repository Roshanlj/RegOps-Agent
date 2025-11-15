"""Base provider interface for all LLM providers"""

from abc import ABC, abstractmethod
from typing import Dict, Any


class LLMProvider(ABC):
    """Base interface for all LLM providers"""
    
    def __init__(self, config: Dict[str, Any]):
        """
        Initialize provider with configuration
        
        Args:
            config: Provider-specific configuration dictionary
        """
        self.config = config
    
    @abstractmethod
    def chat(self, system: str, user: str, **kwargs) -> str:
        """
        Send chat completion request
        
        Args:
            system: System prompt
            user: User prompt
            **kwargs: Provider-specific parameters (temperature, max_tokens, etc.)
            
        Returns:
            Response text from LLM
            
        Raises:
            RateLimitError: When rate limit is hit (HTTP 429)
            ProviderUnavailableError: When provider is not reachable
            TimeoutError: When request exceeds timeout
        """
        pass
    
    @abstractmethod
    def is_available(self) -> bool:
        """
        Check if provider is configured and reachable
        
        Returns:
            True if provider can be used, False otherwise
        """
        pass
    
    @property
    @abstractmethod
    def name(self) -> str:
        """Provider name for logging (e.g., 'gemini', 'openrouter')"""
        pass
    
    @property
    def supports_streaming(self) -> bool:
        """Whether provider supports streaming responses (future enhancement)"""
        return False
