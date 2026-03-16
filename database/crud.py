"""CRUD functions for the articles and feeds database. No AI logic here."""

from datetime import datetime, timedelta
from typing import Optional

from sqlalchemy.orm import Session

from dataclasses_shared import Article, Feed
from database.models import ArticleModel, FeedModel, SessionLocal, init_db


def _article_model_to_dataclass(row: ArticleModel) -> Article:
    """Convert an ORM row to an Article dataclass."""
    return Article(
        title=row.title,
        link=row.link,
        source=row.source,
        topic=row.topic,
        summary=row.summary,
        created_at=row.created_at,
        published_at=row.published_at,
    )


def save_article(article: Article) -> bool:
    """
    Persist an Article to the database.

    Uses `link` as the unique key. Skips the insert if the article
    already exists (no update). Returns True if inserted, False if skipped.

    Args:
        article: A fully populated Article dataclass.

    Returns:
        True if the article was newly inserted, False if it already existed.
    """
    init_db()
    db: Session = SessionLocal()
    try:
        existing = db.query(ArticleModel).filter(ArticleModel.link == article.link).first()
        if existing:
            return False
        row = ArticleModel(
            link=article.link,
            title=article.title,
            source=article.source,
            topic=article.topic,
            summary=article.summary,
            created_at=article.created_at or datetime.utcnow(),
            published_at=article.published_at,
        )
        db.add(row)
        db.commit()
        return True
    finally:
        db.close()


def get_articles(limit: int = 100) -> list[Article]:
    """
    Return the most recent articles, newest first.

    Args:
        limit: Maximum number of articles to return. Defaults to 100.

    Returns:
        List of Article dataclasses ordered by created_at descending.
    """
    init_db()
    db: Session = SessionLocal()
    try:
        rows = (
            db.query(ArticleModel)
            .order_by(ArticleModel.created_at.desc())
            .limit(limit)
            .all()
        )
        return [_article_model_to_dataclass(r) for r in rows]
    finally:
        db.close()


def get_articles_by_topic(topic: str, limit: int = 100) -> list[Article]:
    """
    Return articles filtered by topic, newest first.

    Args:
        topic: One of "research", "industry", "science".
        limit: Maximum number of articles to return. Defaults to 100.

    Returns:
        List of Article dataclasses for the given topic, ordered by
        created_at descending.
    """
    init_db()
    db: Session = SessionLocal()
    try:
        rows = (
            db.query(ArticleModel)
            .filter(ArticleModel.topic == topic)
            .order_by(ArticleModel.created_at.desc())
            .limit(limit)
            .all()
        )
        return [_article_model_to_dataclass(r) for r in rows]
    finally:
        db.close()


def _feed_model_to_dataclass(row: FeedModel) -> Feed:
    """Convert an ORM FeedModel row to a Feed dataclass."""
    return Feed(
        id=row.id,
        name=row.name,
        url=row.url,
        category=row.category,
        enabled=row.enabled,
        last_fetched=row.last_fetched,
        error_count=row.error_count,
        source_type=row.source_type or "independent_blog",
    )


def upsert_feed(
    name: str,
    url: str,
    category: str,
    enabled: bool = False,
    source_type: str = "independent_blog",
) -> Feed:
    """Insert a feed or update name/category/source_type if the URL already exists.

    Does not overwrite `enabled` or `error_count` on update.

    Args:
        name: Display name of the feed source.
        url: RSS feed URL (unique key).
        category: One of "research", "industry", "science".
        enabled: Whether this feed is active. Defaults to False.
        source_type: Display grouping for admin. Defaults to "independent_blog".

    Returns:
        The inserted or updated Feed dataclass.
    """
    init_db()
    db: Session = SessionLocal()
    try:
        existing = db.query(FeedModel).filter(FeedModel.url == url).first()
        if existing:
            existing.name = name
            existing.category = category
            existing.source_type = source_type
            db.commit()
            db.refresh(existing)
            return _feed_model_to_dataclass(existing)
        row = FeedModel(name=name, url=url, category=category, enabled=enabled, source_type=source_type)
        db.add(row)
        db.commit()
        db.refresh(row)
        return _feed_model_to_dataclass(row)
    finally:
        db.close()


def get_feed_by_id(feed_id: int) -> Feed | None:
    """Look up a single feed by primary key.

    Args:
        feed_id: Primary key of the feed to look up.

    Returns:
        Feed dataclass if found, None otherwise.
    """
    init_db()
    db: Session = SessionLocal()
    try:
        row = db.query(FeedModel).filter(FeedModel.id == feed_id).first()
        if not row:
            return None
        return _feed_model_to_dataclass(row)
    finally:
        db.close()


def get_all_feeds() -> list[Feed]:
    """Return all feeds in the registry, ordered by category then name.

    Returns:
        List of all Feed dataclasses.
    """
    init_db()
    db: Session = SessionLocal()
    try:
        rows = (
            db.query(FeedModel)
            .order_by(FeedModel.category, FeedModel.name)
            .all()
        )
        return [_feed_model_to_dataclass(r) for r in rows]
    finally:
        db.close()


def get_enabled_feeds() -> list[Feed]:
    """Return all feeds where enabled=True, ordered by category then name.

    Returns:
        List of enabled Feed dataclasses.
    """
    init_db()
    db: Session = SessionLocal()
    try:
        rows = (
            db.query(FeedModel)
            .filter(FeedModel.enabled.is_(True))
            .order_by(FeedModel.category, FeedModel.name)
            .all()
        )
        return [_feed_model_to_dataclass(r) for r in rows]
    finally:
        db.close()


def set_feed_enabled(feed_id: int, enabled: bool) -> bool:
    """Enable or disable a feed by ID.

    Args:
        feed_id: Primary key of the feed to update.
        enabled: New enabled state.

    Returns:
        True if the feed was found and updated, False if not found.
    """
    init_db()
    db: Session = SessionLocal()
    try:
        row = db.query(FeedModel).filter(FeedModel.id == feed_id).first()
        if not row:
            return False
        row.enabled = enabled
        db.commit()
        return True
    finally:
        db.close()


def mark_feed_fetched(feed_id: int) -> None:
    """Set last_fetched to now and reset error_count to 0.

    Args:
        feed_id: Primary key of the feed.
    """
    init_db()
    db: Session = SessionLocal()
    try:
        row = db.query(FeedModel).filter(FeedModel.id == feed_id).first()
        if row:
            row.last_fetched = datetime.utcnow()
            row.error_count = 0
            db.commit()
    finally:
        db.close()


def increment_feed_error(feed_id: int) -> None:
    """Increment error_count by 1 for a feed.

    Args:
        feed_id: Primary key of the feed.
    """
    init_db()
    db: Session = SessionLocal()
    try:
        row = db.query(FeedModel).filter(FeedModel.id == feed_id).first()
        if row:
            row.error_count = (row.error_count or 0) + 1
            db.commit()
    finally:
        db.close()


def delete_old_articles(days: int = 7) -> int:
    """Delete articles older than the given number of days.

    Args:
        days: Age threshold in days. Articles with created_at older than
              this are deleted. Defaults to 7.

    Returns:
        Number of articles deleted.
    """
    from sqlalchemy import case, or_

    init_db()
    db: Session = SessionLocal()
    try:
        cutoff = datetime.utcnow() - timedelta(days=days)
        # Use published_at when available, fall back to created_at
        effective_date = case(
            (ArticleModel.published_at.isnot(None), ArticleModel.published_at),
            else_=ArticleModel.created_at,
        )
        deleted = (
            db.query(ArticleModel)
            .filter(effective_date < cutoff)
            .delete(synchronize_session="fetch")
        )
        db.commit()
        return deleted
    finally:
        db.close()


def migrate_add_source_type() -> None:
    """Add source_type column to feeds table if it does not already exist.

    Safe to run multiple times — no-op if the column exists.
    Uses raw SQL because SQLAlchemy create_all does not add columns to
    existing tables.
    """
    from sqlalchemy import text

    init_db()
    db: Session = SessionLocal()
    try:
        db.execute(text("ALTER TABLE feeds ADD COLUMN source_type VARCHAR"))
        db.commit()
    except Exception:
        db.rollback()  # column already exists — safe to ignore
    finally:
        db.close()


def get_articles_by_source(source: str, limit: int = 5) -> list[Article]:
    """Return recent articles matching a source name, newest first.

    Matches on the `source` field in the articles table, which is set
    from the RSS feed's own title element during ingestion. Feed names
    in the registry should be set to match feedparser output.

    Args:
        source: Source name to filter by (case-sensitive).
        limit: Maximum number of articles to return. Defaults to 5.

    Returns:
        List of Article dataclasses ordered by created_at descending.
    """
    init_db()
    db: Session = SessionLocal()
    try:
        rows = (
            db.query(ArticleModel)
            .filter(ArticleModel.source == source)
            .order_by(ArticleModel.created_at.desc())
            .limit(limit)
            .all()
        )
        return [_article_model_to_dataclass(r) for r in rows]
    finally:
        db.close()
