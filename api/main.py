"""FastAPI backend for the AI News Aggregator.

Exposes read-only endpoints. No AI logic. No DB writes.
"""

import os
from dataclasses import asdict

from dotenv import load_dotenv
from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from database.crud import get_articles, get_articles_by_topic

load_dotenv()

app = FastAPI(title="AI News API", version="1.0.0")

# Allow the Next.js frontend (localhost:3000 in dev, Vercel in prod) to call this API.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],   # tighten to specific origins in production
    allow_methods=["GET"],
    allow_headers=["*"],
)

VALID_TOPICS = {"ai", "tech", "science"}


@app.get("/health")
def health_check() -> dict[str, str]:
    """Liveness check endpoint.

    Returns:
        JSON object: {"status": "ok"}
    """
    return {"status": "ok"}


@app.get("/articles")
def list_articles(
    topic: str | None = Query(default=None, description="Filter by topic: ai, tech, science"),
    limit: int = Query(default=100, ge=1, le=500, description="Max articles to return"),
) -> JSONResponse:
    """Return a list of stored articles, optionally filtered by topic.

    Args:
        topic: Optional topic filter. Must be one of: "ai", "tech", "science".
               If omitted, all articles are returned.
        limit: Maximum number of articles to return (1–500). Defaults to 100.

    Returns:
        JSON array of article objects matching the Article schema.
        Returns HTTP 400 if an invalid topic is supplied.
    """
    if topic is not None and topic not in VALID_TOPICS:
        return JSONResponse(
            status_code=400,
            content={"error": f"Invalid topic '{topic}'. Must be one of: {sorted(VALID_TOPICS)}"},
        )

    if topic:
        articles = get_articles_by_topic(topic=topic, limit=limit)
    else:
        articles = get_articles(limit=limit)

    payload = []
    for article in articles:
        d = asdict(article)
        # Serialize datetime to ISO 8601 string for JSON compatibility
        d["created_at"] = article.created_at.isoformat()
        payload.append(d)

    return JSONResponse(content=payload)
