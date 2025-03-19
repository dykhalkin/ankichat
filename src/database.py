"""
Database module for persistence of flashcards and decks.

This module provides a SQLite implementation for storing and retrieving data.
"""

import datetime
import json
import logging
import os
import sqlite3
from typing import Any, Dict, List, Optional, Union

from src.models import Deck, Flashcard

logger = logging.getLogger("ankichat")


# Custom adapters and converters for datetime objects to fix deprecation warnings in Python 3.12
def adapt_datetime(dt):
    """Convert datetime to ISO format string for SQLite storage."""
    return dt.isoformat() if dt else None


def convert_datetime(value):
    """Convert ISO format string from SQLite to datetime object."""
    if value is None:
        return None
    try:
        return datetime.datetime.fromisoformat(value)
    except (ValueError, TypeError):
        return None


# Register the adapter and converter
sqlite3.register_adapter(datetime.datetime, adapt_datetime)
sqlite3.register_converter("timestamp", convert_datetime)


class Database:
    """SQLite database implementation for flashcard persistence."""

    def __init__(self, db_path: str = "data/ankichat.db"):
        """
        Initialize the database connection.

        Args:
            db_path: Path to the SQLite database file
        """
        # Ensure the data directory exists
        os.makedirs(os.path.dirname(db_path), exist_ok=True)

        self.db_path = db_path
        self.conn = None

        self._connect()
        self._create_tables()

    def _connect(self) -> None:
        """Establish connection to the SQLite database."""
        try:
            self.conn = sqlite3.connect(self.db_path, detect_types=sqlite3.PARSE_DECLTYPES)
            # Enable foreign keys
            self.conn.execute("PRAGMA foreign_keys = ON")
            # Return rows as dictionaries
            self.conn.row_factory = sqlite3.Row
            logger.info(f"Connected to database at {self.db_path}")
        except sqlite3.Error as e:
            logger.error(f"Error connecting to database: {e}")
            raise

    def _create_tables(self) -> None:
        """Create necessary tables if they don't exist."""
        try:
            cursor = self.conn.cursor()

            # Create decks table
            cursor.execute(
                """
            CREATE TABLE IF NOT EXISTS decks (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                description TEXT,
                created_at timestamp NOT NULL,
                user_id TEXT
            )
            """
            )

            # Create flashcards table
            cursor.execute(
                """
            CREATE TABLE IF NOT EXISTS flashcards (
                id TEXT PRIMARY KEY,
                front TEXT NOT NULL,
                back TEXT NOT NULL,
                language TEXT NOT NULL,
                created_at timestamp NOT NULL,
                due_date timestamp,
                interval REAL NOT NULL,
                ease_factor REAL NOT NULL,
                review_count INTEGER NOT NULL,
                deck_id TEXT,
                FOREIGN KEY (deck_id) REFERENCES decks (id) ON DELETE CASCADE
            )
            """
            )

            # Check if tags column exists in the flashcards table
            cursor.execute("PRAGMA table_info(flashcards)")
            columns = [column[1] for column in cursor.fetchall()]

            # Add tags column if it doesn't exist
            if "tags" not in columns:
                logger.info("Adding tags column to flashcards table")
                cursor.execute("ALTER TABLE flashcards ADD COLUMN tags TEXT")

            self.conn.commit()
            logger.info("Database tables created or already exist")
        except sqlite3.Error as e:
            logger.error(f"Error creating database tables: {e}")
            raise

    def close(self) -> None:
        """Close the database connection."""
        if self.conn:
            self.conn.close()
            logger.info("Database connection closed")

    # Deck CRUD operations

    def create_deck(self, deck: Deck) -> Deck:
        """
        Create a new deck in the database.

        Args:
            deck: The Deck object to save

        Returns:
            The saved Deck object with any updated fields
        """
        try:
            cursor = self.conn.cursor()
            cursor.execute(
                """
                INSERT INTO decks (id, name, description, created_at, user_id)
                VALUES (?, ?, ?, ?, ?)
                """,
                (deck.id, deck.name, deck.description, deck.created_at, deck.user_id),
            )
            self.conn.commit()
            logger.info(f"Created deck '{deck.name}' with ID {deck.id}")
            return deck
        except sqlite3.Error as e:
            self.conn.rollback()
            logger.error(f"Error creating deck: {e}")
            raise

    def get_deck(self, deck_id: str) -> Optional[Deck]:
        """
        Retrieve a deck by its ID.

        Args:
            deck_id: The ID of the deck to retrieve

        Returns:
            The Deck object if found, None otherwise
        """
        try:
            cursor = self.conn.cursor()
            cursor.execute("SELECT * FROM decks WHERE id = ?", (deck_id,))
            row = cursor.fetchone()

            if not row:
                logger.info(f"Deck with ID {deck_id} not found")
                return None

            # Convert row to Deck object
            deck = Deck(
                id=row["id"],
                name=row["name"],
                description=row["description"],
                created_at=row["created_at"],
                user_id=row["user_id"],
            )

            # Get all flashcards for this deck
            deck.cards = self.get_flashcards_by_deck(deck_id)

            logger.info(f"Retrieved deck '{deck.name}' with {len(deck.cards)} cards")
            return deck
        except sqlite3.Error as e:
            logger.error(f"Error retrieving deck: {e}")
            raise

    def update_deck(self, deck: Deck) -> Deck:
        """
        Update an existing deck.

        Args:
            deck: The Deck object with updated values

        Returns:
            The updated Deck object
        """
        try:
            cursor = self.conn.cursor()
            cursor.execute(
                """
                UPDATE decks
                SET name = ?, description = ?, user_id = ?
                WHERE id = ?
                """,
                (deck.name, deck.description, deck.user_id, deck.id),
            )

            if cursor.rowcount == 0:
                logger.warning(f"No deck with ID {deck.id} found to update")
                raise ValueError(f"Deck with ID {deck.id} not found")

            self.conn.commit()
            logger.info(f"Updated deck '{deck.name}' with ID {deck.id}")
            return deck
        except sqlite3.Error as e:
            self.conn.rollback()
            logger.error(f"Error updating deck: {e}")
            raise

    def delete_deck(self, deck_id: str) -> bool:
        """
        Delete a deck by its ID.

        Args:
            deck_id: The ID of the deck to delete

        Returns:
            True if the deck was deleted, False otherwise
        """
        try:
            cursor = self.conn.cursor()
            cursor.execute("DELETE FROM decks WHERE id = ?", (deck_id,))

            deleted = cursor.rowcount > 0
            self.conn.commit()

            if deleted:
                logger.info(f"Deleted deck with ID {deck_id}")
            else:
                logger.warning(f"No deck with ID {deck_id} found to delete")

            return deleted
        except sqlite3.Error as e:
            self.conn.rollback()
            logger.error(f"Error deleting deck: {e}")
            raise

    def list_decks(self, user_id: Optional[str] = None) -> List[Deck]:
        """
        List all decks, optionally filtered by user ID.

        Args:
            user_id: Optional user ID to filter decks by

        Returns:
            List of Deck objects
        """
        try:
            cursor = self.conn.cursor()

            if user_id:
                cursor.execute(
                    "SELECT * FROM decks WHERE user_id = ? ORDER BY created_at DESC", (user_id,)
                )
            else:
                cursor.execute("SELECT * FROM decks ORDER BY created_at DESC")

            rows = cursor.fetchall()
            decks = []

            for row in rows:
                deck = Deck(
                    id=row["id"],
                    name=row["name"],
                    description=row["description"],
                    created_at=row["created_at"],
                    user_id=row["user_id"],
                )
                decks.append(deck)

            logger.info(f"Retrieved {len(decks)} decks")
            return decks
        except sqlite3.Error as e:
            logger.error(f"Error listing decks: {e}")
            raise

    # Flashcard CRUD operations

    def create_flashcard(self, card: Flashcard) -> Flashcard:
        """
        Create a new flashcard in the database.

        Args:
            card: The Flashcard object to save

        Returns:
            The saved Flashcard object with any updated fields
        """
        try:
            cursor = self.conn.cursor()

            # Convert tags list to JSON string
            tags_json = json.dumps(card.tags) if card.tags else None

            cursor.execute(
                """
                INSERT INTO flashcards 
                (id, front, back, language, created_at, due_date, 
                interval, ease_factor, review_count, deck_id, tags)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    card.id,
                    card.front,
                    card.back,
                    card.language,
                    card.created_at,
                    card.due_date,
                    card.interval,
                    card.ease_factor,
                    card.review_count,
                    card.deck_id,
                    tags_json,
                ),
            )
            self.conn.commit()
            logger.info(f"Created flashcard with ID {card.id}")
            return card
        except sqlite3.Error as e:
            self.conn.rollback()
            logger.error(f"Error creating flashcard: {e}")
            raise

    def get_flashcard(self, card_id: str) -> Optional[Flashcard]:
        """
        Retrieve a flashcard by its ID.

        Args:
            card_id: The ID of the flashcard to retrieve

        Returns:
            The Flashcard object if found, None otherwise
        """
        try:
            cursor = self.conn.cursor()
            cursor.execute("SELECT * FROM flashcards WHERE id = ?", (card_id,))
            row = cursor.fetchone()

            if not row:
                logger.info(f"Flashcard with ID {card_id} not found")
                return None

            # Parse tags from JSON
            tags = []
            if row["tags"]:
                try:
                    tags = json.loads(row["tags"])
                except json.JSONDecodeError:
                    logger.warning(f"Invalid tags JSON for flashcard {card_id}")

            card = Flashcard(
                id=row["id"],
                front=row["front"],
                back=row["back"],
                language=row["language"],
                created_at=row["created_at"],
                due_date=row["due_date"],
                interval=row["interval"],
                ease_factor=row["ease_factor"],
                review_count=row["review_count"],
                deck_id=row["deck_id"],
                tags=tags,
            )

            logger.info(f"Retrieved flashcard with ID {card_id}")
            return card
        except sqlite3.Error as e:
            logger.error(f"Error retrieving flashcard: {e}")
            raise

    def update_flashcard(self, card: Flashcard) -> Flashcard:
        """
        Update an existing flashcard.

        Args:
            card: The Flashcard object with updated values

        Returns:
            The updated Flashcard object
        """
        try:
            cursor = self.conn.cursor()

            # Convert tags list to JSON string
            tags_json = json.dumps(card.tags) if card.tags else None

            cursor.execute(
                """
                UPDATE flashcards
                SET front = ?, back = ?, language = ?, due_date = ?,
                interval = ?, ease_factor = ?, review_count = ?, deck_id = ?, tags = ?
                WHERE id = ?
                """,
                (
                    card.front,
                    card.back,
                    card.language,
                    card.due_date,
                    card.interval,
                    card.ease_factor,
                    card.review_count,
                    card.deck_id,
                    tags_json,
                    card.id,
                ),
            )

            if cursor.rowcount == 0:
                logger.warning(f"No flashcard with ID {card.id} found to update")
                raise ValueError(f"Flashcard with ID {card.id} not found")

            self.conn.commit()
            logger.info(f"Updated flashcard with ID {card.id}")
            return card
        except sqlite3.Error as e:
            self.conn.rollback()
            logger.error(f"Error updating flashcard: {e}")
            raise

    def delete_flashcard(self, card_id: str) -> bool:
        """
        Delete a flashcard by its ID.

        Args:
            card_id: The ID of the flashcard to delete

        Returns:
            True if the flashcard was deleted, False otherwise
        """
        try:
            cursor = self.conn.cursor()
            cursor.execute("DELETE FROM flashcards WHERE id = ?", (card_id,))

            deleted = cursor.rowcount > 0
            self.conn.commit()

            if deleted:
                logger.info(f"Deleted flashcard with ID {card_id}")
            else:
                logger.warning(f"No flashcard with ID {card_id} found to delete")

            return deleted
        except sqlite3.Error as e:
            self.conn.rollback()
            logger.error(f"Error deleting flashcard: {e}")
            raise

    def get_flashcards_by_deck(self, deck_id: str) -> List[Flashcard]:
        """
        Get all flashcards belonging to a specific deck.

        Args:
            deck_id: The ID of the deck

        Returns:
            List of Flashcard objects in the deck
        """
        try:
            cursor = self.conn.cursor()
            cursor.execute(
                "SELECT * FROM flashcards WHERE deck_id = ? ORDER BY created_at", (deck_id,)
            )
            rows = cursor.fetchall()

            cards = []
            for row in rows:
                # Parse tags from JSON
                tags = []
                if row["tags"]:
                    try:
                        tags = json.loads(row["tags"])
                    except json.JSONDecodeError:
                        logger.warning(f"Invalid tags JSON for flashcard {row['id']}")

                card = Flashcard(
                    id=row["id"],
                    front=row["front"],
                    back=row["back"],
                    language=row["language"],
                    created_at=row["created_at"],
                    due_date=row["due_date"],
                    interval=row["interval"],
                    ease_factor=row["ease_factor"],
                    review_count=row["review_count"],
                    deck_id=row["deck_id"],
                    tags=tags,
                )
                cards.append(card)

            logger.info(f"Retrieved {len(cards)} flashcards for deck {deck_id}")
            return cards
        except sqlite3.Error as e:
            logger.error(f"Error retrieving flashcards for deck: {e}")
            raise

    def get_due_flashcards(self, user_id: str, limit: int = 10) -> List[Flashcard]:
        """
        Get flashcards that are due for review.

        Args:
            user_id: The ID of the user
            limit: Maximum number of cards to return

        Returns:
            List of Flashcard objects due for review
        """
        try:
            now = datetime.datetime.now()
            cursor = self.conn.cursor()

            # Get cards from decks owned by the user that are due for review
            cursor.execute(
                """
                SELECT f.* FROM flashcards f
                JOIN decks d ON f.deck_id = d.id
                WHERE d.user_id = ? AND (f.due_date IS NULL OR f.due_date <= ?)
                ORDER BY f.due_date IS NULL DESC, f.due_date ASC
                LIMIT ?
                """,
                (user_id, now, limit),
            )

            rows = cursor.fetchall()
            cards = []

            for row in rows:
                # Parse tags from JSON
                tags = []
                if row["tags"]:
                    try:
                        tags = json.loads(row["tags"])
                    except json.JSONDecodeError:
                        logger.warning(f"Invalid tags JSON for flashcard {row['id']}")

                card = Flashcard(
                    id=row["id"],
                    front=row["front"],
                    back=row["back"],
                    language=row["language"],
                    created_at=row["created_at"],
                    due_date=row["due_date"],
                    interval=row["interval"],
                    ease_factor=row["ease_factor"],
                    review_count=row["review_count"],
                    deck_id=row["deck_id"],
                    tags=tags,
                )
                cards.append(card)

            logger.info(f"Retrieved {len(cards)} due flashcards for user {user_id}")
            return cards
        except sqlite3.Error as e:
            logger.error(f"Error retrieving due flashcards: {e}")
            raise
