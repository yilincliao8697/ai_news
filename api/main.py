"""FastAPI backend for the AI News Aggregator.

Exposes public endpoints, feed management endpoints, and admin endpoints.
Pipeline can be triggered via API for manual runs and targeted per-feed fetches.
"""

import os
from contextlib import asynccontextmanager
from dataclasses import asdict
from datetime import datetime, timezone

from dotenv import load_dotenv
from fastapi import BackgroundTasks, Depends, FastAPI, Header, HTTPException, Path, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from agents.filter_agent import filter_article
from agents.summarize_agent import summarize_article
from dataclasses_shared import Article
from database.crud import (
    deactivate_subscriber,
    get_all_feeds,
    get_articles,
    get_articles_by_source,
    get_articles_by_topic,
    get_enabled_feeds,
    get_feed_by_id,
    increment_feed_error,
    mark_feed_fetched,
    save_article,
    set_feed_enabled,
    upsert_feed,
    upsert_subscriber,
)
from ingestion.fetcher import fetch_articles, parse_feed_entries
from scheduler.newsletter import send_newsletter
from scheduler.pipeline import get_last_run, run_pipeline, scheduler

load_dotenv()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Start the background scheduler on API startup and shut it down on exit."""
    scheduler.add_job(
        run_pipeline,
        trigger="cron",
        hour="2,8,14,20",
        minute=0,
        timezone="America/New_York",
        id="pipeline",
        name="AI News Pipeline",
    )
    scheduler.add_job(
        lambda: send_newsletter("daily"),
        "cron",
        hour=8,
        minute=0,
        id="newsletter_daily",
        name="Daily Newsletter",
    )
    scheduler.add_job(
        lambda: send_newsletter("weekly"),
        "cron",
        day_of_week="mon",
        hour=8,
        minute=0,
        id="newsletter_weekly",
        name="Weekly Newsletter",
    )
    scheduler.start()
    yield
    scheduler.shutdown(wait=False)


app = FastAPI(title="AI News API", version="5.0.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["GET", "PATCH", "POST"],
    allow_headers=["*"],
)

VALID_TOPICS = {"research", "industry", "science"}
MAX_ENABLED_FEEDS = 30


def require_admin_key(x_admin_key: str = Header(default="")) -> None:
    """FastAPI dependency: validate the X-Admin-Key header.

    Raises:
        HTTPException 500: if ADMIN_API_KEY env var is not configured.
        HTTPException 401: if the provided key does not match.
    """
    key = os.getenv("ADMIN_API_KEY", "")
    if not key:
        raise HTTPException(status_code=500, detail="Server misconfiguration: ADMIN_API_KEY not set")
    if x_admin_key != key:
        raise HTTPException(status_code=401, detail="Unauthorized")


# --- Request / Response models ---

class FeedToggleRequest(BaseModel):
    enabled: bool


class BulkTogglePayload(BaseModel):
    source_type: str
    enabled: bool


class AddFeedRequest(BaseModel):
    name: str
    url: str
    category: str
    source_type: str


class SubscribeRequest(BaseModel):
    email: str
    frequency: str   # "daily" or "weekly"


class UnsubscribeRequest(BaseModel):
    email: str


# --- Public endpoints ---

@app.get("/health")
def health_check() -> dict[str, str]:
    """Liveness check endpoint.

    Returns:
        JSON object: {"status": "ok"}
    """
    return {"status": "ok"}


@app.get("/articles")
def list_articles(
    topic: str | None = Query(default=None, description="Filter by topic: research, industry, science"),
    limit: int = Query(default=100, ge=1, le=500, description="Max articles to return"),
) -> JSONResponse:
    """Return a list of stored articles, optionally filtered by topic.

    Args:
        topic: Optional topic filter. Must be one of: research, industry, science.
        limit: Maximum number of articles to return (1-500). Defaults to 100.

    Returns:
        JSON array of article objects. HTTP 400 for invalid topic.
    """
    if topic is not None and topic not in VALID_TOPICS:
        return JSONResponse(
            status_code=400,
            content={"error": f"Invalid topic '{topic}'. Must be one of: {sorted(VALID_TOPICS)}"},
        )

    articles = get_articles_by_topic(topic=topic, limit=limit) if topic else get_articles(limit=limit)

    payload = []
    for article in articles:
        d = asdict(article)
        d["created_at"] = article.created_at.isoformat() + "Z"
        d["published_at"] = article.published_at.isoformat() + "Z" if article.published_at else None
        payload.append(d)

    return JSONResponse(content=payload)


# --- Newsletter endpoints ---

VALID_FREQUENCIES = {"daily", "weekly"}


@app.post("/newsletter/subscribe")
def newsletter_subscribe(request: SubscribeRequest) -> JSONResponse:
    """Subscribe an email address to the newsletter.

    Creates a new subscriber or re-activates an existing one and updates
    their frequency preference.

    Args:
        request: JSON body with email and frequency ("daily" or "weekly").

    Returns:
        JSON {"status": "subscribed", "email": ..., "frequency": ...}.
        HTTP 422 if email or frequency is invalid.
    """
    if not request.email or "@" not in request.email:
        raise HTTPException(status_code=422, detail="Invalid email address.")
    if request.frequency not in VALID_FREQUENCIES:
        raise HTTPException(
            status_code=422,
            detail=f"frequency must be one of: {sorted(VALID_FREQUENCIES)}",
        )
    upsert_subscriber(request.email.strip().lower(), request.frequency)
    return JSONResponse(content={
        "status": "subscribed",
        "email": request.email.strip().lower(),
        "frequency": request.frequency,
    })


@app.post("/newsletter/unsubscribe")
def newsletter_unsubscribe(request: UnsubscribeRequest) -> JSONResponse:
    """Unsubscribe an email address from the newsletter.

    Idempotent — returns 200 even if the email was not found.

    Args:
        request: JSON body with the email address to unsubscribe.

    Returns:
        JSON {"status": "unsubscribed", "email": ...}.
    """
    deactivate_subscriber(request.email.strip().lower())
    return JSONResponse(content={
        "status": "unsubscribed",
        "email": request.email.strip().lower(),
    })


# --- Feed endpoints ---

def _run_feed_pipeline(feed_id: int, feed) -> None:
    """Background task: fetch, filter, summarize, and store articles for one feed.

    Args:
        feed_id: Primary key of the feed being processed.
        feed: Feed dataclass instance.
    """
    try:
        raw_articles = parse_feed_entries(feed)
    except Exception:
        increment_feed_error(feed_id)
        return

    for raw in raw_articles:
        try:
            filter_result = filter_article(raw)
            if not filter_result.is_relevant:
                continue
            summary_result = summarize_article(raw)
            if not summary_result.summary:
                continue
            article = Article(
                title=raw.title,
                link=raw.link,
                source=raw.source,
                topic=raw.topic,
                summary=summary_result.summary,
                created_at=datetime.now(timezone.utc),
                published_at=raw.published_at,
            )
            save_article(article)
        except Exception:
            continue

    mark_feed_fetched(feed_id)


@app.post("/feeds/{feed_id}/fetch", status_code=202)
def fetch_single_feed(
    feed_id: int = Path(..., description="Feed ID to fetch"),
    background_tasks: BackgroundTasks = None,
    _: None = Depends(require_admin_key),
) -> JSONResponse:
    """Queue a background pipeline run for a single feed. Returns immediately.

    Validates the feed exists, then queues fetch → filter → summarize → store
    as a background task. Does not block on AI calls.

    Args:
        feed_id: Primary key of the feed to fetch.
        background_tasks: FastAPI background task runner (injected).

    Returns:
        JSON {"status": "started"} with HTTP 202. HTTP 404 if feed not found.
    """
    feed = get_feed_by_id(feed_id)
    if not feed:
        raise HTTPException(status_code=404, detail=f"Feed {feed_id} not found.")

    background_tasks.add_task(_run_feed_pipeline, feed_id, feed)
    return JSONResponse(status_code=202, content={"status": "started"})


# --- Admin endpoints ---

@app.get("/admin/feeds")
def list_feeds() -> JSONResponse:
    """Return all feeds in the registry with recent article previews.

    Each feed entry includes the 5 most recent article titles and links
    from that source, for use in the admin dashboard.

    Returns:
        JSON array of feed objects with a nested `recent_articles` list.
    """
    feeds = get_all_feeds()
    payload = []

    for feed in feeds:
        recent = get_articles_by_source(feed.name, limit=5)
        feed_dict = {
            "id": feed.id,
            "name": feed.name,
            "url": feed.url,
            "category": feed.category,
            "source_type": feed.source_type,
            "enabled": feed.enabled,
            "last_fetched": feed.last_fetched.isoformat() if feed.last_fetched else None,
            "error_count": feed.error_count,
            "recent_articles": [
                {
                    "title": a.title,
                    "link": a.link,
                    "created_at": a.created_at.isoformat(),
                }
                for a in recent
            ],
        }
        payload.append(feed_dict)

    return JSONResponse(content=payload)


@app.post("/admin/feeds", status_code=201)
def add_feed(request: AddFeedRequest, _: None = Depends(require_admin_key)) -> JSONResponse:
    """Add a new feed to the registry, or update an existing one by URL.

    Creates the feed with enabled=False. If a feed with the same URL already
    exists, upsert_feed() updates its name, category, and source_type.

    Args:
        request: JSON body with name, url, category, and source_type.

    Returns:
        JSON object of the created/updated feed. HTTP 422 if category is invalid.
    """
    VALID_CATEGORIES = {"research", "industry", "science"}
    if request.category not in VALID_CATEGORIES:
        raise HTTPException(
            status_code=422,
            detail=f"category must be one of {sorted(VALID_CATEGORIES)}",
        )
    if not request.name.strip() or not request.url.strip() or not request.source_type.strip():
        raise HTTPException(status_code=422, detail="name, url, and source_type must not be empty.")

    feed = upsert_feed(
        name=request.name.strip(),
        url=request.url.strip(),
        category=request.category,
        source_type=request.source_type.strip(),
    )
    return JSONResponse(
        status_code=201,
        content={
            "id": feed.id,
            "name": feed.name,
            "url": feed.url,
            "category": feed.category,
            "source_type": feed.source_type,
            "enabled": feed.enabled,
            "last_fetched": feed.last_fetched.isoformat() if feed.last_fetched else None,
            "error_count": feed.error_count,
        },
    )


@app.patch("/admin/feeds/bulk-toggle")
def bulk_toggle_feeds(payload: BulkTogglePayload, _: None = Depends(require_admin_key)) -> JSONResponse:
    """Enable or disable all feeds in a given source_type group.

    Enforces MAX_ENABLED_FEEDS cap when enabling.

    Args:
        payload: JSON body with source_type (str) and enabled (bool).

    Returns:
        JSON object with count of feeds updated.
        HTTP 409 if enabling would exceed MAX_ENABLED_FEEDS.
    """
    feeds = get_all_feeds()
    matching = [f for f in feeds if f.source_type == payload.source_type]

    if payload.enabled:
        current_count = len(get_enabled_feeds())
        newly_enabled = sum(1 for f in matching if not f.enabled)
        remaining = MAX_ENABLED_FEEDS - current_count
        if newly_enabled > remaining:
            raise HTTPException(
                status_code=409,
                detail=f"Feed limit reached. Only {remaining} slot(s) remaining.",
            )

    for feed in matching:
        set_feed_enabled(feed.id, payload.enabled)
    return JSONResponse(content={"updated": len(matching)})


@app.patch("/admin/feeds/{feed_id}")
def toggle_feed(
    feed_id: int = Path(..., description="Feed ID to update"),
    body: FeedToggleRequest = None,
    _: None = Depends(require_admin_key),
) -> JSONResponse:
    """Enable or disable a feed, enforcing the MAX_ENABLED_FEEDS cap.

    Args:
        feed_id: Primary key of the feed to update.
        body: JSON body with a single field: {"enabled": bool}

    Returns:
        JSON object with the updated id and enabled state.
        HTTP 404 if the feed does not exist.
        HTTP 409 if enabling would exceed MAX_ENABLED_FEEDS.
    """
    if body is None:
        raise HTTPException(status_code=422, detail="Request body required.")

    if body.enabled:
        current_count = len(get_enabled_feeds())
        if current_count >= MAX_ENABLED_FEEDS:
            raise HTTPException(
                status_code=409,
                detail="Feed limit reached. Disable a feed before enabling another.",
            )

    found = set_feed_enabled(feed_id, body.enabled)
    if not found:
        raise HTTPException(status_code=404, detail=f"Feed {feed_id} not found.")

    return JSONResponse(content={"id": feed_id, "enabled": body.enabled})


@app.post("/admin/feeds/{feed_id}/reset-errors")
def reset_feed_errors(
    feed_id: int = Path(..., description="Feed ID to reset"),
    _: None = Depends(require_admin_key),
) -> JSONResponse:
    """Reset error_count to 0 for a feed by calling mark_feed_fetched.

    Args:
        feed_id: Primary key of the feed to reset.

    Returns:
        JSON object {"ok": True}. HTTP 404 if the feed does not exist.
    """
    feed = get_feed_by_id(feed_id)
    if not feed:
        raise HTTPException(status_code=404, detail=f"Feed {feed_id} not found.")
    mark_feed_fetched(feed_id)
    return JSONResponse(content={"ok": True})


@app.get("/scheduler/status")
def scheduler_status() -> JSONResponse:
    """Return the scheduler's last run time and next scheduled run time.

    Returns:
        JSON object with last_run and next_run as ISO strings (or null).
    """
    last_run = get_last_run()
    next_run = None
    try:
        job = scheduler.get_job("pipeline")
        if job and job.next_run_time:
            next_run = job.next_run_time.isoformat()
    except Exception:
        pass

    return JSONResponse(content={
        "last_run": last_run.isoformat() if last_run else None,
        "next_run": next_run,
    })


@app.post("/admin/send-newsletter")
def trigger_newsletter(
    frequency: str = Query(default="daily", description="daily or weekly"),
    _: None = Depends(require_admin_key),
) -> JSONResponse:
    """Manually trigger the newsletter for a given frequency. Blocking."""
    if frequency not in VALID_FREQUENCIES:
        raise HTTPException(status_code=422, detail=f"frequency must be one of: {sorted(VALID_FREQUENCIES)}")
    result = send_newsletter(frequency)
    return JSONResponse(content=result)


@app.post("/admin/run-pipeline")
def trigger_pipeline(_: None = Depends(require_admin_key)) -> JSONResponse:
    """Manually trigger the full ingestion pipeline. Blocking — returns when complete.

    Runs: fetch → filter → summarize → store across all enabled feeds.

    Returns:
        JSON object with saved, skipped, and filtered_out counts.
    """
    saved = 0
    skipped = 0
    filtered_out = 0

    raw_articles = fetch_articles()
    for raw in raw_articles:
        try:
            filter_result = filter_article(raw)
            if not filter_result.is_relevant:
                filtered_out += 1
                continue
            summary_result = summarize_article(raw)
            article = Article(
                title=raw.title,
                link=raw.link,
                source=raw.source,
                topic=raw.topic,
                summary=summary_result.summary,
                created_at=datetime.now(timezone.utc),
                published_at=raw.published_at,
            )
            if save_article(article):
                saved += 1
            else:
                skipped += 1
        except Exception:
            continue

    return JSONResponse(content={"saved": saved, "skipped": skipped, "filtered_out": filtered_out})
