import logging
import os

from src.pipeline import run_pipeline

def main() -> None:
    logging.basicConfig(level=logging.INFO)
    logging.info("Starting to run pipeline locally")
    run_pipeline()
    logging.info("Pipeline execution completed successfully")


if __name__ == "__main__":
    main()
