import logging
import os
import datetime

from src.pipeline import run_pipeline

def main() -> None:
    logging.basicConfig(level=logging.INFO)
    logging.info("Starting to run pipeline locally")
    

    
    end_date = datetime.datetime.now(datetime.timezone.utc)

    
    interval = datetime.timedelta(days=1)
    total_days = datetime.timedelta(days=3)
    start_period = end_date - total_days

    
    current_date = end_date
    while current_date > start_period:
        
        published_date = current_date.strftime("%Y-%m-%d")
        
        
        print(f"Fetching data for: {published_date}")
        run_pipeline(published_on=published_date)
        
        current_date -= interval

    logging.info("Pipeline execution completed successfully")


if __name__ == "__main__":
    main()
