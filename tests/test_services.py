"""
Tests for the service layer.
"""

import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.models import Deck, Flashcard
from src.services import DeckService, FlashcardService


@pytest.fixture
def mock_flashcard_repo():
    """Create a mock flashcard repository."""
    repo = MagicMock()
    repo.create = MagicMock()
    repo.get = MagicMock()
    repo.update = MagicMock()
    repo.delete = MagicMock()
    return repo


@pytest.fixture
def mock_deck_repo():
    """Create a mock deck repository."""
    repo = MagicMock()
    repo.create = MagicMock()
    repo.get = MagicMock()
    repo.update = MagicMock()
    repo.delete = MagicMock()
    repo.list = MagicMock()
    return repo


@pytest.fixture
def mock_llm_client():
    """Create a mock LLM client."""
    client = MagicMock()
    client.detect_language = AsyncMock()
    client.generate_flashcard_content = AsyncMock()
    return client


@pytest.fixture
def flashcard_service(mock_flashcard_repo, mock_deck_repo, mock_llm_client):
    """Create a FlashcardService with mock dependencies."""
    return FlashcardService(mock_flashcard_repo, mock_deck_repo, mock_llm_client)


@pytest.fixture
def deck_service(mock_deck_repo, mock_flashcard_repo, mock_llm_client):
    """Create a DeckService with mock dependencies."""
    return DeckService(mock_deck_repo, mock_flashcard_repo, mock_llm_client)


@pytest.mark.asyncio
async def test_process_new_card_text(flashcard_service, mock_llm_client):
    """Test processing user input for a new flashcard."""
    # Configure mocks
    mock_llm_client.detect_language.return_value = ("es", 0.87)

    mock_llm_client.generate_flashcard_content.return_value = {
        "word": "hola",
        "language_code": "es",
        "definition": "Hello or hi in Spanish",
        "example_sentence": "¡Hola! ¿Cómo estás?",
        "pronunciation_guide": "ˈo.la",
        "part_of_speech": "interjection",
        "notes": "Informal greeting",
    }

    # Call the service
    result = await flashcard_service.process_new_card_text("hola", "user123")

    # Verify the LLM client was called correctly
    mock_llm_client.detect_language.assert_called_once_with("hola")
    mock_llm_client.generate_flashcard_content.assert_called_once_with("hola", "es")

    # Check the result structure
    assert result["input_text"] == "hola"
    assert result["user_id"] == "user123"
    assert result["language"]["code"] == "es"
    assert result["language"]["confidence"] == 0.87
    assert "preview_id" in result

    # Check the content was passed through
    assert result["content"]["word"] == "hola"
    assert result["content"]["definition"] == "Hello or hi in Spanish"
    assert result["content"]["example_sentence"] == "¡Hola! ¿Cómo estás?"


@pytest.mark.asyncio
async def test_create_flashcard_from_preview(
    flashcard_service, mock_deck_repo, mock_flashcard_repo
):
    """Test creating a flashcard from a preview."""
    # Mock deck and flashcard
    deck = Deck(id="deck123", name="Test Deck")
    mock_deck_repo.get.return_value = deck

    created_card = Flashcard(
        id="card123", front="Test Front", back="Test Back", language="en", deck_id="deck123"
    )
    mock_flashcard_repo.create.return_value = created_card

    # Test with user edits
    user_edits = {"front": "Custom Front", "back": "Custom Back", "language": "fr"}

    card = await flashcard_service.create_flashcard_from_preview(
        preview_id="preview123", deck_id="deck123", user_edits=user_edits
    )

    # Verify repository calls
    mock_deck_repo.get.assert_called_once_with("deck123")
    mock_flashcard_repo.create.assert_called_once()

    # Check that edits were applied
    create_call_args = mock_flashcard_repo.create.call_args[0][0]
    assert create_call_args.front == "Custom Front"
    assert create_call_args.back == "Custom Back"
    assert create_call_args.language == "fr"
    assert create_call_args.deck_id == "deck123"

    # Check returned card
    assert card.id == "card123"


@pytest.mark.asyncio
async def test_create_flashcard_from_preview_deck_not_found(flashcard_service, mock_deck_repo):
    """Test error handling when deck is not found."""
    # Mock no deck found
    mock_deck_repo.get.return_value = None

    # Expect an error
    with pytest.raises(ValueError) as excinfo:
        await flashcard_service.create_flashcard_from_preview(
            preview_id="preview123", deck_id="nonexistent"
        )

    assert "Deck not found" in str(excinfo.value)


def test_format_preview_message(flashcard_service):
    """Test formatting a preview message for display."""
    # Create a sample preview
    preview = {
        "input_text": "hola",
        "user_id": "user123",
        "language": {"code": "es", "confidence": 0.87},
        "content": {
            "word": "hola",
            "language_code": "es",
            "definition": "Hello or hi in Spanish",
            "example_sentence": "¡Hola! ¿Cómo estás?",
            "pronunciation_guide": "ˈo.la",
            "part_of_speech": "interjection",
            "notes": "Informal greeting",
        },
        "preview_id": "preview123",
    }

    # Format the message
    message = flashcard_service.format_preview_message(preview)

    # Check the message contains all the content
    assert "Flashcard Preview" in message
    assert "hola" in message
    assert "es (Confidence: 0.87)" in message
    assert "Hello or hi in Spanish" in message
    assert "¡Hola! ¿Cómo estás?" in message
    assert "ˈo.la" in message
    assert "interjection" in message
    assert "Informal greeting" in message


def test_get_user_decks(deck_service, mock_deck_repo):
    """Test getting all decks for a user."""
    # Mock decks
    decks = [
        Deck(id="deck1", name="Deck 1", user_id="user123"),
        Deck(id="deck2", name="Deck 2", user_id="user123"),
    ]
    mock_deck_repo.list.return_value = decks

    # Get decks
    result = deck_service.get_user_decks("user123")

    # Verify
    mock_deck_repo.list.assert_called_once_with("user123")
    assert len(result) == 2
    assert result[0].name == "Deck 1"
    assert result[1].name == "Deck 2"


def test_create_deck(deck_service, mock_deck_repo):
    """Test creating a new deck."""
    # Mock created deck
    created_deck = Deck(
        id="new_deck_id", name="Test Deck", description="Test Description", user_id="user123"
    )
    mock_deck_repo.create.return_value = created_deck

    # Create deck
    result = deck_service.create_deck(
        name="Test Deck", user_id="user123", description="Test Description"
    )

    # Verify
    mock_deck_repo.create.assert_called_once()
    create_args = mock_deck_repo.create.call_args[0][0]
    assert create_args.name == "Test Deck"
    assert create_args.description == "Test Description"
    assert create_args.user_id == "user123"

    assert result.id == "new_deck_id"
