"""Tests for filter and summarize agents. Mocks all Anthropic API calls."""

import json
from unittest.mock import MagicMock, patch

import pytest

from dataclasses_shared import FilterResult, RawArticle, SummaryResult


def make_raw_article(topic: str = "ai") -> RawArticle:
    return RawArticle(
        title="New AI Model Released",
        link="https://example.com/ai-model",
        source="TechCrunch",
        topic=topic,
        content="A new large language model was released today with improved reasoning.",
    )


def _mock_message(content: str) -> MagicMock:
    """Build a minimal mock of an Anthropic API response."""
    msg = MagicMock()
    msg.content = [MagicMock(text=content)]
    return msg


def _mock_json_message(data: dict) -> MagicMock:
    """Mock a JSON response; the agents prefill '{', so the API returns the rest."""
    return _mock_message(json.dumps(data)[1:])


# --- filter_agent tests ---

@patch("agents.filter_agent._client")
def test_filter_article_relevant(mock_client):
    mock_client.messages.create.return_value = _mock_json_message(
        {"is_relevant": True, "reason": "Directly about AI."}
    )
    from agents.filter_agent import filter_article
    result = filter_article(make_raw_article())
    assert isinstance(result, FilterResult)
    assert result.is_relevant is True
    assert result.reason == "Directly about AI."


@patch("agents.filter_agent._client")
def test_filter_article_not_relevant(mock_client):
    mock_client.messages.create.return_value = _mock_json_message(
        {"is_relevant": False, "reason": "Not related to AI."}
    )
    from agents.filter_agent import filter_article
    result = filter_article(make_raw_article())
    assert result.is_relevant is False
    assert result.reason == "Not related to AI."


@patch("agents.filter_agent._client")
def test_filter_article_handles_bad_json(mock_client):
    mock_client.messages.create.return_value = _mock_message("not json at all")
    from agents.filter_agent import filter_article
    result = filter_article(make_raw_article())
    assert result.is_relevant is False
    assert "error" in result.reason.lower()


# --- summarize_agent tests ---

@patch("agents.summarize_agent._client")
def test_summarize_article_returns_summary(mock_client):
    summary_text = "This model improves reasoning. It was released by a major lab."
    mock_client.messages.create.return_value = _mock_json_message(
        {"summary": summary_text}
    )
    from agents.summarize_agent import summarize_article
    result = summarize_article(make_raw_article())
    assert isinstance(result, SummaryResult)
    assert result.summary == summary_text


@patch("agents.summarize_agent._client")
def test_summarize_article_handles_bad_json(mock_client):
    mock_client.messages.create.return_value = _mock_message("bad response")
    from agents.summarize_agent import summarize_article
    result = summarize_article(make_raw_article())
    assert result.summary == ""
