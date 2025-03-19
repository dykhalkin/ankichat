"""
CSV import/export module for the Anki Flashcards System.

This module provides functionality for importing and exporting flashcards
and decks from/to CSV files.
"""

import csv
import datetime
import logging
import os
from typing import List, Optional, Dict, Any, Tuple

from src.models import Flashcard, Deck
from src.repository import DeckRepository, FlashcardRepository

logger = logging.getLogger('ankichat')

# Define CSV column headers for flashcards
FLASHCARD_CSV_HEADERS = [
    'id', 'front', 'back', 'language', 'created_at', 'due_date',
    'interval', 'ease_factor', 'review_count', 'deck_id', 'deck_name'
]

# Define CSV column headers for decks
DECK_CSV_HEADERS = [
    'id', 'name', 'description', 'created_at', 'user_id'
]


class CSVManager:
    """
    Manager for CSV import/export operations.
    """
    
    def __init__(
        self, 
        deck_repo: DeckRepository,
        flashcard_repo: FlashcardRepository
    ):
        """
        Initialize the CSV manager.
        
        Args:
            deck_repo: Repository for deck operations
            flashcard_repo: Repository for flashcard operations
        """
        self.deck_repo = deck_repo
        self.flashcard_repo = flashcard_repo
        logger.info("CSVManager initialized")
    
    def export_deck_to_csv(self, deck_id: str, output_path: str) -> str:
        """
        Export a deck with all its flashcards to a CSV file.
        
        Args:
            deck_id: ID of the deck to export
            output_path: Directory where the CSV file will be saved
            
        Returns:
            Path to the created CSV file
        """
        # Ensure output directory exists
        os.makedirs(output_path, exist_ok=True)
        
        # Get the deck with cards
        deck = self.deck_repo.get(deck_id)
        if not deck:
            logger.error(f"Deck with ID {deck_id} not found")
            raise ValueError(f"Deck with ID {deck_id} not found")
        
        # Get all cards for the deck
        cards = self.flashcard_repo.get_by_deck(deck_id)
        
        # Create filename using the deck name
        safe_name = "".join(c for c in deck.name if c.isalnum() or c in "_ ").strip().replace(" ", "_")
        file_path = os.path.join(output_path, f"{safe_name}.csv")
        
        # Write to CSV file
        with open(file_path, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=FLASHCARD_CSV_HEADERS)
            writer.writeheader()
            
            for card in cards:
                writer.writerow({
                    'id': card.id,
                    'front': card.front,
                    'back': card.back,
                    'language': card.language,
                    'created_at': card.created_at.isoformat() if card.created_at else '',
                    'due_date': card.due_date.isoformat() if card.due_date else '',
                    'interval': card.interval,
                    'ease_factor': card.ease_factor,
                    'review_count': card.review_count,
                    'deck_id': card.deck_id,
                    'deck_name': deck.name
                })
        
        logger.info(f"Exported {len(cards)} flashcards from deck '{deck.name}' to {file_path}")
        return file_path
    
    def export_all_decks_to_csv(self, user_id: str, output_path: str) -> List[str]:
        """
        Export all decks for a user to CSV files.
        
        Args:
            user_id: ID of the user whose decks will be exported
            output_path: Directory where the CSV files will be saved
            
        Returns:
            List of paths to the created CSV files
        """
        # Ensure output directory exists
        os.makedirs(output_path, exist_ok=True)
        
        # Get all decks for the user
        decks = self.deck_repo.list(user_id)
        
        # Export each deck
        exported_files = []
        for deck in decks:
            try:
                file_path = self.export_deck_to_csv(deck.id, output_path)
                exported_files.append(file_path)
            except Exception as e:
                logger.error(f"Error exporting deck {deck.id}: {e}")
        
        logger.info(f"Exported {len(exported_files)} decks for user {user_id}")
        return exported_files
    
    def import_flashcards_from_csv(
        self, 
        file_path: str, 
        user_id: str,
        target_deck_id: Optional[str] = None,
        create_missing_decks: bool = True
    ) -> Tuple[int, int, List[str]]:
        """
        Import flashcards from a CSV file.
        
        Args:
            file_path: Path to the CSV file
            user_id: ID of the user importing the cards
            target_deck_id: Optional ID of a deck to import all cards into
            create_missing_decks: Whether to create decks if they don't exist
            
        Returns:
            Tuple of (cards_imported, decks_created, list of warnings)
        """
        cards_imported = 0
        decks_created = 0
        warnings = []
        
        # Track decks by name to avoid creating duplicates
        deck_name_to_id = {}
        
        # Get existing decks for the user
        for deck in self.deck_repo.list(user_id):
            deck_name_to_id[deck.name] = deck.id
        
        # Read the CSV file
        try:
            with open(file_path, 'r', newline='', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                
                # Validate headers
                if not set(FLASHCARD_CSV_HEADERS).issubset(set(reader.fieldnames or [])):
                    missing = set(FLASHCARD_CSV_HEADERS) - set(reader.fieldnames or [])
                    logger.error(f"CSV file is missing required columns: {missing}")
                    raise ValueError(f"CSV file is missing required columns: {missing}")
                
                for row in reader:
                    try:
                        # Determine the deck for this card
                        deck_id = target_deck_id
                        
                        if not deck_id:
                            # Use the deck from the CSV if no target deck specified
                            deck_name = row.get('deck_name', '')
                            csv_deck_id = row.get('deck_id', '')
                            
                            if deck_name in deck_name_to_id:
                                # Use existing deck with matching name
                                deck_id = deck_name_to_id[deck_name]
                            elif csv_deck_id and self.deck_repo.get(csv_deck_id):
                                # Use the deck ID from CSV if it exists
                                deck_id = csv_deck_id
                                deck_name_to_id[deck_name] = deck_id
                            elif create_missing_decks and deck_name:
                                # Create a new deck
                                import_date = datetime.datetime.now().strftime('%Y-%m-%d')
                                new_deck = Deck(
                                    name=deck_name,
                                    description=f"Imported from CSV on {import_date}",
                                    user_id=user_id
                                )
                                created_deck = self.deck_repo.create(new_deck)
                                deck_id = created_deck.id
                                deck_name_to_id[deck_name] = deck_id
                                decks_created += 1
                                logger.info(f"Created new deck '{deck_name}' with ID {deck_id}")
                            else:
                                warnings.append(f"Skipped card: No valid deck for '{row.get('front', 'Unknown')}'")
                                continue
                        
                        # Parse dates
                        created_at = None
                        due_date = None
                        
                        try:
                            if row.get('created_at'):
                                created_at = datetime.datetime.fromisoformat(row['created_at'])
                        except (ValueError, TypeError):
                            warnings.append(f"Invalid created_at format for card '{row.get('front', 'Unknown')}', using current time")
                        
                        try:
                            if row.get('due_date'):
                                due_date = datetime.datetime.fromisoformat(row['due_date'])
                        except (ValueError, TypeError):
                            warnings.append(f"Invalid due_date format for card '{row.get('front', 'Unknown')}', will be calculated on review")
                        
                        # Create the flashcard
                        card = Flashcard(
                            front=row['front'],
                            back=row['back'],
                            language=row.get('language', 'en'),
                            created_at=created_at or datetime.datetime.now(),
                            due_date=due_date,
                            interval=float(row.get('interval', 1.0)),
                            ease_factor=float(row.get('ease_factor', 2.5)),
                            review_count=int(row.get('review_count', 0)),
                            deck_id=deck_id
                        )
                        
                        # Keep existing ID if provided and not already in use
                        if row.get('id') and not self.flashcard_repo.get(row['id']):
                            card.id = row['id']
                        
                        # Save the card
                        self.flashcard_repo.create(card)
                        cards_imported += 1
                        
                    except Exception as e:
                        logger.error(f"Error importing card: {e}")
                        warnings.append(f"Error importing card '{row.get('front', 'Unknown')}': {e}")
        
        except Exception as e:
            logger.error(f"Error reading CSV file {file_path}: {e}")
            raise
        
        logger.info(f"Imported {cards_imported} cards and created {decks_created} decks from {file_path}")
        return cards_imported, decks_created, warnings


def convert_flashcard_to_csv_row(card: Flashcard, deck_name: str = "") -> Dict[str, Any]:
    """
    Convert a Flashcard object to a dict ready for CSV export.
    
    Args:
        card: The Flashcard to convert
        deck_name: Optional name of the deck
        
    Returns:
        Dictionary with CSV-formatted values
    """
    return {
        'id': card.id,
        'front': card.front,
        'back': card.back,
        'language': card.language,
        'created_at': card.created_at.isoformat() if card.created_at else '',
        'due_date': card.due_date.isoformat() if card.due_date else '',
        'interval': card.interval,
        'ease_factor': card.ease_factor,
        'review_count': card.review_count,
        'deck_id': card.deck_id,
        'deck_name': deck_name
    }


def convert_csv_row_to_flashcard(row: Dict[str, str], user_id: str) -> Flashcard:
    """
    Convert a CSV row to a Flashcard object.
    
    Args:
        row: Dictionary representing a CSV row
        user_id: ID of the user importing the card
        
    Returns:
        Flashcard object
    """
    # Parse dates
    created_at = None
    due_date = None
    
    try:
        if row.get('created_at'):
            created_at = datetime.datetime.fromisoformat(row['created_at'])
    except (ValueError, TypeError):
        pass
    
    try:
        if row.get('due_date'):
            due_date = datetime.datetime.fromisoformat(row['due_date'])
    except (ValueError, TypeError):
        pass
    
    # Create the flashcard
    card = Flashcard(
        front=row['front'],
        back=row['back'],
        language=row.get('language', 'en'),
        created_at=created_at or datetime.datetime.now(),
        due_date=due_date,
        interval=float(row.get('interval', 1.0)),
        ease_factor=float(row.get('ease_factor', 2.5)),
        review_count=int(row.get('review_count', 0)),
        deck_id=row.get('deck_id', None)
    )
    
    # Keep existing ID if provided
    if row.get('id'):
        card.id = row['id']
    
    return card