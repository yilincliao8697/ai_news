"""One-time script to seed major media RSS feeds into the feeds table.

Safe to re-run — uses upsert_feed() which is idempotent on URL.
All feeds are seeded with enabled=False; enable via the admin UI.

Run with:
    python scripts/import_major_media.py
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from dotenv import load_dotenv

load_dotenv()

from database.crud import upsert_feed

MAJOR_MEDIA_FEEDS = [
    ("The New York Times", "https://rss.nytimes.com/services/xml/rss/nyt/HomePage.xml"),
    ("CNN", "http://rss.cnn.com/rss/edition.rss"),
    ("Fox News", "http://feeds.foxnews.com/foxnews/latest"),
    ("NPR", "https://feeds.npr.org/1001/rss.xml"),
    ("The Washington Post", "https://feeds.washingtonpost.com/rss/world"),
    ("BBC News", "http://feeds.bbci.co.uk/news/rss.xml"),
    ("Reuters Technology", "https://www.reutersagency.com/feed/?best-topics=technology"),
    ("The Guardian", "https://www.theguardian.com/world/rss"),
    ("Financial Times", "https://www.ft.com/rss/home"),
    ("Al Jazeera", "https://www.aljazeera.com/xml/rss/all.xml"),
    ("CNBC", "https://www.cnbc.com/id/100003114/device/rss/rss.html"),
]


def main() -> None:
    """Upsert all major media feeds into the database as disabled."""
    for name, url in MAJOR_MEDIA_FEEDS:
        upsert_feed(name=name, url=url, category="industry", source_type="major_media")
        print(f"[import] upserted: {name}")
    print(f"[import] done — {len(MAJOR_MEDIA_FEEDS)} feeds seeded.")


if __name__ == "__main__":
    main()
