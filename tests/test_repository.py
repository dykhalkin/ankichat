"""
Tests for the repository layer.
"""

import pytest
from unittest.mock import MagicMock, patch

from src.models import Flashcard, Deck
from src.repository import SQLiteDeckRepository, SQLiteFlashcardRepository


@pytest.fixture
def mock_db():
    """Create a mock database for testing repositories."""
    return MagicMock()


@pytest.fixture
def deck_repo(mock_db):
    """Create a SQLiteDeckRepository with a mock database."""
    return SQLiteDeckRepository(mock_db)


@pytest.fixture
def card_repo(mock_db):
    """Create a SQLiteFlashcardRepository with a mock database."""
    return SQLiteFlashcardRepository(mock_db)


def test_deck_repository_create(deck_repo, mock_db):
    """Test creating a deck through the repository."""
    # Create a test deck
    deck = Deck(name="Test Deck")
    
    # Configure mock
    mock_db.create_deck.return_value = deck
    
    # Test create method
    result = deck_repo.create(deck)
    
    # Verify method was called with the deck
    mock_db.create_deck.assert_called_once_with(deck)
    
    # Verify result
    assert result == deck


def test_deck_repository_get(deck_repo, mock_db):
    """Test getting a deck through the repository."""
    # Create a test deck
    deck = Deck(name="Test Deck")
    
    # Configure mock
    mock_db.get_deck.return_value = deck
    
    # Test get method
    result = deck_repo.get("test-id")
    
    # Verify method was called with the ID
    mock_db.get_deck.assert_called_once_with("test-id")
    
    # Verify result
    assert result == deck


def test_deck_repository_update(deck_repo, mock_db):
    """Test updating a deck through the repository."""
    # Create a test deck
    deck = Deck(name="Test Deck")
    
    # Configure mock
    mock_db.update_deck.return_value = deck
    
    # Test update method
    result = deck_repo.update(deck)
    
    # Verify method was called with the deck
    mock_db.update_deck.assert_called_once_with(deck)
    
    # Verify result
    assert result == deck


def test_deck_repository_delete(deck_repo, mock_db):
    """Test deleting a deck through the repository."""
    # Configure mock
    mock_db.delete_deck.return_value = True
    
    # Test delete method
    result = deck_repo.delete("test-id")
    
    # Verify method was called with the ID
    mock_db.delete_deck.assert_called_once_with("test-id")
    
    # Verify result
    assert result is True


def test_deck_repository_list(deck_repo, mock_db):
    """Test listing decks through the repository."""
    # Create test decks
    decks = [Deck(name="Deck 1"), Deck(name="Deck 2")]
    
    # Configure mock
    mock_db.list_decks.return_value = decks
    
    # Test list method with user ID
    result = deck_repo.list("user-id")
    
    # Verify method was called with the user ID
    mock_db.list_decks.assert_called_once_with("user-id")
    
    # Verify result
    assert result == decks
    
    # Reset mock
    mock_db.list_decks.reset_mock()
    
    # Test list method without user ID
    result = deck_repo.list()
    
    # Verify method was called without arguments
    mock_db.list_decks.assert_called_once_with(None)


def test_flashcard_repository_create(card_repo, mock_db):
    """Test creating a flashcard through the repository."""
    # Create a test card
    card = Flashcard(front="Test Front", back="Test Back")
    
    # Configure mock
    mock_db.create_flashcard.return_value = card
    
    # Test create method
    result = card_repo.create(card)
    
    # Verify method was called with the card
    mock_db.create_flashcard.assert_called_once_with(card)
    
    # Verify result
    assert result == card


def test_flashcard_repository_get(card_repo, mock_db):
    """Test getting a flashcard through the repository."""
    # Create a test card
    card = Flashcard(front="Test Front", back="Test Back")
    
    # Configure mock
    mock_db.get_flashcard.return_value = card
    
    # Test get method
    result = card_repo.get("test-id")
    
    # Verify method was called with the ID
    mock_db.get_flashcard.assert_called_once_with("test-id")
    
    # Verify result
    assert result == card


def test_flashcard_repository_update(card_repo, mock_db):
    """Test updating a flashcard through the repository."""
    # Create a test card
    card = Flashcard(front="Test Front", back="Test Back")
    
    # Configure mock
    mock_db.update_flashcard.return_value = card
    
    # Test update method
    result = card_repo.update(card)
    
    # Verify method was called with the card
    mock_db.update_flashcard.assert_called_once_with(card)
    
    # Verify result
    assert result == card


def test_flashcard_repository_delete(card_repo, mock_db):
    """Test deleting a flashcard through the repository."""
    # Configure mock
    mock_db.delete_flashcard.return_value = True
    
    # Test delete method
    result = card_repo.delete("test-id")
    
    # Verify method was called with the ID
    mock_db.delete_flashcard.assert_called_once_with("test-id")
    
    # Verify result
    assert result is True


def test_flashcard_repository_get_by_deck(card_repo, mock_db):
    """Test getting flashcards by deck through the repository."""
    # Create test cards
    cards = [
        Flashcard(front="Card 1", back="Back 1"),
        Flashcard(front="Card 2", back="Back 2")
    ]
    
    # Configure mock
    mock_db.get_flashcards_by_deck.return_value = cards
    
    # Test get_by_deck method
    result = card_repo.get_by_deck("deck-id")
    
    # Verify method was called with the deck ID
    mock_db.get_flashcards_by_deck.assert_called_once_with("deck-id")
    
    # Verify result
    assert result == cards


def test_flashcard_repository_get_due(card_repo, mock_db):
    """Test getting due flashcards through the repository."""
    # Create test cards
    cards = [
        Flashcard(front="Card 1", back="Back 1"),
        Flashcard(front="Card 2", back="Back 2")
    ]
    
    # Configure mock
    mock_db.get_due_flashcards.return_value = cards
    
    # Test get_due method
    result = card_repo.get_due("user-id", 5)
    
    # Verify method was called with the arguments
    mock_db.get_due_flashcards.assert_called_once_with("user-id", 5)
    
    # Verify result
    assert result == cards