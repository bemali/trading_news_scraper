import logging

import azure.functions as func

from src.news_scrape import run_pipeline

app = func.FunctionApp()


@app.timer_trigger(
    schedule="0 0 22 * * *",
    arg_name="myTimer",
    run_on_startup=False,
    use_monitor=False,
)
def timer_trigger(myTimer: func.TimerRequest) -> None:
    if myTimer.past_due:
        logging.info("The timer is past due!")

    logging.info("Starting daily news pipeline")
    run_pipeline()
    logging.info("Finished daily news pipeline")
