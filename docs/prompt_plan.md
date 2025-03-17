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

