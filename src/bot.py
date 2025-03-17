"""
Main bot module that initializes and configures the Telegram bot.
"""

import logging
from telegram.ext import (
    Application, CommandHandler, MessageHandler, CallbackQueryHandler,
    ConversationHandler, filters
)
from telegram import Update
import sys

from config import settings
from src.handlers import (
    start_command, help_command, new_card_command, direct_text_handler,
    process_card_text, handle_preview_callback, handle_deck_selection,
    handle_callback_for_direct_input, cancel_command, 
    AWAITING_CARD_TEXT, AWAITING_CONFIRMATION, AWAITING_DECK_SELECTION, AWAITING_EDIT,
    CONFIRM_PREFIX, EDIT_PREFIX, CANCEL_PREFIX, DECK_PREFIX
)

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
        
        # Register basic command handlers
        self.application.add_handler(CommandHandler("start", start_command))
        self.application.add_handler(CommandHandler("help", help_command))
        
        # Register a global callback query handler for direct text input flows
        # Using a pattern to filter based on our prefixes
        callback_pattern = lambda data: (
            data.startswith(CONFIRM_PREFIX) or 
            data.startswith(EDIT_PREFIX) or 
            data.startswith(CANCEL_PREFIX) or
            data.startswith(DECK_PREFIX)
        )
        
        direct_callback_handler = CallbackQueryHandler(
            callback=handle_callback_for_direct_input,
            pattern=callback_pattern
        )
        
        # This must be added before the conversation handler but with a higher group
        # number (lower priority) so the conversation handler gets first chance
        self.application.add_handler(direct_callback_handler, group=1)
            
        # Register the flashcard creation conversation handler
        self._register_flashcard_creation_handler()
        
        # Add handler for direct text messages (outside of conversation)
        self._register_direct_text_handler()
        
        # Register error handler
        self.application.add_error_handler(self._error_handler)
        
        logger.info("Bot command handlers registered")
        return self
    
    def _register_flashcard_creation_handler(self):
        """Register the conversation handler for flashcard creation."""
        flashcard_creation_handler = ConversationHandler(
            entry_points=[
                CommandHandler("new", new_card_command),
            ],
            states={
                AWAITING_CARD_TEXT: [
                    MessageHandler(filters.TEXT & ~filters.COMMAND, process_card_text)
                ],
                AWAITING_CONFIRMATION: [
                    CallbackQueryHandler(handle_preview_callback)
                ],
                AWAITING_DECK_SELECTION: [
                    CallbackQueryHandler(handle_deck_selection)
                ],
                AWAITING_EDIT: [
                    # Edit functionality will be implemented in the future
                    CallbackQueryHandler(handle_preview_callback)
                ]
            },
            fallbacks=[CommandHandler("cancel", cancel_command)],
            name="flashcard_creation",
            # Use group 0 for higher priority than direct text handler
            # but lower priority than global callback handler
            persistent=False,
            allow_reentry=True,
        )
        
        self.application.add_handler(flashcard_creation_handler, group=0)
        logger.info("Flashcard creation conversation handler registered")
    
    def _register_direct_text_handler(self):
        """Register handler for direct text messages to create flashcards."""
        # This handler has a lower priority than the conversation handler
        # and will be used for creating flashcards from direct text messages
        direct_flashcard_handler = MessageHandler(
            filters.TEXT & ~filters.COMMAND, 
            direct_text_handler
        )
        
        # Use group 2 for lowest priority (only called if conversation handler doesn't match)
        self.application.add_handler(direct_flashcard_handler, group=2)
        logger.info("Direct text message handler registered")
    
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