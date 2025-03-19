"""
Tests for CSV import/export functionality.
"""

import csv
import os
import tempfile
from datetime import datetime, timedelta
from typing import Any, Dict, List

import pytest

from src.csv_manager import FLASHCARD_CSV_HEADERS, CSVManager
from src.models import Deck, Flashcard
from src.repository import DeckRepository, FlashcardRepository


class TestCSVManager:
    """Tests for the CSVManager class."""

    @pytest.fixture
    def csv_manager(self, deck_repo_mock, flashcard_repo_mock):
        """Create a CSVManager instance with mock repositories."""
        return CSVManager(deck_repo_mock, flashcard_repo_mock)

    @pytest.fixture
    def sample_deck(self):
        """Create a sample deck for testing."""
        return Deck(
            id="deck-123",
            name="Test_Deck",
            description="Test description",
            user_id="user-123",
            created_at=datetime.now() - timedelta(days=7),
        )

    @pytest.fixture
    def sample_cards(self):
        """Create sample flashcards for testing."""
        return [
            Flashcard(
                id=f"card-{i}",
                front=f"Front {i}",
                back=f"Back {i}",
                language="en",
                deck_id="deck-123",
                created_at=datetime.now() - timedelta(days=i),
                due_date=datetime.now() + timedelta(days=i),
                interval=float(i),
                ease_factor=2.5,
                review_count=i,
                tags=["tag1", "tag2"],
            )
            for i in range(1, 4)
        ]

    @pytest.fixture
    def temp_dir(self):
        """Create a temporary directory for test files."""
        with tempfile.TemporaryDirectory() as temp_dir:
            yield temp_dir

    @pytest.fixture
    def deck_repo_mock(self, sample_deck, sample_cards):
        """Create a mock deck repository."""

        class MockDeckRepo(DeckRepository):
            def __init__(self, deck, cards):
                self.deck = deck
                self.cards = cards
                self.decks = {deck.id: deck}

            def create(self, deck):
                self.decks[deck.id] = deck
                return deck

            def get(self, deck_id):
                return self.decks.get(deck_id)

            def update(self, deck):
                self.decks[deck.id] = deck
                return deck

            def delete(self, deck_id):
                if deck_id in self.decks:
                    del self.decks[deck_id]
                    return True
                return False

            def list(self, user_id=None):
                if user_id:
                    return [d for d in self.decks.values() if d.user_id == user_id]
                return list(self.decks.values())

            def close(self):
                pass

        return MockDeckRepo(sample_deck, sample_cards)

    @pytest.fixture
    def flashcard_repo_mock(self, sample_cards):
        """Create a mock flashcard repository."""

        class MockFlashcardRepo(FlashcardRepository):
            def __init__(self, cards):
                self.cards = {card.id: card for card in cards}

            def create(self, card):
                self.cards[card.id] = card
                return card

            def get(self, card_id):
                return self.cards.get(card_id)

            def update(self, card):
                self.cards[card.id] = card
                return card

            def delete(self, card_id):
                if card_id in self.cards:
                    del self.cards[card_id]
                    return True
                return False

            def get_by_deck(self, deck_id):
                return [card for card in self.cards.values() if card.deck_id == deck_id]

            def get_due(self, user_id, limit=10):
                return list(self.cards.values())[:limit]

            def close(self):
                pass

        return MockFlashcardRepo(sample_cards)

    def test_export_deck_to_csv(
        self, csv_manager, sample_deck, sample_cards, temp_dir, flashcard_repo_mock
    ):
        """Test exporting a deck to a CSV file."""
        # Set up
        deck_id = sample_deck.id

        # Execute
        file_path = csv_manager.export_deck_to_csv(deck_id, temp_dir)

        # Verify
        assert os.path.exists(file_path)
        assert os.path.basename(file_path) == f"{sample_deck.name}.csv"

        # Check CSV content
        with open(file_path, "r", newline="", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            rows = list(reader)

            # Verify all cards are in the CSV
            assert len(rows) == len(sample_cards)

            # Verify headers
            assert set(reader.fieldnames) == set(FLASHCARD_CSV_HEADERS)

            # Verify content of first row
            assert rows[0]["id"] == sample_cards[0].id
            assert rows[0]["front"] == sample_cards[0].front
            assert rows[0]["back"] == sample_cards[0].back
            assert rows[0]["deck_name"] == sample_deck.name

    def test_import_flashcards_from_csv(
        self, csv_manager, sample_deck, temp_dir, deck_repo_mock, flashcard_repo_mock
    ):
        """Test importing flashcards from a CSV file."""
        # Create a test CSV file
        csv_path = os.path.join(temp_dir, "test_import.csv")

        with open(csv_path, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=FLASHCARD_CSV_HEADERS)
            writer.writeheader()

            # Add some test cards
            test_cards = [
                {
                    "id": "import-1",
                    "front": "Imported Front 1",
                    "back": "Imported Back 1",
                    "language": "en",
                    "created_at": datetime.now().isoformat(),
                    "due_date": (datetime.now() + timedelta(days=1)).isoformat(),
                    "interval": "1.0",
                    "ease_factor": "2.5",
                    "review_count": "0",
                    "deck_id": "",
                    "deck_name": "New Imported Deck",
                },
                {
                    "id": "import-2",
                    "front": "Imported Front 2",
                    "back": "Imported Back 2",
                    "language": "es",
                    "created_at": datetime.now().isoformat(),
                    "due_date": "",
                    "interval": "1.0",
                    "ease_factor": "2.5",
                    "review_count": "0",
                    "deck_id": sample_deck.id,
                    "deck_name": sample_deck.name,
                },
            ]

            for card in test_cards:
                writer.writerow(card)

        # Execute import
        cards_imported, decks_created, warnings = csv_manager.import_flashcards_from_csv(
            csv_path, "user-123", None, True
        )

        # Verify
        assert cards_imported == 2
        assert decks_created == 1  # Only one new deck should be created
        assert not warnings  # No warnings expected

        # Check if cards were added to the repository
        assert flashcard_repo_mock.get("import-1") is not None
        assert flashcard_repo_mock.get("import-2") is not None

        # Check if new deck was created
        user_decks = deck_repo_mock.list("user-123")
        deck_names = [d.name for d in user_decks]
        assert "New Imported Deck" in deck_names
