"""Filter agent: decides if a RawArticle is relevant to its topic.

Stateless. No DB. No side effects. Returns FilterResult only.
"""

import json
import os
from pathlib import Path

import anthropic
from dotenv import load_dotenv

from dataclasses_shared import FilterResult, RawArticle

load_dotenv()

_client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))
_MODEL = "claude-3-haiku-20240307"
_PROMPT_PATH = Path(__file__).parent / "prompts" / "filter_prompt.txt"


def _load_prompt() -> str:
    """Load the filter prompt template from disk."""
    return _PROMPT_PATH.read_text(encoding="utf-8")


def filter_article(article: RawArticle) -> FilterResult:
    """Determine whether an article is relevant to its declared topic.

    Calls the Claude API with the article's title, content, and topic.
    Parses the JSON response into a FilterResult. Falls back to
    is_relevant=False on any parsing or API error.

    Args:
        article: A RawArticle with title, content, and topic fields populated.

    Returns:
        A FilterResult with is_relevant (bool) and reason (str).
    """
    prompt_template = _load_prompt()
    prompt = prompt_template.format(
        topic=article.topic,
        title=article.title,
        content=article.content,
    )

    try:
        message = _client.messages.create(
            model=_MODEL,
            max_tokens=256,
            messages=[{"role": "user", "content": prompt}],
        )
        raw_text = message.content[0].text.strip()
        data = json.loads(raw_text)
        return FilterResult(
            is_relevant=bool(data["is_relevant"]),
            reason=str(data.get("reason", "")),
        )
    except (json.JSONDecodeError, KeyError, anthropic.APIError) as e:
        print(f"[filter_agent] ERROR for '{article.title}': {e}")
        return FilterResult(is_relevant=False, reason=f"Agent error: {e}")
