import json
import logging
import time
from pathlib import Path
from typing import Iterable

import psycopg2

from src.models import Article


DEFAULT_MAX_RETRIES = 3
DEFAULT_BACKOFF_SECONDS = 2


def _sleep_backoff(attempt: int, base_seconds: int) -> None:
    delay = base_seconds * (2 ** (attempt - 1))
    time.sleep(delay)


def _read_migration_sql() -> str:
    migration_path = Path(__file__).resolve().parent.parent / "migrations" / "001_create_tables.sql"
    return migration_path.read_text(encoding="utf-8")


def store_results(
    conn_str: str,
    summary: str,
    articles: Iterable[Article],
    init_schema: bool,
) -> None:
    if not conn_str:
        raise ValueError("POSTGRES_CONN_STR is not set")

    for attempt in range(1, DEFAULT_MAX_RETRIES + 1):
        try:
            with psycopg2.connect(conn_str) as conn:
                with conn.cursor() as cur:
                    if init_schema:
                        cur.execute(_read_migration_sql())

                    cur.execute(
                        "INSERT INTO news_summaries(summary) VALUES (%s) RETURNING id",
                        (summary,),
                    )
                    summary_id = cur.fetchone()[0]

                    for a in articles:
                        cur.execute(
                            """
                            INSERT INTO news_articles(id, summary_id, title, url, source, published_at, raw)
                            VALUES (%s, %s, %s, %s, %s, %s, %s)
                            ON CONFLICT (id) DO NOTHING
                            """,
                            (
                                a.id,
                                summary_id,
                                a.title,
                                a.url,
                                a.source,
                                a.published_at or None,
                                json.dumps(a.raw),
                            ),
                        )
            break
        except psycopg2.Error:
            logging.exception("Postgres operation failed on attempt %s", attempt)
            if attempt >= DEFAULT_MAX_RETRIES:
                raise
            _sleep_backoff(attempt, DEFAULT_BACKOFF_SECONDS)
