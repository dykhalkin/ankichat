# AnkiChat

A Telegram bot for creating and managing Anki-style flashcards through spaced repetition learning.

## Overview

This project enables users to create, review, and manage flashcards directly through a Telegram bot. It brings the power of spaced repetition learning to the convenience of Telegram messaging.

## Features

- Create flashcards with front and back content
- Organize flashcards into decks
- Review cards using spaced repetition algorithm
- Multiple training modes (standard, fill-in-blank, multiple choice)
- Import flashcards from CSV files
- Track learning progress

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
- `/new` - Create a new flashcard
- `/review` - Start reviewing due cards
- `/decks` - View and manage your decks
- `/newdeck` - Create a new deck

## Development

### Code Style and Quality

We use several tools to maintain code quality:

- **Black**: Code formatting
- **isort**: Import sorting
- **flake8**: Linting
- **mypy**: Type checking
- **pytest**: Testing with coverage

Run all quality checks with:

```bash
./run_quality_checks.py
```

You can also run specific checks:

```bash
# Format code
./run_quality_checks.py --format

# Run linter
./run_quality_checks.py --lint

# Type check
./run_quality_checks.py --type-check

# Run tests with coverage
./run_quality_checks.py --test --coverage

# Run tests with verbose output
./run_quality_checks.py --test -v

# Run specific tests
./run_quality_checks.py --test tests/test_models.py
```

### Testing

Tests are organized to match the module structure in `src/`. Run tests with:

```bash
pytest
```

Or for more specific test runs:

```bash
# Run specific test file
pytest tests/test_models.py

# Run specific test
pytest tests/test_models.py::test_function_name

# Run with coverage
pytest --cov=src --cov-report=html
```

## Project Structure

```
ankichat/
├── config/             # Configuration files
│   ├── logging_config.py
│   └── settings.py
├── src/                # Source code
│   ├── bot.py          # Bot initialization and setup
│   ├── csv_manager.py  # CSV import/export functionality
│   ├── csv_service.py  # CSV service layer
│   ├── database.py     # Database connection and models
│   ├── handlers.py     # Command handlers
│   ├── llm.py          # Language model integration
│   ├── main.py         # Application entry point
│   ├── models.py       # Data models
│   ├── repository.py   # Data access layer
│   ├── services.py     # Business logic services 
│   ├── srs.py          # Spaced repetition algorithm
│   └── training.py     # Training modes implementation
├── tests/              # Test files
│   ├── conftest.py
│   ├── test_*.py       # Tests for each module
├── .env.example        # Example environment variables
├── pyproject.toml      # Tool configurations
├── requirements.txt    # Python dependencies
└── run_quality_checks.py # Quality check script
```

## CSV Import

To import flashcards from a CSV file:

```bash
python simple_csv_import.py file.csv --user USER_ID [--name "Deck Name"] [--list]
```

See `docs/csv_import.md` for detailed instructions.