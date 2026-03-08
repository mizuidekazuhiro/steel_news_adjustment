from __future__ import annotations

import json
import logging
from typing import Any

import requests

from src.models import NewsCandidate
from src.utils import retry

LOGGER = logging.getLogger(__name__)


class OpenAISummarizer:
    def __init__(self, api_key: str, model: str, timeout_sec: int = 20) -> None:
        self.api_key = api_key
        self.model = model
        self.timeout_sec = timeout_sec
        self.url = "https://api.openai.com/v1/chat/completions"

    def generate_japanese_title(self, item: NewsCandidate) -> str:
        if not item.raw_body:
            return "不明"
        schema_hint = '{"japanese_title":"..."}'
        prompt = (
            "与えられた記事情報から日本語タイトルのみを生成してください。"
            "不明な場合は「不明」を使ってください。"
            f"出力は厳密JSONのみ: {schema_hint}\n"
            f"title={item.title}\nsource={item.source}\nbody={item.raw_body[:2500]}"
        )
        result = self._json_completion(prompt)
        return str(result.get("japanese_title", "不明"))

    def generate_summary(self, item: NewsCandidate) -> dict[str, str]:
        if len(item.raw_body) < 300:
            return {
                "japanese_title": item.japanese_title or "不明",
                "summary": "本文が短いため要約をスキップ",
                "steel_insight": "不明",
                "relevance": "Low",
            }

        prompt = (
            "記事を日本語で要約し、鋼材供給示唆と重要度を作成してください。"
            "推測を避け、不明な点は『不明』と明記。"
            "出力JSONのみ: "
            '{"japanese_title":"...","summary":"...","steel_insight":"...","relevance":"High"}'
            " relevance は High/Medium/Low のみ。\n"
            f"title={item.title}\nsource={item.source}\nbody={item.raw_body[:4000]}"
        )
        result = self._json_completion(prompt)
        relevance = str(result.get("relevance", "Low"))
        if relevance not in {"High", "Medium", "Low"}:
            relevance = "Low"
        return {
            "japanese_title": str(result.get("japanese_title", "不明")),
            "summary": str(result.get("summary", "不明")),
            "steel_insight": str(result.get("steel_insight", "不明")),
            "relevance": relevance,
        }

    def _json_completion(self, prompt: str) -> dict[str, Any]:
        def _call() -> requests.Response:
            return requests.post(
                self.url,
                timeout=self.timeout_sec,
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": self.model,
                    "response_format": {"type": "json_object"},
                    "messages": [
                        {"role": "system", "content": "You are a careful JSON-only assistant."},
                        {"role": "user", "content": prompt},
                    ],
                    "temperature": 0.2,
                },
            )

        for attempt in range(2):
            response = retry(_call, retries=1)
            response.raise_for_status()
            content = response.json()["choices"][0]["message"]["content"]
            try:
                return json.loads(content)
            except json.JSONDecodeError:
                LOGGER.warning("JSON parse failed, retrying attempt=%s", attempt + 1)
        raise ValueError("OpenAI response JSON parsing failed")
