"""Pipeline scheduler: fetch → filter → summarize → store.

Runs every 6 hours via APScheduler. Must work on cloud hosts (Render,
Railway, Fly.io) — no cron dependency.

Run directly:
    python scheduler/pipeline.py
"""

import logging
from datetime import datetime, timezone

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.schedulers.blocking import BlockingScheduler

from agents.filter_agent import filter_article
from agents.summarize_agent import summarize_article
from database.crud import delete_old_articles, save_article
from dataclasses_shared import Article, RawArticle
from ingestion.fetcher import fetch_articles

# Module-level scheduler instance for import by the API process.
scheduler = BackgroundScheduler()

_last_run: datetime | None = None


def get_last_run() -> datetime | None:
    """Return the most recent pipeline run time, or None if never run."""
    return _last_run


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [pipeline] %(message)s",
    datefmt="%Y-%m-%dT%H:%M:%S",
)
log = logging.getLogger(__name__)


def run_pipeline() -> dict[str, int]:
    """Execute one full pipeline run: fetch → filter → summarize → store.

    Stages:
    1. Fetch raw articles from all RSS feeds.
    2. For each article, call filter_article(). Skip if not relevant.
    3. For relevant articles, call summarize_article().
    4. Build an Article dataclass and call save_article().

    All errors at the per-article level are caught and logged so that
    one bad article does not abort the rest of the batch.

    Returns:
        A dict with counts: {"fetched": int, "relevant": int, "saved": int}
    """
    global _last_run
    _last_run = datetime.now(timezone.utc)
    log.info("Pipeline started.")
    stats = {"fetched": 0, "relevant": 0, "saved": 0}

    # Cleanup: remove articles older than 7 days
    removed = delete_old_articles(days=7)
    if removed:
        log.info(f"Cleanup: deleted {removed} articles older than 7 days.")

    # Stage 1: Fetch
    raw_articles: list[RawArticle] = fetch_articles()
    stats["fetched"] = len(raw_articles)
    log.info(f"Stage 1 complete: fetched {stats['fetched']} articles.")

    for raw in raw_articles:
        try:
            # Stage 2: Filter
            filter_result = filter_article(raw)
            if not filter_result.is_relevant:
                log.info(f"Filtered out: '{raw.title}' — {filter_result.reason}")
                continue

            stats["relevant"] += 1
            log.info(f"Relevant: '{raw.title}'")

            # Stage 3: Summarize
            summary_result = summarize_article(raw)
            if not summary_result.summary:
                log.warning(f"Empty summary for '{raw.title}' — skipping.")
                continue

            # Stage 4: Save
            article = Article(
                title=raw.title,
                link=raw.link,
                source=raw.source,
                topic=raw.topic,
                summary=summary_result.summary,
                created_at=datetime.now(timezone.utc),
                published_at=raw.published_at,
            )
            inserted = save_article(article)
            if inserted:
                stats["saved"] += 1
                log.info(f"Saved: '{raw.title}'")
            else:
                log.info(f"Duplicate skipped: '{raw.title}'")

        except Exception as e:
            log.error(f"Unexpected error processing '{raw.title}': {e}")
            continue

    log.info(
        f"Pipeline complete. "
        f"fetched={stats['fetched']} relevant={stats['relevant']} saved={stats['saved']}"
    )
    return stats


def start_scheduler() -> None:
    """Start the APScheduler blocking scheduler.

    Runs run_pipeline() at 2am, 8am, 2pm, and 8pm ET (every 6 hours anchored to 8am ET).
    Uses BlockingScheduler so the process stays alive on cloud hosts
    without requiring cron or a separate process manager.
    """
    scheduler = BlockingScheduler()
    scheduler.add_job(
        run_pipeline,
        trigger="cron",
        hour="2,8,14,20",
        minute=0,
        timezone="America/Los_Angeles",
        id="pipeline",
        name="AI News Pipeline",
    )
    log.info("Scheduler started. Pipeline will run at 2am, 8am, 2pm, 8pm ET.")
    try:
        scheduler.start()
    except (KeyboardInterrupt, SystemExit):
        log.info("Scheduler stopped.")


if __name__ == "__main__":
    start_scheduler()
