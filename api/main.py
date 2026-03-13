"""FastAPI backend for the AI News Aggregator.

Exposes read-only public endpoints and admin endpoints for feed management.
No AI logic. No pipeline triggers.
"""

from dataclasses import asdict

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Path, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from database.crud import (
    get_all_feeds,
    get_articles,
    get_articles_by_source,
    get_articles_by_topic,
    set_feed_enabled,
)

load_dotenv()

app = FastAPI(title="AI News API", version="2.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["GET", "PATCH"],
    allow_headers=["*"],
)

VALID_TOPICS = {"research", "industry", "science"}


# --- Request / Response models ---

class FeedToggleRequest(BaseModel):
    enabled: bool


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


@app.patch("/admin/feeds/{feed_id}")
def toggle_feed(
    feed_id: int = Path(..., description="Feed ID to update"),
    body: FeedToggleRequest = None,
) -> JSONResponse:
    """Enable or disable a feed.

    Args:
        feed_id: Primary key of the feed to update.
        body: JSON body with a single field: {"enabled": bool}

    Returns:
        JSON object with the updated id and enabled state.
        HTTP 404 if the feed does not exist.
    """
    if body is None:
        raise HTTPException(status_code=422, detail="Request body required.")

    found = set_feed_enabled(feed_id, body.enabled)
    if not found:
        raise HTTPException(status_code=404, detail=f"Feed {feed_id} not found.")

    return JSONResponse(content={"id": feed_id, "enabled": body.enabled})
