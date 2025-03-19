"""
Tests for data models (Flashcard and Deck).
"""

import datetime

import pytest

from src.models import Deck, Flashcard


def test_flashcard_creation():
    """Test that a flashcard can be created with correct attributes."""
    # Create a basic flashcard
    card = Flashcard(front="What is the capital of France?", back="Paris")

    # Verify required attributes
    assert card.front == "What is the capital of France?"
    assert card.back == "Paris"
    assert card.language == "en"  # Default value

    # Verify auto-generated ID
    assert card.id is not None
    assert isinstance(card.id, str)

    # Verify SRS metadata defaults
    assert card.interval == 1.0
    assert card.ease_factor == 2.5
    assert card.review_count == 0
    assert card.due_date is None

    # Verify creation timestamp
    assert isinstance(card.created_at, datetime.datetime)


def test_flashcard_with_custom_attributes():
    """Test that a flashcard can be created with custom attributes."""
    # Create card with custom attributes
    due_date = datetime.datetime.now() + datetime.timedelta(days=3)
    card = Flashcard(
        front="Bonjour",
        back="Hello",
        language="fr",
        interval=2.5,
        ease_factor=2.2,
        review_count=5,
        due_date=due_date,
        deck_id="test-deck-id",
    )

    # Verify custom attributes
    assert card.language == "fr"
    assert card.interval == 2.5
    assert card.ease_factor == 2.2
    assert card.review_count == 5
    assert card.due_date == due_date
    assert card.deck_id == "test-deck-id"


def test_deck_creation():
    """Test that a deck can be created with correct attributes."""
    # Create a basic deck
    deck = Deck(name="French Vocabulary")

    # Verify required attributes
    assert deck.name == "French Vocabulary"
    assert deck.description == ""  # Default value

    # Verify auto-generated ID
    assert deck.id is not None
    assert isinstance(deck.id, str)

    # Verify cards list is empty initially
    assert len(deck.cards) == 0

    # Verify creation timestamp
    assert isinstance(deck.created_at, datetime.datetime)


def test_deck_with_cards():
    """Test that a deck can contain flashcards."""
    # Create a deck
    deck = Deck(name="French Vocabulary", description="Basic French words")

    # Create some cards
    card1 = Flashcard(front="Bonjour", back="Hello", deck_id=deck.id)
    card2 = Flashcard(front="Merci", back="Thank you", deck_id=deck.id)

    # Add cards to deck
    deck.cards.append(card1)
    deck.cards.append(card2)

    # Verify deck contains the cards
    assert len(deck.cards) == 2
    assert deck.cards[0].front == "Bonjour"
    assert deck.cards[1].front == "Merci"

    # Verify cards reference the deck
    for card in deck.cards:
        assert card.deck_id == deck.id
