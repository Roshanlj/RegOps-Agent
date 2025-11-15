"""OpenRouter provider implementation"""
import requests
from ..provider import LLMProvider
from ..exceptions import RateLimitError, ProviderUnavailableError, TimeoutError


class OpenRouterProvider(LLMProvider):
    """OpenRouter provider implementation"""
    
    BASE_URL = "https://openrouter.ai/api/v1"
    
    def __init__(self, config):
        super().__init__(config)
        self.api_key = config.get('api_key')
        self.model = config.get('model', 'anthropic/claude-3.5-sonnet')
    
    def chat(self, system: str, user: str, **kwargs) -> str:
        """
        Send chat completion request to OpenRouter
        
        Args:
            system: System prompt
            user: User prompt
            **kwargs: Additional parameters (temperature, timeout, max_tokens, etc.)
            
        Returns:
            Response text from LLM
            
        Raises:
            RateLimitError: When rate limit is hit (HTTP 429)
            ProviderUnavailableError: When provider is not reachable
            TimeoutError: When request exceeds timeout
        """
        if not self.api_key:
            raise ProviderUnavailableError("OpenRouter not configured")
        
        headers = {
            'Authorization': f'Bearer {self.api_key}',
            'Content-Type': 'application/json'
        }
        
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
                f"{self.BASE_URL}/chat/completions",
                headers=headers,
                json=payload,
                timeout=kwargs.get('timeout', 60)
            )
            
            # Explicit HTTP 429 detection for rate limits
            if response.status_code == 429:
                raise RateLimitError("OpenRouter rate limit exceeded")
            
            response.raise_for_status()
            return response.json()['choices'][0]['message']['content']
            
        except requests.Timeout:
            raise TimeoutError("OpenRouter request timeout")
        except RateLimitError:
            raise
        except Exception as e:
            raise ProviderUnavailableError(f"OpenRouter error: {e}")
    
    def is_available(self) -> bool:
        """
        Check if provider is configured and reachable
        
        Returns:
            True if provider can be used, False otherwise
        """
        return self.api_key is not None
    
    @property
    def name(self) -> str:
        """Provider name for logging"""
        return 'openrouter'
