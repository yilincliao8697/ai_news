"""Tests for the feed importer script. Mocks all HTTP calls and DB writes."""

from unittest.mock import MagicMock, patch

import pytest

from scripts.import_feeds import classify, parse_news_feeds, should_enable


# --- classify() tests ---

def test_classify_arxiv_is_research():
    assert classify("arXiv CS", "https://arxiv.org/rss/cs.AI") == "research"


def test_classify_university_is_research():
    assert classify("MIT News", "https://news.mit.edu/rss") == "research"


def test_classify_ieee_is_research():
    assert classify("IEEE Spectrum", "https://spectrum.ieee.org/rss") == "research"


def test_classify_blog_is_industry():
    assert classify("Latent Space", "https://www.latent.space/feed") == "industry"


def test_classify_media_is_industry():
    assert classify("TechCrunch", "https://techcrunch.com/feed/") == "industry"


def test_classify_deepmind_is_research():
    assert classify("DeepMind Blog", "https://deepmind.com/blog/feed/basic/") == "research"


# --- parse_news_feeds() tests ---

SAMPLE_README = """
## AI, ML, Big Data News

- [Latent Space](https://latent.space) - The AI Engineer Podcast. (RSS feed: https://www.latent.space/feed)
- [arXiv CS.AI](https://arxiv.org) - Computer Science AI papers. (RSS feed: https://arxiv.org/rss/cs.AI)
- [Invalid Entry](https://example.com) - No RSS link here.

## AI, ML, Big Data Podcasts

- [Some Channel](https://youtube.com) - Videos. (RSS feed: https://youtube.com/feeds/some)
"""


def test_parse_news_feeds_extracts_entries():
    results = parse_news_feeds(SAMPLE_README)
    urls = [url for _, url in results]
    assert "https://www.latent.space/feed" in urls
    assert "https://arxiv.org/rss/cs.AI" in urls


def test_parse_news_feeds_skips_invalid_entries():
    results = parse_news_feeds(SAMPLE_README)
    names = [name for name, _ in results]
    assert "Invalid Entry" not in names


def test_parse_news_feeds_excludes_videos_section():
    results = parse_news_feeds(SAMPLE_README)
    urls = [url for _, url in results]
    assert "https://youtube.com/feeds/some" not in urls


def test_parse_news_feeds_returns_tuples():
    results = parse_news_feeds(SAMPLE_README)
    for name, url in results:
        assert isinstance(name, str)
        assert isinstance(url, str)
        assert url.startswith("http")


# --- should_enable() tests ---

def test_should_enable_starter_feed():
    assert should_enable("https://arxiv.org/rss/cs.AI") is True
    assert should_enable("https://www.latent.space/feed") is True


def test_should_enable_unknown_feed():
    assert should_enable("https://some-random-blog.com/feed") is False


# --- main() integration tests ---

MOCK_README = """
## AI, ML, Big Data News

- [Latent Space](https://latent.space) - Newsletter. (RSS feed: https://www.latent.space/feed)
- [Unknown Blog](https://unknownblog.com) - Blog. (RSS feed: https://unknownblog.com/rss)

## AI, ML, Big Data Podcasts

- [Some Podcast](https://somepodcast.com) - Podcast. (RSS feed: https://somepodcast.com/feed)
"""


@patch("scripts.import_feeds.get_all_feeds", return_value=[MagicMock(), MagicMock()])
@patch("scripts.import_feeds.set_feed_enabled")
@patch("scripts.import_feeds.upsert_feed", return_value=MagicMock(id=1))
@patch("scripts.import_feeds.httpx.get")
def test_main_inserts_only_news_feeds(mock_get, mock_upsert, mock_enable, mock_all):
    mock_response = MagicMock()
    mock_response.text = MOCK_README
    mock_response.raise_for_status = MagicMock()
    mock_get.return_value = mock_response

    from scripts.import_feeds import main
    main()

    # Only 2 news feeds parsed — video feed excluded
    assert mock_upsert.call_count == 2


@patch("scripts.import_feeds.get_all_feeds", return_value=[])
@patch("scripts.import_feeds.set_feed_enabled")
@patch("scripts.import_feeds.upsert_feed", return_value=MagicMock(id=1))
@patch("scripts.import_feeds.httpx.get")
def test_main_enables_starter_feeds(mock_get, mock_upsert, mock_enable, mock_all):
    mock_response = MagicMock()
    mock_response.text = MOCK_README
    mock_response.raise_for_status = MagicMock()
    mock_get.return_value = mock_response

    from scripts.import_feeds import main
    main()

    # latent.space is in STARTER_SET — should be enabled
    mock_enable.assert_called_once_with(1, True)


@patch("scripts.import_feeds.httpx.get", side_effect=Exception("network error"))
def test_main_exits_on_fetch_failure(mock_get):
    from scripts.import_feeds import main
    with pytest.raises(SystemExit):
        main()
