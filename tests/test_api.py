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


# --- Bulk toggle tests ---

@patch("api.main.get_all_feeds")
@patch("api.main.set_feed_enabled")
def test_bulk_toggle_enables_all_in_group(mock_set, mock_feeds):
    from dataclasses_shared import Feed
    mock_feeds.return_value = [
        Feed(id=1, name="arXiv", url="https://arxiv.org/rss", category="research",
             enabled=False, source_type="academic_journal"),
        Feed(id=2, name="Nature", url="https://nature.com/rss", category="research",
             enabled=False, source_type="academic_journal"),
        Feed(id=3, name="Latent Space", url="https://latent.space/rss", category="industry",
             enabled=False, source_type="independent_blog"),
    ]
    response = client.patch(
        "/admin/feeds/bulk-toggle",
        json={"source_type": "academic_journal", "enabled": True},
    )
    assert response.status_code == 200
    assert response.json()["updated"] == 2
    assert mock_set.call_count == 2


@patch("api.main.get_all_feeds")
@patch("api.main.set_feed_enabled")
def test_bulk_toggle_only_affects_target_group(mock_set, mock_feeds):
    from dataclasses_shared import Feed
    mock_feeds.return_value = [
        Feed(id=1, name="arXiv", url="https://arxiv.org/rss", category="research",
             enabled=True, source_type="academic_journal"),
        Feed(id=2, name="Latent Space", url="https://latent.space/rss", category="industry",
             enabled=True, source_type="independent_blog"),
    ]
    client.patch(
        "/admin/feeds/bulk-toggle",
        json={"source_type": "academic_journal", "enabled": False},
    )
    mock_set.assert_called_once_with(1, False)


@patch("api.main.get_all_feeds", return_value=[])
def test_bulk_toggle_unknown_group_returns_zero(mock_feeds):
    response = client.patch(
        "/admin/feeds/bulk-toggle",
        json={"source_type": "nonexistent_group", "enabled": True},
    )
    assert response.status_code == 200
    assert response.json()["updated"] == 0


# --- Targeted per-feed fetch tests ---

@patch("api.main.parse_feed_entries")
@patch("api.main.filter_article")
@patch("api.main.summarize_article")
@patch("api.main.save_article")
@patch("api.main.mark_feed_fetched")
@patch("api.main.get_feed_by_id")
def test_fetch_single_feed_saves_relevant_articles(
    mock_get_feed, mock_mark, mock_save, mock_summarize, mock_filter, mock_parse
):
    from dataclasses_shared import Feed, RawArticle, FilterResult, SummaryResult

    feed = Feed(id=1, name="arXiv", url="https://arxiv.org/rss",
                category="research", enabled=True)
    raw = RawArticle(title="New paper", link="https://arxiv.org/abs/1",
                     source="arXiv", topic="research", content="Abstract text.")

    mock_get_feed.return_value = feed
    mock_parse.return_value = [raw]
    mock_filter.return_value = FilterResult(is_relevant=True, reason="On topic")
    mock_summarize.return_value = SummaryResult(summary="A summary sentence.")
    mock_save.return_value = True

    response = client.post("/feeds/1/fetch")
    assert response.status_code == 200
    data = response.json()
    assert data["fetched"] == 1
    assert data["saved"] == 1
    mock_mark.assert_called_once_with(1)


@patch("api.main.parse_feed_entries")
@patch("api.main.filter_article")
@patch("api.main.get_feed_by_id")
def test_fetch_single_feed_skips_irrelevant_articles(
    mock_get_feed, mock_filter, mock_parse
):
    from dataclasses_shared import Feed, RawArticle, FilterResult

    feed = Feed(id=1, name="arXiv", url="https://arxiv.org/rss",
                category="research", enabled=True)
    raw = RawArticle(title="Off topic", link="https://arxiv.org/abs/2",
                     source="arXiv", topic="research", content="Not relevant.")

    mock_get_feed.return_value = feed
    mock_parse.return_value = [raw]
    mock_filter.return_value = FilterResult(is_relevant=False, reason="Off topic")

    response = client.post("/feeds/1/fetch")
    assert response.status_code == 200
    assert response.json()["saved"] == 0


@patch("api.main.get_feed_by_id", return_value=None)
def test_fetch_single_feed_returns_404_for_missing(mock_get):
    response = client.post("/feeds/9999/fetch")
    assert response.status_code == 404


# --- Pipeline trigger and error reset tests ---

@patch("api.main.fetch_articles")
@patch("api.main.filter_article")
@patch("api.main.summarize_article")
@patch("api.main.save_article")
def test_run_pipeline_returns_counts(mock_save, mock_summarize, mock_filter, mock_fetch):
    from dataclasses_shared import RawArticle, FilterResult, SummaryResult

    raw = RawArticle(title="Article", link="https://example.com/1",
                     source="Test", topic="industry", content="Content.")
    mock_fetch.return_value = [raw]
    mock_filter.return_value = FilterResult(is_relevant=True, reason="On topic")
    mock_summarize.return_value = SummaryResult(summary="A summary.")
    mock_save.return_value = True

    response = client.post("/admin/run-pipeline")
    assert response.status_code == 200
    data = response.json()
    assert data["saved"] == 1
    assert "skipped" in data
    assert "filtered_out" in data


@patch("api.main.fetch_articles")
@patch("api.main.filter_article")
def test_run_pipeline_counts_filtered_out(mock_filter, mock_fetch):
    from dataclasses_shared import RawArticle, FilterResult

    raw = RawArticle(title="Off topic", link="https://example.com/2",
                     source="Test", topic="industry", content="Content.")
    mock_fetch.return_value = [raw]
    mock_filter.return_value = FilterResult(is_relevant=False, reason="Off topic")

    response = client.post("/admin/run-pipeline")
    assert response.status_code == 200
    data = response.json()
    assert data["filtered_out"] == 1
    assert data["saved"] == 0


@patch("api.main.mark_feed_fetched")
@patch("api.main.get_feed_by_id")
def test_reset_feed_errors_calls_mark_fetched(mock_get_feed, mock_mark):
    mock_get_feed.return_value = make_feed(feed_id=1)
    response = client.post("/admin/feeds/1/reset-errors")
    assert response.status_code == 200
    assert response.json() == {"ok": True}
    mock_mark.assert_called_once_with(1)


@patch("api.main.get_feed_by_id", return_value=None)
def test_reset_feed_errors_returns_404_for_missing(mock_get):
    response = client.post("/admin/feeds/9999/reset-errors")
    assert response.status_code == 404
