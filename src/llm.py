"""
OpenAI integration for the Anki Flashcards System.

This module provides functionality for language detection and
content generation for flashcards using OpenAI's API.
"""

import json
import logging
import re
from typing import Any, Dict, List, Optional, Tuple

from openai import AsyncOpenAI

from config import settings

logger = logging.getLogger("ankichat")


class LLMClient:
    """
    Client for interacting with OpenAI's API for language detection
    and flashcard content generation.
    """

    def __init__(self, model: str = settings.OPENAI_MODEL, api_key: str = settings.OPENAI_API_KEY):
        """
        Initialize the LLM client.

        Args:
            model: The OpenAI model to use
            api_key: The OpenAI API key (defaults to settings)
        """
        self.model = model

        # Check if API key is provided
        if not api_key:
            logger.warning("No OpenAI API key provided - LLM functionality will be limited")
            self.client = None
        else:
            try:
                self.client = AsyncOpenAI(api_key=api_key)
                logger.info(f"Initialized LLM client with model: {model}")
            except Exception as e:
                logger.error(f"Failed to initialize OpenAI client: {e}")
                self.client = None

    async def detect_category(self, content: str) -> str:
        """
        Detect the appropriate category/deck name for flashcard content.

        Args:
            content: The content to analyze

        Returns:
            Suggested category/deck name
        """
        logger.debug(f"Detecting category for content: {content[:30]}...")

        # Check if client is available
        if not self.client:
            logger.warning("LLM client not initialized - returning default category")
            return "General Knowledge"

        try:
            system_prompt = (
                "You are a categorization expert. Your task is to analyze the flashcard content "
                "and suggest an appropriate category or deck name. The name should be 1-4 words, "
                "descriptive, and categorical. Return ONLY the category name with no quotes or formatting."
            )

            response = await self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": content},
                ],
                temperature=0.5,
                max_tokens=50,
                top_p=1.0,
                frequency_penalty=0.0,
                presence_penalty=0.0,
            )

            # Extract response
            category = response.choices[0].message.content.strip()

            # Remove quotes if present
            if category.startswith('"') and category.endswith('"'):
                category = category[1:-1]
            if category.startswith("'") and category.endswith("'"):
                category = category[1:-1]

            # Limit length
            if len(category) > 50:
                category = category[:50]

            logger.info(f"Detected category: {category}")
            return category

        except Exception as e:
            logger.error(f"Error detecting category: {e}")
            # Default category if detection fails
            return "General Knowledge"

    async def detect_language(
        self,
        keyword: str,
        native_language: str,
        learn_languages: List[str],
        last_used_language: str,
    ) -> Dict[str, Any]:
        """
        Detect the language of a given text using OpenAI.

        Args:
            keyword: The keyword to analyze
            native_language: The native language of the user
            learn_languages: The languages the user is learning
            last_used_language: The language the user is currently using

        Returns:
            Tuple of (language_code, confidence)
        """
        logger.debug(f"Detecting language for text: {keyword[:30]}...")

        # Check if client is available
        if not self.client:
            logger.warning("LLM client not initialized - returning default language")
            return "en", 1.0  # Default to English with high confidence

        try:
            system_prompt = f"""
                    Your task is to create content for an Anki flashcard in an easy-to-remember format. You will receive input data, including a keyword, in a JSON object. For any given keyword, which can be any part of speech in any language, create an explanation in English, and provide synonyms in the given language where relevant.

                    Consider the following details:
                    - Focus on providing clear and concise explanations of the given keyword.
                    - Identify synonyms or related terms in the given language if applicable, based on the context provided.
                    - Explanation should be in easy-to-understand English or in a native language for complex cases.

                    # Steps

                    1. **Identify the language of origin**: Refer to the {native_language} and {learn_languages} fields from the JSON input to identify the source language of the given keyword.
                    2. **Identify the target language**: Based on the {learn_languages}, pick the relevant target language with higher probability. If the source language is a native language to the user, then generate translation and explanation in {last_used_language}.
                    3. **Understand the Keyword**: Determine the part of speech and context of the keyword, considering its language of origin.
                    4. **Provide Explanation**: Create a brief yet comprehensive explanation that covers the meaning and usage of the keyword.
                    5. **Identify Synonyms**: If appropriate, find and list one or more synonyms or related terms that fit the context in the given language.
                    6. **Review and Refine**: Ensure that the explanation is clear and the synonyms are relevant.
                    7. **Provide example of usage**: If it's relevant, provide the example of usage the given keyword.

                    # Output Format

                    Produce the output in the following JSON format:

                    ```json
                    {{
                      "explanation": "A concise paragraph explaining the meaning and context of the keyword.",
                      "synonyms": ["synonym1", "synonym2"],
                      "example": "Example of usage of the given keyword in the target language.",
                      "keyword": "The keyword itself. Refined, with the correct case and fixed any typos.",
                      "language": "Language of origin in ISO-639-1 format"
                    }}
                    ```

                    # Notes
                    - Some keywords may not have direct synonyms; provide synonyms only if they truly fit the meaning and context.
                    - Provide output in Markdown formatted text.
                """

            response = await self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": keyword},
                ],
                temperature=0.1,
                max_tokens=150,
                top_p=1.0,
                frequency_penalty=0.0,
                presence_penalty=0.0,
                response_format={"type": "json_object"},
            )

            # Extract JSON response
            result = json.loads(response.choices[0].message.content)

            return result

        except Exception as e:
            logger.error(f"Error generating flashcard content: {e}")
            # Default to English if detection fails
            return "Error generating flashcard content"

    async def generate_flashcard_content(self, word: str, language_code: str) -> Dict[str, Any]:
        """
        Generate content for a flashcard based on the word and language.

        Args:
            word: The word or phrase to create a flashcard for
            language_code: The ISO 639-1 language code

        Returns:
            Dictionary with generated flashcard content
        """
        logger.debug(f"Generating flashcard content for word: {word}")

        # Check if client is available
        if not self.client:
            logger.warning("LLM client not initialized - returning basic flashcard content")
            return {
                "word": word,
                "language_code": language_code,
                "definition": f"Definition for {word}",
                "example_sentence": f"Example sentence with {word}.",
                "pronunciation_guide": "N/A",
                "part_of_speech": "N/A",
                "notes": "LLM functionality is not available",
            }

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
                    {"role": "user", "content": user_prompt},
                ],
                temperature=0.7,
                max_tokens=500,
                top_p=1.0,
                frequency_penalty=0.0,
                presence_penalty=0.0,
                response_format={"type": "json_object"},
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
                "notes": "Content generation failed",
            }

    async def generate_explanation(
        self, card_front: str, correct_answer: str, user_answer: str
    ) -> str:
        """
        Generate an explanation for an incorrect flashcard answer.

        Uses the LLM to create a helpful explanation comparing the user's
        answer to the correct one, explaining the differences.

        Args:
            card_front: The front content of the flashcard
            correct_answer: The correct answer (card back)
            user_answer: The user's answer

        Returns:
            A string explanation
        """
        logger.debug(f"Generating explanation for card: {card_front}")

        # Check if client is available
        if not self.client:
            logger.warning("LLM client not initialized - returning basic explanation")
            return (
                f"The correct answer is: {correct_answer}\n\n"
                f"Your answer was: {user_answer}\n\n"
                f"Try to remember the key details from the flashcard."
            )

        try:
            system_prompt = (
                "You are a helpful tutor explaining flashcard answers. "
                "The user has answered a flashcard incorrectly. "
                "Provide a concise, educational explanation highlighting the differences "
                "between their answer and the correct one. Be encouraging and supportive. "
                "Include key information they missed and any helpful mnemonics or tips."
            )

            user_prompt = (
                f"Front of flashcard: {card_front}\n"
                f"Correct answer: {correct_answer}\n"
                f"User's answer: {user_answer}\n\n"
                f"Please explain why the correct answer is correct and what the user may have missed."
            )

            response = await self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                temperature=0.7,
                max_tokens=300,
                top_p=1.0,
                frequency_penalty=0.0,
                presence_penalty=0.0,
            )

            explanation = response.choices[0].message.content.strip()
            logger.info(f"Generated explanation for card: {card_front[:30]}...")
            return explanation

        except Exception as e:
            logger.error(f"Error generating explanation: {e}")
            # Return a basic explanation if generation fails
            return (
                f"The correct answer is: {correct_answer}\n\n"
                f"Your answer was: {user_answer}\n\n"
                f"Try to remember the key details from the flashcard."
            )

    async def generate_fill_in_blank(self, card_front: str, card_back: str) -> Tuple[str, str]:
        """
        Generate a fill-in-the-blank sentence for a flashcard.

        Uses the LLM to create a natural sentence that uses the term from the card front,
        with that term blanked out for the user to fill in.

        Args:
            card_front: The front content of the flashcard (the term)
            card_back: The back content of the flashcard (definition, examples, etc.)

        Returns:
            A tuple of (blanked_sentence, term_to_blank)
        """
        logger.debug(f"Generating fill-in-blank for: {card_front}")

        # Check if client is available
        if not self.client:
            logger.error("LLM client not initialized - cannot generate fill-in-blank")
            raise ValueError("LLM client is required for fill-in-blank mode")

        try:
            system_prompt = (
                "You are an educational content creator specializing in creating fill-in-the-blank exercises. "
                "Your task is to create a single, natural-sounding sentence that uses a given term in context. "
                "The sentence should be educational and reinforce understanding of the term."
            )

            user_prompt = (
                f"Create a fill-in-the-blank sentence for the term: {card_front}\n"
                f"Using context from this definition: {card_back}\n\n"
                f"Rules:\n"
                f"1. Create EXACTLY ONE sentence that naturally uses the term '{card_front}'\n"
                f"2. The sentence should be clear, educational, and contextually appropriate\n"
                f"3. Do NOT include any explanation, introduction, or additional text\n"
                f"4. Do NOT use bullet points or formatting\n"
                f"5. Do NOT use quotation marks around the sentence\n"
                f"6. Do NOT replace the term with blanks yourself - I will do that later\n"
                f"7. The sentence should be easy to understand for language learners\n"
                f"8. Response should be ONLY the single sentence, nothing more"
            )

            response = await self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                temperature=0.7,
                max_tokens=150,
                top_p=1.0,
                frequency_penalty=0.0,
                presence_penalty=0.0,
            )

            # Get the sentence from the response
            sentence = response.choices[0].message.content.strip()

            # Make sure the sentence isn't too long
            if len(sentence) > 250:
                sentence = sentence[:250] + "..."

            # Find the term in the sentence (case-insensitive)
            pattern = re.compile(re.escape(card_front), re.IGNORECASE)
            term_match = pattern.search(sentence)

            if term_match:
                # Get the actual term as it appears in the sentence (preserving case)
                matched_term = term_match.group(0)
                # Replace the term with blanks
                blanked_sentence = pattern.sub("____________", sentence, count=1)
                logger.info(f"Generated fill-in-blank exercise: {blanked_sentence}")
                return blanked_sentence, matched_term
            else:
                # If the term isn't in the sentence, create a simple template
                logger.warning(
                    f"Term '{card_front}' not found in generated sentence, using fallback"
                )
                return (
                    f"The term ____________ refers to {card_back.split('.')[0]}.",
                    card_front,
                )

        except Exception as e:
            logger.error(f"Error generating fill-in-blank: {e}")
            # Return a basic sentence if generation fails
            return f"____________ is defined as {card_back.split('.')[0]}.", card_front
