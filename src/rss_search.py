from __future__ import annotations

import logging
import urllib.parse
from datetime import datetime, timezone

import feedparser

from src.models import NewsCandidate, SearchQuery
from src.utils import parse_iso_datetime

LOGGER = logging.getLogger(__name__)


def fetch_google_news_rss(query: SearchQuery) -> list[NewsCandidate]:
    encoded_query = urllib.parse.quote(f"{query.query} when:1d")
    lang = "ja" if query.language == "ja" else "en"
    rss_url = f"https://news.google.com/rss/search?q={encoded_query}&hl={lang}&gl=US&ceid=US:{lang}"
    feed = feedparser.parse(rss_url)

    candidates: list[NewsCandidate] = []
    max_results = query.max_results or 10
    for entry in feed.entries[:max_results]:
        candidates.append(
            NewsCandidate(
                title=getattr(entry, "title", ""),
                url=getattr(entry, "link", ""),
                published_at=_extract_published(entry),
                source=_extract_source(entry),
                query_name=query.name,
                region=query.region,
                category=query.category,
                query_priority=query.priority,
            )
        )
    LOGGER.info("RSS fetched: query=%s count=%s", query.name, len(candidates))
    return [c for c in candidates if c.url]


def _extract_source(entry: feedparser.FeedParserDict) -> str:
    source = getattr(entry, "source", None)
    if isinstance(source, dict):
        return source.get("title", "")
    return ""


def _extract_published(entry: feedparser.FeedParserDict) -> datetime | None:
    published = parse_iso_datetime(getattr(entry, "published", None))
    if published:
        return published
    parsed = getattr(entry, "published_parsed", None)
    if parsed:
        return datetime(*parsed[:6], tzinfo=timezone.utc)
    return None
