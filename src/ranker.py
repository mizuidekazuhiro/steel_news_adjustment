from __future__ import annotations

from datetime import datetime, timezone

from src.models import NewsCandidate

REGION_WEIGHT = {
    "Japan": 50,
    "India": 48,
    "ASEAN": 46,
    "Korea": 44,
    "Taiwan": 42,
    "China": 40,
    "Middle East": 30,
    "Australia": 28,
    "US": 20,
    "Europe": 18,
    "Global": 15,
}

CATEGORY_WEIGHT = {
    "DC Construction": 25,
    "Power": 23,
    "Steel": 21,
    "AI Investment": 19,
    "Cooling": 17,
    "Company Watch": 15,
}



def score_article(item: NewsCandidate) -> float:
    now = datetime.now(timezone.utc)
    age_score = 0.0
    if item.published_at:
        published = item.published_at
        if published.tzinfo is None:
            published = published.replace(tzinfo=timezone.utc)
        hours_old = max((now - published).total_seconds() / 3600, 0)
        age_score = max(0, 24 - min(hours_old, 24))

    body_score = {"success": 10, "partial": 4, "failed": 0}.get(item.body_status, 0)
    total = (
        REGION_WEIGHT.get(item.region, 10)
        + CATEGORY_WEIGHT.get(item.category, 10)
        + item.query_priority
        + body_score
        + age_score
    )
    return round(total, 2)


def rank_articles(items: list[NewsCandidate]) -> list[NewsCandidate]:
    for item in items:
        item.rank_score = score_article(item)
    return sorted(items, key=lambda x: x.rank_score, reverse=True)
