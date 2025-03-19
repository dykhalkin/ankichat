# Deck Management and CSV Import/Export

This document outlines the implementation of deck management and CSV import/export functionality for the AnkiChat project.

## Deck Management Features

### Core Features
- Creation, renaming, and deletion of decks
- Moving flashcards between decks
- Automatic suggestion of deck names based on flashcard content using LLM

### Models
- Enhanced `Deck` and `Flashcard` models with utility methods for conversion between objects and dictionaries
- Added tags support to flashcards for better organization

### Service Layer
- Added comprehensive deck management operations to `DeckService`:
  - `create_deck`: Create a new deck for a user
  - `rename_deck`: Rename an existing deck
  - `delete_deck`: Delete a deck and all its cards
  - `get_deck_with_cards`: Retrieve a deck with all its cards
  - `move_card_to_deck`: Move a flashcard from one deck to another
  - `suggest_deck_name`: Use LLM to suggest an appropriate deck name based on card content

### LLM Integration
- Added `detect_category` method to `LLMClient` to analyze flashcard content and suggest appropriate deck names
- Fallback to default names when LLM is unavailable

## CSV Import/Export

### CSV Format
- Defined a standardized CSV format that includes all flashcard fields
- Added support for preserving metadata including SRS parameters

### Implementation
- Created `CSVManager` class for low-level CSV operations:
  - Reading and writing CSV files
  - Mapping between CSV rows and objects
  - Handling data type conversions

- Added `CSVService` for high-level CSV operations:
  - Exporting single decks to CSV
  - Exporting all user decks to CSV
  - Importing flashcards from CSV with various options
  - Automatic deck creation and organization during import

### Features
- Support for both standard and automatic deck creation during import
- LLM-assisted categorization to suggest deck names during import
- Ability to export all decks or individual decks
- Preservation of all flashcard metadata during export/import

## Testing
- Comprehensive test coverage for all new functionality:
  - Unit tests for deck management operations
  - Unit tests for CSV import/export
  - Tests for LLM integration with deck naming suggestion

## Architecture
- Maintained clean separation of concerns:
  - Models define data structures
  - Repositories handle data access
  - Services implement business logic
  - CSV-specific code isolated in dedicated modules

## Dependencies
- No new external dependencies were required
- Leveraged standard library CSV module for file handling
- Used existing OpenAI integration for LLM features

## Auto-Backup
- All operations are reflected immediately in the system
- Database transactions ensure data consistency
- CSV export provides a backup mechanism for user data