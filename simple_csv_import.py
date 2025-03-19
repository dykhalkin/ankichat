#!/usr/bin/env python
"""
Simple CSV importer for AnkiChat flashcards.

This standalone script imports flashcards from a CSV file into the AnkiChat database.
"""

import argparse
import csv
import os
import sys
import logging
import datetime
import uuid
import sqlite3
from typing import List, Dict, Optional, Tuple

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger("simple_csv_import")

# Database path
DEFAULT_DB_PATH = "data/ankichat.db"


def ensure_db_exists(db_path: str) -> None:
    """Make sure the database directory exists."""
    os.makedirs(os.path.dirname(db_path), exist_ok=True)


def list_available_decks(conn: sqlite3.Connection, user_id: str) -> List[Dict]:
    """
    List all available decks for a user.

    Args:
        conn: SQLite connection
        user_id: The user ID to list decks for

    Returns:
        List of deck dictionaries
    """
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM decks WHERE user_id = ?", (user_id,))
    rows = cursor.fetchall()

    decks = []
    for row in rows:
        # Get number of cards in this deck
        card_cursor = conn.cursor()
        card_cursor.execute(
            "SELECT COUNT(*) FROM flashcards WHERE deck_id = ?", (row[0],)
        )
        card_count = card_cursor.fetchone()[0]

        decks.append(
            {
                "id": row[0],
                "name": row[1],
                "description": row[2],
                "created_at": row[3],
                "user_id": row[4],
                "card_count": card_count,
            }
        )

    if not decks:
        print("No decks found. A new deck will be created.")
        return []

    print("\nAvailable decks:")
    print("-" * 50)
    print(f"{'ID':<36} | {'Name':<30} | {'Cards':<5}")
    print("-" * 50)

    for deck in decks:
        print(f"{deck['id']:<36} | {deck['name']:<30} | {deck['card_count']:<5}")

    print("-" * 50)
    return decks


def create_deck_if_needed(
    conn: sqlite3.Connection, user_id: str, deck_name: str
) -> str:
    """
    Create a new deck if one with the given name doesn't exist.

    Args:
        conn: SQLite connection
        user_id: The user ID to create the deck for
        deck_name: The name of the deck to create

    Returns:
        The ID of the created or existing deck
    """
    cursor = conn.cursor()

    # Check if a deck with this name already exists
    cursor.execute(
        "SELECT id FROM decks WHERE user_id = ? AND name = ?", (user_id, deck_name)
    )
    row = cursor.fetchone()

    if row:
        logger.info(f"Found existing deck with name '{deck_name}'")
        return row[0]

    # Create a new deck
    deck_id = str(uuid.uuid4())
    created_at = datetime.datetime.now().isoformat()

    cursor.execute(
        "INSERT INTO decks (id, name, description, created_at, user_id) VALUES (?, ?, ?, ?, ?)",
        (
            deck_id,
            deck_name,
            f"Created via CSV import on {datetime.datetime.now().strftime('%Y-%m-%d')}",
            created_at,
            user_id,
        ),
    )
    conn.commit()

    logger.info(f"Created new deck '{deck_name}' with ID {deck_id}")
    return deck_id


def import_csv(
    conn: sqlite3.Connection,
    file_path: str,
    user_id: str,
    target_deck_id: Optional[str] = None,
    target_deck_name: Optional[str] = None,
) -> Tuple[int, List[str]]:
    """
    Import flashcards from a CSV file with the simplified format.

    The CSV should have the front of the card in the first column (index 0),
    and all other columns will be combined for the back of the card.

    Args:
        conn: SQLite connection
        file_path: Path to the CSV file
        user_id: ID of the user importing the cards
        target_deck_id: Optional ID of the deck to import cards into
        target_deck_name: Optional name of the deck to import cards into (creates if needed)

    Returns:
        Tuple of (cards_imported, warnings)
    """
    cards_imported = 0
    warnings = []

    # Determine target deck
    if not target_deck_id and target_deck_name:
        target_deck_id = create_deck_if_needed(conn, user_id, target_deck_name)

    if not target_deck_id:
        warnings.append("No target deck specified. Creating a default deck.")
        target_deck_id = create_deck_if_needed(conn, user_id, "Imported Flashcards")

    try:
        cursor = conn.cursor()

        # Read the CSV file
        with open(file_path, "r", newline="", encoding="utf-8") as f:
            reader = csv.reader(f, delimiter=";")

            for row_num, row in enumerate(reader, start=1):
                try:
                    if not row or len(row) < 1:
                        warnings.append(f"Skipping empty row {row_num}")
                        continue

                    # Front side is first column
                    front = row[0].strip()
                    if not front:
                        warnings.append(f"Skipping row {row_num}: empty front side")
                        continue

                    # Back side is all remaining columns joined
                    back_parts = [part.strip() for part in row[1:] if part.strip()]
                    back = (
                        "\n\n".join(back_parts) if back_parts else "No details provided"
                    )

                    # Create the flashcard
                    card_id = str(uuid.uuid4())
                    created_at = datetime.datetime.now().isoformat()
                    language = "en"  # Default language
                    interval = 1.0  # Default interval
                    ease_factor = 2.5  # Default ease factor
                    review_count = 0  # Default review count

                    # Check if tags column exists
                    cursor.execute("PRAGMA table_info(flashcards)")
                    columns = [column[1] for column in cursor.fetchall()]
                    has_tags_column = "tags" in columns

                    if has_tags_column:
                        cursor.execute(
                            """
                            INSERT INTO flashcards 
                            (id, front, back, language, created_at, interval, ease_factor, review_count, deck_id, tags) 
                            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                            """,
                            (
                                card_id,
                                front,
                                back,
                                language,
                                created_at,
                                interval,
                                ease_factor,
                                review_count,
                                target_deck_id,
                                "[]",
                            ),
                        )
                    else:
                        cursor.execute(
                            """
                            INSERT INTO flashcards 
                            (id, front, back, language, created_at, interval, ease_factor, review_count, deck_id) 
                            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                            """,
                            (
                                card_id,
                                front,
                                back,
                                language,
                                created_at,
                                interval,
                                ease_factor,
                                review_count,
                                target_deck_id,
                            ),
                        )
                    conn.commit()
                    cards_imported += 1

                except Exception as e:
                    logger.error(f"Error importing row {row_num}: {e}")
                    warnings.append(f"Error in row {row_num}: {e}")

        logger.info(f"Imported {cards_imported} cards into deck {target_deck_id}")
        return cards_imported, warnings

    except Exception as e:
        logger.error(f"Error reading CSV file {file_path}: {e}")
        warnings.append(f"Failed to read CSV file: {e}")
        return 0, warnings


def main():
    """Main entry point for the CSV importer application."""
    parser = argparse.ArgumentParser(description="Import flashcards from CSV file")
    parser.add_argument("file", help="Path to the CSV file to import")
    parser.add_argument(
        "--user", "-u", required=True, help="User ID to import cards for"
    )
    parser.add_argument(
        "--deck", "-d", help="Optional: Target deck ID to import cards into"
    )
    parser.add_argument(
        "--name", "-n", help="Optional: Create or use a deck with this name"
    )
    parser.add_argument(
        "--list", "-l", action="store_true", help="List available decks before import"
    )
    parser.add_argument("--db", help=f"Path to database (default: {DEFAULT_DB_PATH})")

    args = parser.parse_args()

    # Validate file path
    if not os.path.exists(args.file):
        print(f"Error: File '{args.file}' does not exist.")
        sys.exit(1)

    # Determine database path
    db_path = args.db or DEFAULT_DB_PATH
    ensure_db_exists(db_path)

    # Connect to the database
    try:
        conn = sqlite3.connect(db_path)  # No type detection to avoid timestamp issues
        conn.row_factory = sqlite3.Row
    except sqlite3.Error as e:
        print(f"Error connecting to database: {e}")
        sys.exit(1)

    # List decks if requested
    if args.list:
        decks = list_available_decks(conn, args.user)

        # Only ask for input if we're in an interactive terminal
        if not args.deck and not args.name and sys.stdin.isatty():
            try:
                deck_id = input(
                    "\nEnter deck ID to use (leave empty to create a new deck): "
                ).strip()
                if deck_id:
                    args.deck = deck_id
                else:
                    deck_name = input("Enter a name for the new deck: ").strip()
                    if deck_name:
                        args.name = deck_name
            except (EOFError, KeyboardInterrupt):
                print("\nNo input provided. Continuing with default options.")
                pass

    # Import the CSV file
    print(f"\nImporting cards from '{args.file}'...")
    cards_imported, warnings = import_csv(
        conn, args.file, args.user, args.deck, args.name
    )

    # Print results
    print(f"\nImport complete:")
    print(f"- Cards imported: {cards_imported}")

    if warnings:
        print(f"- Warnings: {len(warnings)}")
        should_show = False

        # Only prompt for input if we're in an interactive terminal
        if sys.stdin.isatty():
            try:
                should_show = input("Show warnings? (y/n): ").lower().startswith("y")
            except (EOFError, KeyboardInterrupt):
                pass
        else:
            # When not in interactive mode, just show the warnings
            should_show = True

        if should_show:
            for i, warning in enumerate(warnings, start=1):
                print(f"  {i}. {warning}")

    # Close the database connection
    conn.close()

    print("\nDone.")


if __name__ == "__main__":
    main()
