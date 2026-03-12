"""RSS ingestion module. Fetches and normalizes articles from RSS feeds.

No AI logic. No database writes. Returns RawArticle objects only.
"""

import re
from datetime import datetime

import feedparser

from dataclasses_shared import RawArticle

RSS_FEEDS: dict[str, str] = {
    "ai":      "https://feeds.feedburner.com/venturebeat/SSSR",
    "tech":    "https://feeds.arstechnica.com/arstechnica/index",
    "science": "https://www.sciencedaily.com/rss/top/science.xml",
}

MAX_CONTENT_LENGTH = 1000


def _strip_html(text: str) -> str:
    """Remove HTML tags from a string.

    Args:
        text: Raw string that may contain HTML markup.

    Returns:
        Plain text with all HTML tags removed.
    """
    return re.sub(r"<[^>]+>", "", text or "").strip()


def _extract_content(entry: feedparser.FeedParserDict) -> str:
    """Extract the best available text content from a feed entry.

    Prefers `content[0].value`, falls back to `summary`, then `title`.
    Strips HTML and truncates to MAX_CONTENT_LENGTH characters.

    Args:
        entry: A single parsed feed entry from feedparser.

    Returns:
        Cleaned, truncated plain-text content string.
    """
    raw = ""
    if hasattr(entry, "content") and entry.content:
        raw = entry.content[0].get("value", "")
    elif hasattr(entry, "summary"):
        raw = entry.summary
    elif hasattr(entry, "title"):
        raw = entry.title

    cleaned = _strip_html(raw)
    return cleaned[:MAX_CONTENT_LENGTH]


def _parse_published(entry: feedparser.FeedParserDict) -> datetime:
    """Parse the published date from a feed entry.

    Falls back to the current UTC time if no date is present or parseable.

    Args:
        entry: A single parsed feed entry from feedparser.

    Returns:
        A datetime object representing when the article was published.
    """
    if hasattr(entry, "published_parsed") and entry.published_parsed:
        try:
            return datetime(*entry.published_parsed[:6])
        except (TypeError, ValueError):
            pass
    return datetime.utcnow()


def fetch_feed(topic: str, url: str) -> list[RawArticle]:
    """Fetch and normalize articles from a single RSS feed URL.

    Parses the feed, extracts entries, and converts each to a RawArticle.
    Skips entries that are missing a title or link.

    Args:
        topic: The topic label for this feed (e.g. "ai", "tech", "science").
        url: The RSS feed URL to fetch.

    Returns:
        List of RawArticle objects parsed from the feed.
    """
    feed = feedparser.parse(url)
    articles: list[RawArticle] = []

    for entry in feed.entries:
        title = _strip_html(getattr(entry, "title", "")).strip()
        link = getattr(entry, "link", "").strip()

        if not title or not link:
            continue

        source = _strip_html(getattr(feed.feed, "title", url)).strip()
        content = _extract_content(entry)

        articles.append(
            RawArticle(
                title=title,
                link=link,
                source=source,
                topic=topic,
                content=content,
            )
        )

    return articles


def fetch_articles() -> list[RawArticle]:
    """Fetch articles from all configured RSS feeds.

    Iterates over RSS_FEEDS, calls fetch_feed() for each, and aggregates
    the results. Feed-level errors are caught and logged so one broken
    feed does not abort the others.

    Returns:
        Combined list of RawArticle objects from all feeds.
    """
    all_articles: list[RawArticle] = []

    for topic, url in RSS_FEEDS.items():
        try:
            articles = fetch_feed(topic, url)
            print(f"[ingestion] {topic}: fetched {len(articles)} articles from {url}")
            all_articles.extend(articles)
        except Exception as e:
            print(f"[ingestion] ERROR fetching {topic} ({url}): {e}")

    return all_articles
