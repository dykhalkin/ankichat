"""
Command handlers for the Telegram Anki Flashcards bot.
"""

import logging
from telegram import Update
from telegram.ext import CallbackContext

logger = logging.getLogger('ankichat')

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
        "Use /new and follow the prompts to create front and back sides of your card.\n\n"
        
        "*Reviewing Cards:*\n"
        "Use /review to start a review session. For each card, you'll see the front side "
        "and need to recall the answer. After viewing the answer, rate how well you remembered it.\n\n"
        
        "*Spaced Repetition:*\n"
        "Cards will reappear for review based on how well you remembered them - "
        "the better you know a card, the longer until you see it again."
    )
    
    await update.message.reply_text(help_text, parse_mode="Markdown")