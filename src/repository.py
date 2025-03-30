"""
Repository module providing abstraction for data persistence.

This module defines the interfaces for data access, allowing for
swapping out the underlying persistence mechanism as needed.
"""

import abc
from typing import List, Optional

from src.database import Database
from src.models import Deck, Flashcard, UserPreferences


class BaseRepository(abc.ABC):
    """Abstract base class for repositories."""

    @abc.abstractmethod
    def close(self) -> None:
        """Close any open connections."""
        pass


class DeckRepository(BaseRepository):
    """Repository for Deck-related operations."""

    @abc.abstractmethod
    def create(self, deck: Deck) -> Deck:
        """Create a new deck."""
        pass

    @abc.abstractmethod
    def get(self, deck_id: str) -> Optional[Deck]:
        """Get a deck by ID."""
        pass

    @abc.abstractmethod
    def update(self, deck: Deck) -> Deck:
        """Update an existing deck."""
        pass

    @abc.abstractmethod
    def delete(self, deck_id: str) -> bool:
        """Delete a deck by ID."""
        pass

    @abc.abstractmethod
    def list(self, user_id: Optional[str] = None) -> List[Deck]:
        """List all decks, optionally filtered by user ID."""
        pass


class FlashcardRepository(BaseRepository):
    """Repository for Flashcard-related operations."""

    @abc.abstractmethod
    def create(self, card: Flashcard) -> Flashcard:
        """Create a new flashcard."""
        pass

    @abc.abstractmethod
    def get(self, card_id: str) -> Optional[Flashcard]:
        """Get a flashcard by ID."""
        pass

    @abc.abstractmethod
    def update(self, card: Flashcard) -> Flashcard:
        """Update an existing flashcard."""
        pass

    @abc.abstractmethod
    def delete(self, card_id: str) -> bool:
        """Delete a flashcard by ID."""
        pass

    @abc.abstractmethod
    def get_by_deck(self, deck_id: str) -> List[Flashcard]:
        """Get all flashcards in a deck."""
        pass

    @abc.abstractmethod
    def get_due(self, user_id: str, limit: int = 10) -> List[Flashcard]:
        """Get flashcards due for review."""
        pass


class SQLiteDeckRepository(DeckRepository):
    """SQLite implementation of the DeckRepository."""

    def __init__(self, db: Database):
        """Initialize with a Database instance."""
        self.db = db

    def create(self, deck: Deck) -> Deck:
        """Create a new deck."""
        return self.db.create_deck(deck)

    def get(self, deck_id: str) -> Optional[Deck]:
        """Get a deck by ID."""
        return self.db.get_deck(deck_id)

    def update(self, deck: Deck) -> Deck:
        """Update an existing deck."""
        return self.db.update_deck(deck)

    def delete(self, deck_id: str) -> bool:
        """Delete a deck by ID."""
        return self.db.delete_deck(deck_id)

    def list(self, user_id: Optional[str] = None) -> List[Deck]:
        """List all decks, optionally filtered by user ID."""
        return self.db.list_decks(user_id)

    def close(self) -> None:
        """Close the database connection."""
        pass  # Connection is managed by the Database instance


class SQLiteFlashcardRepository(FlashcardRepository):
    """SQLite implementation of the FlashcardRepository."""

    def __init__(self, db: Database):
        """Initialize with a Database instance."""
        self.db = db

    def create(self, card: Flashcard) -> Flashcard:
        """Create a new flashcard."""
        return self.db.create_flashcard(card)

    def get(self, card_id: str) -> Optional[Flashcard]:
        """Get a flashcard by ID."""
        return self.db.get_flashcard(card_id)

    def update(self, card: Flashcard) -> Flashcard:
        """Update an existing flashcard."""
        return self.db.update_flashcard(card)

    def delete(self, card_id: str) -> bool:
        """Delete a flashcard by ID."""
        return self.db.delete_flashcard(card_id)

    def get_by_deck(self, deck_id: str) -> List[Flashcard]:
        """Get all flashcards in a deck."""
        return self.db.get_flashcards_by_deck(deck_id)

    def get_due(self, user_id: str, limit: int = 10) -> List[Flashcard]:
        """Get flashcards due for review."""
        return self.db.get_due_flashcards(user_id, limit)

    def close(self) -> None:
        """Close the database connection."""
        pass  # Connection is managed by the Database instance
        
        
class UserPreferencesRepository(BaseRepository):
    """Repository for user preferences operations."""
    
    @abc.abstractmethod
    def get(self, user_id: str) -> Optional[UserPreferences]:
        """Get preferences for a user."""
        pass
        
    @abc.abstractmethod
    def save(self, preferences: UserPreferences) -> UserPreferences:
        """Save or update user preferences."""
        pass
        
        
class SQLiteUserPreferencesRepository(UserPreferencesRepository):
    """SQLite implementation of the UserPreferencesRepository."""
    
    def __init__(self, db: Database):
        """Initialize with a Database instance."""
        self.db = db
        
    def get(self, user_id: str) -> Optional[UserPreferences]:
        """Get preferences for a user."""
        return self.db.get_user_preferences(user_id)
        
    def save(self, preferences: UserPreferences) -> UserPreferences:
        """Save or update user preferences."""
        return self.db.save_user_preferences(preferences)
        
    def close(self) -> None:
        """Close the database connection."""
        pass  # Connection is managed by the Database instance
