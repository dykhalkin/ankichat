# AnkiChat Project Guidelines

## Commands
- Run all tests: `pytest`
- Run specific test file: `pytest tests/test_filename.py`
- Run specific test: `pytest tests/test_filename.py::test_function_name`
- Run with verbose output: `pytest -v`
- Check code style: `black .` (install with `pip install black`)
- Type checking: `mypy src/` (install with `pip install mypy`)

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