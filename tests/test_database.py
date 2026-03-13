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


from dataclasses_shared import Feed
from database.crud import (
    upsert_feed, get_all_feeds, get_enabled_feeds,
    set_feed_enabled, mark_feed_fetched, increment_feed_error,
    get_articles_by_source,
)


def make_feed(url: str = "https://example.com/feed", category: str = "industry") -> Feed:
    return upsert_feed(name="Test Feed", url=url, category=category, enabled=False)


def test_upsert_feed_inserts():
    feed = make_feed()
    assert feed.id is not None
    assert feed.enabled is False


def test_upsert_feed_updates_on_duplicate_url():
    make_feed(url="https://example.com/feed")
    upsert_feed(name="Updated", url="https://example.com/feed", category="research")
    feeds = get_all_feeds()
    assert len(feeds) == 1
    assert feeds[0].name == "Updated"
    assert feeds[0].category == "research"


def test_upsert_feed_does_not_overwrite_enabled():
    feed = make_feed()
    set_feed_enabled(feed.id, True)
    upsert_feed(name="Updated", url="https://example.com/feed", category="research")
    feeds = get_all_feeds()
    assert feeds[0].enabled is True


def test_get_enabled_feeds_filters():
    upsert_feed("Enabled", "https://a.com/feed", "industry", enabled=True)
    upsert_feed("Disabled", "https://b.com/feed", "industry", enabled=False)
    enabled = get_enabled_feeds()
    assert len(enabled) == 1
    assert enabled[0].name == "Enabled"


def test_set_feed_enabled_returns_false_for_missing():
    assert set_feed_enabled(9999, True) is False


def test_mark_feed_fetched_resets_error():
    feed = make_feed()
    increment_feed_error(feed.id)
    mark_feed_fetched(feed.id)
    feeds = get_all_feeds()
    assert feeds[0].error_count == 0
    assert feeds[0].last_fetched is not None


def test_increment_feed_error():
    feed = make_feed()
    increment_feed_error(feed.id)
    increment_feed_error(feed.id)
    assert get_all_feeds()[0].error_count == 2


def test_get_articles_by_source():
    save_article(make_article(link="https://example.com/1", topic="research"))
    save_article(make_article(link="https://example.com/2", topic="industry"))
    results = get_articles_by_source("TestSource")
    assert len(results) == 2


def test_get_articles_by_source_limit():
    for i in range(5):
        save_article(make_article(link=f"https://example.com/{i}", topic="research"))
    assert len(get_articles_by_source("TestSource", limit=2)) == 2
