from dataclasses import dataclass
from datetime import datetime


@dataclass
class Article:
    """Fully processed article stored in the database."""
    title: str
    link: str           # unique key — used for deduplication
    source: str         # e.g. "TechCrunch"
    topic: str          # one of: "research", "industry", "science"
    summary: str        # 2–4 sentence AI-generated summary
    created_at: datetime


@dataclass
class RawArticle:
    """Unprocessed article from an RSS feed, passed to agents."""
    title: str
    link: str
    source: str
    topic: str          # one of: "research", "industry", "science"
    content: str        # raw text for agents to process


@dataclass
class FilterResult:
    """Output of the filter agent."""
    is_relevant: bool
    reason: str         # one sentence explanation


@dataclass
class SummaryResult:
    """Output of the summarize agent."""
    summary: str        # 2–4 sentences


@dataclass
class Feed:
    """An RSS feed entry in the feed registry."""
    id: int
    name: str
    url: str            # unique key
    category: str       # one of: "research", "industry", "science"
    enabled: bool
    last_fetched: datetime | None = None
    error_count: int = 0
