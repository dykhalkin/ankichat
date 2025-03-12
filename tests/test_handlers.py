"""
Tests for the Telegram bot command handlers.
"""

import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from telegram import Update, User, Message, Chat

from src.handlers import start_command, help_command

@pytest.fixture
def mock_update():
    """Create a mock update object for testing handlers."""
    user = User(id=1, first_name="Test", is_bot=False, username="testuser")
    chat = Chat(id=1, type="private")
    
    # Create a mock message with a mock reply_text method
    message = MagicMock()
    message.message_id = 1
    message.chat = chat
    message.from_user = user
    message.reply_text = AsyncMock()
    
    # Create a mock update
    update = MagicMock(spec=Update)
    update.update_id = 1
    update.message = message
    update.effective_user = user
    update.effective_chat = chat
    
    return update

@pytest.fixture
def mock_context():
    """Create a mock context object for testing handlers."""
    return AsyncMock()

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