from __future__ import annotations

import logging
from datetime import date
from typing import Any

from src.config import load_config
from src.mailer import send_html_mail
from src.models import NewsCandidate, RunStats
from src.notion_client import NotionClient
from src.ranker import rank_articles
from src.reporter import build_daily_html, build_daily_subject
from src.rss_search import fetch_google_news_rss
from src.scraper import scrape_article
from src.summarizer import OpenAISummarizer
from src.utils import setup_logging

LOGGER = logging.getLogger(__name__)


def run_daily_pipeline() -> None:
    setup_logging()
    cfg = load_config()
    stats = RunStats()

    notion = NotionClient(cfg.notion_token, cfg.request_timeout_sec)
    ai = OpenAISummarizer(cfg.openai_api_key, cfg.openai_model, cfg.request_timeout_sec)

    queries = notion.query_search_queries(cfg.notion_search_queries_db_id)
    stats.fetched_queries = len(queries)

    candidates: list[NewsCandidate] = []
    for query in queries:
        try:
            fetched = fetch_google_news_rss(query)
            candidates.extend(fetched)
            stats.rss_candidates += len(fetched)
        except Exception as err:
            LOGGER.exception("RSS fetch failed for query=%s err=%s", query.name, err)

    if not candidates:
        LOGGER.info("No candidates found. Exiting without email.")
        return

    existing = notion.existing_urls(cfg.notion_news_results_db_id, [c.url for c in candidates])
    seen: set[str] = set()
    unique: list[NewsCandidate] = []
    for candidate in candidates:
        if candidate.url in existing or candidate.url in seen:
            continue
        unique.append(candidate)
        seen.add(candidate.url)
    stats.duplicates_skipped = len(candidates) - len(unique)

    page_map: dict[str, str] = {}
    for item in unique:
        body, status = scrape_article(item.url, cfg.request_timeout_sec)
        item.raw_body = body
        item.body_status = status
        item.processing_status = "scraped" if status != "failed" else "failed"

        if status == "success":
            stats.scraped_success += 1
        elif status == "partial":
            stats.scraped_partial += 1
        else:
            stats.scraped_failed += 1

        try:
            page_id = notion.create_news_result(cfg.notion_news_results_db_id, item)
            stats.saved_raw += 1
            page_map[item.url] = page_id
        except Exception as err:
            LOGGER.exception("Failed to save Notion record: %s", err)

    ranked = rank_articles(unique)
    top15 = ranked[:15]
    stats.selected_top15 = len(top15)

    for idx, item in enumerate(top15):
        page_id = page_map.get(item.url)
        if not page_id or item.body_status == "failed":
            continue

        try:
            item.japanese_title = ai.generate_japanese_title(item)
            item.processing_status = "title_translated"

            if idx < 5:
                summary = ai.generate_summary(item)
                item.japanese_title = summary["japanese_title"]
                item.summary = summary["summary"]
                item.steel_insight = summary["steel_insight"]
                item.relevance = summary["relevance"]
                item.processing_status = "summarized"
                stats.summarized_top5 += 1
            else:
                item.relevance = item.relevance or "Low"

            notion.update_news_result(page_id, _build_update_properties(item, idx))
        except Exception as err:
            LOGGER.exception("AI/Notion update failed for url=%s err=%s", item.url, err)

    if not top15:
        LOGGER.info("No top items to email.")
        return

    subject = build_daily_subject(date.today())
    body = build_daily_html(top15, stats)
    send_html_mail(
        cfg.smtp_host,
        cfg.smtp_port,
        cfg.smtp_user,
        cfg.smtp_password,
        cfg.mail_from,
        cfg.mail_to,
        subject,
        body,
    )


def _build_update_properties(item: NewsCandidate, rank_idx: int) -> dict[str, Any]:
    return {
        "Japanese Title": {"rich_text": _to_rich_text(item.japanese_title)},
        "GPT Summary": {"rich_text": _to_rich_text(item.summary)},
        "Steel Insight": {"rich_text": _to_rich_text(item.steel_insight)},
        "Relevance": {"select": {"name": item.relevance}},
        "Processing Status": {
            "select": {"name": "selected_for_email" if rank_idx >= 5 else item.processing_status}
        },
    }


def _to_rich_text(text: str) -> list[dict[str, Any]]:
    if not text:
        return []
    return [{"text": {"content": text[i : i + 2000]}} for i in range(0, len(text), 2000)]


if __name__ == "__main__":
    run_daily_pipeline()
