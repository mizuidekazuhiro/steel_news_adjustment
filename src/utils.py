from __future__ import annotations

import logging
import time
from datetime import datetime
from email.utils import format_datetime, parsedate_to_datetime
from typing import Callable, Iterable, TypeVar

import requests

T = TypeVar("T")


def setup_logging() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s [%(name)s] %(message)s",
    )


def parse_iso_datetime(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        try:
            return parsedate_to_datetime(value)
        except (TypeError, ValueError):
            return None


def to_rfc2822(dt: datetime | None) -> str:
    if not dt:
        return "不明"
    return format_datetime(dt)


def retry(operation: Callable[[], T], retries: int = 2, backoff_sec: float = 1.0) -> T:
    last_err: Exception | None = None
    for attempt in range(retries + 1):
        try:
            return operation()
        except requests.RequestException as err:
            last_err = err
            if attempt >= retries:
                break
            time.sleep(backoff_sec * (attempt + 1))
    raise RuntimeError(f"Operation failed after retries: {last_err}")


def chunked(items: list[T], size: int) -> Iterable[list[T]]:
    for idx in range(0, len(items), size):
        yield items[idx : idx + size]
