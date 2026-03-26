"""Tests for the FastAPI API layer."""

import os
import pytest
from datetime import datetime
from unittest.mock import patch

os.environ["DATABASE_URL"] = "sqlite:///./test_news.db"
os.environ["ADMIN_API_KEY"] = "test-key"

from fastapi.testclient import TestClient
from dataclasses_shared import Article
from api.main import app

TEST_KEY = "test-key"
client = TestClient(app, headers={"X-Admin-Key": TEST_KEY})


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


@patch("api.main.get_enabled_feeds", return_value=[])
@patch("api.main.set_feed_enabled", return_value=True)
def test_toggle_feed_enables(mock_toggle, mock_enabled):
    response = client.patch("/admin/feeds/1", json={"enabled": True})
    assert response.status_code == 200
    assert response.json() == {"id": 1, "enabled": True}
    mock_toggle.assert_called_once_with(1, True)


@patch("api.main.get_enabled_feeds", return_value=[])
@patch("api.main.set_feed_enabled", return_value=False)
def test_toggle_feed_returns_404_for_missing(mock_toggle, mock_enabled):
    response = client.patch("/admin/feeds/9999", json={"enabled": True})
    assert response.status_code == 404


def test_list_articles_invalid_topic_updated():
    response = client.get("/articles?topic=ai")
    assert response.status_code == 400
    assert "research" in response.json()["error"]


# --- Bulk toggle tests ---

@patch("api.main.get_enabled_feeds", return_value=[])
@patch("api.main.get_all_feeds")
@patch("api.main.set_feed_enabled")
def test_bulk_toggle_enables_all_in_group(mock_set, mock_feeds, mock_enabled):
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


@patch("api.main.get_enabled_feeds", return_value=[])
@patch("api.main.get_all_feeds", return_value=[])
def test_bulk_toggle_unknown_group_returns_zero(mock_feeds, mock_enabled):
    response = client.patch(
        "/admin/feeds/bulk-toggle",
        json={"source_type": "nonexistent_group", "enabled": True},
    )
    assert response.status_code == 200
    assert response.json()["updated"] == 0


# --- Targeted per-feed fetch tests (module 25: non-blocking) ---

@patch("api.main.get_feed_by_id")
def test_fetch_single_feed_returns_202(mock_get_feed):
    from dataclasses_shared import Feed

    feed = Feed(id=1, name="arXiv", url="https://arxiv.org/rss",
                category="research", enabled=True)
    mock_get_feed.return_value = feed

    response = client.post("/feeds/1/fetch")
    assert response.status_code == 202
    assert response.json() == {"status": "started"}


@patch("api.main.get_feed_by_id", return_value=None)
def test_fetch_single_feed_returns_404_for_missing(mock_get):
    response = client.post("/feeds/9999/fetch")
    assert response.status_code == 404


@patch("api.main.parse_feed_entries")
@patch("api.main.filter_article")
@patch("api.main.summarize_article")
@patch("api.main.save_article")
@patch("api.main.mark_feed_fetched")
def test_run_feed_pipeline_saves_relevant_articles(
    mock_mark, mock_save, mock_summarize, mock_filter, mock_parse
):
    from api.main import _run_feed_pipeline
    from dataclasses_shared import Feed, RawArticle, FilterResult, SummaryResult

    feed = Feed(id=1, name="arXiv", url="https://arxiv.org/rss",
                category="research", enabled=True)
    raw = RawArticle(title="New paper", link="https://arxiv.org/abs/1",
                     source="arXiv", topic="research", content="Abstract text.")

    mock_parse.return_value = [raw]
    mock_filter.return_value = FilterResult(is_relevant=True, reason="On topic")
    mock_summarize.return_value = SummaryResult(summary="A summary sentence.")
    mock_save.return_value = True

    _run_feed_pipeline(1, feed)

    mock_save.assert_called_once()
    mock_mark.assert_called_once_with(1)


@patch("api.main.parse_feed_entries")
@patch("api.main.filter_article")
@patch("api.main.summarize_article")
@patch("api.main.save_article")
@patch("api.main.mark_feed_fetched")
def test_run_feed_pipeline_skips_empty_summary(
    mock_mark, mock_save, mock_summarize, mock_filter, mock_parse
):
    from api.main import _run_feed_pipeline
    from dataclasses_shared import Feed, RawArticle, FilterResult, SummaryResult

    feed = Feed(id=1, name="TechCrunch", url="https://techcrunch.com/feed/",
                category="industry", enabled=True)
    raw = RawArticle(title="Some article", link="https://techcrunch.com/1",
                     source="TechCrunch", topic="industry", content="Short content.")

    mock_parse.return_value = [raw]
    mock_filter.return_value = FilterResult(is_relevant=True, reason="On topic")
    mock_summarize.return_value = SummaryResult(summary="")

    _run_feed_pipeline(1, feed)

    mock_save.assert_not_called()
    mock_mark.assert_called_once_with(1)


@patch("api.main.parse_feed_entries")
@patch("api.main.filter_article")
@patch("api.main.increment_feed_error")
def test_run_feed_pipeline_increments_error_on_rss_failure(
    mock_error, mock_filter, mock_parse
):
    from api.main import _run_feed_pipeline
    from dataclasses_shared import Feed

    feed = Feed(id=1, name="arXiv", url="https://arxiv.org/rss",
                category="research", enabled=True)
    mock_parse.side_effect = Exception("RSS fetch failed")

    _run_feed_pipeline(1, feed)

    mock_error.assert_called_once_with(1)
    mock_filter.assert_not_called()


# --- Scheduler status tests (module 28) ---

@patch("api.main.get_last_run", return_value=None)
@patch("api.main.scheduler")
def test_scheduler_status_returns_nulls_when_no_run(mock_scheduler, mock_last_run):
    mock_scheduler.get_job.return_value = None

    response = client.get("/scheduler/status")
    assert response.status_code == 200
    data = response.json()
    assert data["last_run"] is None
    assert data["next_run"] is None


@patch("api.main.get_last_run")
@patch("api.main.scheduler")
def test_scheduler_status_returns_times_when_available(mock_scheduler, mock_last_run):
    from datetime import datetime, timezone
    from unittest.mock import MagicMock

    last = datetime(2026, 3, 16, 9, 0, 0, tzinfo=timezone.utc)
    next_ = datetime(2026, 3, 16, 15, 0, 0, tzinfo=timezone.utc)

    mock_last_run.return_value = last
    mock_job = MagicMock()
    mock_job.next_run_time = next_
    mock_scheduler.get_job.return_value = mock_job

    response = client.get("/scheduler/status")
    assert response.status_code == 200
    data = response.json()
    assert data["last_run"] == last.isoformat()
    assert data["next_run"] == next_.isoformat()


@patch("api.main.get_last_run", return_value=None)
@patch("api.main.scheduler")
def test_scheduler_status_handles_scheduler_error_gracefully(mock_scheduler, mock_last_run):
    mock_scheduler.get_job.side_effect = Exception("Scheduler not running")

    response = client.get("/scheduler/status")
    assert response.status_code == 200
    assert response.json()["next_run"] is None


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


# --- Feed limit tests (module 33) ---

@patch("api.main.get_enabled_feeds")
def test_toggle_feed_returns_409_at_limit(mock_enabled):
    """Enabling a feed when 30 are already enabled returns HTTP 409."""
    from dataclasses_shared import Feed
    mock_enabled.return_value = [
        Feed(id=i, name=f"Feed {i}", url=f"https://feed{i}.com/rss",
             category="industry", enabled=True)
        for i in range(1, 31)
    ]
    response = client.patch("/admin/feeds/99", json={"enabled": True})
    assert response.status_code == 409


@patch("api.main.set_feed_enabled", return_value=True)
def test_toggle_feed_disable_always_allowed(mock_toggle):
    """Disabling a feed is always allowed regardless of enabled count."""
    response = client.patch("/admin/feeds/1", json={"enabled": False})
    assert response.status_code == 200


@patch("api.main.get_enabled_feeds")
@patch("api.main.get_all_feeds")
def test_bulk_toggle_returns_409_when_would_exceed_limit(mock_feeds, mock_enabled):
    """Bulk-enabling a group that would push total over 30 returns HTTP 409."""
    from dataclasses_shared import Feed
    mock_enabled.return_value = [
        Feed(id=i, name=f"Feed {i}", url=f"https://feed{i}.com/rss",
             category="industry", source_type="company_blog", enabled=True)
        for i in range(1, 30)
    ]
    mock_feeds.return_value = mock_enabled.return_value + [
        Feed(id=100 + i, name=f"Blog {i}", url=f"https://blog{i}.com/rss",
             category="industry", source_type="independent_blog", enabled=False)
        for i in range(3)
    ]
    response = client.patch(
        "/admin/feeds/bulk-toggle",
        json={"source_type": "independent_blog", "enabled": True},
    )
    assert response.status_code == 409


# --- Add feed tests (module 39) ---

@patch("api.main.upsert_feed")
def test_add_feed_creates_feed(mock_upsert):
    """POST /admin/feeds with valid body returns 201 and the created feed."""
    mock_upsert.return_value = Feed(
        id=99, name="Reuters Technology",
        url="https://www.reutersagency.com/feed/?best-topics=technology",
        category="industry", source_type="major_media", enabled=False,
    )
    response = client.post("/admin/feeds", json={
        "name": "Reuters Technology",
        "url": "https://www.reutersagency.com/feed/?best-topics=technology",
        "category": "industry",
        "source_type": "major_media",
    })
    assert response.status_code == 201
    data = response.json()
    assert data["name"] == "Reuters Technology"
    assert data["category"] == "industry"
    assert data["source_type"] == "major_media"
    assert data["enabled"] is False
    mock_upsert.assert_called_once_with(
        name="Reuters Technology",
        url="https://www.reutersagency.com/feed/?best-topics=technology",
        category="industry",
        source_type="major_media",
    )


def test_add_feed_rejects_invalid_category():
    """POST /admin/feeds with an unknown category returns 422."""
    response = client.post("/admin/feeds", json={
        "name": "Some Feed",
        "url": "https://example.com/rss",
        "category": "sports",
        "source_type": "major_media",
    })
    assert response.status_code == 422
    assert "category" in response.json()["detail"]


def test_add_feed_rejects_empty_name():
    """POST /admin/feeds with a blank name returns 422."""
    response = client.post("/admin/feeds", json={
        "name": "   ",
        "url": "https://example.com/rss",
        "category": "industry",
        "source_type": "major_media",
    })
    assert response.status_code == 422


def test_add_feed_rejects_empty_source_type():
    """POST /admin/feeds with a blank source_type returns 422."""
    response = client.post("/admin/feeds", json={
        "name": "Some Feed",
        "url": "https://example.com/rss",
        "category": "industry",
        "source_type": "",
    })
    assert response.status_code == 422


def test_add_feed_requires_admin_key():
    """POST /admin/feeds without X-Admin-Key returns 401."""
    unauthed = TestClient(app)
    response = unauthed.post("/admin/feeds", json={
        "name": "Some Feed",
        "url": "https://example.com/rss",
        "category": "industry",
        "source_type": "major_media",
    })
    assert response.status_code == 401


# --- Auth tests (module 34) ---

def test_protected_endpoint_requires_key():
    """PATCH /admin/feeds/{id} returns 401 when X-Admin-Key header is missing."""
    unauthed = TestClient(app)
    response = unauthed.patch("/admin/feeds/1", json={"enabled": True})
    assert response.status_code == 401


def test_protected_endpoint_rejects_wrong_key():
    """PATCH /admin/feeds/{id} returns 401 when X-Admin-Key is incorrect."""
    unauthed = TestClient(app, headers={"X-Admin-Key": "wrong-key"})
    response = unauthed.patch("/admin/feeds/1", json={"enabled": True})
    assert response.status_code == 401


@patch("api.main.get_all_feeds", return_value=[])
@patch("api.main.get_articles", return_value=[])
def test_public_get_endpoints_require_no_key(mock_articles, mock_feeds):
    """GET /admin/feeds and GET /articles do not require X-Admin-Key."""
    unauthed = TestClient(app)
    assert unauthed.get("/admin/feeds").status_code == 200
    assert unauthed.get("/articles").status_code == 200


def test_missing_admin_api_key_env_returns_500():
    """If ADMIN_API_KEY env var is not set, protected endpoints return 500."""
    original = os.environ.pop("ADMIN_API_KEY", None)
    try:
        unauthed = TestClient(app, headers={"X-Admin-Key": "any-key"})
        response = unauthed.patch("/admin/feeds/1", json={"enabled": True})
        assert response.status_code == 500
    finally:
        if original:
            os.environ["ADMIN_API_KEY"] = original
