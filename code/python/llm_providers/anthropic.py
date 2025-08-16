# Copyright (c) 2025 Microsoft Corporation.
# Licensed under the MIT License

"""
Anthropic wrapper for LLM functionality.

WARNING: This code is under development and may undergo changes in future releases.
Backwards compatibility is not guaranteed at this time.
"""

import os
import json
import re
import logging
import asyncio
from typing import Dict, Any, List, Optional

from anthropic import AsyncAnthropic
from core.config import CONFIG
import threading

from llm_providers.llm_provider import LLMProvider

logger = logging.getLogger(__name__)


class ConfigurationError(RuntimeError):
    """Raised when configuration is missing or invalid."""
    pass


class AnthropicProvider(LLMProvider):
    """Implementation of LLMProvider for Anthropic API."""
    
    _client_lock = threading.Lock()
    _client = None
    
    @classmethod
    def get_api_key(cls) -> str:
        """Retrieve the Anthropic API key from the environment or raise an error."""
        # Get the API key from the preferred provider config
        provider_config = CONFIG.llm_endpoints["anthropic"]
        if provider_config and provider_config.api_key:
            api_key = provider_config.api_key
            if api_key:
                api_key = api_key.strip('"')  # Remove quotes if present
                return api_key
        # If we didn't find a key, the environment variable is not set properly
        raise ConfigurationError("Environment variable ANTHROPIC_API_KEY is not set")

    @classmethod
    def get_client(cls) -> AsyncAnthropic:
        """
        Configure and return an async Anthropic client.
        """
        with cls._client_lock:  # Thread-safe client initialization
            if cls._client is None:
                api_key = cls.get_api_key()
                cls._client = AsyncAnthropic(api_key=api_key)
        return cls._client

    @classmethod
    def _build_messages(cls, prompt: str, schema: Dict[str, Any]) -> List[Dict[str, str]]:
        """
        Construct the message sequence for JSON-schema enforcement.
        """
        return [
            {
                "role": "assistant",
                "content": f"I'll provide a JSON response matching this schema: {json.dumps(schema)}"
            },
            {
                "role": "user",
                "content": prompt
            }
        ]

    @classmethod
    def clean_response(cls, content: str) -> Dict[str, Any]:
        """
        Strip markdown fences and extract the first JSON object.
        """
        if not content:
            logger.warning("Received empty content from Anthropic")
            return {}
            
        # Remove markdown code block indicators if present
        cleaned = re.sub(r"```(?:json)?\s*", "", content).strip()
        
        # Find the JSON object within the response
        start_idx = cleaned.find('{')
        end_idx = cleaned.rfind('}') + 1
        
        if start_idx == -1 or end_idx == 0:
            logger.error("No valid JSON object found in response: %r", cleaned)
            return {}
            
        json_str = cleaned[start_idx:end_idx]
        
        try:
            result = json.loads(json_str)
            return result
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse JSON from content: {e}, content: {json_str}")
            return {}

    async def get_completion(
        self,
        prompt: str,
        schema: Dict[str, Any],
        model: Optional[str] = None,
        temperature: float = 1.0,
        max_tokens: int = 4096,
        timeout: float = 60.0,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Send an async chat completion request to Anthropic and return parsed JSON.
        """
        # If model not provided, get it from config
        if model is None:
            provider_config = CONFIG.llm_endpoints["anthropic"]
            # Use the 'high' model for completions by default
            model = provider_config.models.high
        
        client = self.get_client()
        messages = self._build_messages(prompt, schema)

        try:
            response = await asyncio.wait_for(
                client.messages.create(
                    model=model,
                    messages=messages,
                    max_tokens=max_tokens,
                    temperature=temperature,
                    system=f"You are a helpful assistant that always responds with valid JSON matching the provided schema."
                ),
                timeout
            )
        except asyncio.TimeoutError:
            logger.error("Completion request timed out after %s seconds", timeout)
            return {}

        # Extract the response content
        content = response.content[0].text
        return self.clean_response(content)


# Create a singleton instance
provider = AnthropicProvider()

# For backwards compatibility
get_anthropic_completion = provider.get_completion