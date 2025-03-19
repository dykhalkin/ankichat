"""
Tests for the Spaced Repetition System (SRS) module.

These tests cover the implementation of the SM-2 algorithm for scheduling
flashcard reviews and updating card metadata based on user performance.
"""

import datetime

import pytest

from src.models import Flashcard
from src.srs import RecallScore, SRSEngine


@pytest.fixture
def sample_card():
    """Create a sample flashcard for testing."""
    return Flashcard(front="What is the capital of France?", back="Paris")


@pytest.fixture
def reference_time():
    """Create a fixed reference time for consistent testing."""
    return datetime.datetime(2025, 1, 1, 12, 0, 0)


class TestRecallScore:
    """Tests for the RecallScore enum."""

    def test_recall_score_values(self):
        """Test that RecallScore enum has expected values."""
        assert RecallScore.COMPLETE_BLACKOUT == 0
        assert RecallScore.INCORRECT_RECOGNIZED == 1
        assert RecallScore.INCORRECT_FAMILIAR == 2
        assert RecallScore.CORRECT_DIFFICULT == 3
        assert RecallScore.CORRECT_HESITATION == 4
        assert RecallScore.PERFECT_RECALL == 5


class TestSRSEngine:
    """Tests for the SRSEngine class."""

    def test_is_due_with_null_due_date(self, sample_card, reference_time):
        """Test that cards with no due date are always due."""
        sample_card.due_date = None
        assert SRSEngine.is_due(sample_card, reference_time) is True

    def test_is_due_with_past_due_date(self, sample_card, reference_time):
        """Test that cards with past due dates are due."""
        sample_card.due_date = reference_time - datetime.timedelta(days=1)
        assert SRSEngine.is_due(sample_card, reference_time) is True

    def test_is_due_with_future_due_date(self, sample_card, reference_time):
        """Test that cards with future due dates are not due."""
        sample_card.due_date = reference_time + datetime.timedelta(days=1)
        assert SRSEngine.is_due(sample_card, reference_time) is False

    def test_is_due_with_exact_due_date(self, sample_card, reference_time):
        """Test that cards due exactly now are due."""
        sample_card.due_date = reference_time
        assert SRSEngine.is_due(sample_card, reference_time) is True

    def test_reset_card(self, sample_card, reference_time):
        """Test resetting a card's SRS metadata."""
        # Set non-default values
        sample_card.interval = 10.0
        sample_card.ease_factor = 4.0
        sample_card.review_count = 5
        sample_card.due_date = reference_time + datetime.timedelta(days=10)

        # Reset the card
        reset_card = SRSEngine.reset_card(sample_card, reference_time)

        # Verify reset values
        assert reset_card.interval == 1.0
        assert reset_card.ease_factor == 2.5
        assert reset_card.review_count == 0
        assert reset_card.due_date == reference_time + datetime.timedelta(days=1)

    def test_process_recall_perfect_first_review(self, sample_card, reference_time):
        """Test processing a perfect recall on first review."""
        updated_card = SRSEngine.process_recall_result(
            sample_card, RecallScore.PERFECT_RECALL, reference_time
        )

        # Check updated values
        assert updated_card.review_count == 1
        assert updated_card.interval == 1.0  # First review interval is always 1 day
        assert updated_card.ease_factor > 2.5  # Ease factor should increase
        assert updated_card.due_date == reference_time + datetime.timedelta(days=1)

    def test_process_recall_perfect_second_review(self, sample_card, reference_time):
        """Test processing a perfect recall on second review."""
        # First review
        sample_card = SRSEngine.process_recall_result(
            sample_card, RecallScore.PERFECT_RECALL, reference_time
        )

        # Second review
        updated_card = SRSEngine.process_recall_result(
            sample_card, RecallScore.PERFECT_RECALL, reference_time + datetime.timedelta(days=1)
        )

        # Check updated values
        assert updated_card.review_count == 2
        assert updated_card.interval == 6.0  # Second review is 6 days
        assert updated_card.due_date == reference_time + datetime.timedelta(
            days=1
        ) + datetime.timedelta(days=6)

    def test_process_recall_perfect_third_review(self, sample_card, reference_time):
        """Test processing a perfect recall on third review."""
        # First review
        sample_card = SRSEngine.process_recall_result(
            sample_card, RecallScore.PERFECT_RECALL, reference_time
        )

        # Second review
        sample_card = SRSEngine.process_recall_result(
            sample_card, RecallScore.PERFECT_RECALL, reference_time + datetime.timedelta(days=1)
        )

        # Get ease factor before third review
        ease_factor_before = sample_card.ease_factor

        # Third review
        updated_card = SRSEngine.process_recall_result(
            sample_card, RecallScore.PERFECT_RECALL, reference_time + datetime.timedelta(days=7)
        )

        # Check updated values
        assert updated_card.review_count == 3
        assert updated_card.interval == pytest.approx(6.0 * ease_factor_before)
        assert updated_card.ease_factor > ease_factor_before  # Should increase again

    def test_process_recall_difficult(self, sample_card, reference_time):
        """Test processing a difficult but correct recall."""
        updated_card = SRSEngine.process_recall_result(
            sample_card, RecallScore.CORRECT_DIFFICULT, reference_time
        )

        # Check updated values
        assert updated_card.review_count == 1
        assert updated_card.interval == 1.0
        assert updated_card.ease_factor < 2.5  # Ease factor should decrease

    def test_process_recall_incorrect(self, sample_card, reference_time):
        """Test processing an incorrect recall."""
        # First do a successful review to increase interval
        sample_card = SRSEngine.process_recall_result(
            sample_card, RecallScore.PERFECT_RECALL, reference_time
        )
        sample_card = SRSEngine.process_recall_result(
            sample_card, RecallScore.PERFECT_RECALL, reference_time + datetime.timedelta(days=1)
        )

        # Now interval should be 6.0
        assert sample_card.interval == 6.0

        # Store the ease factor before failure
        ease_factor_before = sample_card.ease_factor

        # Now fail the card
        updated_card = SRSEngine.process_recall_result(
            sample_card, RecallScore.COMPLETE_BLACKOUT, reference_time + datetime.timedelta(days=7)
        )

        # Check updated values
        assert updated_card.review_count == 3
        assert updated_card.interval == pytest.approx(6.0 * SRSEngine.AGAIN_INTERVAL_MODIFIER)
        # Compare with stored ease factor (not the card's current ease factor, which was modified)
        assert updated_card.ease_factor < ease_factor_before  # Ease factor should decrease

    def test_ease_factor_bounds(self, sample_card, reference_time):
        """Test that ease factor stays within allowed bounds."""
        # Test minimum bound
        for _ in range(10):  # Multiple very bad reviews
            sample_card = SRSEngine.process_recall_result(
                sample_card, RecallScore.COMPLETE_BLACKOUT, reference_time
            )

        assert sample_card.ease_factor == SRSEngine.MIN_EASE_FACTOR

        # Reset the card
        sample_card = SRSEngine.reset_card(sample_card, reference_time)

        # Test maximum bound
        # Set ease factor close to max to ensure we hit the max bound
        sample_card.ease_factor = 4.9

        # One perfect review should push it to the max
        sample_card = SRSEngine.process_recall_result(
            sample_card, RecallScore.PERFECT_RECALL, reference_time
        )

        assert sample_card.ease_factor == SRSEngine.MAX_EASE_FACTOR

    def test_int_score_conversion(self, sample_card, reference_time):
        """Test that integer scores are converted to RecallScore enum."""
        # Using integer score
        card1 = SRSEngine.process_recall_result(sample_card, 5, reference_time)

        # Using enum score
        sample_card2 = Flashcard(front=sample_card.front, back=sample_card.back)
        card2 = SRSEngine.process_recall_result(
            sample_card2, RecallScore.PERFECT_RECALL, reference_time
        )

        # Results should be identical
        assert card1.interval == card2.interval
        assert card1.ease_factor == card2.ease_factor
        assert card1.review_count == card2.review_count
        assert card1.due_date == card2.due_date

    def test_borderline_case_score_3(self, sample_card, reference_time):
        """Test the borderline case of score 3 (barely passing)."""
        updated_card = SRSEngine.process_recall_result(
            sample_card, RecallScore.CORRECT_DIFFICULT, reference_time
        )

        # This is the threshold for "correct" so interval should advance
        assert updated_card.interval == 1.0
        assert updated_card.ease_factor < 2.5  # But ease factor decreases

    def test_borderline_case_score_2(self, sample_card, reference_time):
        """Test the borderline case of score 2 (barely failing)."""
        # Set interval high enough that the penalty doesn't hit the minimum
        sample_card.interval = 5.0

        updated_card = SRSEngine.process_recall_result(
            sample_card, RecallScore.INCORRECT_FAMILIAR, reference_time
        )

        # Should be treated as incorrect
        assert updated_card.interval == pytest.approx(5.0 * SRSEngine.AGAIN_INTERVAL_MODIFIER)
        assert updated_card.ease_factor < 2.5  # Ease factor decreases
