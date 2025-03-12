"""
Core data models for the Anki Flashcards system.

This module defines the data structures for flashcards and decks.
"""

import datetime
import uuid
from dataclasses import dataclass, field
from typing import List, Optional


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