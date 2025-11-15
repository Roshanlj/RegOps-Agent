"""
Google Gemini provider implementation
"""

import google.generativeai as genai
from ..provider import LLMProvider
from ..exceptions import RateLimitError, ProviderUnavailableError, TimeoutError


class GeminiProvider(LLMProvider):
    """Google Gemini provider implementation"""
    
    def __init__(self, config):
        super().__init__(config)
        self.api_key = config.get('api_key')
        self.model_name = config.get('model', 'gemini-1.5-flash')
        self._client = None
        
        if self.api_key:
            genai.configure(api_key=self.api_key)
            self._client = genai.GenerativeModel(self.model_name)
    
    def chat(self, system: str, user: str, **kwargs) -> str:
        """
        Send chat completion request to Gemini
        
        Args:
            system: System prompt
            user: User prompt
            **kwargs: Additional parameters (temperature, max_tokens, timeout)
            
        Returns:
            Response text from LLM
            
        Raises:
            RateLimitError: When rate limit is hit (HTTP 429)
            ProviderUnavailableError: When provider is not configured or fails
            TimeoutError: When request exceeds timeout
        """
        if not self._client:
            raise ProviderUnavailableError("Gemini not configured")
        
        try:
            # Gemini uses system instruction in model config
            prompt = f"{system}\n\n{user}"
            response = self._client.generate_content(
                prompt,
                generation_config={
                    'temperature': kwargs.get('temperature', 0),
                    'max_output_tokens': kwargs.get('max_tokens', 2048)
                }
            )
            return response.text
        except Exception as e:
            error_str = str(e).lower()
            # Detect rate limit errors (HTTP 429)
            if '429' in error_str or 'rate limit' in error_str or 'quota' in error_str:
                raise RateLimitError(f"Gemini rate limit: {e}")
            # Detect timeout errors
            elif 'timeout' in error_str or 'timed out' in error_str:
                raise TimeoutError(f"Gemini timeout: {e}")
            else:
                raise ProviderUnavailableError(f"Gemini error: {e}")
    
    def is_available(self) -> bool:
        """
        Check if Gemini is configured and available
        
        Returns:
            True if API key is configured and client is initialized
        """
        return self._client is not None and self.api_key is not None
    
    @property
    def name(self) -> str:
        """Provider name for logging"""
        return 'gemini'
