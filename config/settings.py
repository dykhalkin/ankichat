"""
Configuration settings for the Telegram Anki Flashcards System.
"""

import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Telegram Bot API Token
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
if not TELEGRAM_TOKEN:
    raise ValueError("TELEGRAM_TOKEN environment variable is not set")

# Application settings
DEBUG_MODE = os.getenv("DEBUG_MODE", "False").lower() == "true"