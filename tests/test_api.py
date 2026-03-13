"""Tests for the FastAPI API layer."""

import os
import pytest
from datetime import datetime
from unittest.mock import patch

os.environ["DATABASE_URL"] = "sqlite:///./test_news.db"

from fastapi.testclient import TestClient
from dataclasses_shared import Article
from api.main import app

client = TestClient(app)


def make_article(link: str = "https://example.com/1", topic: str = "ai") -> Article:
    return Article(
        title="Test Article",
        link=link,
        source="TestSource",
        topic=topic,
        summary="A short test summary.",
        created_at=datetime(2026, 3, 11, 10, 0, 0),
    )


def test_health():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


@patch("api.main.get_articles")
def test_list_articles_no_filter(mock_get):
    mock_get.return_value = [make_article()]
    response = client.get("/articles")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["title"] == "Test Article"
    assert data[0]["topic"] == "ai"
    assert "created_at" in data[0]


@patch("api.main.get_articles_by_topic")
def test_list_articles_with_valid_topic(mock_get_by_topic):
    mock_get_by_topic.return_value = [make_article(topic="industry")]
    response = client.get("/articles?topic=industry")
    assert response.status_code == 200
    data = response.json()
    assert data[0]["topic"] == "industry"
    mock_get_by_topic.assert_called_once_with(topic="industry", limit=100)


def test_list_articles_invalid_topic():
    response = client.get("/articles?topic=sports")
    assert response.status_code == 400
    assert "error" in response.json()


@patch("api.main.get_articles")
def test_list_articles_limit_param(mock_get):
    mock_get.return_value = []
    client.get("/articles?limit=10")
    mock_get.assert_called_once_with(limit=10)


def test_list_articles_limit_out_of_range():
    response = client.get("/articles?limit=0")
    assert response.status_code == 422   # FastAPI validation error

    response = client.get("/articles?limit=501")
    assert response.status_code == 422


@patch("api.main.get_articles")
def test_created_at_is_iso_string(mock_get):
    mock_get.return_value = [make_article()]
    response = client.get("/articles")
    data = response.json()
    # Should be a parseable ISO string
    datetime.fromisoformat(data[0]["created_at"])

from dataclasses_shared import Feed


def make_feed(feed_id: int = 1) -> Feed:
    return Feed(
        id=feed_id,
        name="Test Feed",
        url="https://testfeed.com/rss",
        category="industry",
        enabled=True,
        last_fetched=datetime(2026, 3, 12, 10, 0, 0),
        error_count=0,
    )


@patch("api.main.get_all_feeds")
@patch("api.main.get_articles_by_source")
def test_list_feeds_returns_all(mock_source, mock_feeds):
    mock_feeds.return_value = [make_feed()]
    mock_source.return_value = []
    response = client.get("/admin/feeds")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["name"] == "Test Feed"
    assert data[0]["category"] == "industry"
    assert "recent_articles" in data[0]
    assert "last_fetched" in data[0]


@patch("api.main.get_all_feeds")
@patch("api.main.get_articles_by_source")
def test_list_feeds_includes_recent_articles(mock_source, mock_feeds):
    mock_feeds.return_value = [make_feed()]
    mock_source.return_value = [
        Article(title="Recent Article", link="https://x.com/1",
                source="Test Feed", topic="industry",
                summary="Summary", created_at=datetime(2026, 3, 12))
    ]
    response = client.get("/admin/feeds")
    data = response.json()
    assert len(data[0]["recent_articles"]) == 1
    assert data[0]["recent_articles"][0]["title"] == "Recent Article"


@patch("api.main.set_feed_enabled", return_value=True)
def test_toggle_feed_enables(mock_toggle):
    response = client.patch("/admin/feeds/1", json={"enabled": True})
    assert response.status_code == 200
    assert response.json() == {"id": 1, "enabled": True}
    mock_toggle.assert_called_once_with(1, True)


@patch("api.main.set_feed_enabled", return_value=False)
def test_toggle_feed_returns_404_for_missing(mock_toggle):
    response = client.patch("/admin/feeds/9999", json={"enabled": True})
    assert response.status_code == 404


def test_list_articles_invalid_topic_updated():
    response = client.get("/articles?topic=ai")
    assert response.status_code == 400
    assert "research" in response.json()["error"]
