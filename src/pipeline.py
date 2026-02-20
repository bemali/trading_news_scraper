import logging
from typing import Any, Dict, Optional

from src.ai_analysis import synthesize_structured_output
from src.config import Config, load_config
from src.db import store_results
from src.news_fetcher import fetch_news
from dotenv import load_dotenv

load_dotenv(override=True)


def run_pipeline(config: Optional[Config] = None, published_on: Optional[str] = None ) -> Dict[str, Any]:
    cfg = config or load_config()

    logging.info("Fetching news categories=%s limit=%s", cfg.news_api_categories, cfg.news_api_limit)
    articles = fetch_news(
        api_key=cfg.news_api_key,
        categories=cfg.news_api_categories,
        limit=cfg.news_api_limit,
        base_url=cfg.news_api_base_url,
        published_on=published_on
    )

    if not articles:
        logging.warning("No articles returned from news API")
        return {"summary": "", "articles": []}

    logging.info("Synthesizing %s articles", len(articles))
    analyses = synthesize_structured_output(
        endpoint=cfg.azure_openai_endpoint,
        api_key=cfg.azure_openai_api_key,
        deployment=cfg.azure_openai_deployment,
        articles=articles,
        api_version=cfg.azure_openai_api_version,
    )

    logging.info("Storing results in Postgres")
    store_results(cfg.postgres_conn_str, analyses, articles, cfg.postgres_init_schema)

    return {"summary": analyses, "articles": articles}


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    run_pipeline()
