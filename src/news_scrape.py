import json
import logging
import os
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional

import psycopg2
import requests
from dotenv import load_dotenv
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
import datetime


load_dotenv()

NEWS_API_BASE_URL = "https://api.thenewsapi.com/v1/news/all"
DEFAULT_CATEGORIES = "business,tech"
DEFAULT_LIMIT = 50

AZURE_OPENAI_API_VERSION_DEFAULT = "2024-02-15-preview"
DEFAULT_MAX_RETRIES = 3
DEFAULT_BACKOFF_SECONDS = 2


@dataclass
class Article:
    id: str
    title: str
    description: str
    url: str
    published_at: str
    source: str
    raw: Dict[str, Any]


def _build_retry_session(max_retries: int) -> requests.Session:
    retry = Retry(
        total=max_retries,
        connect=max_retries,
        read=max_retries,
        status=max_retries,
        backoff_factor=0.8,
        status_forcelist=(429, 500, 502, 503, 504),
        allowed_methods=("GET", "POST"),
        raise_on_status=False,
    )
    adapter = HTTPAdapter(max_retries=retry)
    session = requests.Session()
    session.mount("https://", adapter)
    session.mount("http://", adapter)
    return session


def _sleep_backoff(attempt: int, base_seconds: int) -> None:
    delay = base_seconds * (2 ** (attempt - 1))
    time.sleep(delay)


def _read_migration_sql() -> str:
    migration_path = Path(__file__).resolve().parent.parent / "migrations" / "001_create_tables.sql"
    return migration_path.read_text(encoding="utf-8")


def fetch_news(api_key: str, categories: str, limit:int, page:int=None) -> List[Article]:
    if not api_key:
        raise ValueError("NEWS_API_KEY is not set")
    
    # Get the current date
    now = datetime.datetime.now()
    published_on = now.strftime('%Y-%m-%d')

    params = {
        "api_token": api_key,
        "categories": categories,
        "limit": limit,
        "language": "en",
        "published_on": published_on,  # today
        "locale": "us,ca,au,gb,cn,de,fr,it,jp", 
         "page":page # prioritize English-speaking countries but allow global sources
    }

    session = _build_retry_session(max_retries=DEFAULT_MAX_RETRIES)
    resp = session.get(NEWS_API_BASE_URL, params=params, timeout=30)
    resp.raise_for_status()
    payload = resp.json()

    articles = []
    for item in payload.get("data", []):
        articles.append(
            Article(
                id=str(item.get("uuid") or item.get("id") or ""),
                title=item.get("title") or "",
                description=item.get("description") or "",
                url=item.get("url") or "",
                published_at=item.get("published_at") or "",
                source=(item.get("source") or ""),
                raw=item,
            )
        )

    return articles


def _format_prompt(articles: Iterable[Article]) -> str:
    lines = []
    for a in articles:
        lines.append(f"- {a.title} ({a.source})")
    joined = "\n".join(lines)
    return (
        "Summarize the main market-relevant themes across these headlines. "
        "Return 5-8 bullet points and a 1-sentence overall takeaway.\n\n"
        f"Headlines:\n{joined}"
    )


def synthesize_with_azure_openai(
    endpoint: str,
    api_key: str,
    deployment: str,
    articles: Iterable[Article],
    api_version: str = AZURE_OPENAI_API_VERSION_DEFAULT,
) -> str:
    if not endpoint or not api_key or not deployment:
        raise ValueError("AZURE_OPENAI_ENDPOINT, AZURE_OPENAI_API_KEY, or AZURE_OPENAI_DEPLOYMENT is not set")

    url = f"{endpoint.rstrip('/')}/openai/deployments/{deployment}/chat/completions"
    params = {"api-version": api_version}
    headers = {
        "Content-Type": "application/json",
        "api-key": api_key,
    }

    prompt = _format_prompt(articles)

    body = {
        "messages": [
            {"role": "system", "content": "You are a market news analyst."},
            {"role": "user", "content": prompt},
        ],
        "temperature": 0.2,
        "max_tokens": 600,
    }

    session = _build_retry_session(max_retries=DEFAULT_MAX_RETRIES)
    resp = session.post(url, params=params, headers=headers, json=body, timeout=60)
    resp.raise_for_status()
    data = resp.json()

    try:
        return data["choices"][0]["message"]["content"].strip()
    except (KeyError, IndexError, TypeError):
        logging.exception("Unexpected Azure OpenAI response: %s", json.dumps(data)[:500])
        raise


def store_results(
    conn_str: str,
    summary: str,
    articles: Iterable[Article],
    init_schema: bool,
) -> None:
    if not conn_str:
        raise ValueError("POSTGRES_CONN_STR is not set")

    # Expected tables (create separately):
    # news_summaries(id serial primary key, created_at timestamptz default now(), summary text not null)
    # news_articles(id text primary key, summary_id int references news_summaries(id), title text, url text, source text, published_at timestamptz, raw jsonb)

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


def run_pipeline() -> Dict[str, Any]:
    news_api_key = os.getenv("NEWS_API_KEY")
    categories = os.getenv("NEWS_API_CATEGORIES", DEFAULT_CATEGORIES)
    limit = int(os.getenv("NEWS_API_LIMIT", str(DEFAULT_LIMIT)))

    azure_endpoint = os.getenv("AZURE_OPENAI_ENDPOINT")
    azure_key = os.getenv("AZURE_OPENAI_API_KEY")
    azure_deployment = os.getenv("AZURE_OPENAI_DEPLOYMENT")
    azure_api_version = os.getenv("AZURE_OPENAI_API_VERSION", AZURE_OPENAI_API_VERSION_DEFAULT)

    postgres_conn = os.getenv("POSTGRES_CONN_STR")
    init_schema = os.getenv("POSTGRES_INIT_SCHEMA", "false").lower() in {"1", "true", "yes"}

    logging.info("Fetching news categories=%s limit=%s", categories, limit)
    articles = fetch_news(news_api_key, categories, limit)

    if not articles:
        logging.warning("No articles returned from news API")
        return {"summary": "", "articles": []}

    logging.info("Synthesizing %s articles", len(articles))
    summary = synthesize_with_azure_openai(
        endpoint=azure_endpoint,
        api_key=azure_key,
        deployment=azure_deployment,
        articles=articles,
        api_version=azure_api_version,
    )

    logging.info("Storing results in Postgres")
    store_results(postgres_conn, summary, articles, init_schema)

    return {"summary": summary, "articles": articles}


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    run_pipeline()
