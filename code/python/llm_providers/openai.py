# Copyright (c) 2025 Microsoft Corporation.
# Licensed under the MIT License

"""
OpenAI wrapper for LLM functionality.

WARNING: This code is under development and may undergo changes in future releases.
Backwards compatibility is not guaranteed at this time.
"""

import os
import json
import re
import logging
import asyncio
from typing import Dict, Any, List, Optional

from openai import AsyncOpenAI
from core.config import CONFIG
import threading
from misc.logger.logging_config_helper import get_configured_logger
from misc.logger.logger import LogLevel


from llm_providers.llm_provider import LLMProvider

from misc.logger.logging_config_helper import get_configured_logger, LogLevel
logger = get_configured_logger("llm")


class ConfigurationError(RuntimeError):
    """
    Raised when configuration is missing or invalid.
    """
    pass



class OpenAIProvider(LLMProvider):
    """Implementation of LLMProvider for OpenAI API."""
    
    _client_lock = threading.Lock()
    _client = None

    @classmethod
    def get_api_key(cls) -> str:
        """
        Retrieve the OpenAI API key from environment or raise an error.
        """
        # Get the API key from the preferred provider config
        provider_config = CONFIG.llm_endpoints["openai"]
        api_key = provider_config.api_key
        return api_key

    @classmethod
    def get_client(cls) -> AsyncOpenAI:
        """
        Configure and return an asynchronous OpenAI client.
        """
        with cls._client_lock:  # Thread-safe client initialization
            if cls._client is None:
                api_key = cls.get_api_key()
                cls._client = AsyncOpenAI(api_key=api_key)
        return cls._client

    @classmethod
    def _build_messages(cls, prompt: str, schema: Dict[str, Any]) -> List[Dict[str, str]]:
        """
        Construct the system and user message sequence enforcing a JSON schema.
        """
        return [
            {
                "role": "system",
                "content": (
                    f"Provide a valid JSON response matching this schema: "
                    f"{json.dumps(schema)}"
                )
            },
            {"role": "user", "content": prompt}
        ]

    @classmethod
    def clean_response(cls, content: str) -> Dict[str, Any]:
        """
        Strip markdown fences and extract the first JSON object.
        """
        if not content:
            logger.warning("Received empty content from OpenAI")
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
        temperature: float = 0.7,
        max_tokens: int = 4096,
        timeout: float = 60.0,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Send an async chat completion request and return parsed JSON output.
        """
        # If model not provided, get it from config
        if model is None:
            provider_config = CONFIG.llm_endpoints["openai"]
            # Use the 'high' model for completions by default
            model = provider_config.models.high
        
        client = self.get_client()
        messages = self._build_messages(prompt, schema)

        try:
            response = await asyncio.wait_for(
                client.chat.completions.create(
                    model=model,
                    messages=messages,
                    temperature=temperature,
                    max_tokens=max_tokens,
                ),
                timeout
            )
        except asyncio.TimeoutError:
            logger.error("Completion request timed out after %s seconds", timeout)
            return {}

        try:
            return self.clean_response(response.choices[0].message.content)
        except Exception as e:
            logger.error(f"Error processing OpenAI response: {e}")
            return {}



# Create a singleton instance
provider = OpenAIProvider()
