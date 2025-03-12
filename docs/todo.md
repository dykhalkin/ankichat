# Telegram Anki Flashcards System - TODO Checklist

This checklist outlines all the steps required to build the Telegram Anki Flashcards System. Each item is broken down into actionable tasks to help you implement, test, and integrate features incrementally.

---

## 1. Project Setup & Scaffolding

- [ ] **Repository Structure**
  - [ ] Create the following directories:
    - `/src` for source code.
    - `/tests` for unit and integration tests.
    - `/config` for configuration files.
- [ ] **Dependency Management**
  - [ ] Set up a Python virtual environment.
  - [ ] Create a `requirements.txt` file including:
    - `python-telegram-bot` (or an equivalent library)
    - `pytest`
    - (other necessary libraries)
- [ ] **Documentation & Logging**
  - [ ] Create a `README.md` with an overview of the project.
  - [ ] Set up a basic logging configuration file in `/config`.

---

## 2. Basic Telegram Bot Initialization

- [ ] **Bot Initialization**
  - [ ] Create the main bot file under `/src`.
  - [ ] Initialize the Telegram bot using a chosen framework.
  - [ ] Configure webhook or long polling.
- [ ] **Command Handlers**
  - [ ] Implement a `/start` command handler to send a welcome message.
- [ ] **Error Handling & Logging**
  - [ ] Integrate error handling with logging.
- [ ] **Testing**
  - [ ] Write an integration test simulating the `/start` command and validating the response.

---

## 3. Flashcard Data Models & Persistence Layer

- [ ] **Model Definitions**
  - [ ] Define a `Flashcard` class with attributes:
    - `id`
    - `front_text`
    - `back_text`
    - `language`
    - SRS metadata (e.g., review interval, ease factor)
  - [ ] Define a `Deck` class with attributes:
    - `id`
    - `name`
    - A list of flashcards
- [ ] **CRUD Operations**
  - [ ] Implement CRUD operations for Flashcards.
  - [ ] Implement CRUD operations for Decks.
- [ ] **Persistence**
  - [ ] Use in-memory storage (dictionaries/lists) as a prototype.
- [ ] **Testing**
  - [ ] Write unit tests for all CRUD operations and data integrity.

---

## 4. Flashcard Creation Workflow & LLM-Generated Content Integration

- [ ] **User Input Handling**
  - [ ] Create a function to accept user text input for a new flashcard.
- [ ] **Language Detection**
  - [ ] Simulate auto-detection of language (using heuristics or keyword checks).
- [ ] **Content Generation (Placeholders)**
  - [ ] Generate a flashcard preview including:
    - Definition placeholder
    - Example sentence placeholder
    - Pronunciation audio (TTS placeholder)
    - Transcription (IPA/phonetic placeholder)
- [ ] **User Confirmation**
  - [ ] Present the preview with inline buttons for user confirmation or override.
- [ ] **Testing**
  - [ ] Write unit tests to simulate input and verify preview generation and confirmation flow.

---

## 5. Spaced Repetition Algorithm Module

- [ ] **Algorithm Implementation**
  - [ ] Implement a spaced repetition algorithm (e.g., SM-2).
- [ ] **SRS Metadata Update**
  - [ ] Create a function to update a flashcard’s review schedule based on user performance.
- [ ] **Testing**
  - [ ] Write comprehensive unit tests covering various performance scenarios (correct, incorrect, borderline).

---

## 6. Flashcard Training Modes & Review Session Handling

- [ ] **Training Modes Implementation**
  - [ ] Standard Flashcard Review: Display front text and prompt recall of the back.
  - [ ] Fill-in-the-Blank: Remove key parts of the answer.
  - [ ] Multiple-Choice: Generate distractors alongside the correct answer.
  - [ ] Listening-Based Exercise: Simulate a listening test using TTS placeholders.
- [ ] **Error Handling**
  - [ ] Provide explanations for incorrect answers in a special learning mode.
  - [ ] Update SRS metadata to increase review frequency for incorrect responses.
- [ ] **Session Management**
  - [ ] Dynamically set session length based on due flashcards.
  - [ ] Allow users to end the session early.
- [ ] **Testing**
  - [ ] Write unit tests for each training mode to verify functionality and SRS updates.

---

## 7. Deck Management & CSV Import/Export

- [ ] **Deck Operations**
  - [ ] Implement deck creation, renaming, and deletion.
  - [ ] Enable moving flashcards between decks.
  - [ ] Auto-suggest deck names based on flashcard content.
- [ ] **CSV Functionality**
  - [ ] Define a fixed CSV format for flashcard data.
  - [ ] Implement CSV export for decks and flashcards.
  - [ ] Implement CSV import to add flashcards from a file.
- [ ] **Testing**
  - [ ] Write integration tests to verify deck operations and CSV import/export work as expected.

---

## 8. User Preferences, Settings & Authentication

- [ ] **Settings Module**
  - [ ] Create a settings module to manage user preferences.
  - [ ] Implement auto-save for user settings.
  - [ ] Provide an option to reset settings to default.
  - [ ] Ensure settings sync across devices using Telegram user ID.
- [ ] **Authentication**
  - [ ] Tie authentication to the Telegram account (no separate login).
- [ ] **Testing**
  - [ ] Write tests to confirm that user settings are saved, retrieved, and reset correctly.

---

## 9. UI/UX Enhancements & Inline Button Navigation

- [ ] **Interface Refinement**
  - [ ] Enhance inline button layouts for:
    - Flashcard creation
    - Review sessions
    - Deck management
    - Settings
  - [ ] Group responses to minimize message clutter.
  - [ ] Add text-based progress indicators (e.g., simple progress bars).
- [ ] **Error Messaging**
  - [ ] Implement clear, concise error messages.
- [ ] **Testing**
  - [ ] Write integration tests to simulate user navigation and verify UI flows.

---

## 10. Final Integration & Comprehensive Testing

- [ ] **Module Wiring**
  - [ ] Integrate the Telegram bot with:
    - Data models and persistence layer
    - Flashcard creation and LLM integration
    - SRS module
    - Training modes
    - Deck management and CSV functionalities
    - User settings module
- [ ] **End-to-End Testing**
  - [ ] Develop integration tests for complete flows:
    - User registration and setup via Telegram.
    - Creating flashcards and decks.
    - Conducting review sessions.
    - Adjusting and syncing user settings.
- [ ] **Code Cleanup & Documentation**
  - [ ] Refactor orphaned or unintegrated code.
  - [ ] Write final documentation summarizing the system structure and future extension guidelines.

---

This checklist is designed to guide you through every phase of the project—from initial setup to final integration—ensuring best practices, incremental progress, and strong test coverage throughout development.