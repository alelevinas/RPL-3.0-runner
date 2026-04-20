# RPL-3.0-runner (Code Execution)

## What This Is

A high-performance code execution system that uses Celery and RabbitMQ to process student submissions in isolated Docker containers.

## Architecture

1. **Celery Worker (`celery_app.py`):** Consumes `process_submission` tasks from RabbitMQ.
2. **Prewarmer (`prewarmer.py`):** Maintains a pool of pre-started, paused Docker containers to eliminate startup latency.
3. **Receiver (`receiver.py`):** Fetches submission metadata from the Activities API and manages the execution flow.
4. **Runner Server (`runner_server/`):** Flask server + language runners inside Docker containers. Handles compilation and test execution for C, Python, Go, and Rust.

## Key Boundaries

- **Host side** (`celery_app.py`, `receiver.py`, `prewarmer.py`): Python 3.13, communicates with Docker and the Activities API via HTTP.
- **Container side** (`runner_server/`): Ubuntu Noble with gcc, Python, Go, Rust. All `.py` runner files and `*_Makefile` files are copied **flat** to `/` inside the container, which is why imports between them use bare module names (e.g., `from runner import Runner`).

## Supported Languages

| Key | Runner | Test frameworks |
|---|---|---|
| `c_std11` | `runners/c_runner.py` | Criterion v2 (unit), IO |
| `python_3.10` | `runners/python_runner.py` | unittest (unit), IO |
| `go_1.19` | `runners/go_runner.py` | stdlib testing (unit), IO |
| `rust_1.88.0` | `runners/rust_runner.py` | cargo-nextest / JUnit XML (unit), IO |

## Project Structure

```
RPL-3.0-runner/
├── celery_app.py, receiver.py, prewarmer.py, config.py   (host-side worker)
├── runner_server/
│   ├── server.py          Flask entrypoint (gunicorn server:app)
│   ├── executor.py        Orchestrates tar extraction, runner dispatch, result collection
│   ├── runners/           Base Runner class + language-specific subclasses
│   ├── parsers/           go_parser.py, rust_parser.py
│   ├── makefiles/         *_Makefile per language (copied into submission workdir)
│   ├── libs/              Pre-built test framework files (Criterion, JUnit, Python wrappers)
│   └── shared/            Pydantic DTOs + enums (synced from workspace shared/)
└── tests/
    ├── test_executor.py, test_lint.py, test_receiver.py, test_prewarmer.py
    ├── test_integration.py   Layer 2: executor.process() per language × test type
    └── fixtures/             Source code fixtures used by integration tests
```

## Running Tests

```bash
make test                          # all tests (Layer 1 + Layer 2 where tools available)
pytest -m "not integration"        # Layer 1 only (fastest, no compilers needed)
pytest -m integration -v           # Layer 2 only
```

## Agent Tasks

Useful work an agent can do:

- **Add a new language** (e.g., Java): add `java_runner.py` in `runners/`, a `java_Makefile` in `makefiles/`, update `custom_runners` dict in `executor.py`, add fixtures in `tests/fixtures/java/`, add `TestJavaIO` / `TestJavaUnit` classes in `test_integration.py`.
- **Improve error extraction**: expand regex patterns in `runner_server/shared/mistake_matcher.py` for better student-facing hints.
- **Security audit**: scan `runner_server/Dockerfile` base image for CVEs.
- **Layer 3 E2E tests**: implement Docker-based end-to-end tests as described in `TESTING.md`.
