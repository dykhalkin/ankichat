# AnkiChat Project Guidelines

## Commands
- Run all tests: `pytest`
- Run specific test file: `pytest tests/test_filename.py`
- Run specific test: `pytest tests/test_filename.py::test_function_name`
- Run with verbose output: `pytest -v`
- Check code style: `black .` (install with `pip install black`)
- Type checking: `mypy src/` (install with `pip install mypy`)
- Import flashcards from CSV: `python simple_csv_import.py file.csv --user USER_ID [--name "Deck Name"] [--list]`

## Code Style
- **Imports**: Standard library first, third-party next, local modules last
- **Type Hints**: Always use typing annotations for function parameters and return values
- **Docstrings**: Use triple-quote docstrings for modules, classes, and functions
- **Naming**: snake_case for variables/functions, PascalCase for classes, UPPERCASE for constants
- **Error Handling**: Use try/except with specific exceptions, avoid bare excepts
- **Async**: Use async/await for all I/O operations; tests configured with asyncio_mode=strict

## Architecture
- Organized in layers: models → repository → services → handlers → bot
- Use dataclasses for data models, with sensible defaults
- Keep business logic in service layer, data access in repository layer

## Async Implementation Guidelines
- Always await async methods - check both method attributes and class types
- Use proper coroutine handling throughout the codebase
- Review service methods are all async: start_session, get_next_card, process_answer, end_session
- LLM methods are async (language detection, content generation, fill-in-blank generation)

## Training Modes
- Available modes: STANDARD, FILL_IN_BLANK, MULTIPLE_CHOICE
- LEARNING mode has been completely removed 
- Strategy pattern used for different trainer implementations:
  - StandardTrainer: Basic flashcard review
  - FillInBlankTrainer: Fill-in-the-blank exercises (requires LLM)
  - MultipleChoiceTrainer: Multiple choice questions

## LLM Usage
- LLM client is initialized in ReviewService.start_session when needed
- Handle graceful degradation when LLM is unavailable
- Properly await all LLM-related methods (especially generate_fill_in_blank)

## CSV Import
- Use `simple_csv_import.py` for importing flashcards from CSV files
- CSV format is simple: first column is front of card, remaining columns are combined for back
- Example: `Term,Definition,Additional Info`
- See docs/csv_import.md for detailed instructions
- Database schema is checked for tags column before inserting cards