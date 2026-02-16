import logging

from src.news_scrape import run_pipeline


def main() -> None:
    logging.basicConfig(level=logging.INFO)
    logging.info("Starting news pipeline")
    run_pipeline()
    logging.info("Finished news pipeline")


if __name__ == "__main__":
    main()
