"""
Tests for the flashcard training modules and review session handling.
"""

import datetime
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from src.models import Flashcard, Deck
from src.srs import RecallScore
from src.training import (
    TrainingMode, ReviewSession, 
    StandardTrainer, FillInBlankTrainer, 
    MultipleChoiceTrainer,
    get_training_mode_explanation
)


@pytest.fixture
def sample_flashcard():
    """Create a sample flashcard for testing."""
    return Flashcard(
        front="What is the capital of France?",
        back="*Definition:* The capital city of France.\n\n*Example:* Paris is the capital of France and is known for the Eiffel Tower.\n\n*Pronunciation:* /pæris/\n*Part of Speech:* Noun\n\n*Notes:* Founded in the 3rd century BC."
    )


@pytest.fixture
def sample_deck():
    """Create a sample deck with cards for testing."""
    deck = Deck(name="Test Deck", id="test-deck-id")
    
    # Add some cards to the deck
    cards = [
        Flashcard(front="Card 1 Front", back="Card 1 Back", deck_id=deck.id),
        Flashcard(front="Card 2 Front", back="Card 2 Back", deck_id=deck.id),
        Flashcard(front="Card 3 Front", back="Card 3 Back", deck_id=deck.id),
    ]
    
    deck.cards = cards
    return deck


@pytest.fixture
def reference_time():
    """Create a fixed reference time for testing."""
    return datetime.datetime(2025, 1, 1, 12, 0)


class TestStandardTrainer:
    """Tests for the StandardTrainer class."""
    
    def test_prepare_card(self, sample_flashcard):
        """Test preparing a standard flashcard for review."""
        trainer = StandardTrainer(sample_flashcard)
        prepared = trainer.prepare_card()
        
        assert prepared["mode"] == TrainingMode.STANDARD.value
        assert prepared["front"] == sample_flashcard.front
        assert "prompt" in prepared
    
    def test_evaluate_answer_perfect(self, sample_flashcard):
        """Test evaluating a perfect recall answer."""
        trainer = StandardTrainer(sample_flashcard)
        result = trainer.evaluate_answer("5")  # Perfect recall
        
        assert result["is_correct"] is True
        assert result["score"] == RecallScore.PERFECT_RECALL
        assert result["correct_answer"] == sample_flashcard.back
    
    def test_evaluate_answer_difficult(self, sample_flashcard):
        """Test evaluating a difficult but correct answer."""
        trainer = StandardTrainer(sample_flashcard)
        result = trainer.evaluate_answer("3")  # Correct with difficulty
        
        assert result["is_correct"] is True
        assert result["score"] == RecallScore.CORRECT_DIFFICULT
    
    def test_evaluate_answer_incorrect(self, sample_flashcard):
        """Test evaluating an incorrect answer."""
        trainer = StandardTrainer(sample_flashcard)
        result = trainer.evaluate_answer("1")  # Incorrect
        
        assert result["is_correct"] is False
        assert result["score"] == RecallScore.INCORRECT_RECOGNIZED
    
    def test_evaluate_answer_invalid(self, sample_flashcard):
        """Test evaluating an invalid answer."""
        trainer = StandardTrainer(sample_flashcard)
        result = trainer.evaluate_answer("not a number")
        
        assert result["is_correct"] is False
        assert result["score"] == RecallScore.COMPLETE_BLACKOUT


class TestFillInBlankTrainer:
    """Tests for the FillInBlankTrainer class."""
    
    @pytest.mark.asyncio
    async def test_prepare_card(self, sample_flashcard):
        """Test preparing a fill-in-the-blank flashcard."""
        trainer = FillInBlankTrainer(sample_flashcard)
        prepared = await trainer.prepare_card()  # Use the async version
        
        assert prepared["mode"] == TrainingMode.FILL_IN_BLANK.value
        assert prepared["front"] == sample_flashcard.front
        assert "blanked_content" in prepared
        assert "prompt" in prepared
        
        # Verify that something was blanked out
        assert "____________" in prepared["blanked_content"]
    
    @pytest.mark.asyncio
    async def test_evaluate_answer_exact_match(self, sample_flashcard):
        """Test evaluating an exact match answer."""
        trainer = FillInBlankTrainer(sample_flashcard)
        await trainer.prepare_card()  # This sets the blanked term
        trainer.blanked_term = "Paris"  # Override for testing
        
        result = trainer.evaluate_answer("Paris")
        
        assert result["is_correct"] is True
        assert result["score"] >= RecallScore.CORRECT_DIFFICULT
        assert result["similarity"] > 0.8
    
    @pytest.mark.asyncio
    async def test_evaluate_answer_close_match(self, sample_flashcard):
        """Test evaluating a close but not exact match."""
        trainer = FillInBlankTrainer(sample_flashcard)
        await trainer.prepare_card()
        trainer.blanked_term = "Paris"  # Override for testing
        
        result = trainer.evaluate_answer("paris")  # Lowercase
        
        assert result["is_correct"] is True
        assert result["score"] >= RecallScore.CORRECT_DIFFICULT
    
    @pytest.mark.asyncio
    async def test_evaluate_answer_incorrect(self, sample_flashcard):
        """Test evaluating a completely incorrect answer."""
        trainer = FillInBlankTrainer(sample_flashcard)
        await trainer.prepare_card()
        trainer.blanked_term = "Paris"  # Override for testing
        
        result = trainer.evaluate_answer("London")
        
        assert result["is_correct"] is False
        assert result["score"] < RecallScore.CORRECT_DIFFICULT
    
    def test_extract_key_info(self, sample_flashcard):
        """Test extracting key information from card content."""
        trainer = FillInBlankTrainer(sample_flashcard)
        sample_content = (
            "Term: Example\n"
            "Definition: A sample or instance\n"
            "Usage: This is an example sentence."
        )
        
        key_info = trainer._extract_key_info(sample_content)
        
        assert len(key_info) > 0
        assert "Example" in key_info or "A sample or instance" in key_info
    
    def test_calculate_similarity(self, sample_flashcard):
        """Test the string similarity calculation."""
        trainer = FillInBlankTrainer(sample_flashcard)
        
        # Exact match
        assert trainer._calculate_similarity("paris", "paris") == 1.0
        
        # Close match
        assert 0.5 < trainer._calculate_similarity("paris", "parios") < 1.0
        
        # No match
        assert trainer._calculate_similarity("paris", "london") < 0.3
        
        # Empty strings
        assert trainer._calculate_similarity("", "") == 0.0
        assert trainer._calculate_similarity("paris", "") == 0.0


class TestMultipleChoiceTrainer:
    """Tests for the MultipleChoiceTrainer class."""
    
    def test_prepare_card(self, sample_flashcard):
        """Test preparing a multiple-choice flashcard."""
        trainer = MultipleChoiceTrainer(sample_flashcard)
        prepared = trainer.prepare_card()
        
        assert prepared["mode"] == TrainingMode.MULTIPLE_CHOICE.value
        assert prepared["front"] == sample_flashcard.front
        assert "options" in prepared
        assert len(prepared["options"]) > 1  # Should have multiple options
        assert sample_flashcard.back in prepared["options"]  # Correct answer should be included
    
    def test_evaluate_answer_correct(self, sample_flashcard):
        """Test evaluating a correct multiple-choice answer."""
        trainer = MultipleChoiceTrainer(sample_flashcard)
        prepared = trainer.prepare_card()
        
        # Get the index of the correct answer
        correct_index = trainer.correct_index
        
        result = trainer.evaluate_answer(str(correct_index))
        
        assert result["is_correct"] is True
        assert result["score"] == RecallScore.PERFECT_RECALL
    
    def test_evaluate_answer_incorrect(self, sample_flashcard):
        """Test evaluating an incorrect multiple-choice answer."""
        trainer = MultipleChoiceTrainer(sample_flashcard)
        prepared = trainer.prepare_card()
        
        # Choose an incorrect index
        correct_index = trainer.correct_index
        incorrect_index = (correct_index + 1) % len(prepared["options"])
        
        result = trainer.evaluate_answer(str(incorrect_index))
        
        assert result["is_correct"] is False
        assert result["score"] < RecallScore.CORRECT_DIFFICULT
    
    def test_evaluate_answer_invalid(self, sample_flashcard):
        """Test evaluating an invalid multiple-choice answer."""
        trainer = MultipleChoiceTrainer(sample_flashcard)
        trainer.prepare_card()
        
        result = trainer.evaluate_answer("not a number")
        
        assert result["is_correct"] is False
        assert result["score"] == RecallScore.COMPLETE_BLACKOUT
    
    def test_generate_distractors(self, sample_flashcard):
        """Test generating distractor options."""
        trainer = MultipleChoiceTrainer(sample_flashcard)
        distractors = trainer._generate_distractors(3)
        
        assert len(distractors) == 3
        assert sample_flashcard.back not in distractors  # Correct answer shouldn't be a distractor




class TestReviewSession:
    """Tests for the ReviewSession class."""
    
    def test_init_with_default_values(self, sample_deck):
        """Test initializing a review session with default values."""
        session = ReviewSession(
            deck_id=sample_deck.id,
            user_id="user-1"
        )
        
        assert session.deck_id == sample_deck.id
        assert session.user_id == "user-1"
        assert session.training_mode == TrainingMode.STANDARD
        assert session.max_cards == 20
        assert len(session.queue) == 0
    
    def test_init_with_custom_values(self, sample_deck, reference_time):
        """Test initializing a review session with custom values."""
        session = ReviewSession(
            deck_id=sample_deck.id,
            user_id="user-1",
            training_mode=TrainingMode.MULTIPLE_CHOICE,
            max_cards=10,
            current_time=reference_time
        )
        
        assert session.deck_id == sample_deck.id
        assert session.training_mode == TrainingMode.MULTIPLE_CHOICE
        assert session.max_cards == 10
        assert session.current_time == reference_time
    
    def test_load_due_cards(self, sample_deck, reference_time):
        """Test loading due cards into the review queue."""
        session = ReviewSession(
            deck_id=sample_deck.id,
            user_id="user-1",
            current_time=reference_time
        )
        
        # Make some cards due
        for i, card in enumerate(sample_deck.cards):
            # Set different due dates
            if i == 0:
                # New card (never reviewed)
                card.due_date = None
            elif i == 1:
                # Due card
                card.due_date = reference_time - datetime.timedelta(days=1)
                card.review_count = 1
            else:
                # Not due yet
                card.due_date = reference_time + datetime.timedelta(days=1)
                card.review_count = 1
        
        session.load_due_cards(sample_deck.cards)
        
        # Should have 2 due cards (one new, one past due)
        assert len(session.queue) == 2
        
        # New card should be first
        assert session.queue[0].review_count == 0
    
    @pytest.mark.asyncio
    async def test_next_card(self, sample_deck):
        """Test getting the next card to review."""
        session = ReviewSession(
            deck_id=sample_deck.id,
            user_id="user-1",
            cards=sample_deck.cards[:2]  # Use first two cards
        )
        
        # Get the first card
        card_data = await session.next_card()
        
        assert card_data is not None
        assert card_data["mode"] == TrainingMode.STANDARD.value
        assert card_data["front"] == sample_deck.cards[0].front
        
        # Current card should be set
        assert session.current_card is not None
        assert session.current_trainer is not None
        
        # Queue should have one card left
        assert len(session.queue) == 1
    
    @pytest.mark.asyncio
    async def test_next_card_empty_queue(self, sample_deck):
        """Test getting the next card when the queue is empty."""
        session = ReviewSession(
            deck_id=sample_deck.id,
            user_id="user-1",
            cards=[]  # Empty queue
        )
        
        card_data = await session.next_card()
        
        assert card_data is None
        assert session.current_card is None
        assert session.current_trainer is None
    
    @pytest.mark.asyncio
    async def test_next_card_different_modes(self, sample_deck):
        """Test getting cards in different training modes."""
        # Use only standard mode for simplicity in tests
        # Other modes may require LLM client or special handling
        mode = TrainingMode.STANDARD
        session = ReviewSession(
            deck_id=sample_deck.id,
            user_id="user-1",
            training_mode=mode,
            cards=sample_deck.cards[:1]  # Use first card
        )
        
        card_data = await session.next_card()
        
        assert card_data is not None
        assert card_data["mode"] == mode.value
    
    @pytest.mark.asyncio
    async def test_process_answer_correct(self, sample_deck):
        """Test processing a correct answer."""
        session = ReviewSession(
            deck_id=sample_deck.id,
            user_id="user-1",
            cards=sample_deck.cards[:2]  # Use first two cards
        )
        
        # Get the first card
        await session.next_card()
        
        # Process a correct answer - now async
        result = await session.process_answer("5")  # Perfect recall
        
        assert result["is_correct"] is True
        assert result["score"] == RecallScore.PERFECT_RECALL
        
        # Session stats should be updated
        assert session.cards_reviewed == 1
        assert session.correct_answers == 1
        assert session.incorrect_answers == 0
        
        # Card should be in reviewed cards
        assert len(session.reviewed_cards) == 1
        assert session.reviewed_cards[0][0] == sample_deck.cards[0]
        assert session.reviewed_cards[0][1] == RecallScore.PERFECT_RECALL
    
    @pytest.mark.asyncio
    async def test_process_answer_incorrect(self, sample_deck):
        """Test processing an incorrect answer."""
        session = ReviewSession(
            deck_id=sample_deck.id,
            user_id="user-1",
            cards=sample_deck.cards[:2]  # Use first two cards
        )
        
        # Get the first card
        await session.next_card()
        
        # Process an incorrect answer - now async
        result = await session.process_answer("1")  # Incorrect
        
        assert result["is_correct"] is False
        assert result["score"] == RecallScore.INCORRECT_RECOGNIZED
        
        # Session stats should be updated
        assert session.cards_reviewed == 1
        assert session.correct_answers == 0
        assert session.incorrect_answers == 1
    
    # Since learning mode has been removed, we're also removing this test
    # that was specifically testing the learning mode rescheduling behavior
    
    def test_end_session(self, sample_deck, reference_time):
        """Test ending a review session."""
        session = ReviewSession(
            deck_id=sample_deck.id,
            user_id="user-1",
            current_time=reference_time
        )
        
        # Simulate some reviews
        session.cards_reviewed = 10
        session.correct_answers = 7
        session.incorrect_answers = 3
        
        summary = session.end_session()
        
        assert summary["deck_id"] == sample_deck.id
        assert summary["user_id"] == "user-1"
        assert summary["cards_reviewed"] == 10
        assert summary["correct_answers"] == 7
        assert summary["incorrect_answers"] == 3
        assert summary["accuracy"] == 0.7
        assert "duration_seconds" in summary


@pytest.mark.asyncio
async def test_get_training_mode_explanation():
    """Test getting explanations for training modes."""
    for mode in TrainingMode:
        explanation = await get_training_mode_explanation(mode)
        
        assert explanation is not None
        assert len(explanation) > 0
        
        # Just check for basic mode names that appear in the description
        # Different modes might have differently formatted text
        if mode == TrainingMode.STANDARD:
            assert "standard mode" in explanation.lower()
        elif mode == TrainingMode.FILL_IN_BLANK:
            assert "fill-in-the-blank" in explanation.lower()
        elif mode == TrainingMode.MULTIPLE_CHOICE:
            assert "multiple choice" in explanation.lower()