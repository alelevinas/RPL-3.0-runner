# RPL-3.0-runner

## What This Is

Two-part system that executes student code submissions:
1. **Receiver** (`rabbitmq_receive.py`): Consumes submission jobs from RabbitMQ, calls the runner, reports results back to the Activities API.
2. **Runner** (`rpl_runner/`): A Flask/Gunicorn server inside a Docker container with compilers/interpreters for C, Python, Go, Rust, and Java. Executes student code against unit tests and I/O tests.

## Project Structure

```
RPL-3.0-runner/
├── rabbitmq_receive.py            # RabbitMQ consumer (entry point for receiver)
├── rabbitmq_send.py               # Test utility to publish messages
├── receiver.py                    # Core logic: fetch submission, run tests, report results
├── config.py                      # Environment config
├── requirements.txt               # Python deps for receiver (requests, pika)
├── Dockerfile                     # Receiver container (Python 3.7-alpine)
├── docker-compose.local.yml       # Local integration testing
├── rpl_runner/
│   ├── Dockerfile                 # Runner container (Ubuntu with gcc, go, python, rust)
│   ├── init_server.py             # Flask app entry point
│   ├── runner.py                  # Main runner logic
│   ├── c_runner.py                # C-specific test execution
│   ├── python_runner.py           # Python-specific test execution
│   ├── go_runner.py               # Go-specific test execution
│   ├── rust_runner.py             # Rust-specific test execution
│   ├── *_Makefile                 # Language-specific Makefiles
│   ├── *_parser.py                # Output parsers for test frameworks
│   └── runner-libs/               # Test framework libraries (criterion, etc.)
└── kubernetes/                    # K8s deployment manifests
```

## How It Works

1. Activities API publishes a message to RabbitMQ with a submission ID.
2. Receiver picks up the message, fetches submission metadata from Activities API.
3. Receiver sends the code + tests to the Runner container via HTTP.
4. Runner compiles/runs the code, executes tests, returns results.
5. Receiver posts results back to Activities API.

## Running Locally

The runner is designed to run as Docker containers. For local integration testing:

```bash
# Requires RPL-3.0 metaservices (MySQL + RabbitMQ) to be running first
docker compose -f docker-compose.local.yml up -d --build
```

The receiver Python code can be run directly for development:
```bash
pip install -r requirements.txt
python rabbitmq_receive.py
```

## Dependencies on Other Repos

- **RPL-3.0** (Activities API): Fetches submission data via HTTP, posts results back.
- Uses `RUNNER_API_KEY` for authentication with the Activities API.
- Shares RabbitMQ queue with Activities API (queue name: configurable via `QUEUE_ACTIVITIES_NAME`).

## Supported Languages

| Language | Runner File | Test Framework | Makefile |
|----------|------------|----------------|----------|
| C | `c_runner.py` | Criterion | `c_Makefile` |
| Python | `python_runner.py` | unittest | `python_Makefile` |
| Go | `go_runner.py` | testify | `go_Makefile` |
| Rust | `rust_runner.py` | cargo test + nextest | `rust_Makefile` |

## Agent Tasks

Useful work an agent can do:
- **Add unit tests**: The receiver and runner have no automated tests. Add pytest tests for `receiver.py` logic (mock HTTP calls and RabbitMQ).
- **Update Python version**: Receiver Dockerfile uses Python 3.7 (EOL). Update to 3.13.
- **Update dependencies**: `requests` and `pika` versions are pinned to old versions.
- **Add Java runner**: The runner supports C, Python, Go, Rust but Java support is incomplete.
- **Error handling**: Improve error reporting when compilation fails or tests time out.
- **Logging**: Add structured logging to the receiver for better observability.
