"""Tests for the ingestion module."""

from unittest.mock import MagicMock, patch

import pytest

from dataclasses_shared import RawArticle
from ingestion.fetcher import (
    _strip_html,
    _extract_content,
    fetch_feed,
    fetch_articles,
    RSS_FEEDS,
    MAX_CONTENT_LENGTH,
)


def test_strip_html_removes_tags():
    assert _strip_html("<p>Hello <b>world</b></p>") == "Hello world"


def test_strip_html_handles_none():
    assert _strip_html("") == ""


def test_strip_html_plain_text_unchanged():
    assert _strip_html("plain text") == "plain text"


def _make_mock_feed(entries: list[dict]) -> MagicMock:
    """Build a minimal feedparser-like mock."""
    feed_meta = MagicMock()
    feed_meta.title = "Mock Source"

    mock_feed = MagicMock()
    mock_feed.feed = feed_meta

    mock_entries = []
    for e in entries:
        entry = MagicMock(spec=[])
        entry.title = e.get("title", "")
        entry.link = e.get("link", "")
        entry.summary = e.get("summary", "")
        # No content attribute by default
        mock_entries.append(entry)

    mock_feed.entries = mock_entries
    return mock_feed


@patch("ingestion.fetcher.feedparser.parse")
def test_fetch_feed_returns_raw_articles(mock_parse):
    mock_parse.return_value = _make_mock_feed([
        {"title": "AI News", "link": "https://example.com/1", "summary": "Summary text"},
    ])
    results = fetch_feed("ai", "https://fake-url.com")
    assert len(results) == 1
    assert isinstance(results[0], RawArticle)
    assert results[0].topic == "ai"
    assert results[0].title == "AI News"


@patch("ingestion.fetcher.feedparser.parse")
def test_fetch_feed_skips_missing_link(mock_parse):
    mock_parse.return_value = _make_mock_feed([
        {"title": "No Link Article", "link": "", "summary": "text"},
    ])
    results = fetch_feed("tech", "https://fake-url.com")
    assert results == []


@patch("ingestion.fetcher.feedparser.parse")
def test_fetch_feed_truncates_content(mock_parse):
    long_text = "x" * 2000
    mock_parse.return_value = _make_mock_feed([
        {"title": "Long", "link": "https://example.com/long", "summary": long_text},
    ])
    results = fetch_feed("science", "https://fake-url.com")
    assert len(results[0].content) <= MAX_CONTENT_LENGTH


@patch("ingestion.fetcher.fetch_feed")
def test_fetch_articles_aggregates_all_feeds(mock_fetch_feed):
    mock_fetch_feed.return_value = [
        RawArticle(title="T", link="https://x.com", source="S", topic="ai", content="c")
    ]
    results = fetch_articles()
    # Called once per feed in RSS_FEEDS
    assert mock_fetch_feed.call_count == len(RSS_FEEDS)
    assert len(results) == len(RSS_FEEDS)


@patch("ingestion.fetcher.fetch_feed", side_effect=Exception("network error"))
def test_fetch_articles_continues_on_feed_error(mock_fetch_feed):
    # Should not raise — just skip broken feeds
    results = fetch_articles()
    assert results == []
