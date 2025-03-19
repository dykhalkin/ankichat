Set up scaffolding project
```
Project Prompt 1:
You are tasked with setting up the initial project scaffolding for the Telegram Anki Flashcards System. The requirements are:

1. Create a repository structure with the following directories:
   - /src: for the source code.
   - /tests: for unit and integration tests.
   - /config: for configuration files.
2. Add a `requirements.txt` file that includes dependencies such as:
   - python-telegram-bot (or an equivalent Telegram bot framework)
   - pytest for testing
3. Create a basic README.md with an overview of the project.
4. Set up a basic logging configuration file (e.g., in /config) for later use.

Ensure that the scaffolding is modular and follows best practices. At the end, provide a summary of the folder structure and the contents of the main files.
```

Run Telegram bot
```
Project Prompt 2:
Now, build the foundation of the Telegram bot by creating a basic bot application using  Telegram bot framework (e.g., python-telegram-bot). Your task is:

1. Initialize the bot and set up a webhook or long polling (choose one).
2. Implement a `/start` command handler that sends a welcome message to the user.
3. Include error handling and logging.
4. Write a simple unit test (or integration test) that simulates sending the `/start` command and checks for the correct response.

Make sure the bot’s main file can be executed directly and properly wires the command handler. Include comments and clear separation of concerns.
```

Data model
```
Project Prompt 3:
Develop the core data models and persistence layer for the flashcards and decks. Your tasks are:

1. Define a `Flashcard` class with attributes:
   - id, front text, back text, language, SRS metadata (e.g., review interval, ease factor)
2. Define a `Deck` class with attributes:
   - id, name, list of flashcards
3. Implement CRUD operations for both Flashcard and Deck (create, read, update, delete).
4. Use sqllite database for persistant storage
5. Write unit tests to verify the CRUD operations and data integrity.

Ensure the design is modular so that persistence can be replaced with a more robust solution later.
```

Flashcard creation workflow
```
Project Prompt 4:
Implement the flashcard creation workflow with the following requirements:

1. Create a function that accepts any user text input in update for a new flashcard. Any random text input from the user should trigger a flashcard creation flow  as well as /new command
2. Implement OpenAI API client that implement the next steps including card content creation and language detection.
2. Using instance-based AsyncOpenAI client to  detect the inputted langugage.
3. Generate a preview of the flashcard using placeholder content for:
   - Definition
   - Example sentence
   - Pronunciation audio (TTS placeholder)
   - Transcription (IPA/phonetic placeholder)
4. Present the preview to the user and ask for confirmation or override.
5. Wire this flow into the Telegram bot UI using inline buttons.
6. Include unit tests that simulate the input and verify that the preview is generated and confirmation logic works as expected.

Document the code clearly and ensure that it can be extended later.
```

Spaced Repetition Algorithm Module
```
Project Prompt 5:
Build a module that implements a spaced repetition algorithm (e.g., SM-2 algorithm) for scheduling flashcard reviews. The module should:

1. Accept a flashcard and user performance data (e.g., ease of recall score).
2. Calculate the next review date or interval for the flashcard.
3. Update the flashcard’s SRS metadata accordingly.
4. Include comprehensive unit tests covering different performance scenarios (correct, incorrect, borderline cases).

Ensure that the module is decoupled from the rest of the system for easy testing and future refinement.
```

Training modes and review session handling
```
Project Prompt 6:
Implement the flashcard training modes and review session handling. Your objectives are:

1. Create functions or classes for the following training modes:
   - Standard flashcard review: show front, expect the user to recall the back.
   - Fill-in-the-blank: remove key parts of the answer. Use LLM to generate the blanked content and front term to be filled in.
   - Multiple-choice quizzes: generate distractors along with the correct answer.
2. Incorporate error handling:
   - Increase the review frequency for incorrect answers.
3. Design the review session to:
   - Dynamically determine session length based on due flashcards.
   - Allow the user to end the session early.
4. Write unit tests for each training mode ensuring correct functionality and SRS updates.

Wire the training modes into the Telegram bot commands, ensuring that users can choose which mode to use.
```

Deck management and CSV import/export
```
Project Prompt 7:
Develop the deck management and CSV import/export functionalities:

1. Extend the data model to allow:
   - Creation, renaming, and deletion of decks.
   - Moving flashcards between decks.
   - Automatic suggestion of deck names based on flashcard content. Use LLM assistant to identify proper deck name.
2. Implement CSV import/export:
   - Define a fixed CSV format that includes all flashcard fields.
   - Write functions to import flashcards from a CSV file and export current decks/flashcards to CSV.
3. Ensure that operations are reflected immediately in the system (auto-backup behavior simulated).
4. Implement Telegram App UX flow for deck management.
5. Write integration tests to verify that deck operations and CSV functionalities work correctly.

Ensure that the code is modular and easily testable, with clear separation of concerns.
```

UI/UX Enhancements & Inline Button Navigation
```
Project Prompt 9:
Enhance the Telegram bot UI/UX to provide a smooth, minimal interface:

1. Refine inline button layouts and menu-driven navigation for:
   - Flashcard creation
   - Review sessions
   - Deck management
2. Ensure that bot responses are brief and grouped logically.
3. Add conceptual progress indicators (e.g., simple text-based progress bars) and basic animations if possible.
4. Implement error handling messages that are clear and concise.
5. Write integration tests to simulate user navigation and verify that the UI flows do not produce orphaned or hanging code.

The focus here is to ensure a seamless user experience and logical wiring of commands.
```

Testing and code quality
```
Project Prompt 10:
Ensure that the code is well-tested and of high quality.

1. **Unit Testing:**
   - Use pytest for testing.
   - Ensure that the tests are comprehensive and cover all edge cases.
   - Use asyncio_mode=strict for testing.
2. **Code Quality:**
   - Use black for code formatting.
   - Use flake8 for linting.
   - Use mypy for type checking.
   - Use isort for sorting imports.
   - Use pytest-cov for coverage reporting.
   - Use pytest-asyncio for testing async code.
```

CI/CD Strategy
```
Project Prompt 11:
You are tasked with implementing a full CI/CD strategy using GitHub CI (GitHub Actions) for the Telegram Anki Flashcards System. Your work should include:

1. **GitHub Actions Workflow:**
   - Create a workflow YAML file (e.g., `.github/workflows/ci.yml`) that triggers on pushes to the `main` branch.
   - The workflow should perform the following steps:
     - **Checkout:** Pull the latest code from the repository.
     - **Environment Setup:** Set up Python env using venv and install all dependencies from `requirements.txt`.
     - **Testing:** Run all tests (using `pytest` or a similar framework) to ensure code integrity.
     - **Linting/Static Analysis:** (Optional) Run linters such as `flake8` to maintain code quality.
     - **Deployment:**
       - Use an SSH action to connect to an Ubuntu server.
       - Execute a remote deployment script (detailed in the next section) that updates the application.
       - Ensure secure transfer of any necessary secrets (SSH keys, server credentials) via GitHub Secrets.

2. **Bash Deployment Script:**
   - Create a Bash script (e.g., `deploy.sh`) that deploys the application as a Unix service on an Ubuntu server.
   - The script should perform the following actions:
     - **Service Setup:**
       - Copy or update the project files to a designated directory on the server.
       - Create or update a systemd service file (e.g., `/etc/systemd/system/telegram-anki.service`) with the correct settings to run the bot (pointing to the Python interpreter, virtual environment, and the main bot file).
     - **Service Management:**
       - Reload the systemd daemon to pick up any changes.
       - Enable and restart the service.
     - **Error Handling & Logging:**
       - Include error handling and log messages for each major step.
   - The script should be idempotent so that repeated deployments do not break the service.

3. **Documentation & Comments:**
   - Ensure that both the GitHub Actions workflow and the Bash script include clear inline comments and documentation.
   - The instructions should explain the purpose of each step and best practices for secure, incremental deployments.

Your final output should include:
- A GitHub Actions workflow YAML file with all the described steps.
- A complete Bash script for deploying the Telegram Anki Flashcards System as a Unix service on an Ubuntu server.

Make sure to follow best practices in CI/CD and systemd service configuration. The deployment process must be secure, automated, and easily reproducible.
```