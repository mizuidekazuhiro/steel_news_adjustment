from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional


@dataclass
class SearchQuery:
    name: str
    query: str
    region: str
    language: str
    priority: int
    enabled: bool
    category: str
    max_results: int = 10


@dataclass
class NewsCandidate:
    title: str
    url: str
    published_at: Optional[datetime]
    source: str
    query_name: str
    region: str
    category: str
    query_priority: int
    raw_body: str = ""
    body_status: str = "failed"
    japanese_title: str = ""
    summary: str = ""
    steel_insight: str = ""
    relevance: str = "Low"
    processing_status: str = "new"
    rank_score: float = 0.0
    collected_at: datetime = field(default_factory=datetime.utcnow)


@dataclass
class RunStats:
    fetched_queries: int = 0
    rss_candidates: int = 0
    duplicates_skipped: int = 0
    saved_raw: int = 0
    scraped_success: int = 0
    scraped_partial: int = 0
    scraped_failed: int = 0
    selected_top15: int = 0
    summarized_top5: int = 0
