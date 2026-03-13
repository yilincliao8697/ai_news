"""RSS ingestion module. Fetches and normalizes articles from enabled feeds.

Reads enabled feeds from the database at runtime. No AI logic. No DB writes.
Returns RawArticle objects only.
"""

import re
from datetime import datetime

import feedparser
from dotenv import load_dotenv

from dataclasses_shared import RawArticle

load_dotenv()

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

    Prefers content[0].value, falls back to summary, then title.
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

    Falls back to current UTC time if no date is present or parseable.

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


def fetch_feed(category: str, url: str) -> list[RawArticle]:
    """Fetch and normalize articles from a single RSS feed URL.

    Parses the feed, extracts entries, and converts each to a RawArticle.
    Skips entries missing a title or link.

    Args:
        category: Topic category for this feed ("research", "industry", "science").
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
                topic=category,
                content=content,
            )
        )

    return articles


def fetch_articles() -> list[RawArticle]:
    """Fetch articles from all enabled feeds in the database.

    Calls get_enabled_feeds() to retrieve the current feed list at runtime.
    Calls mark_feed_fetched() on success and increment_feed_error() on failure
    for each feed, so health stats stay current.

    Returns:
        Combined list of RawArticle objects from all enabled feeds.
    """
    from database.crud import get_enabled_feeds, increment_feed_error, mark_feed_fetched

    enabled_feeds = get_enabled_feeds()
    all_articles: list[RawArticle] = []

    for feed in enabled_feeds:
        try:
            articles = fetch_feed(feed.category, feed.url)
            mark_feed_fetched(feed.id)
            print(f"[ingestion] {feed.name}: fetched {len(articles)} articles")
            all_articles.extend(articles)
        except Exception as e:
            increment_feed_error(feed.id)
            print(f"[ingestion] ERROR fetching {feed.name} ({feed.url}): {e}")

    return all_articles
