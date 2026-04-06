"""Newsletter generation agent. Stateless — no DB access, no side effects.

NOTE: Not currently in use. The newsletter scheduler (scheduler/newsletter.py)
sends a plain stats digest instead to avoid Claude API token costs during testing.
This agent is kept for future use when AI-generated summaries are needed.
"""

import os

import anthropic

from dataclasses_shared import Article

client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))
MODEL = "claude-3-haiku-20240307"
MAX_ARTICLES = 8
MAX_SUMMARY_CHARS = 300


def generate_newsletter(articles: list[Article], frequency: str) -> str:
    """Generate HTML newsletter content from a list of articles.

    Args:
        articles: List of Article dataclasses to summarize.
        frequency: "daily" or "weekly" — used to set the tone of the intro.

    Returns:
        HTML string ready to be used as an email body.
    """
    capped = articles[:MAX_ARTICLES]
    stories = "\n".join(
        f"{i + 1}. [{a.source}] {a.title}\n"
        f"   {a.summary[:MAX_SUMMARY_CHARS]}\n"
        f"   Link: {a.link}"
        for i, a in enumerate(capped)
    )

    period = "daily" if frequency == "daily" else "weekly"
    prompt = (
        f"You are an AI news editor. Write a concise {period} digest email summarizing these AI news stories.\n\n"
        f"Format as clean HTML suitable for email:\n"
        f"- A short intro sentence (1 line)\n"
        f"- Each story as: <h3>Title</h3><p>Summary. <a href='link'>Read more →</a></p>\n"
        f"- A short closing line\n\n"
        f"Stories:\n{stories}\n\n"
        f"Rules:\n"
        f"- Keep each story to 2-3 sentences\n"
        f"- Use plain HTML only (no CSS classes or inline styles)\n"
        f"- Do not include a subject line or greeting — body content only"
    )

    message = client.messages.create(
        model=MODEL,
        max_tokens=1024,
        messages=[{"role": "user", "content": prompt}],
    )
    return message.content[0].text
