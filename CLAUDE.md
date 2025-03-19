# AnkiChat Project Guidelines

## Commands
- Run all tests: `pytest`
- Run specific test file: `pytest tests/test_filename.py`
- Run specific test: `pytest tests/test_filename.py::test_function_name`
- Run with verbose output: `pytest -v`
- Run tests with coverage: `pytest --cov=src --cov-report=html`
- Check code style: `black .`
- Sort imports: `isort .`
- Lint code: `flake8 src tests`
- Type checking: `mypy src/`
- Run all quality checks: `./run_quality_checks.py`
- Run specific checks: `./run_quality_checks.py --format --lint --type-check --test --coverage`
- Import flashcards from CSV: `python simple_csv_import.py file.csv --user USER_ID [--name "Deck Name"] [--list]`

## Code Style and Quality
- **Imports**: Standard library first, third-party next, local modules last
- **Type Hints**: Always use typing annotations for function parameters and return values
- **Docstrings**: Use triple-quote docstrings for modules, classes, and functions
- **Naming**: snake_case for variables/functions, PascalCase for classes, UPPERCASE for constants
- **Error Handling**: Use try/except with specific exceptions, avoid bare excepts
- **Async**: Use async/await for all I/O operations; tests configured with asyncio_mode=strict

## Quality Tools
- **Black**: Line length of 100 characters with consistent formatting
- **isort**: Compatible with Black formatter, same line length
- **flake8**: Enforces PEP8 with some exceptions (see .flake8 file)
- **mypy**: Strict type checking with disallow_untyped_defs=true
- **pytest**: For unit and integration testing
- **pytest-cov**: For coverage reporting
- **pytest-asyncio**: For testing async code with asyncio_mode=strict

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

## Requirements and Configuration
- All project dependencies are listed in `requirements.txt`
- Development dependencies include:
  - pytest, pytest-asyncio, pytest-cov (testing)
  - black, isort, flake8, mypy (code quality)
- Configuration files:
  - `pyproject.toml`: Tool configurations for black, isort, mypy, and pytest
  - `.flake8`: Configuration for flake8 linting rules
  - `pytest.ini`: Pytest configuration with asyncio_mode=strict
- Run `run_quality_checks.py` to perform all code quality checks in one command
- Always run tests and quality checks before submitting pull requests