"""Tests for database CRUD functions."""

import os
import pytest
from datetime import datetime

os.environ["DATABASE_URL"] = "sqlite:///./test_news.db"

from dataclasses_shared import Article
from database.crud import save_article, get_articles, get_articles_by_topic
from database.models import init_db, Base, engine


@pytest.fixture(autouse=True)
def reset_db():
    """Drop and recreate all tables before each test."""
    Base.metadata.drop_all(bind=engine)
    init_db()
    yield
    Base.metadata.drop_all(bind=engine)


def make_article(link: str = "https://example.com/1", topic: str = "ai") -> Article:
    return Article(
        title="Test Article",
        link=link,
        source="TestSource",
        topic=topic,
        summary="This is a test summary.",
        created_at=datetime.utcnow(),
    )


def test_save_article_inserts():
    article = make_article()
    result = save_article(article)
    assert result is True


def test_save_article_skips_duplicate():
    article = make_article()
    save_article(article)
    result = save_article(article)
    assert result is False


def test_get_articles_returns_saved():
    save_article(make_article())
    articles = get_articles()
    assert len(articles) == 1
    assert articles[0].title == "Test Article"


def test_get_articles_by_topic_filters():
    save_article(make_article(link="https://example.com/1", topic="ai"))
    save_article(make_article(link="https://example.com/2", topic="tech"))
    ai_articles = get_articles_by_topic("ai")
    assert len(ai_articles) == 1
    assert ai_articles[0].topic == "ai"


def test_get_articles_empty():
    assert get_articles() == []
