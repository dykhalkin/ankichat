# Simple CSV Import Tool for AnkiChat

This document explains how to use the simple CSV import utility to add flashcards to the AnkiChat system.

## CSV Format

The CSV import tool supports a simple format:
- The first column (index 0) contains the front side of the flashcard
- All other columns will be combined to form the back side of the flashcard
- No headers are needed in the CSV file

### Example CSV Format:

```csv
Apple,A fruit with red or green skin,Contains fiber and vitamins
Python,A high-level programming language,Used for web development
Algorithm,A set of steps to solve a problem,Very important in CS
```

This will create three flashcards:
1. Front: "Apple", Back: "A fruit with red or green skin\n\nContains fiber and vitamins"
2. Front: "Python", Back: "A high-level programming language\n\nUsed for web development"
3. Front: "Algorithm", Back: "A set of steps to solve a problem\n\nVery important in CS"

## Usage

To use the import tool, run the following command:

```bash
python simple_csv_import.py path/to/your/file.csv --user USER_ID [--deck DECK_ID] [--name "Deck Name"] [--list]
```

### Parameters:

- `path/to/your/file.csv`: The path to the CSV file you want to import
- `--user USER_ID` or `-u USER_ID`: The user ID to import flashcards for (required)
- `--deck DECK_ID` or `-d DECK_ID`: The target deck ID to import cards into (optional)
- `--name "Deck Name"` or `-n "Deck Name"`: Create or use a deck with this name (optional)
- `--list` or `-l`: List available decks before importing (optional)
- `--db PATH`: Path to the database file (optional, default: data/ankichat.db)

### Examples:

Import into a new deck named "Programming Terms":
```bash
python simple_csv_import.py sample_import.csv --user 123456 --name "Programming Terms"
```

List available decks before importing:
```bash
python simple_csv_import.py sample_import.csv --user 123456 --list
```

Import into an existing deck by ID:
```bash
python simple_csv_import.py sample_import.csv --user 123456 --deck 550e8400-e29b-41d4-a716-446655440000
```

## Notes

- If neither a deck ID nor a deck name is provided, the system will create a new deck called "Imported Flashcards"
- If a deck name is provided and a deck with that name already exists, the system will use the existing deck
- Each card will use default values for SRS parameters (interval, ease factor, etc.)
- The system will skip empty rows or rows with an empty front side
- This tool works directly with the SQLite database, bypassing the application layers for simplicity