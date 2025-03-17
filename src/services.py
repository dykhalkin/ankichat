"""
Service layer for the Anki Flashcards System.

This module contains the business logic for creating and managing flashcards.
"""

import logging
import uuid
import datetime
from typing import Dict, Any, Optional, Tuple, List

from src.models import Flashcard, Deck
from src.repository import DeckRepository, FlashcardRepository
from src.llm import LLMClient

logger = logging.getLogger('ankichat')


class FlashcardService:
    """
    Service that handles flashcard business logic including
    creation, update, and retrieval.
    """

    def __init__(
        self,
        flashcard_repo: FlashcardRepository,
        deck_repo: DeckRepository,
        llm_client: LLMClient
    ):
        self.flashcard_repo = flashcard_repo
        self.deck_repo = deck_repo
        self.llm_client = llm_client
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
        
        # Detect language of the input text
        language_code, confidence = await self.llm_client.detect_language(text)
        
        # Generate flashcard content
        content = await self.llm_client.generate_flashcard_content(text, language_code)
        
        # Create preview object
        preview = {
            "input_text": text,
            "user_id": user_id,
            "language": {
                "code": language_code,
                "confidence": confidence
            },
            "content": content,
            "preview_id": str(uuid.uuid4())
        }
        
        logger.info(f"Created flashcard preview with ID: {preview['preview_id']}")
        return preview
    
    async def create_flashcard_from_preview(
        self,
        preview_id: str,
        deck_id: str,
        user_edits: Optional[Dict[str, Any]] = None
    ) -> Flashcard:
        """
        Create a new flashcard from a preview.
        
        Args:
            preview_id: The ID of the preview to use
            deck_id: The ID of the deck to add the card to
            user_edits: Optional dictionary with user edits to the content
            
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
            deck_id=deck_id
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
        
        # Format the message
        message = (
            f"📝 *Flashcard Preview*\n\n"
            f"*Word/Phrase:* {content['word']}\n"
            f"*Language:* {language_info['code']} (Confidence: {language_info['confidence']:.2f})\n\n"
            f"*Definition:* {content['definition']}\n\n"
            f"*Example:* {content['example_sentence']}\n\n"
            f"*Pronunciation:* {content['pronunciation_guide']}\n"
            f"*Part of Speech:* {content['part_of_speech']}\n\n"
            f"*Notes:* {content['notes']}\n\n"
            f"Would you like to save this flashcard or edit it first?"
        )
        
        return message


class DeckService:
    """Service that handles deck business logic."""

    def __init__(self, deck_repo: DeckRepository):
        self.deck_repo = deck_repo
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