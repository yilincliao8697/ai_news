"""Newsletter scheduler: fetch subscribers and send a stats digest via Resend."""

import logging
import os
from datetime import datetime, timedelta, timezone

import resend

from database.crud import get_active_subscribers, get_articles

logger = logging.getLogger(__name__)


def _build_stats_email(articles: list, frequency: str) -> tuple[str, str]:
    """Build a plain stats email — no AI generation, no token cost.

    Returns:
        Tuple of (subject, html_body).
    """
    period = "today" if frequency == "daily" else "this week"
    count = len(articles)

    sources: dict[str, int] = {}
    for a in articles:
        sources[a.source] = sources.get(a.source, 0) + 1
    top_sources = sorted(sources.items(), key=lambda x: x[1], reverse=True)[:5]

    source_rows = "".join(
        f"<li>{source} — {n} article{'s' if n != 1 else ''}</li>"
        for source, n in top_sources
    )

    subject = f"AI News Pulse — {count} new article{'s' if count != 1 else ''} {period}"
    html_body = f"""
<p>Here's your AI news update for {period}.</p>
<p><strong>{count} new article{'s' if count != 1 else ''}</strong> were added {period}.</p>
{'<p><strong>Top sources:</strong></p><ul>' + source_rows + '</ul>' if top_sources else ''}
<p>Open the <a href="https://ainews.yilincatherineliao.com">AI News digest</a> or the app for full coverage.</p>
"""
    return subject, html_body


def send_newsletter(frequency: str) -> dict[str, int]:
    """Send a stats digest to all active subscribers of the given frequency.

    No AI generation — counts articles and lists top sources only.

    Args:
        frequency: "daily" or "weekly".

    Returns:
        Dict with "sent" and "failed" counts.
    """
    resend.api_key = os.getenv("RESEND_API_KEY")
    from_email = os.getenv("NEWSLETTER_FROM_EMAIL", "onboarding@resend.dev")

    subscribers = get_active_subscribers(frequency)
    if not subscribers:
        logger.info(f"newsletter:no-subscribers frequency={frequency}")
        return {"sent": 0, "failed": 0}

    limit = 200 if frequency == "daily" else 500
    articles = get_articles(limit=limit)
    if not articles:
        logger.info("newsletter:no-articles")
        return {"sent": 0, "failed": 0}

    subject, html_body = _build_stats_email(articles, frequency)

    sent = 0
    failed = 0
    for subscriber in subscribers:
        try:
            resend.Emails.send({
                "from": from_email,
                "to": [subscriber.email],
                "subject": subject,
                "html": html_body,
            })
            sent += 1
            logger.info(f"newsletter:sent to={subscriber.email}")
        except Exception as e:
            failed += 1
            logger.warning(f"newsletter:failed to={subscriber.email} error={e}")

    logger.info(f"newsletter:done frequency={frequency} sent={sent} failed={failed}")
    return {"sent": sent, "failed": failed}
