#!/usr/bin/env python
"""
Telegram Anki Flashcards System - Main Application Entry Point
"""

import os
import sys

from dotenv import load_dotenv

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Load environment variables
load_dotenv()

from config.logging_config import setup_logging
from src.bot import create_bot

# Set up logging
logger = setup_logging()


def main():
    """Main application entry point"""
    logger.info("Starting Telegram Anki Flashcards System")

    try:
        # Initialize and run the Telegram bot
        bot = create_bot()
        logger.info("Telegram bot initialized")

        # Start the bot - this call is blocking
        bot.run()
    except KeyboardInterrupt:
        logger.info("Application stopped by user")
    except Exception as e:
        logger.error(f"Error running the application: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
