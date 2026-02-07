"""
Ollama LLM Client

Provides interface to locally running Ollama for text generation.
"""

import json
import requests
from typing import Dict, Any, Optional, Generator
import logging


class OllamaClient:
    """Client for interacting with Ollama API."""
    
    def __init__(self, config: Dict[str, Any]):
        """Initialize Ollama client.
        
        Args:
            config: Configuration dictionary
        """
        llm_config = config.get("llm", {})
        
        self.base_url = llm_config.get("base_url", "http://localhost:11434")
        self.model = llm_config.get("model", "mistral")
        self.temperature = llm_config.get("temperature", 0.7)
        self.max_tokens = llm_config.get("max_tokens", 2000)
        
        self.logger = logging.getLogger(__name__)
    
    def is_available(self) -> bool:
        """Check if Ollama is running and the model is available.
        
        Returns:
            True if Ollama is available
        """
        try:
            response = requests.get(f"{self.base_url}/api/tags", timeout=5)
            if response.status_code == 200:
                models = response.json().get("models", [])
                model_names = [m.get("name", "").split(":")[0] for m in models]
                return self.model in model_names or f"{self.model}:latest" in [m.get("name") for m in models]
            return False
        except requests.RequestException:
            return False
    
    def generate(self, prompt: str, system_prompt: str = None,
                 temperature: float = None, max_tokens: int = None) -> str:
        """Generate text using Ollama.
        
        Args:
            prompt: The user prompt
            system_prompt: Optional system prompt
            temperature: Override temperature
            max_tokens: Override max tokens
            
        Returns:
            Generated text
        """
        url = f"{self.base_url}/api/generate"
        
        payload = {
            "model": self.model,
            "prompt": prompt,
            "stream": False,
            "options": {
                "temperature": temperature or self.temperature,
                "num_predict": max_tokens or self.max_tokens,
            }
        }
        
        if system_prompt:
            payload["system"] = system_prompt
        
        try:
            response = requests.post(url, json=payload, timeout=120)
            response.raise_for_status()
            
            result = response.json()
            return result.get("response", "")
            
        except requests.RequestException as e:
            self.logger.error(f"Ollama generation failed: {e}")
            return ""
    
    def generate_stream(self, prompt: str, system_prompt: str = None) -> Generator[str, None, None]:
        """Generate text with streaming.
        
        Args:
            prompt: The user prompt
            system_prompt: Optional system prompt
            
        Yields:
            Text chunks as they are generated
        """
        url = f"{self.base_url}/api/generate"
        
        payload = {
            "model": self.model,
            "prompt": prompt,
            "stream": True,
            "options": {
                "temperature": self.temperature,
                "num_predict": self.max_tokens,
            }
        }
        
        if system_prompt:
            payload["system"] = system_prompt
        
        try:
            with requests.post(url, json=payload, stream=True, timeout=120) as response:
                response.raise_for_status()
                
                for line in response.iter_lines():
                    if line:
                        data = json.loads(line)
                        if "response" in data:
                            yield data["response"]
                        if data.get("done", False):
                            break
                            
        except requests.RequestException as e:
            self.logger.error(f"Ollama streaming failed: {e}")
    
    def chat(self, messages: list, temperature: float = None) -> str:
        """Chat completion with conversation history.
        
        Args:
            messages: List of message dicts with 'role' and 'content'
            temperature: Override temperature
            
        Returns:
            Assistant's response
        """
        url = f"{self.base_url}/api/chat"
        
        payload = {
            "model": self.model,
            "messages": messages,
            "stream": False,
            "options": {
                "temperature": temperature or self.temperature,
            }
        }
        
        try:
            response = requests.post(url, json=payload, timeout=120)
            response.raise_for_status()
            
            result = response.json()
            return result.get("message", {}).get("content", "")
            
        except requests.RequestException as e:
            self.logger.error(f"Ollama chat failed: {e}")
            return ""
    
    def pull_model(self, model_name: str = None) -> bool:
        """Pull a model from Ollama registry.
        
        Args:
            model_name: Model to pull (defaults to configured model)
            
        Returns:
            True if successful
        """
        url = f"{self.base_url}/api/pull"
        
        payload = {
            "name": model_name or self.model,
            "stream": False,
        }
        
        try:
            self.logger.info(f"Pulling model: {payload['name']}")
            response = requests.post(url, json=payload, timeout=600)  # 10 min timeout
            response.raise_for_status()
            return True
            
        except requests.RequestException as e:
            self.logger.error(f"Failed to pull model: {e}")
            return False
