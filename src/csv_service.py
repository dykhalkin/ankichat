"""
CSV service module for the Anki Flashcards System.

This module provides service-level functionality for importing and exporting
flashcards and decks from/to CSV files.
"""

import logging
from typing import Any, Dict, List, Optional, Tuple

from src.csv_manager import CSVManager
from src.llm import LLMClient
from src.models import Deck, Flashcard
from src.repository import DeckRepository, FlashcardRepository

logger = logging.getLogger("ankichat")


class CSVService:
    """
    Service for CSV import/export operations.

    This service orchestrates CSV operations and provides business logic
    for handling the import and export of flashcards and decks.
    """

    def __init__(
        self,
        deck_repo: DeckRepository,
        flashcard_repo: FlashcardRepository,
        llm_client: Optional[LLMClient] = None,
    ):
        """
        Initialize the CSV service.

        Args:
            deck_repo: Repository for deck operations
            flashcard_repo: Repository for flashcard operations
            llm_client: Optional LLM client for content analysis
        """
        self.deck_repo = deck_repo
        self.flashcard_repo = flashcard_repo
        self.llm_client = llm_client
        self.csv_manager = CSVManager(deck_repo, flashcard_repo)
        logger.info("CSVService initialized")

    def export_deck_to_csv(self, deck_id: str, output_path: str) -> Dict[str, Any]:
        """
        Export a deck to a CSV file.

        Args:
            deck_id: ID of the deck to export
            output_path: Directory where the CSV file will be saved

        Returns:
            Dictionary with export result information
        """
        try:
            # Check if the deck exists
            deck = self.deck_repo.get(deck_id)
            if not deck:
                logger.error(f"Deck with ID {deck_id} not found")
                return {
                    "success": False,
                    "message": f"Deck with ID {deck_id} not found",
                    "file_path": None,
                }

            # Perform the export
            file_path = self.csv_manager.export_deck_to_csv(deck_id, output_path)

            return {
                "success": True,
                "message": f"Deck '{deck.name}' exported successfully",
                "file_path": file_path,
                "deck_name": deck.name,
            }

        except Exception as e:
            logger.error(f"Error exporting deck {deck_id} to CSV: {e}")
            return {
                "success": False,
                "message": f"Error exporting deck: {str(e)}",
                "file_path": None,
            }

    def export_all_decks(self, user_id: str, output_path: str) -> Dict[str, Any]:
        """
        Export all decks for a user to CSV files.

        Args:
            user_id: ID of the user whose decks will be exported
            output_path: Directory where the CSV files will be saved

        Returns:
            Dictionary with export result information
        """
        try:
            # Get all decks for the user to check if there are any
            decks = self.deck_repo.list(user_id)
            if not decks:
                logger.warning(f"User {user_id} has no decks to export")
                return {"success": False, "message": "You have no decks to export", "files": []}

            # Perform the export
            exported_files = self.csv_manager.export_all_decks_to_csv(user_id, output_path)

            return {
                "success": True,
                "message": f"Exported {len(exported_files)} decks successfully",
                "files": exported_files,
                "deck_count": len(exported_files),
            }

        except Exception as e:
            logger.error(f"Error exporting decks for user {user_id} to CSV: {e}")
            return {"success": False, "message": f"Error exporting decks: {str(e)}", "files": []}

    def import_from_csv(
        self,
        file_path: str,
        user_id: str,
        target_deck_id: Optional[str] = None,
        create_missing_decks: bool = True,
    ) -> Dict[str, Any]:
        """
        Import flashcards from a CSV file.

        Args:
            file_path: Path to the CSV file
            user_id: ID of the user importing the cards
            target_deck_id: Optional ID of a deck to import all cards into
            create_missing_decks: Whether to create decks if they don't exist

        Returns:
            Dictionary with import result information
        """
        try:
            # Check if target deck exists if provided
            if target_deck_id:
                target_deck = self.deck_repo.get(target_deck_id)
                if not target_deck:
                    logger.error(f"Target deck with ID {target_deck_id} not found")
                    return {
                        "success": False,
                        "message": f"Target deck not found",
                        "cards_imported": 0,
                        "decks_created": 0,
                    }

            # Perform the import
            cards_imported, decks_created, warnings = self.csv_manager.import_flashcards_from_csv(
                file_path, user_id, target_deck_id, create_missing_decks
            )

            # Craft response message
            if cards_imported > 0:
                message = f"Successfully imported {cards_imported} flashcards"
                if decks_created > 0:
                    message += f" and created {decks_created} new decks"

                if warnings:
                    message += f". There were {len(warnings)} warnings."

                success = True
            else:
                message = "No flashcards were imported"
                if warnings:
                    message += f": {warnings[0]}"
                success = False

            return {
                "success": success,
                "message": message,
                "cards_imported": cards_imported,
                "decks_created": decks_created,
                "warnings": warnings,
            }

        except Exception as e:
            logger.error(f"Error importing from CSV file {file_path}: {e}")
            return {
                "success": False,
                "message": f"Error importing from CSV: {str(e)}",
                "cards_imported": 0,
                "decks_created": 0,
                "warnings": [str(e)],
            }

    async def import_with_auto_deck(
        self, file_path: str, user_id: str, auto_create_decks: bool = True
    ) -> Dict[str, Any]:
        """
        Import flashcards from a CSV file with automatic deck creation using LLM.

        Args:
            file_path: Path to the CSV file
            user_id: ID of the user importing the cards
            auto_create_decks: Whether to automatically create decks based on content

        Returns:
            Dictionary with import result information
        """
        # Basic import without auto-deck if LLM not available or auto_create_decks is False
        if not auto_create_decks or not self.llm_client or not self.llm_client.client:
            logger.info("Importing without auto-deck creation")
            return self.import_from_csv(file_path, user_id, None, True)

        try:
            # First, import all cards without assigning to specific deck
            # Use a temporary target deck
            temp_deck = self.deck_repo.create(
                Deck(
                    name="Temp Import Deck",
                    description="Temporary deck for CSV import",
                    user_id=user_id,
                )
            )

            import_result = self.import_from_csv(file_path, user_id, temp_deck.id, False)

            if not import_result["success"] or import_result["cards_imported"] == 0:
                # Clean up temporary deck if import failed
                self.deck_repo.delete(temp_deck.id)
                return import_result

            # Get all imported cards
            imported_cards = self.flashcard_repo.get_by_deck(temp_deck.id)

            # Process cards in batches for deck suggestions
            batch_size = 10
            deck_suggestions = {}  # card_id -> suggested_deck_name

            for i in range(0, len(imported_cards), batch_size):
                batch = imported_cards[i : i + batch_size]

                for card in batch:
                    # Combine front and back for content analysis
                    content = f"Front: {card.front}\nBack: {card.back}"

                    # Get deck name suggestion
                    suggested_name = (
                        await self.llm_client.detect_category(content)
                        if self.llm_client
                        else "Imported Cards"
                    )
                    deck_suggestions[card.id] = suggested_name

            # Group cards by suggested deck name
            deck_name_to_id = {}
            cards_moved = 0
            decks_created = 0

            # Get existing decks for the user
            for deck in self.deck_repo.list(user_id):
                deck_name_to_id[deck.name] = deck.id

            # Create decks and move cards
            for card in imported_cards:
                deck_name = deck_suggestions.get(card.id, "Imported Cards")

                # Get or create deck
                if deck_name in deck_name_to_id:
                    deck_id = deck_name_to_id[deck_name]
                else:
                    # Create new deck
                    new_deck = self.deck_repo.create(
                        Deck(
                            name=deck_name,
                            description=f"Auto-created deck for imported cards",
                            user_id=user_id,
                        )
                    )
                    deck_id = new_deck.id
                    deck_name_to_id[deck_name] = deck_id
                    decks_created += 1

                # Move card to the appropriate deck
                card.deck_id = deck_id
                self.flashcard_repo.update(card)
                cards_moved += 1

            # Delete the temporary deck
            self.deck_repo.delete(temp_deck.id)

            return {
                "success": True,
                "message": f"Successfully imported {import_result['cards_imported']} flashcards into {decks_created} auto-created decks",
                "cards_imported": import_result["cards_imported"],
                "decks_created": decks_created,
                "cards_organized": cards_moved,
                "warnings": import_result.get("warnings", []),
            }

        except Exception as e:
            logger.error(f"Error importing with auto-deck creation: {e}")
            return {
                "success": False,
                "message": f"Error importing with auto-deck creation: {str(e)}",
                "cards_imported": 0,
                "decks_created": 0,
                "warnings": [str(e)],
            }
