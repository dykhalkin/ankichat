"""
Tests for the Telegram bot command handlers.
"""

import json
from unittest.mock import AsyncMock, MagicMock, call, patch

import pytest
from telegram import CallbackQuery, Chat, InlineKeyboardMarkup, Message, Update, User
from telegram.ext import ConversationHandler

from src.handlers import (
    AWAITING_CARD_TEXT,
    AWAITING_CONFIRMATION,
    AWAITING_DECK_SELECTION,
    CANCEL_PREFIX,
    CONFIRM_PREFIX,
    DECK_PREFIX,
    EDIT_PREFIX,
    cancel_command,
    handle_deck_selection,
    handle_preview_callback,
    help_command,
    new_card_command,
    process_card_text,
    start_command,
)


@pytest.fixture
def mock_user():
    """Create a mock user."""
    return User(id=1, first_name="Test", is_bot=False, username="testuser")


@pytest.fixture
def mock_update(mock_user):
    """Create a mock update object for testing handlers."""
    chat = Chat(id=1, type="private")

    # Create a mock message with a mock reply_text method
    message = MagicMock()
    message.message_id = 1
    message.chat = chat
    message.from_user = mock_user
    message.reply_text = AsyncMock()
    message.text = "Test message"

    # Create a mock update
    update = MagicMock(spec=Update)
    update.update_id = 1
    update.message = message
    update.effective_user = mock_user
    update.effective_chat = chat
    update.callback_query = None

    return update


@pytest.fixture
def mock_context():
    """Create a mock context object for testing handlers."""
    context = MagicMock()
    context.user_data = {}
    return context


@pytest.fixture
def mock_callback_query(mock_user):
    """Create a mock callback query."""
    query = MagicMock(spec=CallbackQuery)

    # Create a message with an AsyncMock for edit_text
    message = MagicMock()
    edit_text_mock = AsyncMock()
    # Configure the AsyncMock to return a value when awaited
    edit_text_mock.return_value = "edited message"
    message.edit_text = edit_text_mock

    query.message = message
    query.data = "test_callback_data"
    query.from_user = mock_user

    # Create an AsyncMock for answer
    answer_mock = AsyncMock()
    answer_mock.return_value = None
    query.answer = answer_mock

    return query


@pytest.fixture
def mock_update_with_callback(mock_update, mock_callback_query):
    """Create a mock update with a callback query."""
    mock_update.callback_query = mock_callback_query
    mock_update.effective_user = mock_callback_query.from_user
    return mock_update


@pytest.fixture
def mock_flashcard_service():
    """Create a mock flashcard service."""
    with patch("src.handlers._get_flashcard_service") as mock_get_service:
        service = MagicMock()

        # Configure AsyncMock for process_new_card_text
        process_mock = AsyncMock()
        process_mock.return_value = {
            "input_text": "test",
            "user_id": "1",
            "language": {"code": "en", "confidence": 0.9},
            "content": {},
            "preview_id": "preview123",
        }
        service.process_new_card_text = process_mock

        # Configure AsyncMock for create_flashcard_from_preview
        create_mock = AsyncMock()
        create_mock.return_value = MagicMock(id="card123", front="test")
        service.create_flashcard_from_preview = create_mock

        # Regular mock for format_preview_message
        service.format_preview_message = MagicMock(return_value="Formatted message")

        mock_get_service.return_value = service
        yield service


@pytest.fixture
def mock_deck_service():
    """Create a mock deck service."""
    with patch("src.handlers._get_deck_service") as mock_get_service:
        service = MagicMock()
        service.get_user_decks = MagicMock()
        service.create_deck = MagicMock()
        mock_get_service.return_value = service
        yield service


@pytest.mark.asyncio
async def test_start_command(mock_update, mock_context):
    """Test that the start command responds with a welcome message."""
    # Call the handler
    await start_command(mock_update, mock_context)

    # Check if reply_text was called
    assert mock_update.message.reply_text.called

    # Check message content
    call_args = mock_update.message.reply_text.call_args[0][0]
    assert "Welcome to the Anki Flashcards Bot" in call_args
    assert "Hello, Test" in call_args  # Should include user's first name
    assert "/new" in call_args  # Should mention the new card command
    assert "/review" in call_args  # Should mention the review command


@pytest.mark.asyncio
async def test_help_command(mock_update, mock_context):
    """Test that the help command responds with help information."""
    # Call the handler
    await help_command(mock_update, mock_context)

    # Check if reply_text was called
    assert mock_update.message.reply_text.called

    # Check message content and parse mode
    call_args = mock_update.message.reply_text.call_args[0][0]
    call_kwargs = mock_update.message.reply_text.call_args[1]

    assert "AnkiChat Bot Help" in call_args
    assert "Creating Flashcards" in call_args
    assert "Reviewing Cards" in call_args
    assert "Spaced Repetition" in call_args
    assert call_kwargs.get("parse_mode") == "Markdown"


@pytest.mark.asyncio
async def test_new_card_command(mock_update, mock_context):
    """Test that the new card command starts the flashcard creation workflow."""
    # Call the handler
    result = await new_card_command(mock_update, mock_context)

    # Check if reply_text was called with the right message
    mock_update.message.reply_text.assert_called_once()
    call_args = mock_update.message.reply_text.call_args[0][0]
    assert "enter the word or phrase" in call_args

    # Check the returned state
    assert result == AWAITING_CARD_TEXT


@pytest.mark.asyncio
async def test_process_card_text(mock_update, mock_context, mock_flashcard_service):
    """Test processing user input for a new flashcard."""
    # Setup mocks
    mock_update.message.text = "hola"
    processing_message = AsyncMock()
    mock_update.message.reply_text.return_value = processing_message

    preview = {
        "input_text": "hola",
        "user_id": "1",
        "language": {"code": "es", "confidence": 0.95},
        "content": {
            "word": "hola",
            "definition": "Hello in Spanish",
            "example_sentence": "¡Hola! ¿Cómo estás?",
            "pronunciation_guide": "ˈo.la",
            "part_of_speech": "interjection",
            "notes": "Common greeting",
        },
        "preview_id": "preview123",
    }

    mock_flashcard_service.process_new_card_text.return_value = preview
    mock_flashcard_service.format_preview_message.return_value = "Formatted message"

    # Call the handler
    result = await process_card_text(mock_update, mock_context)

    # Check if the service was called correctly
    mock_flashcard_service.process_new_card_text.assert_called_once_with("hola", "1")

    # Check if the preview was stored in context
    assert mock_context.user_data["preview"] == preview

    # Check if the message was edited with the preview and inline keyboard
    processing_message.edit_text.assert_called_once()
    call_args = processing_message.edit_text.call_args
    assert call_args[0][0] == "Formatted message"
    assert "reply_markup" in call_args[1]
    assert "parse_mode" in call_args[1]

    # Check the returned state
    assert result == AWAITING_CONFIRMATION


@pytest.mark.asyncio
async def test_handle_preview_callback_confirm_simple(
    mock_update_with_callback, mock_context, mock_deck_service
):
    """Test handling confirmation of a preview (simplified version)."""
    # Setup mocks
    mock_update_with_callback.callback_query.data = f"{CONFIRM_PREFIX}preview123"

    # Mock deck service
    decks = [MagicMock(id="deck1", name="Deck 1"), MagicMock(id="deck2", name="Deck 2")]
    mock_deck_service.get_user_decks.return_value = decks

    # Call the handler
    result = await handle_preview_callback(mock_update_with_callback, mock_context)

    # Check if preview ID was stored in context
    assert mock_context.user_data["confirmed_preview_id"] == "preview123"

    # Check the returned state
    assert result == AWAITING_DECK_SELECTION


@pytest.mark.asyncio
async def test_handle_preview_callback_cancel_simple(mock_update_with_callback, mock_context):
    """Test handling cancellation from the preview (simplified version)."""
    # Setup mocks
    mock_update_with_callback.callback_query.data = f"{CANCEL_PREFIX}preview123"

    # Call the handler
    result = await handle_preview_callback(mock_update_with_callback, mock_context)

    # Check the returned state
    assert result == ConversationHandler.END


@pytest.mark.asyncio
async def test_handle_deck_selection_simple(
    mock_update_with_callback, mock_context, mock_flashcard_service
):
    """Test handling deck selection (simplified version)."""
    # Setup mocks
    mock_update_with_callback.callback_query.data = f"{DECK_PREFIX}deck123"
    mock_context.user_data["confirmed_preview_id"] = "preview123"
    mock_context.user_data["preview"] = {
        "content": {
            "word": "hola",
            "language_code": "es",
            "definition": "Hello in Spanish",
            "example_sentence": "¡Hola!",
            "pronunciation_guide": "ˈo.la",
            "part_of_speech": "interjection",
            "notes": "Common greeting",
        }
    }

    created_card = MagicMock(id="card123", front="hola")
    mock_flashcard_service.create_flashcard_from_preview.return_value = created_card

    # Call the handler
    result = await handle_deck_selection(mock_update_with_callback, mock_context)

    # Check the returned state
    assert result == ConversationHandler.END


@pytest.mark.asyncio
async def test_cancel_command(mock_update, mock_context):
    """Test cancelling the conversation."""
    # Call the handler
    result = await cancel_command(mock_update, mock_context)

    # Check if reply_text was called with cancellation message
    mock_update.message.reply_text.assert_called_once()
    assert "cancelled" in mock_update.message.reply_text.call_args[0][0].lower()

    # Check the returned state
    assert result == ConversationHandler.END


def test_format_card_back():
    """Test formatting the back of a flashcard."""
    from src.handlers import _format_card_back

    # Test with complete content
    content = {
        "definition": "Hello in Spanish",
        "example_sentence": "¡Hola!",
        "pronunciation_guide": "ˈo.la",
        "part_of_speech": "interjection",
        "notes": "Common greeting",
    }

    back = _format_card_back(content)

    assert "*Definition:* Hello in Spanish" in back
    assert "*Example:* ¡Hola!" in back
    assert "*Pronunciation:* ˈo.la" in back
    assert "*Part of Speech:* interjection" in back
    assert "*Notes:* Common greeting" in back

    # Test with missing fields
    content = {"definition": "Hello in Spanish", "example_sentence": "¡Hola!"}

    back = _format_card_back(content)

    assert "*Definition:* Hello in Spanish" in back
    assert "*Example:* ¡Hola!" in back
    assert "*Pronunciation:* N/A" in back
    assert "*Part of Speech:* N/A" in back
    assert "*Notes:*" not in back


@pytest.mark.asyncio
async def test_handle_preview_callback_exists():
    """Test that the handle_preview_callback function exists and can be imported."""
    from src.handlers import handle_preview_callback

    assert callable(handle_preview_callback)


@pytest.mark.asyncio
async def test_handle_deck_selection_exists():
    """Test that the handle_deck_selection function exists and can be imported."""
    from src.handlers import handle_deck_selection

    assert callable(handle_deck_selection)
