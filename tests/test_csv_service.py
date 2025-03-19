"""
Tests for the CSV service module.
"""

import csv
import os
import tempfile
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.csv_manager import FLASHCARD_CSV_HEADERS
from src.csv_service import CSVService
from src.models import Deck, Flashcard


class TestCSVService:
    """Tests for the CSVService class."""

    @pytest.fixture
    def deck_repo_mock(self):
        """Create a mock deck repository."""
        mock = MagicMock()

        # Setup test deck
        test_deck = Deck(
            id="deck-123", name="Test Deck", description="Test description", user_id="user-123"
        )
        mock.get.return_value = test_deck
        mock.list.return_value = [test_deck]
        mock.create.return_value = test_deck

        return mock

    @pytest.fixture
    def flashcard_repo_mock(self):
        """Create a mock flashcard repository."""
        mock = MagicMock()

        # Setup test card
        test_card = Flashcard(
            id="card-123", front="Test Front", back="Test Back", deck_id="deck-123"
        )
        mock.get.return_value = test_card
        mock.get_by_deck.return_value = [test_card]

        return mock

    @pytest.fixture
    def llm_client_mock(self):
        """Create a mock LLM client."""
        mock = AsyncMock()
        mock.detect_category = AsyncMock(return_value="Suggested Category")

        return mock

    @pytest.fixture
    def csv_service(self, deck_repo_mock, flashcard_repo_mock, llm_client_mock):
        """Create a CSVService with mock dependencies."""
        service = CSVService(deck_repo_mock, flashcard_repo_mock, llm_client_mock)

        # Mock the csv_manager to avoid file system operations
        service.csv_manager.export_deck_to_csv = MagicMock(return_value="/path/to/exported.csv")
        service.csv_manager.export_all_decks_to_csv = MagicMock(
            return_value=["/path/to/exported1.csv", "/path/to/exported2.csv"]
        )
        service.csv_manager.import_flashcards_from_csv = MagicMock(return_value=(5, 2, []))

        return service

    @pytest.fixture
    def temp_csv_file(self):
        """Create a temporary CSV file for testing."""
        with tempfile.NamedTemporaryFile(suffix=".csv", mode="w", delete=False) as temp:
            writer = csv.DictWriter(temp, fieldnames=FLASHCARD_CSV_HEADERS)
            writer.writeheader()

            # Add a test card
            writer.writerow(
                {
                    "id": "test-card-1",
                    "front": "Test Front",
                    "back": "Test Back",
                    "language": "en",
                    "created_at": datetime.now().isoformat(),
                    "due_date": "",
                    "interval": "1.0",
                    "ease_factor": "2.5",
                    "review_count": "0",
                    "deck_id": "",
                    "deck_name": "Test Import Deck",
                }
            )

            temp_path = temp.name

        yield temp_path

        # Clean up
        os.unlink(temp_path)

    def test_export_deck_to_csv(self, csv_service):
        """Test exporting a deck to CSV."""
        # Execute
        result = csv_service.export_deck_to_csv("deck-123", "/tmp")

        # Verify
        assert result["success"] is True
        assert "exported successfully" in result["message"]
        assert result["file_path"] == "/path/to/exported.csv"
        csv_service.csv_manager.export_deck_to_csv.assert_called_once_with("deck-123", "/tmp")

    def test_export_all_decks(self, csv_service):
        """Test exporting all decks for a user."""
        # Execute
        result = csv_service.export_all_decks("user-123", "/tmp")

        # Verify
        assert result["success"] is True
        assert "Exported 2 decks" in result["message"]
        assert len(result["files"]) == 2
        csv_service.csv_manager.export_all_decks_to_csv.assert_called_once_with("user-123", "/tmp")

    def test_import_from_csv(self, csv_service, temp_csv_file):
        """Test importing flashcards from CSV."""
        # Execute
        result = csv_service.import_from_csv(temp_csv_file, "user-123")

        # Verify
        assert result["success"] is True
        assert "Successfully imported 5 flashcards" in result["message"]
        assert result["cards_imported"] == 5
        assert result["decks_created"] == 2
        csv_service.csv_manager.import_flashcards_from_csv.assert_called_once()

    @pytest.mark.asyncio
    async def test_import_with_auto_deck(self, csv_service, temp_csv_file, flashcard_repo_mock):
        """Test importing with automatic deck creation."""
        # Setup
        flashcard_repo_mock.get_by_deck.return_value = [
            Flashcard(id="card-1", front="Paris", back="Capital of France"),
            Flashcard(id="card-2", front="London", back="Capital of England"),
        ]

        # Mock the import_from_csv method to avoid calling the real implementation
        csv_service.import_from_csv = MagicMock(
            return_value={"success": True, "cards_imported": 2, "decks_created": 1, "warnings": []}
        )

        # Execute
        result = await csv_service.import_with_auto_deck(temp_csv_file, "user-123")

        # Verify
        assert result["success"] is True
        csv_service.import_from_csv.assert_called_once()
