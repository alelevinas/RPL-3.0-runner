# RPL-3.0-runner

Celery-based worker that processes student code submissions in isolated Docker containers.

## Architecture

```
RabbitMQ → Celery worker (celery_app.py)
               └─▶ receiver.py builds tar, POSTs to runner Flask server
                       └─▶ rpl_runner/ Flask server (inside Docker container)
                               └─▶ language runner (c_runner.py, python_runner.py, …)
                                       └─▶ compile + execute student code
               └─▶ POST results back to Activities API
```

The **runner Flask server** (`rpl_runner/init_server.py`) runs inside a Docker image that has gcc, Python, Go, Rust, and Java installed. The Celery worker is a thin coordinator that fetches submission metadata, builds the tar, and delegates execution to that container.

## Prerequisites

- Docker Desktop
- Python 3.13 (via pyenv)
- `python-dotenv` CLI: `pip install python-dotenv`
- RabbitMQ running (see workspace `docker-compose.infra.yml`)
- Activities API running on port 8001

## Local Setup

### 1. Copy the shared module into the build context

The runner image needs the workspace `shared/` package. Copy it before building:

```bash
cp -r ../shared rpl_runner/shared
```

This directory is gitignored — re-copy it after any upstream changes to `shared/`.

### 2. Build the runner Docker image

```bash
docker build -t rpl-runner:local ./rpl_runner/
```

### 3. Start the runner container

```bash
docker run -d --name rpl-runner-local -p 8002:8000 rpl-runner:local
# Verify:
curl http://localhost:8002/health   # should return "pong"
```

### 4. Install Celery worker dependencies

```bash
pip install -r requirements.txt
```

### 5. Start the Celery worker

```bash
URL_RUNNER=http://localhost:8002 python -m dotenv -f .env run -- \
  celery -A celery_app worker --loglevel=info -c 2
```

Key environment variables (set in `.env` or overridden on the command line):

| Variable | Default | Description |
|---|---|---|
| `QUEUE_URL` | `amqp://guest:guest@localhost:5672` | RabbitMQ connection |
| `URL_RPL_BACKEND` | `http://localhost:8080` | Activities API base URL — **must be `http://localhost:8001`** for local dev |
| `API_KEY` | `test_api_key` | Must match `RUNNER_API_KEY` in Activities API `.env` |
| `URL_RUNNER` | `http://runner:8000` | Runner Flask server — **must be `http://localhost:8002`** for local dev |

The `.env` file in this directory already sets `URL_RPL_BACKEND=http://localhost:8001` and `API_KEY=local_runner_api_key`. `URL_RUNNER` must be passed explicitly since it defaults to the Docker hostname `runner`.

## Stopping

```bash
# Stop the Celery worker with Ctrl+C, then:
docker rm -f rpl-runner-local
```

## Testing

```bash
python -m pytest
```
