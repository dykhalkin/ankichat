"""Handlers for managing user preferences in the AnkiChat application."""

import logging
from typing import cast

from telegram import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import CallbackContext, ConversationHandler

from src.handlers import _get_status_bar, _get_user_service

logger = logging.getLogger("ankichat")

# Conversation states
(
    AWAITING_NATIVE_LANGUAGE,
    AWAITING_LEARNING_LANGUAGE_ACTION,
    AWAITING_LEARNING_LANGUAGE_SELECTION,
    AWAITING_SETTINGS_ACTION,
) = range(4)

# Callback data prefixes
LANG_PREFIX = "lang_"
ADD_LANG_PREFIX = "add_lang_"
REMOVE_LANG_PREFIX = "remove_lang_"
CANCEL_PREFIX = "cancel_"
SETTING_PREFIX = "setting_"
BACK_PREFIX = "back_"

# Common language codes and their full names
COMMON_LANGUAGES = {
    "en": "English",
    "es": "Spanish",
    "fr": "French",
    "de": "German",
    "it": "Italian",
    "ru": "Russian",
    "zh": "Chinese",
    "ja": "Japanese",
    "ko": "Korean",
    "ar": "Arabic",
    "pt": "Portuguese",
    "nl": "Dutch",
    "pl": "Polish",
    "sv": "Swedish",
    "tr": "Turkish",
    "uk": "Ukrainian",
    "vi": "Vietnamese",
    "th": "Thai",
}


async def native_language_command(update: Update, context: CallbackContext) -> int:
    """
    Command handler for /native - sets the user's native language.

    Args:
        update: The update object
        context: The context object

    Returns:
        The next conversation state
    """
    user_id = str(update.effective_user.id)
    logger.info(f"User {user_id} is setting their native language")

    # Get current user preferences
    user_service = _get_user_service()
    user_prefs = user_service.get_user_preferences(user_id)

    # Create keyboard with language options
    keyboard = []

    # Build language option buttons - 3 per row for better UX
    row = []
    for i, (code, name) in enumerate(COMMON_LANGUAGES.items()):
        is_current = code == user_prefs.native_language
        label = f"{name} {'✓' if is_current else ''}"
        button = InlineKeyboardButton(label, callback_data=f"{LANG_PREFIX}{code}")

        row.append(button)
        if len(row) == 3 or i == len(COMMON_LANGUAGES) - 1:
            keyboard.append(row)
            row = []

    # Add cancel button
    keyboard.append([InlineKeyboardButton("❌ Cancel", callback_data=f"{CANCEL_PREFIX}native")])

    reply_markup = InlineKeyboardMarkup(keyboard)

    # Add status bar to show current settings
    status_bar = await _get_status_bar(user_id)
    await update.message.reply_text(
        status_bar + "Please select your native language:",
        reply_markup=reply_markup,
        parse_mode="Markdown",
    )

    return AWAITING_NATIVE_LANGUAGE


async def handle_native_language_selection(update: Update, context: CallbackContext) -> int:
    """
    Handle the native language selection.

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
        await query.edit_message_text("Operation cancelled.")
        return ConversationHandler.END

    # Check if user wants to go back to settings
    if callback_data.startswith(BACK_PREFIX):
        # Return to main settings menu
        return await settings_command(update, context)

    # Check if the user selected a language
    if callback_data.startswith(LANG_PREFIX):
        language_code = callback_data[len(LANG_PREFIX) :]

        # Update the user's native language
        user_service = _get_user_service()
        user_service.set_native_language(user_id, language_code)

        # Get the language name for confirmation message
        language_name = COMMON_LANGUAGES.get(language_code, language_code.upper())

        # Create a fresh status bar that reflects the change
        status_bar = await _get_status_bar(user_id)

        await query.edit_message_text(
            status_bar + f"✅ Your native language has been set to *{language_name}*.",
            parse_mode="Markdown",
        )

        return ConversationHandler.END

    # Unknown callback data
    logger.warning(f"Unknown callback data: {callback_data}")
    await query.edit_message_text("Sorry, something went wrong. Please try again.")
    return ConversationHandler.END


async def learning_languages_command(update: Update, context: CallbackContext) -> int:
    """
    Command handler for /learn - manages languages being learned.

    Args:
        update: The update object
        context: The context object

    Returns:
        The next conversation state
    """
    user_id = str(update.effective_user.id)
    logger.info(f"User {user_id} is managing their learning languages")

    # Get current user preferences
    user_service = _get_user_service()
    user_prefs = user_service.get_user_preferences(user_id)

    # Create keyboard with action options
    keyboard = [
        [InlineKeyboardButton("➕ Add a language", callback_data=f"{ADD_LANG_PREFIX}select")],
        [InlineKeyboardButton("➖ Remove a language", callback_data=f"{REMOVE_LANG_PREFIX}select")],
        [InlineKeyboardButton("❌ Cancel", callback_data=f"{CANCEL_PREFIX}learn")],
    ]

    reply_markup = InlineKeyboardMarkup(keyboard)

    # Format the list of currently learning languages
    learning_languages = [
        COMMON_LANGUAGES.get(code, code.upper()) for code in user_prefs.learning_languages
    ]
    learning_list = "\n• ".join(learning_languages)

    # Add status bar to show current settings
    status_bar = await _get_status_bar(user_id)
    await update.message.reply_text(
        status_bar
        + f"*Languages you're currently learning:*\n• {learning_list}\n\nWhat would you like to do?",
        reply_markup=reply_markup,
        parse_mode="Markdown",
    )

    return AWAITING_LEARNING_LANGUAGE_ACTION


async def handle_learning_language_action(update: Update, context: CallbackContext) -> int:
    """
    Handle the learning language action selection (add or remove).

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
        await query.edit_message_text("Operation cancelled.")
        return ConversationHandler.END

    # Check if user wants to go back to settings
    if callback_data.startswith(BACK_PREFIX):
        # Return to main settings menu
        return await settings_command(update, context)

    # Get user preferences
    user_service = _get_user_service()
    user_prefs = user_service.get_user_preferences(user_id)

    # Check if the user wants to add a language
    if callback_data.startswith(ADD_LANG_PREFIX):
        # Create keyboard with language options that aren't already being learned
        keyboard = []
        row = []

        for i, (code, name) in enumerate(COMMON_LANGUAGES.items()):
            # Skip languages already being learned
            if code in user_prefs.learning_languages:
                continue

            button = InlineKeyboardButton(name, callback_data=f"{ADD_LANG_PREFIX}{code}")
            row.append(button)

            if len(row) == 3 or i == len(COMMON_LANGUAGES) - 1:
                if row:  # Only add non-empty rows
                    keyboard.append(row)
                row = []

        # Add cancel button
        keyboard.append([InlineKeyboardButton("❌ Cancel", callback_data=f"{CANCEL_PREFIX}add")])

        # Add back button if coming from settings
        if "from_settings" in context.user_data and context.user_data["from_settings"]:
            keyboard.append(
                [InlineKeyboardButton("◀️ Back to Settings", callback_data=f"{BACK_PREFIX}settings")]
            )

        reply_markup = InlineKeyboardMarkup(keyboard)

        await query.edit_message_text(
            "Select a language to add to your learning list:", reply_markup=reply_markup
        )

        return AWAITING_LEARNING_LANGUAGE_SELECTION

    # Check if the user wants to remove a language
    if callback_data.startswith(REMOVE_LANG_PREFIX):
        # Create keyboard with languages currently being learned
        keyboard = []

        for code in user_prefs.learning_languages:
            name = COMMON_LANGUAGES.get(code, code.upper())
            keyboard.append(
                [InlineKeyboardButton(name, callback_data=f"{REMOVE_LANG_PREFIX}{code}")]
            )

        # Add cancel button
        keyboard.append([InlineKeyboardButton("❌ Cancel", callback_data=f"{CANCEL_PREFIX}remove")])

        # Add back button if coming from settings
        if "from_settings" in context.user_data and context.user_data["from_settings"]:
            keyboard.append(
                [InlineKeyboardButton("◀️ Back to Settings", callback_data=f"{BACK_PREFIX}settings")]
            )

        reply_markup = InlineKeyboardMarkup(keyboard)

        await query.edit_message_text(
            "Select a language to remove from your learning list:", reply_markup=reply_markup
        )

        return AWAITING_LEARNING_LANGUAGE_SELECTION

    # Unknown callback data
    logger.warning(f"Unknown callback data: {callback_data}")
    await query.edit_message_text("Sorry, something went wrong. Please try again.")
    return ConversationHandler.END


async def handle_learning_language_selection(update: Update, context: CallbackContext) -> int:
    """
    Handle the selection of a specific language to add or remove.

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
        await query.edit_message_text("Operation cancelled.")
        return ConversationHandler.END

    # Check if user wants to go back to settings
    if callback_data.startswith(BACK_PREFIX):
        # Return to main settings menu
        return await settings_command(update, context)

    user_service = _get_user_service()

    # Check if the user is adding a language
    if callback_data.startswith(ADD_LANG_PREFIX):
        language_code = callback_data[len(ADD_LANG_PREFIX) :]

        # Add the language to the user's learning languages
        user_service.add_learning_language(user_id, language_code)

        # Get the language name for confirmation message
        language_name = COMMON_LANGUAGES.get(language_code, language_code.upper())

        # Create a fresh status bar that reflects the change
        status_bar = await _get_status_bar(user_id)

        await query.edit_message_text(
            status_bar + f"✅ *{language_name}* has been added to your learning languages.",
            parse_mode="Markdown",
        )

        return ConversationHandler.END

    # Check if the user is removing a language
    if callback_data.startswith(REMOVE_LANG_PREFIX):
        language_code = callback_data[len(REMOVE_LANG_PREFIX) :]

        # Remove the language from the user's learning languages
        user_service.remove_learning_language(user_id, language_code)

        # Get the language name for confirmation message
        language_name = COMMON_LANGUAGES.get(language_code, language_code.upper())

        # Create a fresh status bar that reflects the change
        status_bar = await _get_status_bar(user_id)

        await query.edit_message_text(
            status_bar + f"✅ *{language_name}* has been removed from your learning languages.",
            parse_mode="Markdown",
        )

        return ConversationHandler.END

    # Unknown callback data
    logger.warning(f"Unknown callback data: {callback_data}")
    await query.edit_message_text("Sorry, something went wrong. Please try again.")
    return ConversationHandler.END


async def settings_command(update: Update, context: CallbackContext) -> int:
    """
    Command handler for /settings - displays all user preferences and allows modifications.

    Args:
        update: The update object
        context: The context object

    Returns:
        The next conversation state
    """
    user_id = str(update.effective_user.id)
    logger.info(f"User {user_id} is accessing settings")

    # Get current user preferences
    user_service = _get_user_service()
    user_prefs = user_service.get_user_preferences(user_id)

    # Get the deck name
    deck_name = "None"
    if user_prefs.last_deck_id:
        from src.handlers import _get_deck_service

        deck_service = _get_deck_service()
        deck = deck_service.deck_repo.get(user_prefs.last_deck_id)
        if deck:
            deck_name = deck.name

    # Get language names
    current_language = COMMON_LANGUAGES.get(
        user_prefs.last_language, user_prefs.last_language.upper()
    )
    native_language = COMMON_LANGUAGES.get(
        user_prefs.native_language, user_prefs.native_language.upper()
    )

    # Format learning languages
    learning_languages = [
        COMMON_LANGUAGES.get(code, code.upper()) for code in user_prefs.learning_languages
    ]
    learning_list = ", ".join(learning_languages)

    # Create message with all settings
    settings_message = (
        f"*📊 User Settings*\n\n"
        f"*Current Deck:* {deck_name}\n"
        f"*Current Language:* {current_language}\n"
        f"*Native Language:* {native_language}\n"
        f"*Learning Languages:* {learning_list}\n\n"
        f"Select a setting to change:"
    )

    # Create keyboard with settings options
    keyboard = [
        [
            InlineKeyboardButton(
                "🌐 Change Native Language", callback_data=f"{SETTING_PREFIX}native"
            )
        ],
        [
            InlineKeyboardButton(
                "📚 Manage Learning Languages", callback_data=f"{SETTING_PREFIX}learn"
            )
        ],
        [InlineKeyboardButton("❌ Close", callback_data=f"{CANCEL_PREFIX}settings")],
    ]

    reply_markup = InlineKeyboardMarkup(keyboard)

    # Store that we're in settings mode
    context.user_data["from_settings"] = True

    # Check if this is from a message or callback query
    if update.message:
        await update.message.reply_text(
            settings_message, reply_markup=reply_markup, parse_mode="Markdown"
        )
    else:
        # It's from a callback query
        query = cast(CallbackQuery, update.callback_query)
        await query.edit_message_text(
            settings_message, reply_markup=reply_markup, parse_mode="Markdown"
        )

    return AWAITING_SETTINGS_ACTION


async def handle_settings_action(update: Update, context: CallbackContext) -> int:
    """
    Handle the settings menu actions.

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

    # Check if the user wants to cancel/close
    if callback_data.startswith(CANCEL_PREFIX):
        await query.edit_message_text("Settings closed.")
        return ConversationHandler.END

    # Check if the user selected a setting to change
    if callback_data.startswith(SETTING_PREFIX):
        action = callback_data[len(SETTING_PREFIX) :]

        # Handle native language change
        if action == "native":
            # Get current user preferences
            user_service = _get_user_service()
            user_prefs = user_service.get_user_preferences(user_id)

            # Create keyboard with language options
            keyboard = []
            row = []

            # Build language option buttons - 3 per row for better UX
            for i, (code, name) in enumerate(COMMON_LANGUAGES.items()):
                is_current = code == user_prefs.native_language
                label = f"{name} {'✓' if is_current else ''}"
                button = InlineKeyboardButton(label, callback_data=f"{LANG_PREFIX}{code}")

                row.append(button)
                if len(row) == 3 or i == len(COMMON_LANGUAGES) - 1:
                    keyboard.append(row)
                    row = []

            # Add back button
            keyboard.append(
                [InlineKeyboardButton("◀️ Back to Settings", callback_data=f"{BACK_PREFIX}settings")]
            )

            reply_markup = InlineKeyboardMarkup(keyboard)

            await query.edit_message_text("Select your native language:", reply_markup=reply_markup)

            return AWAITING_NATIVE_LANGUAGE

        # Handle learning languages management
        elif action == "learn":
            # Get current user preferences
            user_service = _get_user_service()
            user_prefs = user_service.get_user_preferences(user_id)

            # Create keyboard with action options
            keyboard = [
                [
                    InlineKeyboardButton(
                        "➕ Add a language", callback_data=f"{ADD_LANG_PREFIX}select"
                    )
                ],
                [
                    InlineKeyboardButton(
                        "➖ Remove a language", callback_data=f"{REMOVE_LANG_PREFIX}select"
                    )
                ],
                [
                    InlineKeyboardButton(
                        "◀️ Back to Settings", callback_data=f"{BACK_PREFIX}settings"
                    )
                ],
            ]

            reply_markup = InlineKeyboardMarkup(keyboard)

            # Format the list of currently learning languages
            learning_languages = [
                COMMON_LANGUAGES.get(code, code.upper()) for code in user_prefs.learning_languages
            ]
            learning_list = "\n• ".join(learning_languages)

            await query.edit_message_text(
                f"*Languages you're currently learning:*\n• {learning_list}\n\nWhat would you like to do?",
                reply_markup=reply_markup,
                parse_mode="Markdown",
            )

            return AWAITING_LEARNING_LANGUAGE_ACTION

    # Check if user clicked back button
    if callback_data.startswith(BACK_PREFIX):
        # Return to main settings menu
        return await settings_command(update, context)

    # Unknown callback data
    logger.warning(f"Unknown callback data in settings: {callback_data}")
    await query.edit_message_text("Sorry, something went wrong. Please try again.")
    return ConversationHandler.END
