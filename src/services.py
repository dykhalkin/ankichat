"""
Service layer for the Anki Flashcards System.

This module contains the business logic for creating and managing flashcards.
"""

import datetime
import logging
import uuid
from typing import Any, Dict, List, Optional, Tuple, Union

from config import settings
from src.llm import LLMClient
from src.models import Deck, Flashcard, UserPreferences
from src.repository import DeckRepository, FlashcardRepository, UserPreferencesRepository
from src.training import FillInBlankTrainer, ReviewSession, TrainingMode

logger = logging.getLogger("ankichat")

# Dictionary to store active review sessions
# Key: user_id, Value: ReviewSession
ACTIVE_SESSIONS: Dict[str, ReviewSession] = {}


class FlashcardService:
    """
    Service that handles flashcard business logic including
    creation, update, and retrieval.
    """

    def __init__(
        self,
        flashcard_repo: FlashcardRepository,
        deck_repo: DeckRepository,
        llm_client: LLMClient,
        user_service: Optional["UserService"] = None,
    ):
        self.flashcard_repo = flashcard_repo
        self.deck_repo = deck_repo
        self.llm_client = llm_client
        self.user_service = user_service
        logger.info("FlashcardService initialized")

    async def process_new_card_text(self, text: str, user_id: str) -> Dict[str, Any]:
        """
        Process user input for creating a new flashcard.

        This function detects the language and generates flashcard content.

        Args:
            text: The text input from the user
            user_id: The ID of the user

        Returns:
            Dictionary with the generated flashcard preview
        """
        logger.info(f"Processing new card text: {text[:30]}...")

        user_preferences = self.user_service.get_user_preferences(user_id)
        card_content = await self.llm_client.detect_language(
            text,
            user_preferences.native_language,
            user_preferences.learning_languages,
            user_preferences.last_language,
        )

        # Generate flashcard content
        # content = await self.llm_client.generate_flashcard_content(text, language_code)

        # Create preview object
        preview = {
            "input_text": text,
            "user_id": user_id,
            "language": {"code": card_content["language"], "confidence": 1},
            "content": card_content,
            "preview_id": str(uuid.uuid4()),
        }

        logger.info(f"Created flashcard preview with ID: {preview['preview_id']}")
        return preview

    async def create_flashcard_from_preview(
        self,
        preview_id: str,
        deck_id: str,
        user_edits: Optional[Dict[str, Any]] = None,
        user_id: Optional[str] = None,
    ) -> Flashcard:
        """
        Create a new flashcard from a preview.

        Args:
            preview_id: The ID of the preview to use
            deck_id: The ID of the deck to add the card to
            user_edits: Optional dictionary with user edits to the content
            user_id: Optional user ID for storing preferences

        Returns:
            The created Flashcard object
        """
        # In a real application, you would store the preview in a temporary storage
        # and retrieve it here. For this example, we'll simulate it.

        # Get the deck
        deck = self.deck_repo.get(deck_id)
        if not deck:
            logger.error(f"Deck not found with ID: {deck_id}")
            raise ValueError(f"Deck not found with ID: {deck_id}")

        # Create the flashcard (in a real app, use the stored preview)
        # This is simulated as we don't have actual storage for previews
        card = Flashcard(
            front=f"Simulated front for preview {preview_id}",
            back=f"Simulated back for preview {preview_id}",
            language="en",
            deck_id=deck_id,
        )

        # Apply any user edits
        if user_edits:
            if "front" in user_edits:
                card.front = user_edits["front"]
            if "back" in user_edits:
                card.back = user_edits["back"]
            if "language" in user_edits:
                card.language = user_edits["language"]

        # Save the card
        saved_card = self.flashcard_repo.create(card)
        logger.info(f"Created flashcard with ID: {saved_card.id} in deck: {deck_id}")

        # Store user preferences if UserService is available and user_id is provided
        if self.user_service and user_id:
            try:
                # Update the last used deck and language in user preferences
                self.user_service.update_preferences(
                    user_id=user_id, last_deck_id=deck_id, last_language=card.language
                )
                logger.info(
                    f"Updated user preferences for user {user_id} with deck {deck_id} and language {card.language}"
                )
            except Exception as e:
                # Don't fail the card creation if preference update fails
                logger.error(f"Error updating user preferences: {e}")

        return saved_card

    def format_preview_message(self, preview: Dict[str, Any]) -> str:
        """
        Format a flashcard preview for display to the user.

        Args:
            preview: The flashcard preview data

        Returns:
            Formatted message text
        """
        content = preview["content"]
        language_info = preview["language"]

        # Get current deck, native and learning language information
        user_id = preview.get("user_id")
        current_deck = None
        native_lang = "EN"  # Default
        learning_lang = "EN"  # Default

        if self.user_service and user_id:
            try:
                prefs = self.user_service.get_user_preferences(user_id)
                if prefs.last_deck_id:
                    deck = self.deck_repo.get(prefs.last_deck_id)
                    current_deck = deck.name if deck else None
                native_lang = prefs.native_language.upper() if prefs.native_language else "EN"
                learning_lang = prefs.last_language.upper() if prefs.last_language else "EN"
            except Exception as e:
                logger.error(f"Error getting user preferences: {e}")

        # Add user info header
        deck_info = (
            f"📍 *Current Deck:* {current_deck} | *Language:* {language_info['code'].upper()}\n"
        )
        user_info = f"👤 *Native:* {native_lang} | *Learning:* {learning_lang}\n"
        separator = "┄" * 25 + "\n\n"

        # Format the message
        message = (
            f"{deck_info}"
            f"{user_info}"
            f"{separator}"
            f"📝 *Flashcard Preview*\n\n"
            f"*Word/Phrase:* {content['keyword']}\n"
            f"*Language:* {language_info['code']}\n\n"
            f"*Definition:* {content['explanation']}\n\n"
            f"*Example:* {content['example']}\n\n"
            f"*Synonyms:* {content.get('synonyms', ['None'])}\n\n"
            f"Would you like to save this flashcard or edit it first?"
        )

        return message


class DeckService:
    """Service that handles deck business logic."""

    def __init__(
        self,
        deck_repo: DeckRepository,
        flashcard_repo: FlashcardRepository,
        llm_client: Optional[LLMClient] = None,
        user_service: Optional["UserService"] = None,
    ):
        self.deck_repo = deck_repo
        self.flashcard_repo = flashcard_repo
        self.llm_client = llm_client
        self.user_service = user_service
        logger.info("DeckService initialized")

    def get_user_decks(self, user_id: str) -> List[Deck]:
        """
        Get all decks for a user.

        Args:
            user_id: The ID of the user

        Returns:
            List of Deck objects
        """
        decks = self.deck_repo.list(user_id)
        logger.info(f"Retrieved {len(decks)} decks for user {user_id}")
        return decks

    def create_deck(self, name: str, user_id: str, description: str = "") -> Deck:
        """
        Create a new deck for a user.

        Args:
            name: The name of the deck
            user_id: The ID of the user
            description: Optional description for the deck

        Returns:
            The created Deck object
        """
        deck = Deck(name=name, description=description, user_id=user_id)
        created_deck = self.deck_repo.create(deck)
        logger.info(f"Created deck '{name}' with ID {created_deck.id} for user {user_id}")
        return created_deck

    def rename_deck(self, deck_id: str, new_name: str) -> Deck:
        """
        Rename a deck.

        Args:
            deck_id: The ID of the deck to rename
            new_name: The new name for the deck

        Returns:
            The updated Deck object
        """
        deck = self.deck_repo.get(deck_id)
        if not deck:
            logger.error(f"Deck with ID {deck_id} not found")
            raise ValueError(f"Deck with ID {deck_id} not found")

        old_name = deck.name
        deck.name = new_name
        updated_deck = self.deck_repo.update(deck)

        logger.info(f"Renamed deck from '{old_name}' to '{new_name}' with ID {deck_id}")
        return updated_deck

    def delete_deck(self, deck_id: str) -> bool:
        """
        Delete a deck and all its flashcards.

        Args:
            deck_id: The ID of the deck to delete

        Returns:
            True if the deck was deleted, False otherwise
        """
        # Check if the deck exists
        deck = self.deck_repo.get(deck_id)
        if not deck:
            logger.warning(f"Deck with ID {deck_id} not found")
            return False

        # Delete the deck (cascade delete will remove the flashcards)
        deleted = self.deck_repo.delete(deck_id)

        if deleted:
            logger.info(f"Deleted deck '{deck.name}' with ID {deck_id}")
        else:
            logger.warning(f"Failed to delete deck with ID {deck_id}")

        return deleted

    def get_deck_with_cards(self, deck_id: str) -> Optional[Deck]:
        """
        Get a deck with all its cards.

        Args:
            deck_id: The ID of the deck

        Returns:
            The deck with cards or None if not found
        """
        deck = self.deck_repo.get(deck_id)

        if deck:
            # Load cards from the repository
            deck.cards = self.flashcard_repo.get_by_deck(deck_id)
            logger.info(f"Retrieved deck {deck_id} with {len(deck.cards)} cards")
        else:
            logger.warning(f"Deck {deck_id} not found")

        return deck

    def move_card_to_deck(self, card_id: str, target_deck_id: str) -> Flashcard:
        """
        Move a flashcard from its current deck to another deck.

        Args:
            card_id: The ID of the flashcard to move
            target_deck_id: The ID of the destination deck

        Returns:
            The updated Flashcard object
        """
        # Get the card
        card = self.flashcard_repo.get(card_id)
        if not card:
            logger.error(f"Flashcard with ID {card_id} not found")
            raise ValueError(f"Flashcard with ID {card_id} not found")

        # Get the target deck
        target_deck = self.deck_repo.get(target_deck_id)
        if not target_deck:
            logger.error(f"Target deck with ID {target_deck_id} not found")
            raise ValueError(f"Target deck with ID {target_deck_id} not found")

        # Update the card's deck ID
        original_deck_id = card.deck_id
        card.deck_id = target_deck_id
        updated_card = self.flashcard_repo.update(card)

        logger.info(f"Moved flashcard {card_id} from deck {original_deck_id} to {target_deck_id}")
        return updated_card

    async def suggest_deck_name(self, content: str) -> str:
        """
        Suggest a deck name based on flashcard content using LLM.

        Args:
            content: The content to analyze (typically front and back of a flashcard)

        Returns:
            Suggested deck name
        """
        # Check if LLM client is available
        if not self.llm_client or not self.llm_client.client:
            logger.warning("LLM client not available for deck name suggestion")
            # Return a default name if no LLM available
            return "New Deck"

        try:
            system_prompt = (
                "You are a deck naming assistant for a flashcard application. "
                "Your task is to analyze the content of a flashcard and suggest "
                "a concise, descriptive name for a deck that would contain similar cards. "
                "The name should be 1-4 words, descriptive, and categorical. "
                "Do not use generic names like 'Flashcards' or 'Study Deck'. "
                "Return ONLY the suggested deck name with no explanation or additional text."
            )

            response = await self.llm_client.client.chat.completions.create(
                model=self.llm_client.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {
                        "role": "user",
                        "content": f"Suggest a deck name for this flashcard content:\n\n{content}",
                    },
                ],
                temperature=0.7,
                max_tokens=50,
                top_p=1.0,
                frequency_penalty=0.0,
                presence_penalty=0.0,
            )

            suggested_name = response.choices[0].message.content.strip()

            # Limit length if necessary
            if len(suggested_name) > 50:
                suggested_name = suggested_name[:50]

            logger.info(f"Suggested deck name: {suggested_name}")
            return suggested_name

        except Exception as e:
            logger.error(f"Error generating deck name suggestion: {e}")
            return "New Deck"


class UserService:
    """
    Service for managing user preferences.
    """

    def __init__(self, preferences_repo: UserPreferencesRepository):
        """Initialize with repositories."""
        self.preferences_repo = preferences_repo
        logger.info("UserService initialized")

    def get_user_preferences(self, user_id: str) -> UserPreferences:
        """
        Get user preferences, creating default preferences if none exist.

        Args:
            user_id: The ID of the user

        Returns:
            The user's preferences
        """
        prefs = self.preferences_repo.get(user_id)
        if not prefs:
            # Create default preferences
            prefs = UserPreferences(user_id=user_id)
            self.preferences_repo.save(prefs)
            logger.info(f"Created default preferences for user {user_id}")
        return prefs

    def update_preferences(
        self,
        user_id: str,
        last_deck_id: Optional[str] = None,
        last_language: Optional[str] = None,
        native_language: Optional[str] = None,
        learning_languages: Optional[List[str]] = None,
    ) -> UserPreferences:
        """
        Update user preferences.

        Args:
            user_id: The ID of the user
            last_deck_id: Optional deck ID to update
            last_language: Optional language code to update
            native_language: Optional native language code to update
            learning_languages: Optional list of language codes the user is learning

        Returns:
            The updated preferences
        """
        prefs = self.get_user_preferences(user_id)

        if last_deck_id is not None:
            prefs.last_deck_id = last_deck_id

        if last_language is not None:
            prefs.last_language = last_language

        if native_language is not None:
            prefs.native_language = native_language

        if learning_languages is not None:
            prefs.learning_languages = learning_languages

        updated_prefs = self.preferences_repo.save(prefs)
        logger.info(f"Updated preferences for user {user_id}")
        return updated_prefs

    def set_native_language(self, user_id: str, language_code: str) -> UserPreferences:
        """
        Set the user's native language.

        Args:
            user_id: The ID of the user
            language_code: The language code (e.g., 'en', 'es', 'fr')

        Returns:
            The updated preferences
        """
        return self.update_preferences(user_id, native_language=language_code)

    def add_learning_language(self, user_id: str, language_code: str) -> UserPreferences:
        """
        Add a language to the user's learning languages.

        Args:
            user_id: The ID of the user
            language_code: The language code to add

        Returns:
            The updated preferences
        """
        prefs = self.get_user_preferences(user_id)

        # Only add if not already in the list
        if language_code not in prefs.learning_languages:
            learning_languages = prefs.learning_languages.copy()
            learning_languages.append(language_code)
            return self.update_preferences(user_id, learning_languages=learning_languages)

        return prefs

    def remove_learning_language(self, user_id: str, language_code: str) -> UserPreferences:
        """
        Remove a language from the user's learning languages.

        Args:
            user_id: The ID of the user
            language_code: The language code to remove

        Returns:
            The updated preferences
        """
        prefs = self.get_user_preferences(user_id)

        # Make sure we have at least one language after removal
        if language_code in prefs.learning_languages and len(prefs.learning_languages) > 1:
            learning_languages = prefs.learning_languages.copy()
            learning_languages.remove(language_code)
            return self.update_preferences(user_id, learning_languages=learning_languages)

        return prefs


class ReviewService:
    """Service that handles flashcard review sessions."""

    def __init__(
        self,
        deck_repo: DeckRepository,
        flashcard_repo: FlashcardRepository,
        llm_client: Optional[LLMClient] = None,
    ):
        self.deck_repo = deck_repo
        self.flashcard_repo = flashcard_repo
        self.llm_client = llm_client
        self.ACTIVE_SESSIONS = ACTIVE_SESSIONS
        logger.info("ReviewService initialized")

    async def start_session(
        self,
        user_id: str,
        deck_id: str,
        training_mode: TrainingMode,
        api_key: str = settings.OPENAI_API_KEY,
        model: str = settings.OPENAI_MODEL,
    ) -> Dict[str, Any]:
        """
        Start a new review session.

        Args:
            user_id: The ID of the user
            deck_id: The ID of the deck to review
            training_mode: The training mode to use
            api_key: Optional OpenAI API key (defaults to settings)
            model: Optional OpenAI model (defaults to settings)

        Returns:
            Dictionary with session information
        """
        # Initialize LLM client if needed for this session
        if training_mode == TrainingMode.FILL_IN_BLANK:
            # We need LLM for this mode
            if not self.llm_client:
                logger.info("Initializing LLM client for review session")
                self.llm_client = LLMClient(model=model, api_key=api_key)

            # Check if LLM is available after initialization
            if not self.llm_client.client:
                logger.error(f"{training_mode.value} mode requires LLM but none is available")
                return {
                    "success": False,
                    "message": f"{training_mode.value} mode requires advanced AI features that are not available. Please try a different mode.",
                }

        # Get the deck with cards
        deck = self.deck_repo.get(deck_id)

        if not deck:
            logger.error(f"Deck {deck_id} not found")
            raise ValueError(f"Deck {deck_id} not found")

        # In a real implementation, you would load the cards from the repository
        if not deck.cards:
            logger.warning(f"Deck {deck_id} has no cards")
            return {"success": False, "message": "This deck has no cards to review."}

        # Create a new review session
        session = ReviewSession(
            deck_id=deck_id, user_id=user_id, training_mode=training_mode, max_cards=20
        )

        # Load due cards into the session
        session.load_due_cards(deck.cards)

        if not session.queue:
            logger.info(f"No due cards for deck {deck_id}")
            return {"success": False, "message": "No cards are due for review in this deck."}

        # Set up the LLM client for trainers that need it
        if training_mode == TrainingMode.FILL_IN_BLANK:
            # Get the first card and set up its trainer to have LLM
            first_card = session.queue[0] if session.queue else None
            if first_card:
                # Pre-create the trainer and set the LLM client
                logger.info(
                    f"Pre-initializing FillInBlankTrainer with LLM client: {self.llm_client is not None}"
                )
                trainer = FillInBlankTrainer(first_card, self.llm_client)
                # Store it for later use
                session._pre_initialized_trainer = trainer
                logger.info("FillInBlankTrainer stored in session._pre_initialized_trainer")

        # Store the session for the user
        self.ACTIVE_SESSIONS[user_id] = session

        logger.info(
            f"Started review session for user {user_id}, deck {deck_id}, mode {training_mode.value}"
        )
        return {
            "success": True,
            "session_info": {
                "deck_id": deck_id,
                "deck_name": deck.name,
                "training_mode": training_mode.value,
                "cards_due": len(session.queue),
            },
        }

    async def get_next_card(self, user_id: str) -> Optional[Dict[str, Any]]:
        """
        Get the next card for review in the user's active session.

        Args:
            user_id: The ID of the user

        Returns:
            Card data or None if the session is over
        """
        # Check if the user has an active session
        session = self.ACTIVE_SESSIONS.get(user_id)

        if not session:
            logger.warning(f"No active session for user {user_id}")
            return None

        try:
            # Get the next card from the session - this is now async
            card_data = await session.next_card()

            if not card_data:
                logger.info(f"Review session complete for user {user_id}")
                return None

            # Add the review progress
            card_data["progress"] = {
                "current": session.cards_reviewed + 1,
                "total": session.cards_reviewed + 1 + len(session.queue),
                "correct": session.correct_answers,
                "incorrect": session.incorrect_answers,
            }

            logger.info(f"Serving next card to user {user_id}")
            return card_data
        except Exception as e:
            # This catches any async errors that might occur during card preparation
            logger.error(f"Error getting next card for user {user_id}: {e}")
            logger.exception("Full error traceback:")

            # Return an error card
            return {
                "mode": "error",
                "error": f"An error occurred while preparing your flashcard: {e}",
                "progress": {
                    "current": session.cards_reviewed + 1 if session else 1,
                    "total": (session.cards_reviewed + 1 + len(session.queue)) if session else 1,
                    "correct": session.correct_answers if session else 0,
                    "incorrect": session.incorrect_answers if session else 0,
                },
            }

    async def process_answer(self, user_id: str, answer: str) -> Dict[str, Any]:
        """
        Process a user's answer in their active review session.

        Args:
            user_id: The ID of the user
            answer: The user's answer

        Returns:
            Result data including feedback
        """
        # Check if the user has an active session
        session = self.ACTIVE_SESSIONS.get(user_id)

        if not session:
            logger.warning(f"No active session for user {user_id}")
            return {"success": False, "message": "You don't have an active review session."}

        try:
            # Check if we need to handle fill-in-blank mode that requires LLM
            if session.training_mode == TrainingMode.FILL_IN_BLANK:
                # Provide the LLM client to the trainer
                if hasattr(session.current_trainer, "llm_client"):
                    session.current_trainer.llm_client = self.llm_client

            # All training modes use process_answer uniformly now
            logger.info(f"Processing answer for session with mode: {session.training_mode.value}")

            try:
                # Process the answer using the session's async process_answer method
                result = await session.process_answer(answer)
            except TypeError as e:
                # This catches errors related to awaiting non-coroutines
                logger.error(f"TypeError in process_answer: {e}")
                logger.exception("Full traceback:")

                if "can't be used in 'await' expression" in str(e):
                    # Handle the specific case where we're trying to await a non-awaitable
                    raise ValueError(
                        f"Error processing answer: {e} - There may be a mismatch between async/sync methods"
                    )
                else:
                    # Re-raise other type errors
                    raise

            # Save the updated card
            if session.current_card:
                self.flashcard_repo.update(session.current_card)

            # Add session status
            result["session_status"] = {
                "cards_left": len(session.queue),
                "cards_reviewed": session.cards_reviewed,
                "correct": session.correct_answers,
                "incorrect": session.incorrect_answers,
            }

            # Ensure success flag exists
            if "success" not in result:
                result["success"] = True

            # Clean up any potential markdown entities that might cause rendering issues
            if "explanation" in result:
                # Replace potential problematic characters in explanation with safe alternatives
                result["explanation"] = result["explanation"].replace("*", "•").replace("_", "-")

            logger.info(f"Processed answer for user {user_id}, correct: {result['is_correct']}")
            return result

        except Exception as e:
            logger.error(f"Error processing answer: {e}")
            return {"success": False, "message": "There was an error processing your answer."}

    async def end_session(self, user_id: str) -> Dict[str, Any]:
        """
        End a user's review session.

        Args:
            user_id: The ID of the user

        Returns:
            Summary of the review session
        """
        # Check if the user has an active session
        session = self.ACTIVE_SESSIONS.get(user_id)

        if not session:
            logger.warning(f"No active session to end for user {user_id}")
            return {"success": False, "message": "You don't have an active review session."}

        # Get the session summary
        summary = session.end_session()

        # Clean up the session
        del self.ACTIVE_SESSIONS[user_id]

        logger.info(f"Ended review session for user {user_id}")
        return {"success": True, "summary": summary}
