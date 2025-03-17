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
    handle_callback_for_direct_input, cancel_command, review_command,
    handle_review_deck_selection, handle_training_mode_selection,
    handle_session_continue, handle_card_answer,
    AWAITING_CARD_TEXT, AWAITING_CONFIRMATION, AWAITING_DECK_SELECTION, AWAITING_EDIT,
    AWAITING_REVIEW_DECK_SELECTION, AWAITING_TRAINING_MODE_SELECTION, 
    AWAITING_ANSWER, REVIEWING_CARD,
    CONFIRM_PREFIX, EDIT_PREFIX, CANCEL_PREFIX, DECK_PREFIX, MODE_PREFIX,
    ANSWER_PREFIX, RATE_PREFIX, CONTINUE_PREFIX, END_PREFIX
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
        
        # Register the flashcard review conversation handler
        self._register_review_handler()
        
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
            # This prevents direct_text_handler from catching text during flashcard creation
            per_chat=True
        )
        
        # Use very high priority (negative group number) to ensure it runs before direct text handler
        self.application.add_handler(flashcard_creation_handler, group=-10)
        logger.info("Flashcard creation conversation handler registered")
    
    def _register_direct_text_handler(self):
        """Register handler for direct text messages to create flashcards."""
        # This handler has a lower priority than the conversation handler
        # and will be used for creating flashcards from direct text messages
        direct_flashcard_handler = MessageHandler(
            filters.TEXT & ~filters.COMMAND, 
            direct_text_handler
        )
        
        # Use a high positive group number for lowest priority
        # This ensures it only runs if no conversation handler has matched
        self.application.add_handler(direct_flashcard_handler, group=100)
        logger.info("Direct text message handler registered")
        
    def _register_review_handler(self):
        """Register the conversation handler for flashcard review."""
        review_handler = ConversationHandler(
            entry_points=[
                CommandHandler("review", review_command),
            ],
            states={
                AWAITING_REVIEW_DECK_SELECTION: [
                    CallbackQueryHandler(handle_review_deck_selection)
                ],
                AWAITING_TRAINING_MODE_SELECTION: [
                    CallbackQueryHandler(handle_training_mode_selection)
                ],
                REVIEWING_CARD: [
                    CallbackQueryHandler(handle_session_continue)
                ],
                AWAITING_ANSWER: [
                    # For callback-based answers (standard mode, multiple choice)
                    CallbackQueryHandler(handle_card_answer),
                    # For text-based answers (fill-in-blank, learning mode)
                    # We give this higher priority by putting it in group 1 to ensure it runs
                    # before the direct text handler
                    MessageHandler(filters.TEXT & ~filters.COMMAND, handle_card_answer)
                ]
            },
            fallbacks=[
                CommandHandler("cancel", cancel_command),
                # Add a catch-all fallback for any messages during a review session
                MessageHandler(filters.ALL, handle_card_answer)
            ],
            name="flashcard_review",
            persistent=False,
            allow_reentry=True,
            # This prevents direct_text_handler from catching text during a review
            # Higher priority than direct text handler
            per_chat=True
        )
        
        # Register with HIGH priority (negative group number) to ensure it runs BEFORE the direct text handler
        # This is critical to prevent fill-in-blank answers from being treated as new flashcard commands
        self.application.add_handler(review_handler, group=-10)
        logger.info("Flashcard review conversation handler registered")
    
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