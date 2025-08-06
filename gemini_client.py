# gemini_client.py

#!/usr/bin/env python3
"""
Gemini API Client Class

This module contains the GeminiClient class, which provides a simple interface
for interacting with the Google Gemini 2.5 Flash model.
"""

import logging
from typing import Optional

# This is the official Google library for the Gemini API
import google.generativeai as genai


class GeminiError(Exception):
    """Custom exception for transcriber-related errors."""
    pass


class GeminiClient:
    """A client for making API calls to the Gemini 2.5 Flash model."""

    def __init__(self, api_key: str, system_prompt_path: str, logger: Optional[logging.Logger] = None):
        """
        Initialize the Gemini client.

        Args:
            api_key: Your Google AI Studio API key.
            system_prompt_path: Filepath to a .txt file containing the system prompt.
            logger: Logger instance (creates new one if None).
        
        Raises:
            GeminiError: If the API key is missing or the system prompt file is not found.
        """
        if not api_key:
            raise GeminiError("A Google AI Studio API key is required for the Gemini client.")
        
        self.logger = logger or logging.getLogger(__name__)
        self.system_prompt = self._load_system_prompt(system_prompt_path)
        
        try:
            # Configure the API client with your key
            genai.configure(api_key=api_key)
            
            # Create the model instance with the loaded system prompt
            # The system prompt is a powerful way to set the model's behavior and persona.
            self.model = genai.GenerativeModel(
                model_name="gemini-2.5-flash-preview-05-20",
                system_instruction=self.system_prompt
            )
            self.logger.info("Gemini client initialized successfully with model 'gemini-2.5-flash-preview-05-20'.")

        except Exception as e:
            self.logger.error(f"Failed to configure Gemini client: {e}")
            raise GeminiError(f"Could not initialize Gemini client. Check your API key. Error: {e}")

    def _load_system_prompt(self, path: str) -> str:
        """
        Loads the system prompt from a specified text file.

        Args:
            path: The file path to the system prompt.

        Returns:
            The content of the file as a string.
        
        Raises:
            GeminiError: If the file cannot be found or read.
        """
        try:
            with open(path, 'r', encoding='utf-8') as f:
                prompt_text = f.read()
                self.logger.info(f"System prompt loaded successfully from: {path}")
                return prompt_text
        except FileNotFoundError:
            self.logger.error(f"System prompt file not found at path: {path}")
            raise GeminiError(f"System prompt file not found: {path}")
        except Exception as e:
            self.logger.error(f"Failed to read system prompt file: {e}")
            raise GeminiError(f"Failed to read system prompt file: {e}")

    def generate_text(self, user_prompt: str) -> str:
        """
        Generates text by sending a prompt to the Gemini model.

        Args:
            user_prompt: The user's input/question for the model.

        Returns:
            The generated text response from the model as a string.
            
        Raises:
            GeminiError: If the API call fails for any reason.
        """
        if not user_prompt:
            self.logger.warning("generate_text called with an empty prompt.")
            return ""
            
        try:
            self.logger.info("Sending prompt to Gemini model...")
            
            # The system prompt is already configured in the model,
            # so we only need to send the user's part of the conversation.
            response = self.model.generate_content(user_prompt)
            
            # The response object contains the generated text.
            # We also check for safety ratings or other issues.
            if not response.parts:
                # This can happen if the response was blocked for safety reasons.
                self.logger.warning("Gemini API returned an empty response. It may have been blocked.")
                # You can inspect response.prompt_feedback for more details
                if hasattr(response, 'prompt_feedback') and response.prompt_feedback.block_reason:
                     raise GeminiError(f"Request was blocked by the API. Reason: {response.prompt_feedback.block_reason.name}")
                return "The model returned an empty response."

            self.logger.info("Successfully received response from Gemini.")
            return response.text

        except Exception as e:
            self.logger.error(f"Gemini API call failed: {e}")
            raise GeminiError(f"Gemini API call failed: {e}")