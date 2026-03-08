from __future__ import annotations

import logging
from datetime import datetime
from typing import Any

import requests

from src.models import NewsCandidate, SearchQuery
from src.utils import retry

LOGGER = logging.getLogger(__name__)
NOTION_VERSION = "2022-06-28"
_MAX_RICH_TEXT_CHARS = 2000


class NotionClient:
    def __init__(self, token: str, timeout_sec: int = 20) -> None:
        self.base_url = "https://api.notion.com/v1"
        self.timeout_sec = timeout_sec
        self.session = requests.Session()
        self.session.headers.update(
            {
                "Authorization": f"Bearer {token}",
                "Notion-Version": NOTION_VERSION,
                "Content-Type": "application/json",
            }
        )

    def query_search_queries(self, db_id: str) -> list[SearchQuery]:
        payload: dict[str, Any] = {
            "filter": {"property": "Enabled", "checkbox": {"equals": True}},
            "page_size": 100,
        }
        response = retry(
            lambda: self.session.post(
                f"{self.base_url}/databases/{db_id}/query", json=payload, timeout=self.timeout_sec
            )
        )
        response.raise_for_status()
        rows = response.json().get("results", [])

        queries: list[SearchQuery] = []
        for row in rows:
            prop = row.get("properties", {})
            try:
                queries.append(
                    SearchQuery(
                        name=self._title(prop, "Name"),
                        query=self._rich_text(prop, "Query"),
                        region=self._select(prop, "Region", "Global"),
                        language=self._select(prop, "Language", "en"),
                        priority=self._number(prop, "Priority", 0),
                        enabled=self._checkbox(prop, "Enabled", False),
                        category=self._select(prop, "Category", "Company Watch"),
                        max_results=self._number(prop, "Max Results", 10),
                    )
                )
            except Exception as err:
                LOGGER.warning("Skipping malformed Search Query row: %s", err)
        return queries

    def existing_urls(self, db_id: str, urls: list[str]) -> set[str]:
        existing: set[str] = set()
        for url in set(urls):
            payload = {
                "filter": {"property": "Duplicate Key", "rich_text": {"equals": url}},
                "page_size": 1,
            }
            response = retry(
                lambda: self.session.post(
                    f"{self.base_url}/databases/{db_id}/query", json=payload, timeout=self.timeout_sec
                )
            )
            response.raise_for_status()
            if response.json().get("results"):
                existing.add(url)
        return existing

    def create_news_result(self, db_id: str, item: NewsCandidate) -> str:
        payload = {"parent": {"database_id": db_id}, "properties": self._build_news_properties(item)}
        response = retry(lambda: self.session.post(f"{self.base_url}/pages", json=payload, timeout=self.timeout_sec))
        response.raise_for_status()
        return response.json().get("id", "")

    def update_news_result(self, page_id: str, updates: dict[str, Any]) -> None:
        payload = {"properties": updates}
        response = retry(lambda: self.session.patch(f"{self.base_url}/pages/{page_id}", json=payload, timeout=self.timeout_sec))
        response.raise_for_status()

    def _build_news_properties(self, item: NewsCandidate) -> dict[str, Any]:
        published = item.published_at.isoformat() if item.published_at else None
        return {
            "Title": {"title": self._to_rich_text(item.title[:_MAX_RICH_TEXT_CHARS])},
            "Japanese Title": {"rich_text": self._to_rich_text(item.japanese_title)},
            "URL": {"url": item.url},
            "Published At": {"date": {"start": published}} if published else {"date": None},
            "Source": {"rich_text": self._to_rich_text(item.source)},
            "Query Name": {"rich_text": self._to_rich_text(item.query_name)},
            "Region": {"select": {"name": item.region}},
            "Category": {"select": {"name": item.category}},
            "Collected At": {"date": {"start": datetime.utcnow().isoformat()}},
            "Duplicate Key": {"rich_text": self._to_rich_text(item.url)},
            "Raw Body": {"rich_text": self._to_rich_text(item.raw_body[:5000])},
            "Body Status": {"select": {"name": item.body_status}},
            "GPT Summary": {"rich_text": self._to_rich_text(item.summary)},
            "Steel Insight": {"rich_text": self._to_rich_text(item.steel_insight)},
            "Relevance": {"select": {"name": item.relevance}},
            "Processing Status": {"select": {"name": item.processing_status}},
        }

    @staticmethod
    def _to_rich_text(text: str) -> list[dict[str, Any]]:
        if not text:
            return []
        chunks = [text[i : i + _MAX_RICH_TEXT_CHARS] for i in range(0, len(text), _MAX_RICH_TEXT_CHARS)]
        return [{"text": {"content": chunk}} for chunk in chunks]

    @staticmethod
    def _title(props: dict[str, Any], name: str) -> str:
        arr = props.get(name, {}).get("title", [])
        return "".join(x.get("plain_text", "") for x in arr)

    @staticmethod
    def _rich_text(props: dict[str, Any], name: str) -> str:
        arr = props.get(name, {}).get("rich_text", [])
        return "".join(x.get("plain_text", "") for x in arr)

    @staticmethod
    def _select(props: dict[str, Any], name: str, default: str) -> str:
        return props.get(name, {}).get("select", {}).get("name") or default

    @staticmethod
    def _checkbox(props: dict[str, Any], name: str, default: bool) -> bool:
        return props.get(name, {}).get("checkbox", default)

    @staticmethod
    def _number(props: dict[str, Any], name: str, default: int) -> int:
        value = props.get(name, {}).get("number")
        return int(value) if value is not None else default
