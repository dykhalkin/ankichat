"""
Command handlers for the Telegram Anki Flashcards bot.
"""

import json
import logging
from typing import Any, Coroutine, Dict, Optional, Union, cast

from telegram import (
    CallbackQuery,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    ReplyKeyboardMarkup,
    ReplyKeyboardRemove,
    Update,
)
from telegram.ext import CallbackContext, ConversationHandler

from src.database import Database
from src.llm import LLMClient
from src.models import Deck, Flashcard, UserPreferences
from src.repository import (
    SQLiteDeckRepository,
    SQLiteFlashcardRepository,
    SQLiteUserPreferencesRepository,
)
from src.services import DeckService, FlashcardService, ReviewService, UserService
from src.srs import RecallScore
from src.training import FillInBlankTrainer, TrainingMode, get_training_mode_explanation

logger = logging.getLogger("ankichat")

# Conversation states
(
    AWAITING_CARD_TEXT,
    AWAITING_CONFIRMATION,
    AWAITING_DECK_SELECTION,
    AWAITING_EDIT,
    AWAITING_REVIEW_DECK_SELECTION,
    AWAITING_TRAINING_MODE_SELECTION,
    AWAITING_ANSWER,
    REVIEWING_CARD,
    # Deck management states
    AWAITING_DECK_COMMAND,
    AWAITING_DECK_NAME,
    AWAITING_DECK_RENAME,
    AWAITING_DECK_DELETE_CONFIRMATION,
    AWAITING_DECK_MOVE_CARD_SELECTION,
    AWAITING_DECK_MOVE_TARGET_SELECTION,
) = range(14)

# Callback data prefixes
CONFIRM_PREFIX = "confirm_"
EDIT_PREFIX = "edit_"
DECK_PREFIX = "deck_"
CANCEL_PREFIX = "cancel_"
MODE_PREFIX = "mode_"
ANSWER_PREFIX = "answer_"
RATE_PREFIX = "rate_"
CONTINUE_PREFIX = "continue_"
END_PREFIX = "end_"

# Deck management prefixes
DECK_CREATE_PREFIX = "deck_create_"
DECK_RENAME_PREFIX = "deck_rename_"
DECK_DELETE_PREFIX = "deck_delete_"
DECK_CONFIRM_DELETE_PREFIX = "deck_confirm_delete_"
DECK_CANCEL_DELETE_PREFIX = "deck_cancel_delete_"
DECK_MANAGE_PREFIX = "deck_manage_"
DECK_MOVE_CARD_PREFIX = "deck_move_card_"
DECK_LIST_PREFIX = "deck_list_"
DECK_BACK_PREFIX = "deck_back_"

# Direct text conversation map
# This is used to store conversation state for direct text input
# outside of the built-in ConversationHandler
DIRECT_CONVERSATIONS = {}

# Direct conversation state constants
DIRECT_AWAITING_CONFIRMATION = "awaiting_confirmation"
DIRECT_AWAITING_DECK_SELECTION = "awaiting_deck_selection"


async def start_command(update: Update, context: CallbackContext) -> None:
    """
    Handle the /start command.

    This is sent when a user starts a conversation with the bot.
    Sends a welcome message explaining the bot's functionality.
    """
    user = update.effective_user
    logger.info(f"User {user.id} ({user.username}) started the bot")

    welcome_message = (
        f"👋 Hello, {user.first_name}!\n\n"
        f"Welcome to the Anki Flashcards Bot. This bot helps you create and review "
        f"flashcards directly in Telegram using spaced repetition.\n\n"
        f"Here are the main commands:\n"
        f"• /new - Create a new flashcard\n"
        f"• /review - Start reviewing your due cards\n"
        f"• /decks - Manage your decks\n"
        f"• /settings - View and change all preferences\n"
        f"• /native - Set your native language\n"
        f"• /learn - Manage languages you're learning\n"
        f"• /stats - View your learning statistics\n"
        f"• /help - Get more detailed instructions\n\n"
        f"Let's start learning together! 🚀"
    )

    # Add status bar to show current preferences
    status_bar = await _get_status_bar(str(user.id))
    await update.message.reply_text(status_bar + welcome_message, parse_mode="Markdown")


async def help_command(update: Update, context: CallbackContext) -> None:
    """Handle the /help command."""
    logger.info(f"User {update.effective_user.id} requested help")

    help_text = (
        "📚 *AnkiChat Bot Help*\n\n"
        "*Available Commands:*\n"
        "• /start - Start the bot and see welcome message\n"
        "• /new - Create a new flashcard\n"
        "• /review - Start reviewing due cards\n"
        "• /decks - Manage your decks\n"
        "• /settings - View and change all preferences\n"
        "• /native - Set your native language\n"
        "• /learn - Manage languages you're learning\n"
        "• /stats - View your learning statistics\n"
        "• /help - Show this help message\n\n"
        "*Creating Flashcards:*\n"
        "Use the /new command and follow the prompts to create a flashcard\n\n"
        "*Managing Decks:*\n"
        "Use /decks to:\n"
        "• Create new decks\n"
        "• Rename existing decks\n"
        "• Delete decks\n"
        "• Move cards between decks\n\n"
        "*Language Settings:*\n"
        "• Use /settings to view and manage all preferences in one place\n"
        "• Use /native to set your native language directly\n"
        "• Use /learn to add or remove languages you're learning\n\n"
        "*Training Modes:*\n"
        "When reviewing, you can choose from three training modes:\n"
        "• Standard - Show the front, rate how well you recalled the answer\n"
        "• Fill-in-the-blank - Key information is blanked out for you to complete\n"
        "• Multiple choice - Choose the correct answer from options\n\n"
        "*Reviewing Cards:*\n"
        "Use /review to start a review session. For each card, you'll see the front side "
        "and need to recall the answer. After viewing the answer, rate how well you remembered it.\n\n"
        "*Spaced Repetition:*\n"
        "Cards will reappear for review based on how well you remembered them - "
        "the better you know a card, the longer until you see it again."
    )

    # Add status bar to show current preferences
    status_bar = await _get_status_bar(str(update.effective_user.id))
    await update.message.reply_text(status_bar + help_text, parse_mode="Markdown")


# Flashcard creation handlers


async def new_card_command(update: Update, context: CallbackContext) -> int:
    """
    Start the flashcard creation workflow.

    Args:
        update: The update object
        context: The context object

    Returns:
        The next conversation state
    """
    user = update.effective_user
    logger.info(f"User {user.id} started creating a new flashcard")

    await update.message.reply_text(
        "Please enter the word or phrase you want to create a flashcard for:"
    )

    return AWAITING_CARD_TEXT


async def direct_text_handler(update: Update, context: CallbackContext) -> None:
    """
    Handle direct text messages outside of a conversation flow.

    This handler is triggered when a user sends any text message directly to the bot
    that isn't part of an ongoing conversation and isn't a command.
    It processes the text as input for a new flashcard.

    Args:
        update: The update object
        context: The context object
    """
    user_id = str(update.effective_user.id)
    chat_id = str(update.effective_chat.id)
    text = update.message.text

    logger.info(f"Direct text handler triggered for user {user_id} with text: {text[:20]}...")

    # CRITICAL: Check if the user has an active review session
    # If so, this message should have been handled by the review conversation handler
    # We need this extra check in case the conversation handler priorities fail
    from src.services import ACTIVE_SESSIONS

    if user_id in ACTIVE_SESSIONS:
        logger.warning(
            f"User {user_id} has an active review session but message reached direct_text_handler. Ignoring."
        )
        await update.message.reply_text(
            "It looks like you're in the middle of a review session. "
            "This message will be ignored. If you're trying to answer a flashcard, "
            "please respond directly to the most recent flashcard message. "
            "You can use /cancel to end your current session."
        )
        return

    # Process the text just like the regular card creation flow
    await _process_flashcard_input(update, context)

    # Store in our direct conversations map to handle callbacks properly
    DIRECT_CONVERSATIONS[chat_id] = DIRECT_AWAITING_CONFIRMATION
    logger.info(
        f"User {user_id} started direct flashcard creation, state: {DIRECT_CONVERSATIONS[chat_id]}"
    )


async def process_card_text(update: Update, context: CallbackContext) -> int:
    """
    Process the text entered by the user after the /new command.

    This handler is part of the conversation flow started by /new command.

    Args:
        update: The update object
        context: The context object

    Returns:
        The next conversation state
    """
    # Use the shared processing function
    await _process_flashcard_input(update, context)

    # Return the next state for the conversation handler
    return AWAITING_CONFIRMATION


async def _process_flashcard_input(update: Update, context: CallbackContext) -> None:
    """
    Shared function to process text input for flashcard creation.

    Used by both the conversation handler and direct text handler.

    Args:
        update: The update object
        context: The context object
    """
    user = update.effective_user
    text = update.message.text

    # Send a processing message with a simple animation
    processing_message = await update.message.reply_text("⏳ Creating flashcard...")

    # Get the services
    flashcard_service = _get_flashcard_service()

    try:
        # Process the text and generate a preview
        preview = await flashcard_service.process_new_card_text(text, str(user.id))

        # Store the preview in the context for later use
        context.user_data["preview"] = preview

        # Store detected language in user preferences
        language_info = preview.get("language", {})
        if language_info and "code" in language_info:
            language_code = language_info["code"]
            user_service = _get_user_service()
            try:
                user_service.update_preferences(user_id=str(user.id), last_language=language_code)
                logger.info(f"Updated last used language for user {user.id} to {language_code}")
            except Exception as e:
                # Don't fail if preference update fails
                logger.error(f"Error updating language preference: {e}")

        # Format the preview message
        message_text = flashcard_service.format_preview_message(preview)

        # Create a cleaner, more organized inline keyboard
        keyboard = [
            [
                InlineKeyboardButton(
                    "✅ Save", callback_data=f"{CONFIRM_PREFIX}{preview['preview_id']}"
                )
            ],
            [InlineKeyboardButton("✏️ Edit", callback_data=f"{EDIT_PREFIX}{preview['preview_id']}")],
            [
                InlineKeyboardButton(
                    "❌ Cancel", callback_data=f"{CANCEL_PREFIX}{preview['preview_id']}"
                )
            ],
        ]

        reply_markup = InlineKeyboardMarkup(keyboard)

        # Add status bar to the preview message
        status_bar = await _get_status_bar(str(user.id))

        # Edit the processing message with the preview and status bar
        await processing_message.edit_text(
            status_bar + message_text,
            reply_markup=reply_markup,
            parse_mode="Markdown",
        )

    except Exception as e:
        logger.error(f"Error processing card text: {e}")
        await processing_message.edit_text(
            "❌ Unable to create flashcard. Please check your input and try again."
        )


async def handle_callback_for_direct_input(
    update: Update, context: CallbackContext
) -> Optional[int]:
    """
    Router function to handle callbacks from direct text input.

    This function determines the current state of the direct conversation
    and routes the callback to the appropriate handler.

    Args:
        update: The update object
        context: The context object

    Returns:
        None as this is only used for direct conversations outside the ConversationHandler
    """
    chat_id = str(update.effective_chat.id)

    # Check if this is a direct text conversation
    if chat_id not in DIRECT_CONVERSATIONS:
        return None

    # Get the current state
    current_state = DIRECT_CONVERSATIONS[chat_id]
    logger.info(f"Handling direct callback for chat {chat_id} in state {current_state}")

    # Route to the appropriate handler based on state
    if current_state == DIRECT_AWAITING_CONFIRMATION:
        await handle_preview_callback(update, context)
    elif current_state == DIRECT_AWAITING_DECK_SELECTION:
        await handle_deck_selection(update, context)
    else:
        # Unknown state
        logger.warning(f"Unknown direct conversation state: {current_state}")
        query = cast(CallbackQuery, update.callback_query)
        await query.answer()
        await query.edit_message_text("Sorry, something went wrong. Please try again.")
        del DIRECT_CONVERSATIONS[chat_id]

    return None


async def handle_preview_callback(update: Update, context: CallbackContext) -> int:
    """
    Handle callbacks from the preview message's inline keyboard.

    This handler handles callbacks from both the conversation flow
    and direct text messages.

    Args:
        update: The update object
        context: The context object

    Returns:
        The next conversation state
    """
    query = cast(CallbackQuery, update.callback_query)
    await query.answer()

    callback_data = query.data
    user_id = str(update.effective_user.id)
    chat_id = str(update.effective_chat.id)

    # Only process callbacks that start with our prefixes
    if not (
        callback_data.startswith(CONFIRM_PREFIX)
        or callback_data.startswith(EDIT_PREFIX)
        or callback_data.startswith(CANCEL_PREFIX)
    ):
        # This might be a callback for a different handler
        return None

    # Check if this is part of a direct text conversation
    is_direct = chat_id in DIRECT_CONVERSATIONS

    # Log the callback data and conversation state
    logger.info(f"Handling preview callback: {callback_data}, direct: {is_direct}")
    if is_direct:
        logger.info(f"Direct conversation state: {DIRECT_CONVERSATIONS[chat_id]}")

    # Check if the user wants to cancel
    if callback_data.startswith(CANCEL_PREFIX):
        await query.edit_message_text("Flashcard creation cancelled.")

        # Clean up direct conversation state if needed
        if is_direct:
            del DIRECT_CONVERSATIONS[chat_id]

        return ConversationHandler.END

    # Check if the user wants to confirm
    if callback_data.startswith(CONFIRM_PREFIX):
        preview_id = callback_data[len(CONFIRM_PREFIX) :]

        # Get user's decks
        deck_service = _get_deck_service()
        decks = deck_service.get_user_decks(user_id)

        if not decks:
            # Create a default deck if user doesn't have any
            default_deck = deck_service.create_deck(
                name="My First Deck",
                user_id=user_id,
                description="Default deck created automatically",
            )
            decks = [default_deck]

        # Store the preview ID for later
        context.user_data["confirmed_preview_id"] = preview_id

        # Get user preferences to find last used deck
        user_service = _get_user_service()
        user_prefs = user_service.get_user_preferences(user_id)
        last_deck_id = user_prefs.last_deck_id

        # Create inline keyboard with decks - maximum 3 decks per row for better UX
        keyboard = []
        current_row = []

        # If user has a last used deck, create a special button for quick selection
        if last_deck_id:
            # Find the last used deck object
            last_deck = next((deck for deck in decks if deck.id == last_deck_id), None)

            if last_deck:
                # Add "Last Used" special button at the top
                keyboard.append(
                    [
                        InlineKeyboardButton(
                            f"✨ Last Used: {last_deck.name}",
                            callback_data=f"{DECK_PREFIX}{last_deck.id}",
                        )
                    ]
                )

        # Add all decks
        for i, deck in enumerate(decks):
            current_row.append(
                InlineKeyboardButton(deck.name, callback_data=f"{DECK_PREFIX}{deck.id}")
            )

            # Start a new row after every 2 deck buttons
            if (i + 1) % 2 == 0 or i == len(decks) - 1:
                keyboard.append(current_row)
                current_row = []

        # Add a cancel button in its own row
        keyboard.append(
            [InlineKeyboardButton("❌ Cancel", callback_data=f"{CANCEL_PREFIX}{preview_id}")]
        )

        reply_markup = InlineKeyboardMarkup(keyboard)

        # Add status bar and ask user to select a deck
        status_bar = await _get_status_bar(user_id)
        await query.edit_message_text(
            status_bar + "Please select a deck for this flashcard:",
            reply_markup=reply_markup,
            parse_mode="Markdown",
        )

        # Update the state for direct conversations
        if is_direct:
            DIRECT_CONVERSATIONS[chat_id] = DIRECT_AWAITING_DECK_SELECTION
            logger.info(f"Updated direct conversation state to {DIRECT_AWAITING_DECK_SELECTION}")

        return AWAITING_DECK_SELECTION

    # Check if the user wants to edit
    if callback_data.startswith(EDIT_PREFIX):
        preview_id = callback_data[len(EDIT_PREFIX) :]

        # Tell the user editing is coming soon
        await query.edit_message_text(
            "Editing functionality will be available in a future update. "
            "Please cancel and try again if you need to make changes."
        )

        # Clean up direct conversation state if needed
        if is_direct:
            del DIRECT_CONVERSATIONS[chat_id]

        return ConversationHandler.END

    # Unknown callback data (but starts with our prefix)
    logger.warning(f"Unknown callback data: {callback_data}")
    await query.edit_message_text("Sorry, something went wrong. Please try again.")

    # Clean up direct conversation state if needed
    if is_direct:
        del DIRECT_CONVERSATIONS[chat_id]

    return ConversationHandler.END


async def handle_deck_selection(update: Update, context: CallbackContext) -> int:
    """
    Handle deck selection for the new flashcard.

    This handler handles deck selection from both the conversation flow
    and direct text messages.

    Args:
        update: The update object
        context: The context object

    Returns:
        The next conversation state
    """
    query = cast(CallbackQuery, update.callback_query)
    await query.answer()

    callback_data = query.data
    user_id = str(update.effective_user.id)
    chat_id = str(update.effective_chat.id)

    # Only process callbacks that start with our prefixes
    if not (callback_data.startswith(DECK_PREFIX) or callback_data.startswith(CANCEL_PREFIX)):
        # This might be a callback for a different handler
        return None

    # Check if this is part of a direct text conversation
    is_direct = chat_id in DIRECT_CONVERSATIONS

    # Log the callback data and conversation state
    logger.info(f"Handling deck selection callback: {callback_data}, direct: {is_direct}")
    if is_direct:
        logger.info(f"Direct conversation state: {DIRECT_CONVERSATIONS[chat_id]}")

    # Check if the user wants to cancel
    if callback_data.startswith(CANCEL_PREFIX):
        await query.edit_message_text("Flashcard creation cancelled.")

        # Clean up direct conversation state if needed
        if is_direct:
            del DIRECT_CONVERSATIONS[chat_id]

        return ConversationHandler.END

    # Check if the user selected a deck
    if callback_data.startswith(DECK_PREFIX):
        deck_id = callback_data[len(DECK_PREFIX) :]
        preview_id = context.user_data.get("confirmed_preview_id")

        if not preview_id:
            logger.error("No preview ID found in user data")
            await query.edit_message_text("Sorry, something went wrong. Please try again.")

            # Clean up direct conversation state if needed
            if is_direct:
                del DIRECT_CONVERSATIONS[chat_id]

            return ConversationHandler.END

        # Create the flashcard
        flashcard_service = _get_flashcard_service()

        try:
            # In a real implementation, you would retrieve the preview from storage
            preview = context.user_data.get("preview", {})

            # Create the flashcard using the preview content
            content = preview.get("content", {})

            # Create a properly formatted flashcard from the preview content
            user_edits = {
                "front": content.get("word", ""),
                "back": _format_card_back(content),
                "language": content.get("language_code", "en"),
            }

            flashcard = await flashcard_service.create_flashcard_from_preview(
                preview_id=preview_id,
                deck_id=deck_id,
                user_edits=user_edits,
                user_id=user_id,  # Pass user_id to store preferences
            )

            # Notify the user
            await query.edit_message_text(
                f"✅ Flashcard created successfully!\n\n"
                f"*Front:* {flashcard.front}\n"
                f"*Added to deck:* {deck_id}\n\n"
                f"Use /review to start practicing.",
                parse_mode="Markdown",
            )

            # Clean up direct conversation state if needed
            if is_direct:
                del DIRECT_CONVERSATIONS[chat_id]

            return ConversationHandler.END

        except Exception as e:
            logger.error(f"Error creating flashcard: {e}")
            await query.edit_message_text(
                "Sorry, there was an error creating your flashcard. Please try again."
            )

            # Clean up direct conversation state if needed
            if is_direct:
                del DIRECT_CONVERSATIONS[chat_id]

            return ConversationHandler.END

    # Unknown callback data (but starts with our prefix)
    logger.warning(f"Unknown callback data: {callback_data}")
    await query.edit_message_text("Sorry, something went wrong. Please try again.")

    # Clean up direct conversation state if needed
    if is_direct:
        del DIRECT_CONVERSATIONS[chat_id]

    return ConversationHandler.END


async def cancel_command(update: Update, context: CallbackContext) -> int:
    """
    Cancel the current conversation.

    Args:
        update: The update object
        context: The context object

    Returns:
        ConversationHandler.END
    """
    logger.info(f"User {update.effective_user.id} cancelled the operation")
    await update.message.reply_text("Operation cancelled.")
    return ConversationHandler.END


# Review session handlers


async def review_command(update: Update, context: CallbackContext) -> int:
    """
    Start the flashcard review workflow.

    Args:
        update: The update object
        context: The context object

    Returns:
        The next conversation state
    """
    user = update.effective_user
    user_id = str(user.id)
    logger.info(f"User {user_id} started a review session")

    # Check if user already has an active session
    review_service = _get_review_service()
    active_session = user_id in review_service.ACTIVE_SESSIONS

    if active_session:
        # Ask if user wants to continue existing session or start a new one
        keyboard = [
            [
                InlineKeyboardButton("Continue", callback_data=f"{CONTINUE_PREFIX}session"),
                InlineKeyboardButton("End current session", callback_data=f"{END_PREFIX}session"),
            ]
        ]

        reply_markup = InlineKeyboardMarkup(keyboard)

        await update.message.reply_text(
            "You already have an active review session. Do you want to continue it or end it and start a new one?",
            reply_markup=reply_markup,
        )

        return REVIEWING_CARD

    # Get user's decks to review
    deck_service = _get_deck_service()
    decks = deck_service.get_user_decks(user_id)

    if not decks:
        # Create a default deck if user doesn't have any
        default_deck = deck_service.create_deck(
            name="My First Deck",
            user_id=user_id,
            description="Default deck created automatically",
        )
        decks = [default_deck]

    # Get user preferences to find last used deck
    user_service = _get_user_service()
    user_prefs = user_service.get_user_preferences(user_id)
    last_deck_id = user_prefs.last_deck_id

    # Create inline keyboard with decks
    keyboard = []

    # If user has a last used deck, create a special button for quick selection
    if last_deck_id:
        # Find the last used deck object
        last_deck = next((deck for deck in decks if deck.id == last_deck_id), None)

        if last_deck:
            # Add "Last Used" special button at the top
            keyboard.append(
                [
                    InlineKeyboardButton(
                        f"✨ Last Used: {last_deck.name}",
                        callback_data=f"{DECK_PREFIX}{last_deck.id}",
                    )
                ]
            )

    # Add all decks
    for deck in decks:
        keyboard.append([InlineKeyboardButton(deck.name, callback_data=f"{DECK_PREFIX}{deck.id}")])

    # Add a cancel button
    keyboard.append([InlineKeyboardButton("❌ Cancel", callback_data=f"{CANCEL_PREFIX}review")])

    reply_markup = InlineKeyboardMarkup(keyboard)

    # Add status bar and ask user to select a deck
    status_bar = await _get_status_bar(user_id)
    await update.message.reply_text(
        status_bar + "Please select a deck to review:",
        reply_markup=reply_markup,
        parse_mode="Markdown",
    )

    return AWAITING_REVIEW_DECK_SELECTION


async def handle_review_deck_selection(update: Update, context: CallbackContext) -> int:
    """
    Handle deck selection for review.

    Args:
        update: The update object
        context: The context object

    Returns:
        The next conversation state
    """
    query = cast(CallbackQuery, update.callback_query)
    await query.answer()

    callback_data = query.data
    user_id = str(update.effective_user.id)

    # Check if the user wants to cancel
    if callback_data.startswith(CANCEL_PREFIX):
        await query.edit_message_text("Review session cancelled.")
        return ConversationHandler.END

    # Check if the user selected a deck
    if callback_data.startswith(DECK_PREFIX):
        deck_id = callback_data[len(DECK_PREFIX) :]

        # Store the selected deck_id
        context.user_data["selected_deck_id"] = deck_id

        # Store this deck as the last used deck in user preferences
        user_service = _get_user_service()
        try:
            user_service.update_preferences(user_id=user_id, last_deck_id=deck_id)
            logger.info(f"Updated last used deck for user {user_id} to {deck_id}")
        except Exception as e:
            # Don't fail the review session if preference update fails
            logger.error(f"Error updating user preferences: {e}")

        # Present training mode options
        keyboard = []

        # Create buttons for each training mode
        for mode in TrainingMode:
            keyboard.append(
                [
                    InlineKeyboardButton(
                        mode.value.replace("_", " ").title(),
                        callback_data=f"{MODE_PREFIX}{mode.value}",
                    )
                ]
            )

        # Add a cancel button
        keyboard.append([InlineKeyboardButton("❌ Cancel", callback_data=f"{CANCEL_PREFIX}mode")])

        reply_markup = InlineKeyboardMarkup(keyboard)

        # Get deck information
        deck_service = _get_deck_service()
        deck = deck_service.deck_repo.get(deck_id)
        deck_name = deck.name if deck else deck_id

        # Add status bar and ask user to select a training mode
        status_bar = await _get_status_bar(user_id)
        await query.edit_message_text(
            status_bar + f"You selected deck: *{deck_name}*\n\n" "Please choose a training mode:",
            reply_markup=reply_markup,
            parse_mode="Markdown",
        )

        return AWAITING_TRAINING_MODE_SELECTION

    # Unknown callback data
    logger.warning(f"Unknown callback data: {callback_data}")
    await query.edit_message_text("Sorry, something went wrong. Please try again.")
    return ConversationHandler.END


async def handle_training_mode_selection(update: Update, context: CallbackContext) -> int:
    """
    Handle training mode selection for review.

    Args:
        update: The update object
        context: The context object

    Returns:
        The next conversation state
    """
    query = cast(CallbackQuery, update.callback_query)
    await query.answer()

    callback_data = query.data
    user_id = str(update.effective_user.id)

    # Check if the user wants to cancel
    if callback_data.startswith(CANCEL_PREFIX):
        await query.edit_message_text("Review session cancelled.")
        return ConversationHandler.END

    # Check if the user selected a training mode
    if callback_data.startswith(MODE_PREFIX):
        mode_value = callback_data[len(MODE_PREFIX) :]
        training_mode = None

        # Find the corresponding TrainingMode enum
        for mode in TrainingMode:
            if mode.value == mode_value:
                training_mode = mode
                break

        if not training_mode:
            logger.warning(f"Invalid training mode: {mode_value}")
            await query.edit_message_text("Invalid training mode. Please try again.")
            return ConversationHandler.END

        # Get the selected deck
        deck_id = context.user_data.get("selected_deck_id")
        if not deck_id:
            logger.error("No deck ID found in user data")
            await query.edit_message_text("Sorry, something went wrong. Please try again.")
            return ConversationHandler.END

        # Get explanation for the selected mode
        mode_explanation = await get_training_mode_explanation(training_mode)

        # Start the review session
        review_service = _get_review_service()

        try:
            # Use the async version of start_session
            result = await review_service.start_session(user_id, deck_id, training_mode)

            if not result["success"]:
                # No cards to review
                await query.edit_message_text(
                    f"{result['message']}\n\n" "Try creating more flashcards first with /new."
                )
                return ConversationHandler.END

            # Session started successfully
            session_info = result["session_info"]

            # First, show an explanation of the selected mode
            await query.edit_message_text(
                f"{mode_explanation}\n\n"
                f"You're about to review {session_info['cards_due']} cards "
                f"from deck '{session_info['deck_name']}'.\n\n"
                "Let's begin!",
                parse_mode="Markdown",
            )

            # Send the first card
            return await _send_next_card(update, context)

        except Exception as e:
            logger.error(f"Error starting review session: {e}")
            await query.edit_message_text(
                "Sorry, there was an error starting the review session. Please try again."
            )
            return ConversationHandler.END

    # Unknown callback data
    logger.warning(f"Unknown callback data: {callback_data}")
    await query.edit_message_text("Sorry, something went wrong. Please try again.")
    return ConversationHandler.END


async def handle_session_continue(update: Update, context: CallbackContext) -> int:
    """
    Handle continuing or ending an existing session.

    Args:
        update: The update object
        context: The context object

    Returns:
        The next conversation state
    """
    query = cast(CallbackQuery, update.callback_query)
    await query.answer()

    callback_data = query.data
    user_id = str(update.effective_user.id)

    if callback_data.startswith(CONTINUE_PREFIX):
        # Continue the existing session
        await query.edit_message_text("Continuing your review session...")

        # Send the next card
        return await _send_next_card(update, context)

    elif callback_data.startswith(END_PREFIX):
        # End the existing session
        review_service = _get_review_service()
        result = await review_service.end_session(user_id)

        if result["success"]:
            summary = result["summary"]

            # Format the summary message
            summary_message = (
                "📊 •Review Session Summary•\n\n"
                f"Cards reviewed: {summary['cards_reviewed']}\n"
                f"Correct answers: {summary['correct_answers']}\n"
                f"Incorrect answers: {summary['incorrect_answers']}\n"
                f"Accuracy: {summary['accuracy']:.1%}\n"
                f"Duration: {summary['duration_seconds'] / 60:.1f} minutes\n\n"
                "Ready to start a new session?"
            )

            await query.edit_message_text(summary_message, parse_mode="Markdown")

            # Start a new review session
            await review_command(update, context)
            return AWAITING_REVIEW_DECK_SELECTION
        else:
            await query.edit_message_text(result["message"])
            return ConversationHandler.END

    # Unknown callback data
    logger.warning(f"Unknown callback data: {callback_data}")
    await query.edit_message_text("Sorry, something went wrong. Please try again.")
    return ConversationHandler.END


async def handle_card_answer(update: Update, context: CallbackContext) -> int:
    """
    Handle a user's answer to a flashcard.

    Args:
        update: The update object
        context: The context object

    Returns:
        The next conversation state
    """
    user_id = str(update.effective_user.id)
    logger.info(f"Card answer handler triggered for user {user_id}")

    # Check if this was triggered by the catch-all fallback
    if not (update.callback_query or (update.message and update.message.text)):
        logger.warning(f"Catch-all fallback triggered for user {user_id} - ignoring")
        await update.message.reply_text(
            "Please provide a text answer to the flashcard. If you're trying to do something else, "
            "you can use /cancel to end your current review session first."
        )
        return AWAITING_ANSWER
    # Check if this is a direct message or a callback
    if update.callback_query:
        # Handle callback (for standard mode's self-rating)
        query = cast(CallbackQuery, update.callback_query)
        await query.answer()

        callback_data = query.data
        # User ID already defined above

        # Extract the rating from callback data
        if callback_data.startswith(RATE_PREFIX):
            rating = callback_data[len(RATE_PREFIX) :]
            answer = rating  # The rating is the answer

            # Edit original message to show both question and answer
            # Process the answer and get next card
            review_service = _get_review_service()
            result = await review_service.process_answer(user_id, answer)

            if not result["success"]:
                await query.edit_message_text(result["message"])
                return ConversationHandler.END

            # Update the message with answer feedback
            if "correct_answer" in result:
                feedback_message = (
                    f"Your self-rating: {answer}\n\n"
                    f"Cards left: {result['session_status']['cards_left']}"
                )

                await query.edit_message_text(feedback_message)

            # Send the next card
            return await _send_next_card(update, context)

        elif callback_data.startswith(ANSWER_PREFIX):
            # This is for multiple choice mode
            selected_index = callback_data[len(ANSWER_PREFIX) :]
            answer = selected_index

            # Process the answer and get next card
            review_service = _get_review_service()
            result = await review_service.process_answer(user_id, answer)

            if not result["success"]:
                await query.edit_message_text(result["message"])
                return ConversationHandler.END

            # Update the message with answer feedback
            if "correct_answer_index" in result:
                correct_index = result["correct_answer_index"]
                is_correct = result["is_correct"]

                # Create a visual progress indicator
                cards_left = result["session_status"]["cards_left"]
                cards_total = result["session_status"].get("cards_total", cards_left + 1)
                cards_complete = cards_total - cards_left

                # Create progress bar
                progress_bar = "▓" * cards_complete + "░" * cards_left

                feedback_emoji = "🎯" if is_correct else "❌"
                progress_percentage = (
                    int((cards_complete / cards_total) * 100) if cards_total > 0 else 0
                )

                feedback_message = (
                    f"{feedback_emoji} {'Correct!' if is_correct else 'Incorrect!'}\n\n"
                    f"Your answer: Option {answer}\n"
                    f"Correct answer: Option {correct_index}\n\n"
                    f"Progress: {progress_percentage}% complete\n"
                    f"{progress_bar}\n"
                    f"{cards_complete}/{cards_total} cards reviewed"
                )

                await query.edit_message_text(feedback_message)

            # Send the next card
            return await _send_next_card(update, context)

        elif callback_data.startswith(END_PREFIX):
            # End the session
            review_service = _get_review_service()
            result = await review_service.end_session(user_id)

            if result["success"]:
                summary = result["summary"]

                # Format the summary message
                # Calculate accuracy for visual representation
                accuracy = summary["accuracy"]
                accuracy_bar = "🟩" * int(accuracy * 10) + "⬜" * (10 - int(accuracy * 10))
                minutes = summary["duration_seconds"] / 60
                seconds = summary["duration_seconds"] % 60

                summary_message = (
                    "🏆 *Session Complete!*\n\n"
                    f"📊 *Stats:*\n"
                    f"• Cards reviewed: {summary['cards_reviewed']}\n"
                    f"• Correct: {summary['correct_answers']} | Incorrect: {summary['incorrect_answers']}\n"
                    f"• Accuracy: {summary['accuracy']:.1%}\n"
                    f"{accuracy_bar}\n"
                    f"• Time: {int(minutes)}m {int(seconds)}s\n\n"
                    "Type /review to start a new session!"
                )

                await query.edit_message_text(summary_message, parse_mode="Markdown")

                return ConversationHandler.END
            else:
                await query.edit_message_text(result["message"])
                return ConversationHandler.END

        # Unknown callback data
        logger.warning(f"Unknown callback data: {callback_data}")
        await query.edit_message_text("Sorry, something went wrong. Please try again.")
        return ConversationHandler.END

    else:
        # Handle text message answer (for fill-in-blank mode)
        # User ID already defined above
        answer = update.message.text
        logger.info(f"Received text answer from user {user_id}: {answer[:20]}...")

        # Process the answer
        review_service = _get_review_service()
        result = await review_service.process_answer(user_id, answer)

        if not result["success"]:
            await update.message.reply_text(result["message"])
            return ConversationHandler.END

        # Provide feedback on the answer
        if "is_correct" in result:
            is_correct = result["is_correct"]
            correct_answer = result.get("correct_answer", "") or result.get("blanked_term", "")

            # Create a visual progress indicator
            cards_left = result["session_status"]["cards_left"]
            cards_total = result["session_status"].get("cards_total", cards_left + 1)
            cards_complete = cards_total - cards_left

            # Create progress bar
            progress_bar = "▓" * cards_complete + "░" * cards_left

            feedback_emoji = "🎯" if is_correct else "❌"
            progress_percentage = (
                int((cards_complete / cards_total) * 100) if cards_total > 0 else 0
            )

            feedback_message = (
                f"{feedback_emoji} {'Correct!' if is_correct else 'Incorrect!'}\n\n"
                f"Your answer: {result.get('user_answer', '')}\n"
                f"Correct answer: {correct_answer}\n\n"
                f"Progress: {progress_percentage}% complete\n"
                f"{progress_bar}\n"
                f"{cards_complete}/{cards_total} cards reviewed"
            )

            # Add status bar to feedback message
            status_bar = await _get_status_bar(user_id)
            await update.message.reply_text(status_bar + feedback_message, parse_mode="Markdown")

        # Send the next card
        return await _send_next_card(update, context)


async def _send_next_card(update: Update, context: CallbackContext) -> int:
    """
    Send the next card to the user.

    Args:
        update: The update object
        context: The context object

    Returns:
        The next conversation state
    """
    user_id = str(update.effective_user.id)
    logger.info(f"Sending next card to user {user_id}")

    try:
        # Get the next card - need to await as it's now an async method
        review_service = _get_review_service()
        card_data = await review_service.get_next_card(user_id)
        logger.info(f"Retrieved card data: {card_data}")
    except Exception as e:
        # This is a critical error handler to catch any async issues
        logger.error(f"Critical error in _send_next_card: {e}")
        logger.exception("Full traceback:")

        # Inform the user
        if update.callback_query:
            await update.callback_query.edit_message_text(
                "An unexpected error occurred. Please try a different training mode or contact support."
            )
        else:
            await update.message.reply_text(
                "An unexpected error occurred. Please try a different training mode or contact support."
            )
        return ConversationHandler.END

    # Check for error mode (especially fill-in-blank without LLM)
    if card_data and card_data.get("mode") == "error":
        error_message = card_data.get("error", "Cannot start this mode due to an error")
        if update.callback_query:
            await update.callback_query.edit_message_text(
                f"Error: {error_message}\n\nPlease try a different training mode.",
                reply_markup=None,
            )
        else:
            await update.message.reply_text(
                f"Error: {error_message}\n\nPlease try a different training mode."
            )

        # End the conversation
        return ConversationHandler.END

    if not card_data:
        # No more cards to review
        result = await review_service.end_session(user_id)

        if result["success"]:
            summary = result["summary"]

            # Format the summary message
            summary_message = (
                "🎉 •Review Session Complete!•\n\n"
                f"Cards reviewed: {summary['cards_reviewed']}\n"
                f"Correct answers: {summary['correct_answers']}\n"
                f"Incorrect answers: {summary['incorrect_answers']}\n"
                f"Accuracy: {summary['accuracy']:.1%}\n"
                f"Duration: {summary['duration_seconds'] / 60:.1f} minutes\n\n"
                "Great job! Use /review to start a new session."
            )

            # Add status bar to summary message
            status_bar = await _get_status_bar(user_id)

            # Send the message to the right place
            if update.callback_query:
                await update.callback_query.edit_message_text(
                    status_bar + summary_message, parse_mode="Markdown"
                )
            else:
                await update.message.reply_text(status_bar + summary_message, parse_mode="Markdown")

            return ConversationHandler.END
        else:
            message = result.get("message", "Error ending session")

            if update.callback_query:
                await update.callback_query.edit_message_text(message)
            else:
                await update.message.reply_text(message)

            return ConversationHandler.END

    # We have a card to show
    mode = card_data["mode"]
    front = card_data["front"]
    progress = card_data["progress"]

    # Format the message based on the training mode
    if mode == TrainingMode.STANDARD.value:
        # Standard mode - show front and ask user to recall with a progress bar
        progress_bar = "▓" * progress["current"] + "░" * (progress["total"] - progress["current"])

        message = (
            f"📝 *Card {progress['current']}/{progress['total']}*\n"
            f"{progress_bar}\n\n"
            f"{front}\n\n"
            f"{card_data['prompt']}\n\n"
            "Rate how well you remembered:"
        )

        # Create improved rating buttons with emoji indicators
        rating_labels = [
            "0 ❌ Complete blackout",
            "1 😕 Recognized only",
            "2 🤔 Familiar",
            "3 🙂 Correct (hard)",
            "4 😀 Correct (slight hesitation)",
            "5 🎯 Perfect recall",
        ]

        # Create two rows of rating buttons for better UX
        keyboard = []
        row1 = []
        row2 = []

        for rating in range(6):
            button = InlineKeyboardButton(
                rating_labels[rating], callback_data=f"{RATE_PREFIX}{rating}"
            )
            if rating < 3:
                row1.append(button)
            else:
                row2.append(button)

        keyboard.append(row1)
        keyboard.append(row2)

        # Add end session button
        keyboard.append([InlineKeyboardButton("End Session", callback_data=f"{END_PREFIX}session")])

        reply_markup = InlineKeyboardMarkup(keyboard)

        # Add status bar to the message
        status_bar = await _get_status_bar(user_id)

        # Send the message with status bar
        if update.callback_query:
            await update.callback_query.edit_message_text(
                status_bar + message, reply_markup=reply_markup, parse_mode="Markdown"
            )
        else:
            await update.message.reply_text(
                status_bar + message, reply_markup=reply_markup, parse_mode="Markdown"
            )

    elif mode == TrainingMode.MULTIPLE_CHOICE.value:
        # Multiple choice mode - show front and options with progress bar
        options = card_data["options"]

        # Create visual progress bar
        progress_bar = "▓" * progress["current"] + "░" * (progress["total"] - progress["current"])

        message = (
            f"📝 *Card {progress['current']}/{progress['total']}*\n"
            f"{progress_bar}\n\n"
            f"{front}\n\n"
            f"{card_data['prompt']}\n\n"
            "*Choose the correct answer:*\n"
        )

        # Create option buttons - one button per row for better readability
        keyboard = []

        for i, option in enumerate(options):
            # Add each option as its own button in a separate row for clarity
            keyboard.append(
                [InlineKeyboardButton(f"{option}", callback_data=f"{ANSWER_PREFIX}{i}")]
            )

        # Add end session button
        keyboard.append([InlineKeyboardButton("End Session", callback_data=f"{END_PREFIX}session")])

        reply_markup = InlineKeyboardMarkup(keyboard)

        # Add status bar to the message
        status_bar = await _get_status_bar(user_id)

        # Send the message with status bar
        if update.callback_query:
            await update.callback_query.edit_message_text(
                status_bar + message, reply_markup=reply_markup, parse_mode="Markdown"
            )
        else:
            await update.message.reply_text(
                status_bar + message, reply_markup=reply_markup, parse_mode="Markdown"
            )

    elif mode == TrainingMode.FILL_IN_BLANK.value:
        # Fill-in-blank mode - show front and blanked content with progress bar
        blanked_content = card_data["blanked_content"]

        # Create visual progress bar
        progress_bar = "▓" * progress["current"] + "░" * (progress["total"] - progress["current"])

        message = (
            f"📝 *Card {progress['current']}/{progress['total']}*\n"
            f"{progress_bar}\n\n"
            f"{blanked_content}\n\n"
            f"*{card_data['prompt']}*"
        )

        # Add single button to end session
        keyboard = [[InlineKeyboardButton("End Session", callback_data=f"{END_PREFIX}session")]]
        reply_markup = InlineKeyboardMarkup(keyboard)

        # Add status bar to the message
        status_bar = await _get_status_bar(user_id)

        # Send the message with status bar
        if update.callback_query:
            await update.callback_query.edit_message_text(
                status_bar + message, reply_markup=reply_markup, parse_mode="Markdown"
            )
        else:
            await update.message.reply_text(
                status_bar + message, reply_markup=reply_markup, parse_mode="Markdown"
            )

    else:  # Other modes
        # Handle any other modes
        message = (
            f"•Card {progress['current']}/{progress['total']}•\n\n"
            f"{front}\n\n"
            f"{card_data['prompt']}"
        )

        # Add end session button
        keyboard = [[InlineKeyboardButton("End Session", callback_data=f"{END_PREFIX}session")]]

        reply_markup = InlineKeyboardMarkup(keyboard)

        # Add status bar to the message
        status_bar = await _get_status_bar(user_id)

        # Send the message with status bar
        if update.callback_query:
            await update.callback_query.edit_message_text(
                status_bar + message, reply_markup=reply_markup, parse_mode="Markdown"
            )
        else:
            await update.message.reply_text(
                status_bar + message, reply_markup=reply_markup, parse_mode="Markdown"
            )

    return AWAITING_ANSWER


# Deck management handlers


async def decks_command(update: Update, context: CallbackContext) -> int:
    """
    Handle the /decks command to manage decks.

    This command shows the list of available decks and management options.

    Args:
        update: The update object
        context: The context object

    Returns:
        The next conversation state
    """
    user = update.effective_user
    user_id = str(user.id)
    logger.info(f"User {user_id} started deck management")

    # Get the user's decks
    deck_service = _get_deck_service()
    decks = deck_service.get_user_decks(user_id)

    # Create an inline keyboard for deck management options
    keyboard = [[InlineKeyboardButton("Create New Deck", callback_data=f"{DECK_CREATE_PREFIX}new")]]

    # Add buttons for each existing deck
    for deck in decks:
        keyboard.append(
            [InlineKeyboardButton(deck.name, callback_data=f"{DECK_MANAGE_PREFIX}{deck.id}")]
        )

    # Add a cancel button
    keyboard.append([InlineKeyboardButton("❌ Cancel", callback_data=f"{CANCEL_PREFIX}decks")])

    reply_markup = InlineKeyboardMarkup(keyboard)

    # Count total cards across all decks
    total_cards = sum(len(deck.cards) for deck in decks)

    # Add status bar to deck management screen
    status_bar = await _get_status_bar(user_id)
    await update.message.reply_text(
        status_bar + "📚 *Deck Management*\n\n"
        f"You have {len(decks)} decks with {total_cards} total cards.\n"
        "Choose an option below:",
        reply_markup=reply_markup,
        parse_mode="Markdown",
    )

    return AWAITING_DECK_COMMAND


async def handle_deck_command(update: Update, context: CallbackContext) -> int:
    """
    Handle user selection from the deck management menu.

    Args:
        update: The update object
        context: The context object

    Returns:
        The next conversation state
    """
    query = cast(CallbackQuery, update.callback_query)
    await query.answer()

    callback_data = query.data
    user_id = str(update.effective_user.id)

    # Check if the user wants to cancel
    if callback_data.startswith(CANCEL_PREFIX):
        await query.edit_message_text("Deck management cancelled.")
        return ConversationHandler.END

    # User wants to create a new deck
    if callback_data.startswith(DECK_CREATE_PREFIX):
        await query.edit_message_text("Please enter a name for your new deck:")
        return AWAITING_DECK_NAME

    # User selected a deck to manage
    if callback_data.startswith(DECK_MANAGE_PREFIX):
        deck_id = callback_data[len(DECK_MANAGE_PREFIX) :]
        context.user_data["selected_deck_id"] = deck_id

        # Get the deck details
        deck_service = _get_deck_service()
        deck = deck_service.get_deck_with_cards(deck_id)

        if not deck:
            await query.edit_message_text("Sorry, this deck no longer exists.")
            return ConversationHandler.END

        # Store the deck name for later use
        context.user_data["selected_deck_name"] = deck.name

        # Create a keyboard with deck management options
        keyboard = [
            [InlineKeyboardButton("✏️ Rename Deck", callback_data=f"{DECK_RENAME_PREFIX}{deck_id}")],
            [InlineKeyboardButton("🗑️ Delete Deck", callback_data=f"{DECK_DELETE_PREFIX}{deck_id}")],
            [
                InlineKeyboardButton(
                    "🔄 Move Cards", callback_data=f"{DECK_MOVE_CARD_PREFIX}{deck_id}"
                )
            ],
            [InlineKeyboardButton("◀️ Back to Decks", callback_data=f"{DECK_LIST_PREFIX}back")],
            [InlineKeyboardButton("❌ Cancel", callback_data=f"{CANCEL_PREFIX}deck_manage")],
        ]

        reply_markup = InlineKeyboardMarkup(keyboard)

        # Format the message with deck details
        created_date = deck.created_at.strftime("%Y-%m-%d") if deck.created_at else "Unknown"
        message = (
            f"📚 *Deck: {deck.name}*\n\n"
            f"• Cards: {len(deck.cards)}\n"
            f"• Created: {created_date}\n\n"
            f"What would you like to do with this deck?"
        )

        await query.edit_message_text(message, reply_markup=reply_markup, parse_mode="Markdown")

        return AWAITING_DECK_COMMAND

    # User wants to go back to deck list
    if callback_data.startswith(DECK_LIST_PREFIX):
        # Clear any selected deck data
        if "selected_deck_id" in context.user_data:
            del context.user_data["selected_deck_id"]
        if "selected_deck_name" in context.user_data:
            del context.user_data["selected_deck_name"]

        # Get user's decks and show the list again
        deck_service = _get_deck_service()
        decks = deck_service.get_user_decks(user_id)

        keyboard = [
            [InlineKeyboardButton("Create New Deck", callback_data=f"{DECK_CREATE_PREFIX}new")]
        ]

        for deck in decks:
            keyboard.append(
                [InlineKeyboardButton(deck.name, callback_data=f"{DECK_MANAGE_PREFIX}{deck.id}")]
            )

        keyboard.append([InlineKeyboardButton("❌ Cancel", callback_data=f"{CANCEL_PREFIX}decks")])

        reply_markup = InlineKeyboardMarkup(keyboard)

        await query.edit_message_text(
            "📚 *Deck Management*\n\n"
            "Here are your decks. Select one to manage or create a new deck:",
            reply_markup=reply_markup,
            parse_mode="Markdown",
        )

        return AWAITING_DECK_COMMAND

    # Handle rename deck request
    if callback_data.startswith(DECK_RENAME_PREFIX):
        deck_id = callback_data[len(DECK_RENAME_PREFIX) :]
        context.user_data["rename_deck_id"] = deck_id

        # Get current deck name
        deck_service = _get_deck_service()
        deck = deck_service.get_deck_with_cards(deck_id)

        if not deck:
            await query.edit_message_text("Sorry, this deck no longer exists.")
            return ConversationHandler.END

        await query.edit_message_text(
            f"Current name: *{deck.name}*\n\n" "Please enter a new name for this deck:",
            parse_mode="Markdown",
        )

        return AWAITING_DECK_RENAME

    # Handle delete deck request
    if callback_data.startswith(DECK_DELETE_PREFIX):
        deck_id = callback_data[len(DECK_DELETE_PREFIX) :]
        context.user_data["delete_deck_id"] = deck_id

        # Get deck details
        deck_service = _get_deck_service()
        deck = deck_service.get_deck_with_cards(deck_id)

        if not deck:
            await query.edit_message_text("Sorry, this deck no longer exists.")
            return ConversationHandler.END

        # Ask for confirmation
        keyboard = [
            [
                InlineKeyboardButton(
                    "Yes, Delete", callback_data=f"{DECK_CONFIRM_DELETE_PREFIX}{deck_id}"
                ),
                InlineKeyboardButton(
                    "No, Cancel", callback_data=f"{DECK_CANCEL_DELETE_PREFIX}{deck_id}"
                ),
            ]
        ]

        reply_markup = InlineKeyboardMarkup(keyboard)

        await query.edit_message_text(
            f"⚠️ Are you sure you want to delete the deck *{deck.name}*?\n\n"
            f"This will permanently delete all {len(deck.cards)} cards in this deck. "
            f"This action cannot be undone.",
            reply_markup=reply_markup,
            parse_mode="Markdown",
        )

        return AWAITING_DECK_DELETE_CONFIRMATION

    # Handle move cards request
    if callback_data.startswith(DECK_MOVE_CARD_PREFIX):
        deck_id = callback_data[len(DECK_MOVE_CARD_PREFIX) :]
        context.user_data["source_deck_id"] = deck_id

        # Get the source deck with its cards
        deck_service = _get_deck_service()
        source_deck = deck_service.get_deck_with_cards(deck_id)

        if not source_deck or not source_deck.cards:
            await query.edit_message_text("This deck doesn't exist or has no cards to move.")
            return ConversationHandler.END

        # Store the source deck name
        context.user_data["source_deck_name"] = source_deck.name

        # Create a keyboard with all cards from the source deck
        keyboard = []
        for card in source_deck.cards:
            # Truncate card text if too long
            card_text = card.front[:30] + ("..." if len(card.front) > 30 else "")
            keyboard.append(
                [InlineKeyboardButton(card_text, callback_data=f"{DECK_MOVE_CARD_PREFIX}{card.id}")]
            )

        # Add back and cancel buttons
        keyboard.append(
            [InlineKeyboardButton("◀️ Back", callback_data=f"{DECK_MANAGE_PREFIX}{deck_id}")]
        )
        keyboard.append(
            [InlineKeyboardButton("❌ Cancel", callback_data=f"{CANCEL_PREFIX}move_cards")]
        )

        reply_markup = InlineKeyboardMarkup(keyboard)

        await query.edit_message_text(
            f"Select a card from *{source_deck.name}* to move:",
            reply_markup=reply_markup,
            parse_mode="Markdown",
        )

        return AWAITING_DECK_MOVE_CARD_SELECTION

    # Unknown callback data
    logger.warning(f"Unknown callback data in deck management: {callback_data}")
    await query.edit_message_text("Sorry, something went wrong. Please try again.")
    return ConversationHandler.END


async def handle_create_deck(update: Update, context: CallbackContext) -> int:
    """
    Handle the creation of a new deck.

    Args:
        update: The update object
        context: The context object

    Returns:
        The next conversation state
    """
    user_id = str(update.effective_user.id)
    new_deck_name = update.message.text

    # Create the new deck
    deck_service = _get_deck_service()

    try:
        creation_date = (
            update.message.date.strftime("%Y-%m-%d") if update.message.date else "unknown date"
        )
        new_deck = deck_service.create_deck(
            name=new_deck_name, user_id=user_id, description=f"Created on {creation_date}"
        )

        # Create a keyboard to go back to deck list
        keyboard = [
            [InlineKeyboardButton("◀️ Back to Decks", callback_data=f"{DECK_LIST_PREFIX}back")],
            [InlineKeyboardButton("❌ Close", callback_data=f"{CANCEL_PREFIX}after_create")],
        ]

        reply_markup = InlineKeyboardMarkup(keyboard)

        await update.message.reply_text(
            f"✅ Deck *{new_deck_name}* created successfully!",
            reply_markup=reply_markup,
            parse_mode="Markdown",
        )

        return AWAITING_DECK_COMMAND

    except Exception as e:
        logger.error(f"Error creating deck: {e}")
        await update.message.reply_text(
            "Sorry, there was an error creating your deck. Please try again."
        )
        return ConversationHandler.END


async def handle_rename_deck(update: Update, context: CallbackContext) -> int:
    """
    Handle renaming an existing deck.

    Args:
        update: The update object
        context: The context object

    Returns:
        The next conversation state
    """
    user_id = str(update.effective_user.id)
    new_name = update.message.text
    deck_id = context.user_data.get("rename_deck_id")

    if not deck_id:
        await update.message.reply_text("Sorry, I couldn't find the deck you're trying to rename.")
        return ConversationHandler.END

    # Rename the deck
    deck_service = _get_deck_service()

    try:
        updated_deck = deck_service.rename_deck(deck_id, new_name)

        # Create a keyboard to go back to deck management
        keyboard = [
            [
                InlineKeyboardButton(
                    "◀️ Back to Deck", callback_data=f"{DECK_MANAGE_PREFIX}{deck_id}"
                )
            ],
            [InlineKeyboardButton("📚 All Decks", callback_data=f"{DECK_LIST_PREFIX}back")],
            [InlineKeyboardButton("❌ Close", callback_data=f"{CANCEL_PREFIX}after_rename")],
        ]

        reply_markup = InlineKeyboardMarkup(keyboard)

        await update.message.reply_text(
            f"✅ Deck renamed to *{new_name}* successfully!",
            reply_markup=reply_markup,
            parse_mode="Markdown",
        )

        # Update the stored deck name
        context.user_data["selected_deck_name"] = new_name

        return AWAITING_DECK_COMMAND

    except Exception as e:
        logger.error(f"Error renaming deck: {e}")
        await update.message.reply_text(
            "Sorry, there was an error renaming your deck. Please try again."
        )
        return ConversationHandler.END


async def handle_delete_deck_confirmation(update: Update, context: CallbackContext) -> int:
    """
    Handle confirmation of deck deletion.

    Args:
        update: The update object
        context: The context object

    Returns:
        The next conversation state
    """
    query = cast(CallbackQuery, update.callback_query)
    await query.answer()

    callback_data = query.data
    user_id = str(update.effective_user.id)

    # User cancelled deletion
    if callback_data.startswith(DECK_CANCEL_DELETE_PREFIX):
        deck_id = callback_data[len(DECK_CANCEL_DELETE_PREFIX) :]

        await query.edit_message_text(
            "Deck deletion cancelled. Your deck is safe.",
            reply_markup=InlineKeyboardMarkup(
                [
                    [
                        InlineKeyboardButton(
                            "◀️ Back to Deck", callback_data=f"{DECK_MANAGE_PREFIX}{deck_id}"
                        )
                    ]
                ]
            ),
        )

        return AWAITING_DECK_COMMAND

    # User confirmed deletion
    if callback_data.startswith(DECK_CONFIRM_DELETE_PREFIX):
        deck_id = callback_data[len(DECK_CONFIRM_DELETE_PREFIX) :]
        deck_name = context.user_data.get("selected_deck_name", "Unknown deck")

        # Delete the deck
        deck_service = _get_deck_service()

        try:
            success = deck_service.delete_deck(deck_id)

            if success:
                await query.edit_message_text(
                    f"✅ Deck *{deck_name}* has been deleted.",
                    parse_mode="Markdown",
                    reply_markup=InlineKeyboardMarkup(
                        [
                            [
                                InlineKeyboardButton(
                                    "◀️ Back to Decks", callback_data=f"{DECK_LIST_PREFIX}back"
                                )
                            ]
                        ]
                    ),
                )
            else:
                await query.edit_message_text(
                    "Sorry, there was an error deleting the deck.",
                    reply_markup=InlineKeyboardMarkup(
                        [
                            [
                                InlineKeyboardButton(
                                    "◀️ Back to Decks", callback_data=f"{DECK_LIST_PREFIX}back"
                                )
                            ]
                        ]
                    ),
                )

            # Clean up user data
            if "selected_deck_id" in context.user_data:
                del context.user_data["selected_deck_id"]
            if "selected_deck_name" in context.user_data:
                del context.user_data["selected_deck_name"]
            if "delete_deck_id" in context.user_data:
                del context.user_data["delete_deck_id"]

            return AWAITING_DECK_COMMAND

        except Exception as e:
            logger.error(f"Error deleting deck: {e}")
            await query.edit_message_text(
                "Sorry, there was an error deleting your deck. Please try again.",
                reply_markup=InlineKeyboardMarkup(
                    [
                        [
                            InlineKeyboardButton(
                                "◀️ Back to Decks", callback_data=f"{DECK_LIST_PREFIX}back"
                            )
                        ]
                    ]
                ),
            )
            return AWAITING_DECK_COMMAND

    # Unknown callback data
    logger.warning(f"Unknown callback data in deck deletion confirmation: {callback_data}")
    await query.edit_message_text(
        "Sorry, something went wrong. Please try again.",
        reply_markup=InlineKeyboardMarkup(
            [[InlineKeyboardButton("◀️ Back to Decks", callback_data=f"{DECK_LIST_PREFIX}back")]]
        ),
    )
    return AWAITING_DECK_COMMAND


async def handle_move_card_selection(update: Update, context: CallbackContext) -> int:
    """
    Handle selection of a card to move between decks.

    Args:
        update: The update object
        context: The context object

    Returns:
        The next conversation state
    """
    query = cast(CallbackQuery, update.callback_query)
    await query.answer()

    callback_data = query.data
    user_id = str(update.effective_user.id)

    # Check if the user wants to cancel
    if callback_data.startswith(CANCEL_PREFIX):
        await query.edit_message_text("Card move operation cancelled.")
        return ConversationHandler.END

    # Check if user wants to go back to deck management
    if callback_data.startswith(DECK_MANAGE_PREFIX):
        deck_id = callback_data[len(DECK_MANAGE_PREFIX) :]
        # Clear any move-related data
        for key in ["source_deck_id", "source_deck_name", "card_to_move_id"]:
            if key in context.user_data:
                del context.user_data[key]

        # Redirect to deck management
        return await handle_deck_command(update, context)

    # User selected a card to move
    if callback_data.startswith(DECK_MOVE_CARD_PREFIX):
        card_id = callback_data[len(DECK_MOVE_CARD_PREFIX) :]
        source_deck_id = context.user_data.get("source_deck_id")

        if not source_deck_id:
            await query.edit_message_text("Sorry, I couldn't find the source deck.")
            return ConversationHandler.END

        # Store the card ID to move
        context.user_data["card_to_move_id"] = card_id

        # Get the flashcard details
        deck_service = _get_deck_service()
        flashcard_repo = deck_service.flashcard_repo
        card = flashcard_repo.get(card_id)

        if not card:
            await query.edit_message_text("Sorry, I couldn't find the card you selected.")
            return ConversationHandler.END

        # Store card front for reference
        context.user_data["card_to_move_front"] = card.front

        # Get all decks except the source deck
        decks = deck_service.get_user_decks(user_id)
        target_decks = [deck for deck in decks if deck.id != source_deck_id]

        if not target_decks:
            await query.edit_message_text(
                "You don't have any other decks to move this card to. "
                "Please create another deck first."
            )
            return ConversationHandler.END

        # Create a keyboard with target decks
        keyboard = []
        for deck in target_decks:
            keyboard.append(
                [InlineKeyboardButton(deck.name, callback_data=f"{DECK_PREFIX}{deck.id}")]
            )

        # Add back and cancel buttons
        keyboard.append(
            [
                InlineKeyboardButton(
                    "◀️ Back", callback_data=f"{DECK_MOVE_CARD_PREFIX}{source_deck_id}"
                )
            ]
        )
        keyboard.append(
            [InlineKeyboardButton("❌ Cancel", callback_data=f"{CANCEL_PREFIX}move_card_target")]
        )

        reply_markup = InlineKeyboardMarkup(keyboard)

        # Truncate card text if too long
        card_text = card.front[:50] + ("..." if len(card.front) > 50 else "")

        await query.edit_message_text(
            f"Select a destination deck for card:\n" f"*{card_text}*",
            reply_markup=reply_markup,
            parse_mode="Markdown",
        )

        return AWAITING_DECK_MOVE_TARGET_SELECTION

    # Unknown callback data
    logger.warning(f"Unknown callback data in move card selection: {callback_data}")
    await query.edit_message_text("Sorry, something went wrong. Please try again.")
    return ConversationHandler.END


async def handle_move_card_target_selection(update: Update, context: CallbackContext) -> int:
    """
    Handle selection of a target deck for moving a card.

    Args:
        update: The update object
        context: The context object

    Returns:
        The next conversation state
    """
    query = cast(CallbackQuery, update.callback_query)
    await query.answer()

    callback_data = query.data
    user_id = str(update.effective_user.id)

    # Check if the user wants to cancel
    if callback_data.startswith(CANCEL_PREFIX):
        await query.edit_message_text("Card move operation cancelled.")
        return ConversationHandler.END

    # Check if user wants to go back to card selection
    if callback_data.startswith(DECK_MOVE_CARD_PREFIX):
        source_deck_id = callback_data[len(DECK_MOVE_CARD_PREFIX) :]
        # Clear the selected card
        if "card_to_move_id" in context.user_data:
            del context.user_data["card_to_move_id"]
        if "card_to_move_front" in context.user_data:
            del context.user_data["card_to_move_front"]

        # Go back to card selection from source deck
        deck_service = _get_deck_service()
        source_deck = deck_service.get_deck_with_cards(source_deck_id)

        if not source_deck or not source_deck.cards:
            await query.edit_message_text("This deck doesn't exist or has no cards to move.")
            return ConversationHandler.END

        # Create a keyboard with all cards from the source deck
        keyboard = []
        for card in source_deck.cards:
            # Truncate card text if too long
            card_text = card.front[:30] + ("..." if len(card.front) > 30 else "")
            keyboard.append(
                [InlineKeyboardButton(card_text, callback_data=f"{DECK_MOVE_CARD_PREFIX}{card.id}")]
            )

        # Add back and cancel buttons
        keyboard.append(
            [InlineKeyboardButton("◀️ Back", callback_data=f"{DECK_MANAGE_PREFIX}{source_deck_id}")]
        )
        keyboard.append(
            [InlineKeyboardButton("❌ Cancel", callback_data=f"{CANCEL_PREFIX}move_cards")]
        )

        reply_markup = InlineKeyboardMarkup(keyboard)

        await query.edit_message_text(
            f"Select a card from *{source_deck.name}* to move:",
            reply_markup=reply_markup,
            parse_mode="Markdown",
        )

        return AWAITING_DECK_MOVE_CARD_SELECTION

    # User selected a target deck
    if callback_data.startswith(DECK_PREFIX):
        target_deck_id = callback_data[len(DECK_PREFIX) :]
        card_id = context.user_data.get("card_to_move_id")
        source_deck_id = context.user_data.get("source_deck_id")
        card_front = context.user_data.get("card_to_move_front", "selected card")

        if not card_id or not source_deck_id:
            await query.edit_message_text("Sorry, I couldn't find the card or source deck.")
            return ConversationHandler.END

        # Move the card to the target deck
        deck_service = _get_deck_service()

        try:
            # Get deck names for the message
            source_deck = deck_service.get_deck_with_cards(source_deck_id)
            target_deck = deck_service.get_deck_with_cards(target_deck_id)

            if not source_deck or not target_deck:
                await query.edit_message_text("Sorry, one of the decks no longer exists.")
                return ConversationHandler.END

            # Move the card
            moved_card = deck_service.move_card_to_deck(card_id, target_deck_id)

            # Create a keyboard to go back
            keyboard = [
                [
                    InlineKeyboardButton(
                        "◀️ Back to Source Deck",
                        callback_data=f"{DECK_MANAGE_PREFIX}{source_deck_id}",
                    )
                ],
                [InlineKeyboardButton("📚 All Decks", callback_data=f"{DECK_LIST_PREFIX}back")],
                [InlineKeyboardButton("❌ Close", callback_data=f"{CANCEL_PREFIX}after_move")],
            ]

            reply_markup = InlineKeyboardMarkup(keyboard)

            # Truncate card text if too long
            card_text = card_front[:30] + ("..." if len(card_front) > 30 else "")

            await query.edit_message_text(
                f"✅ Card *{card_text}* moved successfully from "
                f"*{source_deck.name}* to *{target_deck.name}*.",
                reply_markup=reply_markup,
                parse_mode="Markdown",
            )

            # Clean up user data
            for key in ["card_to_move_id", "card_to_move_front"]:
                if key in context.user_data:
                    del context.user_data[key]

            return AWAITING_DECK_COMMAND

        except Exception as e:
            logger.error(f"Error moving card: {e}")
            await query.edit_message_text(
                "Sorry, there was an error moving the card. Please try again.",
                reply_markup=InlineKeyboardMarkup(
                    [
                        [
                            InlineKeyboardButton(
                                "◀️ Back to Decks", callback_data=f"{DECK_LIST_PREFIX}back"
                            )
                        ]
                    ]
                ),
            )
            return AWAITING_DECK_COMMAND

    # Unknown callback data
    logger.warning(f"Unknown callback data in move target selection: {callback_data}")
    await query.edit_message_text("Sorry, something went wrong. Please try again.")
    return ConversationHandler.END


# Helper functions


def _get_user_service() -> UserService:
    """Create and return a UserService instance."""
    db = Database()
    preferences_repo = SQLiteUserPreferencesRepository(db)
    return UserService(preferences_repo)


def _get_flashcard_service() -> FlashcardService:
    """Create and return a FlashcardService instance."""
    db = Database()
    flashcard_repo = SQLiteFlashcardRepository(db)
    deck_repo = SQLiteDeckRepository(db)
    llm_client = LLMClient()
    user_service = _get_user_service()

    return FlashcardService(flashcard_repo, deck_repo, llm_client, user_service)


def _get_deck_service() -> DeckService:
    """Create and return a DeckService instance."""
    db = Database()
    deck_repo = SQLiteDeckRepository(db)
    flashcard_repo = SQLiteFlashcardRepository(db)
    llm_client = LLMClient()
    user_service = _get_user_service()

    return DeckService(deck_repo, flashcard_repo, llm_client, user_service)


def _get_review_service() -> ReviewService:
    """Create and return a ReviewService instance."""
    db = Database()
    deck_repo = SQLiteDeckRepository(db)
    flashcard_repo = SQLiteFlashcardRepository(db)
    llm_client = LLMClient()

    return ReviewService(deck_repo, flashcard_repo, llm_client)


def _format_card_back(content: Dict[str, Any]) -> str:
    """Format the back of the flashcard using the content from the preview."""
    back = (
        f"*Definition:* {content.get('definition', 'N/A')}\n\n"
        f"*Example:* {content.get('example_sentence', 'N/A')}\n\n"
        f"*Pronunciation:* {content.get('pronunciation_guide', 'N/A')}\n"
        f"*Part of Speech:* {content.get('part_of_speech', 'N/A')}\n\n"
    )

    notes = content.get("notes")
    if notes:
        back += f"*Notes:* {notes}\n"

    return back


async def _get_status_bar(user_id: str) -> str:
    """
    Generate status bar displaying the user's current preferences.

    Args:
        user_id: The ID of the user

    Returns:
        Formatted status bar string with Markdown formatting
    """
    user_service = _get_user_service()
    user_prefs = user_service.get_user_preferences(user_id)

    # Get deck name if available
    deck_name = "None"
    if user_prefs.last_deck_id:
        deck_service = _get_deck_service()
        deck = deck_service.deck_repo.get(user_prefs.last_deck_id)
        if deck:
            deck_name = deck.name

    # Format language codes to be more readable
    current_language = user_prefs.last_language.upper()
    native_language = user_prefs.native_language.upper()

    # Format learning languages list
    learning_langs = [lang.upper() for lang in user_prefs.learning_languages]
    learning_langs_str = ", ".join(learning_langs)

    # Create first line with current deck and language
    status_line1 = f"📍 *Current Deck:* {deck_name} | *Language:* {current_language}\n"

    # Create second line with native language and learning languages
    status_line2 = f"👤 *Native:* {native_language} | *Learning:* {learning_langs_str}\n"

    # Create status bar with divider
    status_bar = status_line1 + status_line2 + "┄" * 30 + "\n\n"
    return status_bar
