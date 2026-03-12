"""CRUD functions for the articles database. No AI logic here."""

from datetime import datetime
from typing import Optional

from sqlalchemy.orm import Session

from dataclasses_shared import Article
from database.models import ArticleModel, SessionLocal, init_db


def _article_model_to_dataclass(row: ArticleModel) -> Article:
    """Convert an ORM row to an Article dataclass."""
    return Article(
        title=row.title,
        link=row.link,
        source=row.source,
        topic=row.topic,
        summary=row.summary,
        created_at=row.created_at,
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
        topic: One of "ai", "tech", "science".
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
