# Telegram Anki Flashcards System

A bot system for creating and managing Anki-style flashcards through Telegram.

## Overview

This project enables users to create, review, and manage flashcards directly through a Telegram bot. It brings the power of spaced repetition learning to the convenience of Telegram messaging.

## Features

- Create flashcards with front and back content
- Review cards using spaced repetition algorithm
- Track learning progress
- Simple command-based interface

## Setup

1. Clone this repository
2. Install dependencies: `pip install -r requirements.txt`
3. Copy the `.env.example` file to `.env` and set your Telegram Bot token:
   ```
   cp .env.example .env
   # Edit .env and add your Telegram Bot token
   ```
4. Run the bot: `python src/main.py`

## Commands

- `/start` - Start the bot and see welcome message
- `/help` - Display help information about using the bot
- `/new` - Create a new flashcard (coming soon)
- `/review` - Start reviewing due cards (coming soon)
- `/stats` - View your learning statistics (coming soon)

## Development

- Source code is in the `/src` directory
- Tests are in the `/tests` directory
- Configuration files are in the `/config` directory

## Running Tests

To run the tests, use pytest:

```
pytest
```

## Project Structure

```
ankichat/
├── config/             # Configuration files
│   ├── logging_config.py
│   └── settings.py
├── src/                # Source code
│   ├── bot.py          # Bot initialization and setup
│   ├── handlers.py     # Command handlers
│   └── main.py         # Application entry point
├── tests/              # Test files
│   ├── conftest.py
│   ├── test_bot.py
│   └── test_handlers.py
├── .env.example        # Example environment variables
└── requirements.txt    # Python dependencies
```