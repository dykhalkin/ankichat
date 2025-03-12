"""
Tests for the bot module that sets up the Telegram bot.
"""

import pytest
from unittest.mock import patch, MagicMock
from telegram.ext import Application, CommandHandler

from src.bot import AnkiChatBot, create_bot

@pytest.fixture
def mock_application():
    """Create a mock Application object for testing."""
    app_mock = MagicMock()
    app_mock.add_handler = MagicMock()
    app_mock.add_error_handler = MagicMock()
    app_mock.run_polling = MagicMock()
    return app_mock

def test_ankichatbot_setup(mock_application):
    """Test that the bot correctly sets up handlers."""
    with patch('src.bot.Application.builder') as mock_builder:
        # Configure the mock
        builder_mock = MagicMock()
        mock_builder.return_value = builder_mock
        token_mock = MagicMock()
        builder_mock.token.return_value = token_mock
        token_mock.build.return_value = mock_application
        
        # Create bot
        bot = AnkiChatBot().setup()
        
        # Check that handlers were added
        assert mock_application.add_handler.call_count >= 2  # At least start and help
        assert mock_application.add_error_handler.call_count == 1
        
        # Check return value
        assert isinstance(bot, AnkiChatBot)

def test_create_bot():
    """Test the create_bot factory function."""
    with patch('src.bot.AnkiChatBot') as mock_bot_class:
        mock_bot = MagicMock()
        mock_bot_class.return_value = mock_bot
        mock_bot.setup.return_value = "setup_called"
        
        result = create_bot()
        
        # Check that setup was called
        assert mock_bot.setup.called
        assert result == "setup_called"