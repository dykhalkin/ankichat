"""
Tests for the LLM integration module.
"""

import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.llm import LLMClient


@pytest.fixture
def mock_async_openai():
    """Create a mock for the AsyncOpenAI client."""
    with patch("src.llm.AsyncOpenAI") as mock_openai_class:
        # Setup the mock client instance
        mock_client = MagicMock()
        mock_client.chat = MagicMock()
        mock_client.chat.completions = MagicMock()
        mock_client.chat.completions.create = AsyncMock()

        # Configure the class to return our mock client
        mock_openai_class.return_value = mock_client

        yield mock_client


@pytest.mark.asyncio
async def test_detect_language(mock_async_openai):
    """Test language detection functionality."""
    # Setup mock response
    mock_response = MagicMock()
    mock_response.choices = [
        MagicMock(
            message=MagicMock(content=json.dumps({"language_code": "fr", "confidence": 0.95}))
        )
    ]
    mock_async_openai.chat.completions.create.return_value = mock_response

    # Create client and test
    client = LLMClient(model="test-model")
    language_code, confidence = await client.detect_language("Bonjour le monde")

    # Verify results
    assert language_code == "fr"
    assert confidence == 0.95

    # Verify API was called correctly
    mock_async_openai.chat.completions.create.assert_called_once()
    call_args = mock_async_openai.chat.completions.create.call_args[1]
    assert call_args["model"] == "test-model"
    assert len(call_args["messages"]) == 2
    assert call_args["messages"][1]["content"] == "Bonjour le monde"
    assert call_args["response_format"] == {"type": "json_object"}


@pytest.mark.asyncio
async def test_detect_language_error_handling(mock_async_openai):
    """Test that language detection handles errors gracefully."""
    # Setup mock to raise an exception
    mock_async_openai.chat.completions.create.side_effect = Exception("Test error")

    # Create client and test
    client = LLMClient()
    language_code, confidence = await client.detect_language("Hello world")

    # Verify default values are returned on error
    assert language_code == "en"
    assert confidence == 0.0


@pytest.mark.asyncio
async def test_generate_flashcard_content(mock_async_openai):
    """Test flashcard content generation."""
    # Setup mock response
    content = {
        "definition": "A greeting in French",
        "example_sentence": "Bonjour, comment ça va?",
        "pronunciation_guide": "bɔ̃.ʒuʁ",
        "part_of_speech": "interjection",
        "notes": "Commonly used as a formal greeting",
    }

    mock_response = MagicMock()
    mock_response.choices = [MagicMock(message=MagicMock(content=json.dumps(content)))]
    mock_async_openai.chat.completions.create.return_value = mock_response

    # Create client and test
    client = LLMClient()
    result = await client.generate_flashcard_content("bonjour", "fr")

    # Verify results
    assert result["word"] == "bonjour"
    assert result["language_code"] == "fr"
    assert result["definition"] == "A greeting in French"
    assert result["example_sentence"] == "Bonjour, comment ça va?"
    assert result["pronunciation_guide"] == "bɔ̃.ʒuʁ"
    assert result["part_of_speech"] == "interjection"

    # Verify API was called correctly
    mock_async_openai.chat.completions.create.assert_called_once()
    call_args = mock_async_openai.chat.completions.create.call_args[1]
    assert (
        "Create a flashcard for the fr word or phrase: bonjour"
        in call_args["messages"][1]["content"]
    )
    assert call_args["response_format"] == {"type": "json_object"}


@pytest.mark.asyncio
async def test_generate_flashcard_content_error_handling(mock_async_openai):
    """Test that content generation handles errors gracefully."""
    # Setup mock to raise an exception
    mock_async_openai.chat.completions.create.side_effect = Exception("Test error")

    # Create client and test
    client = LLMClient()
    result = await client.generate_flashcard_content("hello", "en")

    # Verify fallback content is returned
    assert result["word"] == "hello"
    assert result["language_code"] == "en"
    assert "Definition for hello" in result["definition"]
    assert "Example sentence with hello" in result["example_sentence"]
    assert result["pronunciation_guide"] == "N/A"
    assert result["notes"] == "Content generation failed"
