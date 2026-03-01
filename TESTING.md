# Runner Testing Plan (RPL-3.0-runner)

Testing strategy for the code execution worker and isolated runners.

## 1. Unit & Logic Tests (Current)
- **Tool**: `pytest`
- **Scope**: `receiver.py`, `prewarmer.py`, parsers (`go_parser`, `rust_parser`).
- **LINT Testing**: `tests/test_lint.py` (added recently).

## 2. Gaps & Improvements (Target)

### 2.1. Isolated Runner Verification
We need to verify that each language runner (C, Python, Go, Rust, Java) correctly executes code within a container and returns standardized results.
- **Plan**: Use `subprocess` to run a local mock container and check output.

### 2.2. Pre-warmed Container Pool
Ensure the `Prewarmer` correctly manages the container lifecycle.
- **Plan**: Stress test the pre-warmer with high concurrency and verify that no containers are leaked.

### 2.3. Celery Integration
Verify that RabbitMQ messages correctly trigger worker tasks.
- **Plan**: Integration test using `celery[pytest]`.

## 3. GitHub Actions Workflow (`.github/workflows/pytest.yml`)

The workflow must include:
1. **Docker Setup**: Needs `docker` and `docker-compose`.
2. **Execution**: `python -m pytest tests/`.
3. **Language Matrix**: Verify that each language runner (C, Python, etc.) can be built and run.

## 4. Test Categories

- **Parser Tests**: JSON/Text output parsing from compiler/test runners.
- **Logic Tests**: Container URL retrieval and refill logic.
- **Execution Tests**: Real code submission execution (requires Docker).
