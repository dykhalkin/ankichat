"""
Main bot module that initializes and configures the Telegram bot.
"""

import logging
import sys

from telegram import Update
from telegram.ext import (
    Application,
    CallbackQueryHandler,
    CommandHandler,
    ConversationHandler,
    MessageHandler,
    filters,
)

from config import settings
from src.handlers import (  # Deck management handlers; Conversation states; Callback prefixes
    AWAITING_ANSWER,
    AWAITING_CARD_TEXT,
    AWAITING_CONFIRMATION,
    AWAITING_DECK_COMMAND,
    AWAITING_DECK_DELETE_CONFIRMATION,
    AWAITING_DECK_MOVE_CARD_SELECTION,
    AWAITING_DECK_MOVE_TARGET_SELECTION,
    AWAITING_DECK_NAME,
    AWAITING_DECK_RENAME,
    AWAITING_DECK_SELECTION,
    AWAITING_EDIT,
    AWAITING_REVIEW_DECK_SELECTION,
    AWAITING_TRAINING_MODE_SELECTION,
    CANCEL_PREFIX,
    CONFIRM_PREFIX,
    DECK_BACK_PREFIX,
    DECK_CANCEL_DELETE_PREFIX,
    DECK_CONFIRM_DELETE_PREFIX,
    DECK_CREATE_PREFIX,
    DECK_DELETE_PREFIX,
    DECK_LIST_PREFIX,
    DECK_MANAGE_PREFIX,
    DECK_MOVE_CARD_PREFIX,
    DECK_PREFIX,
    DECK_RENAME_PREFIX,
    EDIT_PREFIX,
    REVIEWING_CARD,
    cancel_command,
    decks_command,
    handle_callback_for_direct_input,
    handle_card_answer,
    handle_create_deck,
    handle_deck_command,
    handle_deck_selection,
    handle_delete_deck_confirmation,
    handle_move_card_selection,
    handle_move_card_target_selection,
    handle_preview_callback,
    handle_rename_deck,
    handle_review_deck_selection,
    handle_session_continue,
    handle_training_mode_selection,
    help_command,
    new_card_command,
    process_card_text,
    review_command,
    start_command,
)
from src.preference_handlers import (
    ADD_LANG_PREFIX,
    AWAITING_LEARNING_LANGUAGE_ACTION,
    AWAITING_LEARNING_LANGUAGE_SELECTION,
    AWAITING_NATIVE_LANGUAGE,
    AWAITING_SETTINGS_ACTION,
    BACK_PREFIX,
    LANG_PREFIX,
    REMOVE_LANG_PREFIX,
    SETTING_PREFIX,
    handle_learning_language_action,
    handle_learning_language_selection,
    handle_native_language_selection,
    handle_settings_action,
    learning_languages_command,
    native_language_command,
    settings_command,
)

logger = logging.getLogger("ankichat")


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

        # Register user preference handlers
        self._register_user_preference_handlers()

        # Register a global callback query handler for direct text input flows
        # Using a pattern to filter based on our prefixes
        def callback_pattern(data):
            """Filter callback data based on recognized prefixes."""
            return (
                data.startswith(CONFIRM_PREFIX)
                or data.startswith(EDIT_PREFIX)
                or data.startswith(CANCEL_PREFIX)
                or data.startswith(DECK_PREFIX)
                or data.startswith(DECK_CREATE_PREFIX)
                or data.startswith(DECK_RENAME_PREFIX)
                or data.startswith(DECK_DELETE_PREFIX)
                or data.startswith(DECK_CONFIRM_DELETE_PREFIX)
                or data.startswith(DECK_CANCEL_DELETE_PREFIX)
                or data.startswith(DECK_MANAGE_PREFIX)
                or data.startswith(DECK_MOVE_CARD_PREFIX)
                or data.startswith(DECK_LIST_PREFIX)
                or data.startswith(DECK_BACK_PREFIX)
                or data.startswith(LANG_PREFIX)
                or data.startswith(ADD_LANG_PREFIX)
                or data.startswith(REMOVE_LANG_PREFIX)
            )

        direct_callback_handler = CallbackQueryHandler(
            callback=handle_callback_for_direct_input, pattern=callback_pattern
        )

        # This must be added before the conversation handler but with a higher group
        # number (lower priority) so the conversation handler gets first chance
        self.application.add_handler(direct_callback_handler, group=1)

        # Register the flashcard creation conversation handler
        self._register_flashcard_creation_handler()

        # Register the flashcard review conversation handler
        self._register_review_handler()

        # Register the deck management conversation handler
        self._register_deck_management_handler()

        # Direct text handler is removed - use only /new command for new card creation

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
                AWAITING_CONFIRMATION: [CallbackQueryHandler(handle_preview_callback)],
                AWAITING_DECK_SELECTION: [CallbackQueryHandler(handle_deck_selection)],
                AWAITING_EDIT: [
                    # Edit functionality will be implemented in the future
                    CallbackQueryHandler(handle_preview_callback)
                ],
            },
            fallbacks=[CommandHandler("cancel", cancel_command)],
            name="flashcard_creation",
            # Use group 0 for higher priority than direct text handler
            # but lower priority than global callback handler
            persistent=False,
            allow_reentry=True,
            # This prevents direct_text_handler from catching text during flashcard creation
            per_chat=True,
        )

        # Use very high priority (negative group number) to ensure it runs before direct text handler
        self.application.add_handler(flashcard_creation_handler, group=-10)
        logger.info("Flashcard creation conversation handler registered")

    # Direct text handler removed - using only /new command for creating flashcards

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
                REVIEWING_CARD: [CallbackQueryHandler(handle_session_continue)],
                AWAITING_ANSWER: [
                    # For callback-based answers (standard mode, multiple choice)
                    CallbackQueryHandler(handle_card_answer),
                    # For text-based answers (fill-in-blank, learning mode)
                    # We give this higher priority by putting it in group 1 to ensure it runs
                    # before the direct text handler
                    MessageHandler(filters.TEXT & ~filters.COMMAND, handle_card_answer),
                ],
            },
            fallbacks=[
                CommandHandler("cancel", cancel_command),
                # Add a catch-all fallback for any messages during a review session
                MessageHandler(filters.ALL, handle_card_answer),
            ],
            name="flashcard_review",
            persistent=False,
            allow_reentry=True,
            # This prevents direct_text_handler from catching text during a review
            # Higher priority than direct text handler
            per_chat=True,
        )

        # Register with HIGH priority (negative group number) to ensure it runs BEFORE the direct text handler
        # This is critical to prevent fill-in-blank answers from being treated as new flashcard commands
        self.application.add_handler(review_handler, group=-10)
        logger.info("Flashcard review conversation handler registered")

    def _register_deck_management_handler(self):
        """Register the conversation handler for deck management."""
        deck_management_handler = ConversationHandler(
            entry_points=[
                CommandHandler("decks", decks_command),
            ],
            states={
                AWAITING_DECK_COMMAND: [CallbackQueryHandler(handle_deck_command)],
                AWAITING_DECK_NAME: [
                    MessageHandler(filters.TEXT & ~filters.COMMAND, handle_create_deck)
                ],
                AWAITING_DECK_RENAME: [
                    MessageHandler(filters.TEXT & ~filters.COMMAND, handle_rename_deck)
                ],
                AWAITING_DECK_DELETE_CONFIRMATION: [
                    CallbackQueryHandler(handle_delete_deck_confirmation)
                ],
                AWAITING_DECK_MOVE_CARD_SELECTION: [
                    CallbackQueryHandler(handle_move_card_selection)
                ],
                AWAITING_DECK_MOVE_TARGET_SELECTION: [
                    CallbackQueryHandler(handle_move_card_target_selection)
                ],
            },
            fallbacks=[CommandHandler("cancel", cancel_command)],
            name="deck_management",
            persistent=False,
            allow_reentry=True,
            per_chat=True,
        )

        # Use high priority like the other conversation handlers
        self.application.add_handler(deck_management_handler, group=-10)
        logger.info("Deck management conversation handler registered")

    def _register_user_preference_handlers(self):
        """Register the conversation handlers for user preferences."""
        # Native language handler
        native_language_handler = ConversationHandler(
            entry_points=[
                CommandHandler("native", native_language_command),
            ],
            states={
                AWAITING_NATIVE_LANGUAGE: [CallbackQueryHandler(handle_native_language_selection)],
            },
            fallbacks=[CommandHandler("cancel", cancel_command)],
            name="native_language_settings",
            persistent=False,
            allow_reentry=True,
            per_chat=True,
        )

        # Learning languages handler
        learning_languages_handler = ConversationHandler(
            entry_points=[
                CommandHandler("learn", learning_languages_command),
            ],
            states={
                AWAITING_LEARNING_LANGUAGE_ACTION: [
                    CallbackQueryHandler(handle_learning_language_action)
                ],
                AWAITING_LEARNING_LANGUAGE_SELECTION: [
                    CallbackQueryHandler(handle_learning_language_selection)
                ],
            },
            fallbacks=[CommandHandler("cancel", cancel_command)],
            name="learning_languages_settings",
            persistent=False,
            allow_reentry=True,
            per_chat=True,
        )

        # Settings handler
        settings_handler = ConversationHandler(
            entry_points=[
                CommandHandler("settings", settings_command),
            ],
            states={
                AWAITING_SETTINGS_ACTION: [CallbackQueryHandler(handle_settings_action)],
                AWAITING_NATIVE_LANGUAGE: [CallbackQueryHandler(handle_native_language_selection)],
                AWAITING_LEARNING_LANGUAGE_ACTION: [
                    CallbackQueryHandler(handle_learning_language_action)
                ],
                AWAITING_LEARNING_LANGUAGE_SELECTION: [
                    CallbackQueryHandler(handle_learning_language_selection)
                ],
            },
            fallbacks=[CommandHandler("cancel", cancel_command)],
            name="settings",
            persistent=False,
            allow_reentry=True,
            per_chat=True,
        )

        # Register all handlers with high priority
        self.application.add_handler(native_language_handler, group=-10)
        self.application.add_handler(learning_languages_handler, group=-10)
        self.application.add_handler(settings_handler, group=-10)
        logger.info("User preference handlers registered")

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
