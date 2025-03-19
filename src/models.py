"""
Core data models for the Anki Flashcards system.

This module defines the data structures for flashcards and decks.
"""

import datetime
import uuid
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class Flashcard:
    """
    Represents a flashcard with front and back content and SRS metadata.

    Attributes:
        id: Unique identifier for the flashcard
        front: Text content for the front of the card
        back: Text content for the back of the card
        language: Language of the flashcard content
        created_at: Timestamp when the card was created
        due_date: Next scheduled review date
        interval: Current interval in days for spaced repetition
        ease_factor: Difficulty factor (higher means easier to remember)
        review_count: Number of times the card has been reviewed
        deck_id: ID of the deck this card belongs to
        tags: List of tags for the flashcard
    """

    front: str
    back: str
    language: str = "en"
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    created_at: datetime.datetime = field(default_factory=datetime.datetime.now)
    due_date: Optional[datetime.datetime] = None
    interval: float = 1.0  # Initial interval (in days)
    ease_factor: float = 2.5  # Initial ease factor
    review_count: int = 0
    deck_id: Optional[str] = None
    tags: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        """Convert the flashcard to a dictionary."""
        return {
            "id": self.id,
            "front": self.front,
            "back": self.back,
            "language": self.language,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "due_date": self.due_date.isoformat() if self.due_date else None,
            "interval": self.interval,
            "ease_factor": self.ease_factor,
            "review_count": self.review_count,
            "deck_id": self.deck_id,
            "tags": self.tags,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Flashcard":
        """Create a flashcard from a dictionary."""
        # Convert string dates to datetime objects
        created_at = data.get("created_at")
        if created_at and isinstance(created_at, str):
            created_at = datetime.datetime.fromisoformat(created_at)

        due_date = data.get("due_date")
        if due_date and isinstance(due_date, str):
            due_date = datetime.datetime.fromisoformat(due_date)

        return cls(
            id=data.get("id", str(uuid.uuid4())),
            front=data["front"],
            back=data["back"],
            language=data.get("language", "en"),
            created_at=created_at or datetime.datetime.now(),
            due_date=due_date,
            interval=float(data.get("interval", 1.0)),
            ease_factor=float(data.get("ease_factor", 2.5)),
            review_count=int(data.get("review_count", 0)),
            deck_id=data.get("deck_id"),
            tags=data.get("tags", []),
        )


@dataclass
class Deck:
    """
    Represents a collection of flashcards.

    Attributes:
        id: Unique identifier for the deck
        name: Name of the deck
        description: Description of the deck contents
        created_at: Timestamp when the deck was created
        user_id: ID of the user who owns this deck
        cards: List of flashcards in this deck
    """

    name: str
    description: str = ""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    created_at: datetime.datetime = field(default_factory=datetime.datetime.now)
    user_id: Optional[str] = None
    cards: List[Flashcard] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        """Convert the deck to a dictionary."""
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "user_id": self.user_id,
            "card_count": len(self.cards),
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Deck":
        """Create a deck from a dictionary."""
        # Convert string dates to datetime objects
        created_at = data.get("created_at")
        if created_at and isinstance(created_at, str):
            created_at = datetime.datetime.fromisoformat(created_at)

        return cls(
            id=data.get("id", str(uuid.uuid4())),
            name=data["name"],
            description=data.get("description", ""),
            created_at=created_at or datetime.datetime.now(),
            user_id=data.get("user_id"),
            cards=data.get("cards", []),
        )

    def add_card(self, card: Flashcard) -> None:
        """Add a card to this deck."""
        card.deck_id = self.id
        self.cards.append(card)

    def remove_card(self, card_id: str) -> Optional[Flashcard]:
        """Remove a card from this deck by ID."""
        for i, card in enumerate(self.cards):
            if card.id == card_id:
                return self.cards.pop(i)
        return None
