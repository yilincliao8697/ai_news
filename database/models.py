"""SQLAlchemy ORM models for the Article and Feed tables."""

from datetime import datetime

from sqlalchemy import Boolean, Column, DateTime, Integer, String, create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker

import os
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./news.db")

engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


class Base(DeclarativeBase):
    pass


class ArticleModel(Base):
    """ORM model representing a processed, stored article."""

    __tablename__ = "articles"

    link = Column(String, primary_key=True, index=True)   # unique key
    title = Column(String, nullable=False)
    source = Column(String, nullable=False)
    topic = Column(String, nullable=False, index=True)
    summary = Column(String, nullable=False)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)


class FeedModel(Base):
    """ORM model representing an RSS feed in the feed registry."""

    __tablename__ = "feeds"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String, nullable=False)
    url = Column(String, unique=True, nullable=False, index=True)
    category = Column(String, nullable=False, index=True)
    enabled = Column(Boolean, default=False, nullable=False)
    last_fetched = Column(DateTime, nullable=True)
    error_count = Column(Integer, default=0, nullable=False)


def init_db() -> None:
    """Create all tables if they don't already exist."""
    Base.metadata.create_all(bind=engine)
