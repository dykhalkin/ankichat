"""
Tests for the SQLite database implementation.
"""

import os
import datetime
import pytest
import tempfile
import sqlite3
from src.database import Database
from src.models import Flashcard, Deck


@pytest.fixture
def test_db():
    """Create a temporary test database."""
    # Create a temporary directory
    with tempfile.TemporaryDirectory() as temp_dir:
        db_path = os.path.join(temp_dir, "test.db")
        # Create and return the database
        db = Database(db_path)
        yield db
        # Close the database (cleanup will happen automatically)
        db.close()


def test_database_initialization(test_db):
    """Test that the database is properly initialized."""
    # Check that the database file exists
    assert os.path.exists(test_db.db_path)
    
    # Check that the connection is established
    assert test_db.conn is not None
    
    # Try a simple query to verify the connection works
    cursor = test_db.conn.cursor()
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
    tables = cursor.fetchall()
    
    # Check that our tables exist
    table_names = [row['name'] for row in tables]
    assert "decks" in table_names
    assert "flashcards" in table_names


def test_deck_crud_operations(test_db):
    """Test create, read, update, and delete operations for decks."""
    # Create a test deck
    deck = Deck(name="Test Deck", description="A deck for testing")
    
    # Test create
    created_deck = test_db.create_deck(deck)
    assert created_deck.id == deck.id
    assert created_deck.name == "Test Deck"
    
    # Test read
    retrieved_deck = test_db.get_deck(deck.id)
    assert retrieved_deck is not None
    assert retrieved_deck.id == deck.id
    assert retrieved_deck.name == "Test Deck"
    assert retrieved_deck.description == "A deck for testing"
    
    # Test update
    deck.name = "Updated Deck"
    updated_deck = test_db.update_deck(deck)
    assert updated_deck.name == "Updated Deck"
    
    # Verify update
    retrieved_deck = test_db.get_deck(deck.id)
    assert retrieved_deck.name == "Updated Deck"
    
    # Test delete
    assert test_db.delete_deck(deck.id) is True
    
    # Verify delete
    assert test_db.get_deck(deck.id) is None
    
    # Test delete non-existent deck
    assert test_db.delete_deck("non-existent-id") is False


def test_flashcard_crud_operations(test_db):
    """Test create, read, update, and delete operations for flashcards."""
    # Create a test deck first (for foreign key constraint)
    deck = Deck(name="Card Test Deck")
    test_db.create_deck(deck)
    
    # Create a test flashcard
    card = Flashcard(
        front="Test Front",
        back="Test Back",
        deck_id=deck.id
    )
    
    # Test create
    created_card = test_db.create_flashcard(card)
    assert created_card.id == card.id
    assert created_card.front == "Test Front"
    assert created_card.back == "Test Back"
    
    # Test read
    retrieved_card = test_db.get_flashcard(card.id)
    assert retrieved_card is not None
    assert retrieved_card.id == card.id
    assert retrieved_card.front == "Test Front"
    assert retrieved_card.back == "Test Back"
    assert retrieved_card.deck_id == deck.id
    
    # Test update
    card.front = "Updated Front"
    card.back = "Updated Back"
    card.interval = 2.5
    updated_card = test_db.update_flashcard(card)
    assert updated_card.front == "Updated Front"
    assert updated_card.back == "Updated Back"
    assert updated_card.interval == 2.5
    
    # Verify update
    retrieved_card = test_db.get_flashcard(card.id)
    assert retrieved_card.front == "Updated Front"
    
    # Test delete
    assert test_db.delete_flashcard(card.id) is True
    
    # Verify delete
    assert test_db.get_flashcard(card.id) is None
    
    # Test delete non-existent card
    assert test_db.delete_flashcard("non-existent-id") is False


def test_deck_with_cards(test_db):
    """Test retrieving a deck with its cards."""
    # Create a test deck
    deck = Deck(name="Deck with Cards")
    test_db.create_deck(deck)
    
    # Create some flashcards in the deck
    card1 = Flashcard(front="Card 1 Front", back="Card 1 Back", deck_id=deck.id)
    card2 = Flashcard(front="Card 2 Front", back="Card 2 Back", deck_id=deck.id)
    
    test_db.create_flashcard(card1)
    test_db.create_flashcard(card2)
    
    # Retrieve the deck with its cards
    retrieved_deck = test_db.get_deck(deck.id)
    
    # Verify the deck has the cards
    assert len(retrieved_deck.cards) == 2
    
    # Verify card contents
    fronts = [card.front for card in retrieved_deck.cards]
    assert "Card 1 Front" in fronts
    assert "Card 2 Front" in fronts


def test_cascade_delete(test_db):
    """Test that deleting a deck also deletes its cards (foreign key cascade)."""
    # Create a test deck
    deck = Deck(name="Cascade Test Deck")
    test_db.create_deck(deck)
    
    # Create some flashcards in the deck
    card1 = Flashcard(front="Cascade Card 1", back="Back 1", deck_id=deck.id)
    card2 = Flashcard(front="Cascade Card 2", back="Back 2", deck_id=deck.id)
    
    test_db.create_flashcard(card1)
    test_db.create_flashcard(card2)
    
    # Delete the deck
    test_db.delete_deck(deck.id)
    
    # Verify the cards were also deleted
    assert test_db.get_flashcard(card1.id) is None
    assert test_db.get_flashcard(card2.id) is None


def test_get_flashcards_by_deck(test_db):
    """Test retrieving flashcards by deck ID."""
    # Create test decks
    deck1 = Deck(name="Deck 1")
    deck2 = Deck(name="Deck 2")
    
    test_db.create_deck(deck1)
    test_db.create_deck(deck2)
    
    # Create cards in each deck
    card1 = Flashcard(front="Deck 1 Card", back="Back", deck_id=deck1.id)
    card2 = Flashcard(front="Deck 2 Card 1", back="Back", deck_id=deck2.id)
    card3 = Flashcard(front="Deck 2 Card 2", back="Back", deck_id=deck2.id)
    
    test_db.create_flashcard(card1)
    test_db.create_flashcard(card2)
    test_db.create_flashcard(card3)
    
    # Get cards for deck 1
    deck1_cards = test_db.get_flashcards_by_deck(deck1.id)
    assert len(deck1_cards) == 1
    assert deck1_cards[0].front == "Deck 1 Card"
    
    # Get cards for deck 2
    deck2_cards = test_db.get_flashcards_by_deck(deck2.id)
    assert len(deck2_cards) == 2
    fronts = [card.front for card in deck2_cards]
    assert "Deck 2 Card 1" in fronts
    assert "Deck 2 Card 2" in fronts


def test_list_decks(test_db):
    """Test listing all decks and filtering by user."""
    # Create test decks
    deck1 = Deck(name="User 1 Deck", user_id="user1")
    deck2 = Deck(name="User 2 Deck", user_id="user2")
    deck3 = Deck(name="User 1 Second Deck", user_id="user1")
    
    test_db.create_deck(deck1)
    test_db.create_deck(deck2)
    test_db.create_deck(deck3)
    
    # List all decks
    all_decks = test_db.list_decks()
    assert len(all_decks) == 3
    
    # Filter by user
    user1_decks = test_db.list_decks(user_id="user1")
    assert len(user1_decks) == 2
    
    # Verify deck names
    names = [deck.name for deck in user1_decks]
    assert "User 1 Deck" in names
    assert "User 1 Second Deck" in names


def test_get_due_flashcards(test_db):
    """Test retrieving flashcards that are due for review."""
    # Create test deck
    deck = Deck(name="Due Cards Test", user_id="user1")
    test_db.create_deck(deck)
    
    # Create cards with different due dates
    now = datetime.datetime.now()
    past_date = now - datetime.timedelta(days=1)
    future_date = now + datetime.timedelta(days=1)
    
    # Card that is due (past due date)
    card1 = Flashcard(
        front="Due Card",
        back="Back",
        deck_id=deck.id,
        due_date=past_date
    )
    
    # Card that is not yet due
    card2 = Flashcard(
        front="Not Due Card",
        back="Back",
        deck_id=deck.id,
        due_date=future_date
    )
    
    # Card with no due date (should be treated as due)
    card3 = Flashcard(
        front="No Due Date Card",
        back="Back",
        deck_id=deck.id
    )
    
    test_db.create_flashcard(card1)
    test_db.create_flashcard(card2)
    test_db.create_flashcard(card3)
    
    # Get due cards
    due_cards = test_db.get_due_flashcards("user1")
    
    # Verify only the due cards are returned
    assert len(due_cards) == 2
    
    # Check that the future card is not included
    fronts = [card.front for card in due_cards]
    assert "Due Card" in fronts
    assert "No Due Date Card" in fronts
    assert "Not Due Card" not in fronts