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
    mock_get_by_topic.return_value = [make_article(topic="tech")]
    response = client.get("/articles?topic=tech")
    assert response.status_code == 200
    data = response.json()
    assert data[0]["topic"] == "tech"
    mock_get_by_topic.assert_called_once_with(topic="tech", limit=100)


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
