# RPL-3.0-runner

Celery-based worker that processes student code submissions in isolated Docker containers.

## Architecture

```
RabbitMQ → Celery worker (celery_app.py)
               └─▶ receiver.py builds tar, POSTs to runner Flask server
                       └─▶ runner_server/ Flask server (inside Docker container)
                               └─▶ language runner (runners/c_runner.py, runners/python_runner.py, …)
                                       └─▶ compile + execute student code
               └─▶ POST results back to Activities API
```

The **runner Flask server** (`runner_server/server.py`) runs inside a Docker image that has gcc, Python, Go, Rust, and Java installed. The Celery worker is a thin coordinator that fetches submission metadata, builds the tar, and delegates execution to that container.

## Project Structure

```
RPL-3.0-runner/
├── celery_app.py            # Celery application and task definition
├── receiver.py              # Core logic: fetch data, call runner, report results
├── prewarmer.py             # Logic for managing pre-started containers
├── config.py                # Environment configuration
├── requirements.txt
├── Dockerfile               # Celery worker image (Python 3.13-alpine)
├── docker-compose.local.yml
│
├── runner_server/           # Code that runs INSIDE the Docker container
│   ├── Dockerfile           # Base image (Ubuntu Noble + gcc, Python, Go, Rust)
│   ├── server.py            # Flask app receiving code tars (entrypoint)
│   ├── executor.py          # Orchestrates extraction, runner selection, result collection
│   ├── logger.py
│   ├── runners/             # Language-specific runners
│   │   ├── runner.py        # Base Runner class (lint → build → run lifecycle)
│   │   ├── c_runner.py
│   │   ├── python_runner.py
│   │   ├── go_runner.py
│   │   └── rust_runner.py
│   ├── parsers/             # Test output parsers
│   │   ├── go_parser.py
│   │   └── rust_parser.py
│   ├── makefiles/           # Per-language Makefiles (copied into the submission dir)
│   │   ├── c_Makefile
│   │   ├── python_Makefile
│   │   ├── go_Makefile
│   │   └── rust_Makefile
│   ├── libs/                # Pre-built test framework libraries
│   │   ├── c/               # Criterion (pre-compiled)
│   │   ├── python/          # custom_IO_main.py, unit_test_wrapper.py
│   │   └── java/            # JUnit JARs
│   └── shared/              # Pydantic DTOs and enums (copied from workspace shared/)
│
└── tests/
    ├── conftest.py
    ├── test_receiver.py
    ├── test_prewarmer.py
    ├── test_executor.py     # Unit tests: parsers, executor helpers, Flask health
    ├── test_lint.py         # Unit tests: lint phase (mocked)
    ├── test_integration.py  # Layer 2: end-to-end executor.process() per language
    └── fixtures/            # Source code fixtures for integration tests
        ├── python/{io,unit}/
        ├── c/{io,unit}/
        ├── go/{io,unit}/
        └── rust/{io,unit}/
```

## Prerequisites

- Docker Desktop
- Python 3.13 (via pyenv)
- `python-dotenv` CLI: `pip install python-dotenv`
- RabbitMQ running (see workspace `docker-compose.infra.yml`)
- Activities API running on port 8001

### Installing Python 3.13 with pyenv

```bash
# Install pyenv (if not already installed)
brew install pyenv

# Install Python 3.13
pyenv install 3.13

# Set it as the local version for this directory
pyenv local 3.13

# Verify
python --version   # should print Python 3.13.x
```

Add this to your shell profile if `pyenv` isn't initialising automatically:
```bash
export PYENV_ROOT="$HOME/.pyenv"
eval "$(pyenv init -)"
```

## Local Setup

### 1. Copy the shared module into the build context

The runner image needs the workspace `shared/` package. Copy it before building:

```bash
cp -r ../shared runner_server/shared
```

This directory is gitignored — re-copy it after any upstream changes to `shared/`.

### 2. Build the runner Docker image

```bash
docker build -t rpl-runner:local ./runner_server/
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
# Unit + integration tests (no Docker needed):
python -m pytest

# Integration tests only:
python -m pytest -m integration

# Unit tests only (fastest, no compilers needed):
python -m pytest -m "not integration"
```

See [TESTING.md](TESTING.md) for the full testing strategy.
