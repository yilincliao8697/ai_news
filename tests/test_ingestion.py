"""Tests for the ingestion module."""

from unittest.mock import MagicMock, patch
from datetime import datetime

from dataclasses_shared import Feed, RawArticle
from ingestion.fetcher import (
    MAX_CONTENT_LENGTH,
    _extract_content,
    _strip_html,
    fetch_feed,
    fetch_articles,
)


def test_strip_html_removes_tags():
    assert _strip_html("<p>Hello <b>world</b></p>") == "Hello world"


def test_strip_html_handles_empty():
    assert _strip_html("") == ""


def test_strip_html_plain_text_unchanged():
    assert _strip_html("plain text") == "plain text"


def _make_mock_feed(entries: list[dict]) -> MagicMock:
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
        mock_entries.append(entry)
    mock_feed.entries = mock_entries
    return mock_feed


def _make_feed_obj(feed_id: int = 1, category: str = "industry") -> Feed:
    return Feed(id=feed_id, name="Mock Feed", url="https://mock.com/feed",
                category=category, enabled=True)


@patch("ingestion.fetcher.feedparser.parse")
def test_fetch_feed_returns_raw_articles(mock_parse):
    mock_parse.return_value = _make_mock_feed([
        {"title": "AI News", "link": "https://example.com/1", "summary": "Summary"},
    ])
    results = fetch_feed("industry", "https://fake.com")
    assert len(results) == 1
    assert isinstance(results[0], RawArticle)
    assert results[0].topic == "industry"


@patch("ingestion.fetcher.feedparser.parse")
def test_fetch_feed_skips_missing_link(mock_parse):
    mock_parse.return_value = _make_mock_feed([
        {"title": "No Link", "link": "", "summary": "text"},
    ])
    assert fetch_feed("research", "https://fake.com") == []


@patch("ingestion.fetcher.feedparser.parse")
def test_fetch_feed_truncates_content(mock_parse):
    mock_parse.return_value = _make_mock_feed([
        {"title": "Long", "link": "https://example.com/long", "summary": "x" * 2000},
    ])
    results = fetch_feed("science", "https://fake.com")
    assert len(results[0].content) <= MAX_CONTENT_LENGTH


@patch("database.crud.get_enabled_feeds")
@patch("ingestion.fetcher.fetch_feed")
def test_fetch_articles_uses_enabled_feeds(mock_fetch_feed, mock_get_enabled):
    mock_get_enabled.return_value = [_make_feed_obj(1), _make_feed_obj(2)]
    mock_fetch_feed.return_value = [
        RawArticle(title="T", link="https://x.com", source="S", topic="industry", content="c")
    ]
    results = fetch_articles()
    assert mock_fetch_feed.call_count == 2
    assert len(results) == 2


@patch("database.crud.increment_feed_error")
@patch("database.crud.get_enabled_feeds")
@patch("ingestion.fetcher.fetch_feed", side_effect=Exception("network error"))
def test_fetch_articles_increments_error_on_failure(mock_fetch, mock_enabled, mock_error):
    mock_enabled.return_value = [_make_feed_obj(1)]
    results = fetch_articles()
    assert results == []
    mock_error.assert_called_once_with(1)
