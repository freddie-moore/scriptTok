#!/usr/bin/env python3
"""
Gemini API Client Class

This module contains the GeminiClient class, which provides a simple interface
for interacting with the Google Gemini 2.5 Flash model with Google Search grounding.
"""

import logging
from typing import Optional

# New Gemini client library
from google import genai
from google.genai import types


class GeminiError(Exception):
    """Custom exception for Gemini-related errors."""
    pass


class GeminiClient:
    """A client for making API calls to the Gemini 2.5 Flash model."""

    def __init__(self, api_key: str, system_prompt_path: str, logger: Optional[logging.Logger] = None):
        """
        Initialize the Gemini client.

        Args:
            api_key: Your Google API key.
            system_prompt_path: Path to a .txt file containing the system prompt.
            logger: Optional logger instance.
        """
        if not api_key:
            raise GeminiError("A Google API key is required for the Gemini client.")

        self.logger = logger or logging.getLogger(__name__)
        self.system_prompt = self._load_system_prompt(system_prompt_path)

        try:
            # Configure the API client
            self.client = genai.Client(api_key=api_key)
            self.model_name = "gemini-2.5-flash"

            # Prepare the Google Search grounding tool
            self.grounding_tool = types.Tool(
                google_search=types.GoogleSearch()
            )

            self.logger.info(f"Gemini client initialized successfully with model '{self.model_name}'.")
        except Exception as e:
            self.logger.error(f"Failed to configure Gemini client: {e}")
            raise GeminiError(f"Could not initialize Gemini client: {e}")

    def _load_system_prompt(self, path: str) -> str:
        """Load the system prompt from a file."""
        try:
            with open(path, 'r', encoding='utf-8') as f:
                prompt_text = f.read()
                self.logger.info(f"System prompt loaded successfully from: {path}")
                return prompt_text
        except FileNotFoundError:
            self.logger.error(f"System prompt file not found: {path}")
            raise GeminiError(f"System prompt file not found: {path}")
        except Exception as e:
            self.logger.error(f"Failed to read system prompt file: {e}")
            raise GeminiError(f"Failed to read system prompt file: {e}")

    def generate_text(self, user_prompt: str) -> str:
        """
        Generate text from the Gemini model with Google Search grounding.

        Args:
            user_prompt: The user's input.

        Returns:
            The generated text from the model.
        """
        if not user_prompt:
            self.logger.warning("generate_text called with an empty prompt.")
            return ""

        try:
            self.logger.info("Sending prompt to Gemini model with Google Search grounding...")

            # Build generation config with search tool
            config = types.GenerateContentConfig(
                tools=[self.grounding_tool]
            )

            # Combine system prompt + user prompt
            contents = f"{self.system_prompt.strip()}\n\n{user_prompt.strip()}"

            # Make the request
            response = self.client.models.generate_content(
                model=self.model_name,
                contents=contents,
                config=config,
            )

            if not response.text:
                self.logger.warning("Gemini API returned an empty response.")
                return "The model returned an empty response."

            self.logger.info("Successfully received response from Gemini.")
            return response.text

        except Exception as e:
            self.logger.error(f"Gemini API call failed: {e}")
            raise GeminiError(f"Gemini API call failed: {e}")
