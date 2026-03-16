"""Diagnostic script: find articles whose source doesn't match any feed name.

These articles will never be hidden when their feed is disabled because the
left join in get_articles() can't match them to a feed row.

Run with:
    python scripts/check_source_mismatches.py
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from dotenv import load_dotenv
load_dotenv()

from database.models import init_db, SessionLocal, ArticleModel, FeedModel
from sqlalchemy import func

init_db()
db = SessionLocal()

try:
    # Get all distinct source names from articles
    article_sources = {
        row[0] for row in db.query(ArticleModel.source).distinct().all()
    }

    # Get all feed names
    feed_names = {
        row[0] for row in db.query(FeedModel.name).all()
    }

    mismatches = article_sources - feed_names

    if not mismatches:
        print("No mismatches found — all article sources match a feed name.")
    else:
        print(f"Found {len(mismatches)} source(s) with no matching feed name:\n")
        for source in sorted(mismatches):
            count = db.query(func.count(ArticleModel.link)).filter(
                ArticleModel.source == source
            ).scalar()
            print(f"  '{source}'  ({count} articles)")

        print("\nThese articles will always show in the digest regardless of feed enabled status.")
        print("Fix: update the feed 'name' in the DB to match the source string above.")
finally:
    db.close()
