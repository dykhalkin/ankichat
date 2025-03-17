"""
OpenAI integration for the Anki Flashcards System.

This module provides functionality for language detection and
content generation for flashcards using OpenAI's API.
"""

import logging
import json
from typing import Dict, Any, Optional, Tuple

from openai import AsyncOpenAI
from config import settings

logger = logging.getLogger('ankichat')

class LLMClient:
    """
    Client for interacting with OpenAI's API for language detection
    and flashcard content generation.
    """

    def __init__(self, model: str = settings.OPENAI_MODEL):
        """
        Initialize the LLM client.

        Args:
            model: The OpenAI model to use
        """
        self.model = model
        self.client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)
        logger.info(f"Initialized LLM client with model: {model}")

    async def detect_language(self, text: str) -> Tuple[str, float]:
        """
        Detect the language of a given text using OpenAI.

        Args:
            text: The text to analyze

        Returns:
            Tuple of (language_code, confidence)
        """
        logger.debug(f"Detecting language for text: {text[:30]}...")

        try:
            system_prompt = (
                "You are a language detection expert. Your task is to analyze the input text "
                "and determine the language it is written in. Return a JSON object with "
                "fields: 'language_code' (ISO 639-1 two-letter code) and 'confidence' "
                "(a float between 0 and 1 indicating your confidence level)."
            )

            response = await self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": text}
                ],
                temperature=0.1,
                max_tokens=150,
                top_p=1.0,
                frequency_penalty=0.0,
                presence_penalty=0.0,
                response_format={"type": "json_object"}
            )

            # Extract JSON response
            result = json.loads(response.choices[0].message.content)
            
            language_code = result.get("language_code", "en")
            confidence = float(result.get("confidence", 0.5))
            
            logger.info(f"Detected language: {language_code} with confidence {confidence}")
            return language_code, confidence

        except Exception as e:
            logger.error(f"Error detecting language: {e}")
            # Default to English if detection fails
            return "en", 0.0

    async def generate_flashcard_content(
        self, 
        word: str, 
        language_code: str
    ) -> Dict[str, Any]:
        """
        Generate content for a flashcard based on the word and language.

        Args:
            word: The word or phrase to create a flashcard for
            language_code: The ISO 639-1 language code

        Returns:
            Dictionary with generated flashcard content
        """
        logger.debug(f"Generating flashcard content for word: {word}")

        try:
            system_prompt = (
                "You are a language learning assistant. Create a comprehensive flashcard for "
                "the given word or phrase. Your response should be in JSON format with the "
                "following fields:\n"
                "- definition: A clear, concise definition\n"
                "- example_sentence: A natural example sentence using the word\n"
                "- pronunciation_guide: Phonetic transcription, use IPA notation for non-English\n"
                "- part_of_speech: The grammatical category\n"
                "- notes: Any additional information that would be helpful for learning\n"
            )

            user_prompt = f"Create a flashcard for the {language_code} word or phrase: {word}"

            response = await self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=0.7,
                max_tokens=500,
                top_p=1.0,
                frequency_penalty=0.0,
                presence_penalty=0.0,
                response_format={"type": "json_object"}
            )

            # Extract JSON response
            content = json.loads(response.choices[0].message.content)
            
            # Add source word and language to the content
            content["word"] = word
            content["language_code"] = language_code
            
            logger.info(f"Generated flashcard content for '{word}'")
            return content

        except Exception as e:
            logger.error(f"Error generating flashcard content: {e}")
            # Return basic structure if generation fails
            return {
                "word": word,
                "language_code": language_code,
                "definition": f"Definition for {word}",
                "example_sentence": f"Example sentence with {word}.",
                "pronunciation_guide": "N/A",
                "part_of_speech": "N/A",
                "notes": "Content generation failed"
            }