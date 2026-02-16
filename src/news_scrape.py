import logging

from src.db import store_results
from src.news_fetcher import fetch_news
from src.pipeline import run_pipeline

__all__ = ["fetch_news", "store_results", "run_pipeline"]


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    run_pipeline()
