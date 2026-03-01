# RPL-3.0-runner

The RPL-3.0-runner is a Celery-based worker that executes student code submissions in isolated Docker containers.

## Architecture

1.  **Celery Worker:** Listens for `process_submission` tasks from RabbitMQ.
2.  **Prewarmer:** Maintains a pool of pre-started, paused Docker containers to reduce execution latency.
3.  **Language Runners:** Specialized scripts (e.g., `c_runner.py`, `python_runner.py`) that handle compilation and execution within the containers.

## Setup

### Prerequisites

- Docker
- Python 3.13
- RabbitMQ (configured in `.env`)

### Local Development

1.  **Install dependencies:**
    ```bash
    pip install -r requirements.txt
    ```

2.  **Start the Celery worker:**
    ```bash
    celery -A celery_app worker --loglevel=info -c 4
    ```

## Configuration

Environment variables can be set in `.env`:

- `QUEUE_URL`: RabbitMQ connection string.
- `RUNNER_POOL_SIZE`: Number of pre-warmed containers per language.
- `RUNNER_LANGUAGES`: JSON mapping of language IDs to Docker images.

## Testing

Run unit tests for the runner logic:

```bash
python -m pytest
```
