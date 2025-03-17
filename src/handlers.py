"""
Command handlers for the Telegram Anki Flashcards bot.
"""

import logging
import json
from typing import Dict, Any, Optional, cast, Union, Coroutine

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, CallbackQuery
from telegram.ext import CallbackContext, ConversationHandler

from src.services import FlashcardService, DeckService
from src.models import Deck
from src.llm import LLMClient
from src.repository import SQLiteDeckRepository, SQLiteFlashcardRepository
from src.database import Database

logger = logging.getLogger('ankichat')

# Conversation states
(
    AWAITING_CARD_TEXT,
    AWAITING_CONFIRMATION,
    AWAITING_DECK_SELECTION,
    AWAITING_EDIT
) = range(4)

# Callback data prefixes
CONFIRM_PREFIX = "confirm_"
EDIT_PREFIX = "edit_"
DECK_PREFIX = "deck_"
CANCEL_PREFIX = "cancel_"

# Direct text conversation map
# This is used to store conversation state for direct text input
# outside of the built-in ConversationHandler
DIRECT_CONVERSATIONS = {}

# Direct conversation state constants
DIRECT_AWAITING_CONFIRMATION = 'awaiting_confirmation'
DIRECT_AWAITING_DECK_SELECTION = 'awaiting_deck_selection'


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
        f"• /stats - View your learning statistics\n"
        f"• /help - Get more detailed instructions\n\n"
        f"You can also simply send any word or phrase to create a flashcard right away!\n\n"
        f"Let's start learning together! 🚀"
    )
    
    await update.message.reply_text(welcome_message)
    
async def help_command(update: Update, context: CallbackContext) -> None:
    """Handle the /help command."""
    logger.info(f"User {update.effective_user.id} requested help")
    
    help_text = (
        "📚 *AnkiChat Bot Help*\n\n"
        "*Available Commands:*\n"
        "• /start - Start the bot and see welcome message\n"
        "• /new - Create a new flashcard\n"
        "• /review - Start reviewing due cards\n"
        "• /stats - View your learning statistics\n"
        "• /help - Show this help message\n\n"
        
        "*Creating Flashcards:*\n"
        "There are two ways to create flashcards:\n"
        "1. Just send any word or phrase directly to the bot\n"
        "2. Use /new and follow the prompts\n\n"
        
        "*Reviewing Cards:*\n"
        "Use /review to start a review session. For each card, you'll see the front side "
        "and need to recall the answer. After viewing the answer, rate how well you remembered it.\n\n"
        
        "*Spaced Repetition:*\n"
        "Cards will reappear for review based on how well you remembered them - "
        "the better you know a card, the longer until you see it again."
    )
    
    await update.message.reply_text(help_text, parse_mode="Markdown")


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
    
    # Process the text just like the regular card creation flow
    await _process_flashcard_input(update, context)
    
    # Store in our direct conversations map to handle callbacks properly
    DIRECT_CONVERSATIONS[chat_id] = DIRECT_AWAITING_CONFIRMATION
    logger.info(f"User {user_id} started direct flashcard creation, state: {DIRECT_CONVERSATIONS[chat_id]}")


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
    
    # Send a processing message
    processing_message = await update.message.reply_text(
        "Processing your request... This may take a moment."
    )
    
    # Get the services
    flashcard_service = _get_flashcard_service()
    
    try:
        # Process the text and generate a preview
        preview = await flashcard_service.process_new_card_text(text, str(user.id))
        
        # Store the preview in the context for later use
        context.user_data["preview"] = preview
        
        # Format the preview message
        message_text = flashcard_service.format_preview_message(preview)
        
        # Create inline keyboard
        keyboard = [
            [
                InlineKeyboardButton("✅ Save", callback_data=f"{CONFIRM_PREFIX}{preview['preview_id']}"),
                InlineKeyboardButton("✏️ Edit", callback_data=f"{EDIT_PREFIX}{preview['preview_id']}")
            ],
            [
                InlineKeyboardButton("❌ Cancel", callback_data=f"{CANCEL_PREFIX}{preview['preview_id']}")
            ]
        ]
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        # Edit the processing message with the preview
        await processing_message.edit_text(
            message_text,
            reply_markup=reply_markup,
            parse_mode="Markdown"
        )
        
    except Exception as e:
        logger.error(f"Error processing card text: {e}")
        await processing_message.edit_text(
            "Sorry, there was an error processing your request. Please try again."
        )


async def handle_callback_for_direct_input(update: Update, context: CallbackContext) -> Optional[int]:
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
    if not (callback_data.startswith(CONFIRM_PREFIX) or
            callback_data.startswith(EDIT_PREFIX) or
            callback_data.startswith(CANCEL_PREFIX)):
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
        preview_id = callback_data[len(CONFIRM_PREFIX):]
        
        # Get user's decks
        deck_service = _get_deck_service()
        decks = deck_service.get_user_decks(user_id)
        
        if not decks:
            # Create a default deck if user doesn't have any
            default_deck = deck_service.create_deck(
                name="My First Deck",
                user_id=user_id,
                description="Default deck created automatically"
            )
            decks = [default_deck]
        
        # Store the preview ID for later
        context.user_data["confirmed_preview_id"] = preview_id
        
        # Create inline keyboard with decks
        keyboard = []
        for deck in decks:
            keyboard.append([
                InlineKeyboardButton(deck.name, callback_data=f"{DECK_PREFIX}{deck.id}")
            ])
        
        # Add a cancel button
        keyboard.append([
            InlineKeyboardButton("❌ Cancel", callback_data=f"{CANCEL_PREFIX}{preview_id}")
        ])
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        # Ask user to select a deck
        await query.edit_message_text(
            "Please select a deck for this flashcard:",
            reply_markup=reply_markup
        )
        
        # Update the state for direct conversations
        if is_direct:
            DIRECT_CONVERSATIONS[chat_id] = DIRECT_AWAITING_DECK_SELECTION
            logger.info(f"Updated direct conversation state to {DIRECT_AWAITING_DECK_SELECTION}")
            
        return AWAITING_DECK_SELECTION
    
    # Check if the user wants to edit
    if callback_data.startswith(EDIT_PREFIX):
        preview_id = callback_data[len(EDIT_PREFIX):]
        
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
    if not (callback_data.startswith(DECK_PREFIX) or
            callback_data.startswith(CANCEL_PREFIX)):
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
        deck_id = callback_data[len(DECK_PREFIX):]
        preview_id = context.user_data.get("confirmed_preview_id")
        
        if not preview_id:
            logger.error("No preview ID found in user data")
            await query.edit_message_text(
                "Sorry, something went wrong. Please try again."
            )
            
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
                "language": content.get("language_code", "en")
            }
            
            flashcard = await flashcard_service.create_flashcard_from_preview(
                preview_id=preview_id,
                deck_id=deck_id,
                user_edits=user_edits
            )
            
            # Notify the user
            await query.edit_message_text(
                f"✅ Flashcard created successfully!\n\n"
                f"*Front:* {flashcard.front}\n"
                f"*Added to deck:* {deck_id}\n\n"
                f"Use /review to start practicing.",
                parse_mode="Markdown"
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


# Helper functions

def _get_flashcard_service() -> FlashcardService:
    """Create and return a FlashcardService instance."""
    db = Database()
    flashcard_repo = SQLiteFlashcardRepository(db)
    deck_repo = SQLiteDeckRepository(db)
    llm_client = LLMClient()
    
    return FlashcardService(flashcard_repo, deck_repo, llm_client)


def _get_deck_service() -> DeckService:
    """Create and return a DeckService instance."""
    db = Database()
    deck_repo = SQLiteDeckRepository(db)
    
    return DeckService(deck_repo)


def _format_card_back(content: Dict[str, Any]) -> str:
    """Format the back of the flashcard using the content from the preview."""
    back = (
        f"*Definition:* {content.get('definition', 'N/A')}\n\n"
        f"*Example:* {content.get('example_sentence', 'N/A')}\n\n"
        f"*Pronunciation:* {content.get('pronunciation_guide', 'N/A')}\n"
        f"*Part of Speech:* {content.get('part_of_speech', 'N/A')}\n\n"
    )
    
    notes = content.get('notes')
    if notes:
        back += f"*Notes:* {notes}\n"
    
    return back