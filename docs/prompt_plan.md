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