"""One-time script to seed the feeds table from the allainews_sources README.

Fetches the raw README from GitHub, parses the AI/ML news section,
classifies each feed as research or industry, inserts all feeds as
disabled, then enables a curated starter set.

Run with:
    python scripts/import_feeds.py

Safe to run multiple times — upsert_feed() is idempotent.
"""

import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import httpx
from dotenv import load_dotenv

load_dotenv()

from database.crud import get_all_feeds, migrate_add_source_type, set_feed_enabled, upsert_feed

README_URL = (
    "https://raw.githubusercontent.com/foorilla/allainews_sources/main/README.md"
)

# Feeds to enable by default. Matched against the feed URL as a substring.
# Add or remove entries to adjust the starter set.
STARTER_SET_URL_SUBSTRINGS = [
    "arxiv.org",
    "latent.space",
    "anthropic.com",
    "openai.com",
    "deepmind.com",
    "research.google",
    "ai.meta.com",
    "microsoft.com/research",
    "huggingface.co",
    "theverge.com",
    "wired.com",
    "techcrunch.com",
    "arstechnica.com",
    "thedecoder.de",
    "venturebeat.com",
    "technologyreview.com",
    "scientificamerican.com",
    "nature.com",
    "ieee.org",
    "acm.org",
    "mit.edu",
    "stanford.edu",
    "berkeley.edu",
    "kdnuggets.com",
    "towardsdatascience.com",
]

# URL or name substrings that indicate a research-category source.
RESEARCH_SIGNALS = [
    "arxiv.org",
    "ieee.org",
    "acm.org",
    "nature.com",
    "science.org",
    "mit.edu",
    "stanford.edu",
    "berkeley.edu",
    "oxford.ac.uk",
    "cambridge.ac.uk",
    ".edu",
    "research.google",
    "deepmind.com",
    "anthropic.com",
    "ai.meta.com",
    "openai.com/research",
    "microsoft.com/research",
    "proceedings.",
    "journal",
    "lab.",
    "labs.",
]


def classify_source_type(name: str, url: str) -> str:
    """Classify a feed's source_type from its name and URL.

    Args:
        name: Feed display name.
        url: Feed RSS URL.

    Returns:
        One of the valid source_type values.
    """
    name_lower = name.lower()
    url_lower = url.lower()

    academic_journals = ["arxiv", "ieee", "nature", "science", "acm", "springer"]
    academic_institutions = [
        "mit", "stanford", "carnegie", "oxford", "cambridge",
        "berkeley", "cmu", "harvard", "university", "institute",
    ]
    company_research = [
        "anthropic", "deepmind", "openai", "google research", "google ai",
        "meta ai", "microsoft research", "apple ml",
    ]
    company_blogs = [
        "aws", "nvidia", "hugging face", "huggingface", "cohere",
        "mistral", "stability", "inflection",
    ]
    science_media = ["nasa", "quanta", "science daily", "sciencedaily", "nih"]

    for keyword in academic_journals:
        if keyword in name_lower or keyword in url_lower:
            return "academic_journal"
    for keyword in academic_institutions:
        if keyword in name_lower or keyword in url_lower:
            return "academic_institution"
    for keyword in company_research:
        if keyword in name_lower:
            return "company_research"
    for keyword in company_blogs:
        if keyword in name_lower:
            return "company_blog"
    for keyword in science_media:
        if keyword in name_lower or keyword in url_lower:
            return "science_media"
    return "independent_blog"


def classify(name: str, url: str) -> str:
    """Classify a feed as research or industry based on URL and name heuristics.

    Args:
        name: Display name of the feed.
        url: RSS feed URL.

    Returns:
        "research" if the source matches research signals, otherwise "industry".
    """
    combined = (name + " " + url).lower()
    for signal in RESEARCH_SIGNALS:
        if signal in combined:
            return "research"
    return "industry"


def parse_news_feeds(readme: str) -> list[tuple[str, str]]:
    """Extract (name, rss_url) pairs from the AI/ML Big Data News section.

    Parses lines matching the actual README format:
        - [Source Name](website) - Description (RSS feed: rss_url)

    Only parses entries between the News section header and the next
    top-level section (Podcasts, Videos, or Jobs).

    Args:
        readme: Full raw README markdown content.

    Returns:
        List of (name, rss_url) tuples.
    """
    news_section_match = re.search(
        r"##\s*AI, ML, Big Data News\n(.*?)(?=\n##\s*AI, ML, Big Data)",
        readme,
        re.DOTALL,
    )
    if not news_section_match:
        print("[importer] WARNING: Could not find News section — parsing full README.")
        section = readme
    else:
        section = news_section_match.group(1)

    # Match: - [Name](site) - Description (RSS feed: url)
    pattern = re.compile(
        r"^-\s+\[([^\]]+)\]\([^)]+\).*?\(RSS feed:\s*(https?://[^)]+)\)",
        re.MULTILINE,
    )

    results = []
    for match in pattern.finditer(section):
        name = match.group(1).strip()
        url = match.group(2).strip()
        results.append((name, url))

    return results


def should_enable(url: str) -> bool:
    """Return True if the feed URL matches a starter set substring.

    Args:
        url: RSS feed URL.

    Returns:
        True if the feed should be pre-enabled.
    """
    url_lower = url.lower()
    return any(s in url_lower for s in STARTER_SET_URL_SUBSTRINGS)


def main() -> None:
    """Fetch, parse, classify, and seed all feeds into the database."""
    migrate_add_source_type()

    print(f"[importer] Fetching README from {README_URL}")
    try:
        response = httpx.get(README_URL, timeout=30, follow_redirects=True)
        response.raise_for_status()
    except Exception as e:
        print(f"[importer] ERROR: Failed to fetch README: {e}")
        sys.exit(1)

    readme = response.text
    feeds = parse_news_feeds(readme)
    print(f"[importer] Parsed {len(feeds)} news feeds.")

    inserted = 0
    enabled_count = 0

    for name, url in feeds:
        category = classify(name, url)
        source_type = classify_source_type(name, url)
        feed = upsert_feed(name=name, url=url, category=category, enabled=False, source_type=source_type)
        inserted += 1

        if should_enable(url):
            set_feed_enabled(feed.id, True)
            enabled_count += 1

    all_feeds = get_all_feeds()
    print(
        f"[importer] Done. "
        f"total={len(all_feeds)} inserted/updated={inserted} pre-enabled={enabled_count}"
    )


if __name__ == "__main__":
    main()
