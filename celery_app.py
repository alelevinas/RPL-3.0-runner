import os
import logging
from celery import Celery
import receiver
from prewarmer import Prewarmer

QUEUE_URL = os.environ.get("QUEUE_URL", "amqp://guest:guest@localhost:5672")
QUEUE_ACTIVITIES_NAME = os.environ.get("QUEUE_ACTIVITIES_NAME", "hello")

app = Celery("rpl_runner", broker=QUEUE_URL, backend="rpc://")

# Initialize Prewarmer
prewarmer = Prewarmer()
try:
    prewarmer.prewarm()
except Exception as e:
    logging.error(f"Initial prewarm failed: {e}")

@app.task(
    name="process_submission",
    bind=True,
    autoretry_for=(Exception,),
    retry_kwargs={'max_retries': 3, 'countdown': 5}
)
def process_submission(self, decoded_message):
    logging.info(f"Processing submission: {decoded_message}")
    subm, lang = decoded_message.split()
    
    try:
        # Update status to PROCESSING as soon as we start
        try:
            # Module-level double-underscore functions are accessible but conventionally private.
            # We call it to ensure the backend knows we are working on it.
            receiver.__update_submission_status(subm, "PROCESSING")
        except Exception as e:
            logging.warning(f"Failed to update status to PROCESSING for {subm}: {e}")

        runner_url = prewarmer.get_container_url(lang)
        if runner_url:
            logging.info(f"Using pre-warmed container at {runner_url} for {lang}")
            receiver.ejecutar(subm, lang, runner_url=runner_url)
            
            # Extract container ID from URL to stop/remove it
            container_id = runner_url.split("//")[1].split(":")[0]
            try:
                container = prewarmer.client.containers.get(container_id)
                container.stop()
                container.remove()
            except Exception as e:
                logging.warning(f"Failed to cleanup container {container_id}: {e}")
        else:
            logging.warning(f"No pre-warmed container for {lang}, falling back to standard execution")
            receiver.ejecutar(subm, lang)
            
    except Exception as e:
        logging.error(f"Error in process_submission: {e}")
        raise e

if __name__ == "__main__":
    app.start()
