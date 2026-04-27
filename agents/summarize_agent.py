"""Summarize agent: generates a 2–4 sentence summary of a RawArticle.

Stateless. No DB. No side effects. Returns SummaryResult only.
"""

import json
import os
from pathlib import Path

import anthropic
from dotenv import load_dotenv

from dataclasses_shared import RawArticle, SummaryResult

load_dotenv()

_client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))
_MODEL = "claude-haiku-4-5-20251001"
_PROMPT_PATH = Path(__file__).parent / "prompts" / "summarize_prompt.txt"


def _load_prompt() -> str:
    """Load the summarize prompt template from disk."""
    return _PROMPT_PATH.read_text(encoding="utf-8")


def summarize_article(article: RawArticle) -> SummaryResult:
    """Generate a 2–4 sentence summary of the given article.

    Calls the Claude API with the article's title and content.
    Parses the JSON response into a SummaryResult. Falls back to
    an empty summary string on any parsing or API error.

    Args:
        article: A RawArticle with title and content fields populated.

    Returns:
        A SummaryResult with a summary string (2–4 sentences).
    """
    prompt_template = _load_prompt()
    prompt = prompt_template.format(
        title=article.title,
        content=article.content,
    )

    try:
        message = _client.messages.create(
            model=_MODEL,
            max_tokens=512,
            messages=[{"role": "user", "content": prompt}],
        )
        raw_text = message.content[0].text.strip()
        data = json.loads(raw_text)
        return SummaryResult(summary=str(data["summary"]))
    except (json.JSONDecodeError, KeyError, anthropic.APIError) as e:
        print(f"[summarize_agent] ERROR for '{article.title}': {e}")
        return SummaryResult(summary="")
