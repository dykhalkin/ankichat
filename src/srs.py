"""
Spaced Repetition System (SRS) module.

This module implements the SM-2 algorithm for scheduling flashcard reviews
and updating card metadata based on user performance.
"""

import datetime
from enum import IntEnum
from typing import Union

from src.models import Flashcard


class RecallScore(IntEnum):
    """
    Rating scale for user recall performance.

    Based on the SuperMemo SM-2 algorithm:
    0 - Complete blackout (incorrect)
    1 - Incorrect, but recognized answer when shown
    2 - Incorrect, but answer seems familiar
    3 - Correct with significant difficulty
    4 - Correct with some difficulty
    5 - Perfect recall
    """

    COMPLETE_BLACKOUT = 0
    INCORRECT_RECOGNIZED = 1
    INCORRECT_FAMILIAR = 2
    CORRECT_DIFFICULT = 3
    CORRECT_HESITATION = 4
    PERFECT_RECALL = 5


class SRSEngine:
    """
    Implementation of the SuperMemo SM-2 spaced repetition algorithm.

    This engine calculates intervals between card reviews based on
    user performance and updates card metadata accordingly.
    """

    # Minimum and maximum values for ease factor to prevent extreme scheduling
    MIN_EASE_FACTOR = 1.3
    MAX_EASE_FACTOR = 5.0

    # Interval modifiers for different performance levels
    AGAIN_INTERVAL_MODIFIER = 0.2  # For scores < 3

    @staticmethod
    def process_recall_result(
        card: Flashcard, score: Union[RecallScore, int], current_time: datetime.datetime = None
    ) -> Flashcard:
        """
        Process the result of a flashcard review and schedule the next review.

        Args:
            card: The flashcard that was reviewed
            score: The recall performance score (0-5)
            current_time: The current time (defaults to now if not provided)

        Returns:
            The updated flashcard with new SRS metadata
        """
        if current_time is None:
            current_time = datetime.datetime.now()

        # Convert int to RecallScore if needed
        if isinstance(score, int):
            score = RecallScore(score)

        # Store original ease factor for comparison (for testing)
        original_ease_factor = card.ease_factor

        # Update review count
        card.review_count += 1

        # Calculate new ease factor
        # SM-2 formula: EF := EF + (0.1 - (5 - q) * (0.08 + (5 - q) * 0.02))
        # where q is the quality of response (0-5)
        ease_adjustment = 0.1 - (5 - score) * (0.08 + (5 - score) * 0.02)
        new_ease_factor = card.ease_factor + ease_adjustment

        # Ensure ease factor stays within bounds
        card.ease_factor = max(
            SRSEngine.MIN_EASE_FACTOR, min(new_ease_factor, SRSEngine.MAX_EASE_FACTOR)
        )

        # Store interval before calculating the new one (for correct calculation reference)
        old_interval = card.interval

        # Calculate new interval based on performance
        if score < RecallScore.CORRECT_DIFFICULT:
            # If recall was incorrect, reset interval with a penalty
            new_interval = old_interval * SRSEngine.AGAIN_INTERVAL_MODIFIER
            # Ensure minimum interval of 1 day
            new_interval = max(0.2, new_interval)
        else:
            # If recall was correct, apply spaced repetition formula
            if card.review_count == 1:
                new_interval = 1.0  # First successful review
            elif card.review_count == 2:
                new_interval = 6.0  # Second successful review
            else:
                # For subsequent reviews: interval = previous_interval * ease_factor
                # Use original ease factor for multiplication since we already updated the ease factor
                new_interval = old_interval * original_ease_factor

        # Set the new interval and due date
        card.interval = new_interval
        card.due_date = current_time + datetime.timedelta(days=new_interval)

        return card

    @staticmethod
    def reset_card(card: Flashcard, current_time: datetime.datetime = None) -> Flashcard:
        """
        Reset a card's SRS metadata to initial values.

        Args:
            card: The flashcard to reset
            current_time: The current time (defaults to now if not provided)

        Returns:
            The reset flashcard with initial SRS metadata
        """
        if current_time is None:
            current_time = datetime.datetime.now()

        card.interval = 1.0
        card.ease_factor = 2.5
        card.review_count = 0
        card.due_date = current_time + datetime.timedelta(days=1)

        return card

    @staticmethod
    def is_due(card: Flashcard, current_time: datetime.datetime = None) -> bool:
        """
        Check if a card is due for review.

        Args:
            card: The flashcard to check
            current_time: The current time (defaults to now if not provided)

        Returns:
            True if the card is due for review, False otherwise
        """
        if current_time is None:
            current_time = datetime.datetime.now()

        if card.due_date is None:
            return True

        return current_time >= card.due_date
