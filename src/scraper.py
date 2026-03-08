from __future__ import annotations

import logging

import requests
from bs4 import BeautifulSoup

from src.utils import retry

LOGGER = logging.getLogger(__name__)
USER_AGENT = "Mozilla/5.0 (compatible; SteelNewsMonitor/1.0; +https://example.com/bot)"


def scrape_article(url: str, timeout_sec: int = 20) -> tuple[str, str]:
    """Returns (body_text, body_status)."""

    def _get() -> requests.Response:
        return requests.get(url, timeout=timeout_sec, headers={"User-Agent": USER_AGENT})

    try:
        response = retry(_get, retries=1)
        response.raise_for_status()
    except Exception as err:
        LOGGER.warning("Failed to fetch article url=%s err=%s", url, err)
        return "", "failed"

    soup = BeautifulSoup(response.text, "html.parser")
    for tag in soup(["script", "style", "noscript"]):
        tag.decompose()

    text = _extract_paragraphs(soup, "article p")
    if not text:
        text = _extract_paragraphs(soup, "main p")
    if not text:
        text = _extract_paragraphs(soup, "p")

    clean = "\n".join(line.strip() for line in text.splitlines() if line.strip())[:5000]
    if len(clean) < 120:
        return clean, "failed"
    if len(clean) < 300:
        return clean, "partial"
    return clean, "success"


def _extract_paragraphs(soup: BeautifulSoup, selector: str) -> str:
    paragraphs = [p.get_text(" ", strip=True) for p in soup.select(selector)]
    return "\n".join(p for p in paragraphs if p)
