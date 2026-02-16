import datetime
import time
from typing import List, Optional

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from src.config import NEWS_API_BASE_URL_DEFAULT
from src.models import Article


DEFAULT_MAX_RETRIES = 3
DEFAULT_BACKOFF_SECONDS = 2


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


def fetch_news(
    api_key: str,
    categories: str,
    limit: int,
    page: Optional[int] = None,
    base_url: str = NEWS_API_BASE_URL_DEFAULT,
    published_on: Optional[str] = None,
) -> List[Article]:
    if not api_key:
        raise ValueError("NEWS_API_KEY is not set")

    published_date = published_on
    if not published_date:
        now = datetime.datetime.now(datetime.timezone.utc)
        published_date = now.strftime("%Y-%m-%d")

    params = {
        "api_token": api_key,
        "categories": categories,
        "limit": limit,
        "language": "en",
        "published_on": published_date,
        "locale": "us,ca,au,gb,cn,de,fr,it,jp",
        "page": page,
    }

    session = _build_retry_session(max_retries=DEFAULT_MAX_RETRIES)
    resp = session.get(base_url, params=params, timeout=30)
    resp.raise_for_status()
    payload = resp.json()

    articles: List[Article] = []
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
