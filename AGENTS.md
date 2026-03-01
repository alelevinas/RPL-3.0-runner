# RPL-3.0-runner (Code Execution)

## What This Is

A high-performance code execution system that uses Celery and RabbitMQ to process student submissions in isolated Docker containers.

## Architecture

1.  **Celery Worker (`celery_app.py`):** Consumes `process_submission` tasks from RabbitMQ.
2.  **Prewarmer (`prewarmer.py`):** Maintains a pool of pre-started, paused Docker containers to eliminate startup latency.
3.  **Receiver (`receiver.py`):** Fetches submission metadata from the Activities API and manages the execution flow.
4.  **Language Runners (`rpl_runner/`):** Specialized scripts inside Docker containers that handle compilation and test execution for C, Python, Go, Rust, and Java.

## Project Structure

```
RPL-3.0-runner/
├── celery_app.py            # Celery application and task definition
├── prewarmer.py             # Logic for managing pre-started containers
├── receiver.py              # Core logic: fetch data, call runner, report results
├── config.py                # Environment configuration
├── requirements.txt         # Python dependencies (celery, docker, requests)
├── Dockerfile               # Runner container entry point (Python 3.13-alpine)
├── docker-compose.local.yml # Local integration testing with RabbitMQ
├── rpl_runner/
│   ├── Dockerfile           # Base image for language runners
│   ├── init_server.py       # Flask app inside containers to receive code
│   ├── runner.py            # Main execution logic inside containers
│   ├── c_runner.py          # C-specific execution (Criterion)
│   ├── python_runner.py     # Python-specific execution (unittest)
│   ├── go_runner.py         # Go-specific execution (testify)
│   ├── rust_runner.py       # Rust-specific execution (cargo test)
│   └── runner-libs/         # Test framework libraries
└── tests/                   # Automated tests for the runner logic
```

## How It Works

1.  **Enqueuing:** The Activities API sends a task to the `process_submission` queue via Celery.
2.  **Dispatching:** A Celery worker picks up the task and requests a container from the `Prewarmer`.
3.  **Execution:** The `Receiver` sends the code to the pre-warmed container via HTTP.
4.  **Results:** The container executes the code, and the `Receiver` posts the results back to the Activities API.
5.  **Cleanup:** The used container is stopped and removed, and the `Prewarmer` refills the pool in the background.

## Running Locally

```bash
# Start the Celery worker
celery -A celery_app worker --loglevel=info -c 4
```

## Automated Tests

We use `pytest` for unit testing the runner logic:

```bash
# In RPL-3.0-runner/
python -m pytest
```

## Agent Tasks

Useful work an agent can do:
- **Language Support**: Add support for new languages (e.g., Java, Ruby).
- **Security Audit**: Scan the base Docker images for vulnerabilities.
- **Performance Profiling**: Benchmark the execution latency with and without pre-warmed containers.
- **Error Extraction**: Improve regex patterns in `shared/mistake_matcher.py` for better student hints.
