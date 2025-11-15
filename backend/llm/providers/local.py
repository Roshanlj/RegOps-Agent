"""
OpenAI-compatible local LLM provider (LM Studio, llama.cpp, vLLM, etc.)
"""

import requests
from ..provider import LLMProvider
from ..exceptions import ProviderUnavailableError, TimeoutError


class LocalLLMProvider(LLMProvider):
    """OpenAI-compatible local LLM provider (LM Studio, llama.cpp, vLLM, etc.)"""
    
    def __init__(self, config):
        super().__init__(config)
        self.base_url = config.get('base_url')
        self.model = config.get('model', 'local')
        self._available = None
    
    def chat(self, system: str, user: str, **kwargs) -> str:
        """
        Send chat completion request to local LLM
        
        Args:
            system: System prompt
            user: User prompt
            **kwargs: Additional parameters (temperature, max_tokens, timeout, etc.)
        
        Returns:
            Response text from LLM
        
        Raises:
            ProviderUnavailableError: When provider is not configured or unreachable
            TimeoutError: When request exceeds timeout
        """
        if not self.base_url:
            raise ProviderUnavailableError("Local LLM base URL not configured")
        
        if not self.is_available():
            raise ProviderUnavailableError("Local LLM not available")
        
        payload = {
            'model': self.model,
            'messages': [
                {'role': 'system', 'content': system},
                {'role': 'user', 'content': user}
            ],
            'temperature': kwargs.get('temperature', 0)
        }
        
        try:
            response = requests.post(
                f"{self.base_url}/chat/completions",
                json=payload,
                timeout=kwargs.get('timeout', 60)
            )
            response.raise_for_status()
            return response.json()['choices'][0]['message']['content']
            
        except requests.Timeout:
            raise TimeoutError("Local LLM request timeout")
        except Exception as e:
            raise ProviderUnavailableError(f"Local LLM error: {e}")
    
    def is_available(self) -> bool:
        """
        Check if local LLM is available
        
        Performs network check to /models endpoint with 2-second timeout.
        Caches result to avoid repeated network checks.
        
        Returns:
            True if provider is available, False otherwise
        """
        if self._available is not None:
            return self._available
        
        if not self.base_url:
            return False
        
        try:
            response = requests.get(f"{self.base_url}/models", timeout=2)
            self._available = response.status_code == 200
        except:
            self._available = False
        
        return self._available
    
    @property
    def name(self) -> str:
        """Provider name for logging"""
        return 'local'
