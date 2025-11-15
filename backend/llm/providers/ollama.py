"""
Ollama local LLM provider
"""

import requests
from ..provider import LLMProvider
from ..exceptions import ProviderUnavailableError, TimeoutError


class OllamaProvider(LLMProvider):
    """Ollama local LLM provider"""
    
    def __init__(self, config):
        super().__init__(config)
        self.base_url = config.get('base_url', 'http://localhost:11434')
        self.model = config.get('model', 'llama3.1:8b')
        self._available = None  # Cache availability check
    
    def chat(self, system: str, user: str, **kwargs) -> str:
        """
        Send chat completion request to Ollama
        
        Args:
            system: System prompt
            user: User prompt
            **kwargs: Additional parameters (temperature, timeout)
            
        Returns:
            Response text from LLM
            
        Raises:
            ProviderUnavailableError: When Ollama is not available or fails
            TimeoutError: When request exceeds timeout
        """
        if not self.is_available():
            raise ProviderUnavailableError("Ollama not available")
        
        payload = {
            'model': self.model,
            'messages': [
                {'role': 'system', 'content': system},
                {'role': 'user', 'content': user}
            ],
            'stream': False,
            'options': {
                'temperature': kwargs.get('temperature', 0)
            }
        }
        
        try:
            response = requests.post(
                f"{self.base_url}/api/chat",
                json=payload,
                timeout=kwargs.get('timeout', 60)
            )
            response.raise_for_status()
            return response.json()['message']['content']
            
        except requests.Timeout:
            raise TimeoutError("Ollama request timeout")
        except Exception as e:
            raise ProviderUnavailableError(f"Ollama error: {e}")
    
    def is_available(self) -> bool:
        """
        Check if Ollama is configured and reachable
        
        Returns:
            True if Ollama server is reachable, False otherwise
        """
        if self._available is not None:
            return self._available
        
        try:
            response = requests.get(f"{self.base_url}/api/tags", timeout=2)
            self._available = response.status_code == 200
        except:
            self._available = False
        
        return self._available
    
    @property
    def name(self) -> str:
        """Provider name for logging"""
        return 'ollama'
