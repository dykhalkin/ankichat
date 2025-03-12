"""
Main bot module that initializes and configures the Telegram bot.
"""

import logging
from telegram.ext import Application, CommandHandler, MessageHandler, filters
from telegram import Update
import sys

from config import settings
from src.handlers import start_command, help_command

logger = logging.getLogger('ankichat')

class AnkiChatBot:
    """
    Main bot class that handles initialization and configuration.
    """
    
    def __init__(self):
        """Initialize the bot with the Telegram token from settings."""
        self.application = None
        
        # Check if token is available
        if not settings.TELEGRAM_TOKEN:
            logger.error("Telegram token not found in environment variables")
            sys.exit(1)
            
        logger.info("Initializing Telegram bot")
    
    def setup(self):
        """Set up the bot with command handlers and error handlers."""
        # Create application
        self.application = Application.builder().token(settings.TELEGRAM_TOKEN).build()
        
        # Register command handlers
        self.application.add_handler(CommandHandler("start", start_command))
        self.application.add_handler(CommandHandler("help", help_command))
        
        # Register error handler
        self.application.add_error_handler(self._error_handler)
        
        logger.info("Bot command handlers registered")
        return self
    
    async def _error_handler(self, update, context):
        """Log errors caused by updates."""
        logger.error(f"Update {update} caused error: {context.error}")
        
        # Send a message to the user if possible
        if update and update.effective_message:
            await update.effective_message.reply_text(
                "Sorry, something went wrong. The error has been logged."
            )
    
    def run(self):
        """Start the bot using long polling."""
        if not self.application:
            logger.error("Bot not set up. Call setup() before run()")
            return
            
        logger.info("Starting bot with long polling")
        self.application.run_polling(allowed_updates=Update.ALL_TYPES)
        
def create_bot():
    """Factory function to create and set up a new bot instance."""
    return AnkiChatBot().setup()