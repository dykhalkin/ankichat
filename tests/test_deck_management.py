"""
Tests for deck management functionality.
"""

import pytest
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock

from src.models import Flashcard, Deck
from src.services import DeckService


class TestDeckManagement:
    """Tests for deck management functionality."""
    
    @pytest.fixture
    def deck_repo_mock(self):
        """Create a mock deck repository."""
        mock = MagicMock()
        
        # Setup some test decks
        mock.get.return_value = Deck(
            id="deck-123",
            name="Test Deck",
            description="Test description",
            user_id="user-123",
            created_at=datetime.now()
        )
        
        mock.list.return_value = [
            Deck(id="deck-123", name="Test Deck", user_id="user-123"),
            Deck(id="deck-456", name="Another Deck", user_id="user-123")
        ]
        
        return mock
    
    @pytest.fixture
    def flashcard_repo_mock(self):
        """Create a mock flashcard repository."""
        mock = MagicMock()
        
        # Setup some test cards
        test_card = Flashcard(
            id="card-123", 
            front="Test Front", 
            back="Test Back", 
            deck_id="deck-123"
        )
        mock.get.return_value = test_card
        mock.get_by_deck.return_value = [test_card]
        
        return mock
    
    @pytest.fixture
    def llm_client_mock(self):
        """Create a mock LLM client."""
        mock = AsyncMock()
        mock.client = AsyncMock()
        mock.suggest_deck_name = AsyncMock(return_value="Suggested Deck")
        mock.detect_category = AsyncMock(return_value="Suggested Category")
        
        return mock
    
    @pytest.fixture
    def deck_service(self, deck_repo_mock, flashcard_repo_mock, llm_client_mock):
        """Create a DeckService with mock dependencies."""
        return DeckService(deck_repo_mock, flashcard_repo_mock, llm_client_mock)
    
    def test_get_user_decks(self, deck_service, deck_repo_mock):
        """Test retrieving all decks for a user."""
        # Execute
        decks = deck_service.get_user_decks("user-123")
        
        # Verify
        deck_repo_mock.list.assert_called_once_with("user-123")
        assert len(decks) == 2
        assert decks[0].name == "Test Deck"
        assert decks[1].name == "Another Deck"
    
    def test_create_deck(self, deck_service, deck_repo_mock):
        """Test creating a new deck."""
        # Setup
        deck_repo_mock.create.return_value = Deck(
            id="new-deck-123",
            name="New Deck",
            description="New description",
            user_id="user-123"
        )
        
        # Execute
        deck = deck_service.create_deck("New Deck", "user-123", "New description")
        
        # Verify
        assert deck.id == "new-deck-123"
        assert deck.name == "New Deck"
        assert deck.description == "New description"
        assert deck.user_id == "user-123"
        
        # Verify repository call
        deck_repo_mock.create.assert_called_once()
        created_deck = deck_repo_mock.create.call_args[0][0]
        assert created_deck.name == "New Deck"
        assert created_deck.description == "New description"
        assert created_deck.user_id == "user-123"
    
    def test_rename_deck(self, deck_service, deck_repo_mock):
        """Test renaming a deck."""
        # Setup
        test_deck = Deck(
            id="deck-123",
            name="Test Deck",
            description="Test description",
            user_id="user-123"
        )
        deck_repo_mock.get.return_value = test_deck
        deck_repo_mock.update.return_value = Deck(
            id="deck-123",
            name="Renamed Deck",
            description="Test description",
            user_id="user-123"
        )
        
        # Execute
        updated_deck = deck_service.rename_deck("deck-123", "Renamed Deck")
        
        # Verify
        assert updated_deck.name == "Renamed Deck"
        deck_repo_mock.get.assert_called_once_with("deck-123")
        deck_repo_mock.update.assert_called_once()
    
    def test_delete_deck(self, deck_service, deck_repo_mock):
        """Test deleting a deck."""
        # Setup
        deck_repo_mock.delete.return_value = True
        
        # Execute
        result = deck_service.delete_deck("deck-123")
        
        # Verify
        assert result is True
        deck_repo_mock.delete.assert_called_once_with("deck-123")
    
    def test_get_deck_with_cards(self, deck_service, deck_repo_mock, flashcard_repo_mock):
        """Test getting a deck with all its cards."""
        # Execute
        deck = deck_service.get_deck_with_cards("deck-123")
        
        # Verify
        deck_repo_mock.get.assert_called_once_with("deck-123")
        flashcard_repo_mock.get_by_deck.assert_called_once_with("deck-123")
        assert deck.id == "deck-123"
        assert len(deck.cards) == 1
        assert deck.cards[0].id == "card-123"
    
    def test_move_card_to_deck(self, deck_service, flashcard_repo_mock, deck_repo_mock):
        """Test moving a card from one deck to another."""
        # Setup
        test_card = Flashcard(
            id="card-123", 
            front="Test Front", 
            back="Test Back", 
            deck_id="deck-123"
        )
        flashcard_repo_mock.get.return_value = test_card
        flashcard_repo_mock.update.return_value = Flashcard(
            id="card-123", 
            front="Test Front", 
            back="Test Back", 
            deck_id="deck-456"
        )
        
        target_deck = Deck(id="deck-456", name="Target Deck")
        deck_repo_mock.get.return_value = target_deck
        
        # Execute
        updated_card = deck_service.move_card_to_deck("card-123", "deck-456")
        
        # Verify
        assert updated_card.deck_id == "deck-456"
        flashcard_repo_mock.get.assert_called_once_with("card-123")
        deck_repo_mock.get.assert_called_once_with("deck-456")
        flashcard_repo_mock.update.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_suggest_deck_name(self, deck_service, llm_client_mock):
        """Test suggesting a deck name based on content."""
        # Setup
        content = "Front: Capital of France\nBack: Paris"
        llm_client_mock.client.chat.completions.create.return_value.choices = [
            MagicMock(message=MagicMock(content="Geography"))
        ]
        
        # Execute
        suggested_name = await deck_service.suggest_deck_name(content)
        
        # Verify
        assert suggested_name == "Geography"
        llm_client_mock.client.chat.completions.create.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_suggest_deck_name_no_llm(self, deck_service):
        """Test suggesting a deck name when LLM is not available."""
        # Setup
        deck_service.llm_client = None
        content = "Front: Capital of France\nBack: Paris"
        
        # Execute
        suggested_name = await deck_service.suggest_deck_name(content)
        
        # Verify
        assert suggested_name == "New Deck"