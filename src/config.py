from __future__ import annotations

import os
from dataclasses import dataclass

from dotenv import load_dotenv


@dataclass(frozen=True)
class Config:
    notion_token: str
    notion_search_queries_db_id: str
    notion_news_results_db_id: str
    openai_api_key: str
    openai_model: str
    smtp_host: str
    smtp_port: int
    smtp_user: str
    smtp_password: str
    mail_from: str
    mail_to: str
    request_timeout_sec: int = 20


REQUIRED_ENV_KEYS = [
    "NOTION_TOKEN",
    "NOTION_SEARCH_QUERIES_DB_ID",
    "NOTION_NEWS_RESULTS_DB_ID",
    "OPENAI_API_KEY",
    "SMTP_HOST",
    "SMTP_PORT",
    "SMTP_USER",
    "SMTP_PASSWORD",
    "MAIL_FROM",
    "MAIL_TO",
]


def load_config() -> Config:
    load_dotenv()
    missing = [key for key in REQUIRED_ENV_KEYS if not os.getenv(key)]
    if missing:
        missing_text = ", ".join(missing)
        raise ValueError(f"Missing required environment variables: {missing_text}")

    return Config(
        notion_token=os.environ["NOTION_TOKEN"],
        notion_search_queries_db_id=os.environ["NOTION_SEARCH_QUERIES_DB_ID"],
        notion_news_results_db_id=os.environ["NOTION_NEWS_RESULTS_DB_ID"],
        openai_api_key=os.environ["OPENAI_API_KEY"],
        openai_model=os.getenv("OPENAI_MODEL", "gpt-4o-mini"),
        smtp_host=os.environ["SMTP_HOST"],
        smtp_port=int(os.environ["SMTP_PORT"]),
        smtp_user=os.environ["SMTP_USER"],
        smtp_password=os.environ["SMTP_PASSWORD"],
        mail_from=os.environ["MAIL_FROM"],
        mail_to=os.environ["MAIL_TO"],
        request_timeout_sec=int(os.getenv("REQUEST_TIMEOUT_SEC", "20")),
    )
