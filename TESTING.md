# Testing Strategy — RPL-3.0-runner

## Layers

### Layer 1 — Unit tests (no compiler, no Docker)

Pure logic tests that mock all subprocess and Docker calls.

| File | What it covers |
|---|---|
| `test_executor.py` | `parse_student_only_outputs_from_runs`, `get_custom_unit_test_results_json`, `sanitize_rust_stderr`, `get_unit_test_results`, Go/Rust parsers, Flask `/health` endpoint |
| `test_lint.py` | Lint phase: verifies `CRunner` invokes `cppcheck`, `PythonRunner` invokes `pylint` |
| `test_receiver.py` | Tar building per language, HTTP calls (get metadata, update status, post exec log), full flow |
| `test_prewarmer.py` | Container pool lifecycle (create, pause, unpause, refill, cleanup) |

Run with:
```bash
pytest -m "not integration"
```

### Layer 2 — Integration tests (compilers required, no Docker)

Tests call `executor.process()` end-to-end using real source files from `tests/fixtures/`. Each test patches the runner's `generate_files()` to use local makefiles instead of Docker's `/` paths.

| Class | Language | Test type | Requires |
|---|---|---|---|
| `TestExecutorErrorPaths` | — | error paths | nothing |
| `TestPythonIO` | Python | IO | `python3`, `make` |
| `TestPythonUnit` | Python | unit | `python3`, `make` |
| `TestCIO` | C | IO | `gcc`, `make` |
| `TestCUnit` | C | unit | `gcc`, `make`, Criterion library |
| `TestGoIO` | Go | IO | `go`, `make` |
| `TestGoUnit` | Go | unit | `go`, `make` |
| `TestRustIO` | Rust | IO | `cargo`, `cargo-nextest` |
| `TestRustUnit` | Rust | unit | `cargo`, `cargo-nextest` |

Tests that require tools not on `PATH` are automatically skipped. `TestCUnit` and `TestRust*` require the full Docker image environment since they depend on Criterion (custom-built) and cargo-nextest.

Run all integration tests:
```bash
pytest -m integration -v
```

Run inside Docker for full coverage:
```bash
docker run --rm -v $(pwd):/app rpl-runner:local \
  bash -c "pip install pytest pytest-mock && cd /app && python -m pytest -m integration -v"
```

### Layer 3 — E2E tests (Docker required)

Spin up the Flask server (`runner_server/server.py`) in a real container, POST a tar to it, verify the JSON response. One test per language is sufficient since the execution path is covered by Layer 2.

Not yet implemented. Suggested tooling: `pytest` + `requests` + a fixture that starts the Docker container on a random port.

## Fixture Source Files

```
tests/fixtures/
  python/io/          assignment_main.py (reads int, prints n*2), IO_test_1 (input: 5)
  python/unit/        assignment_main.py (add, multiply), unit_test.py, unit_test_failing.py
  c/io/               main.c (reads int, prints n*2), IO_test_1
  c/unit/             main.c (add, multiply functions), unit_test.c (Criterion tests)
  go/io/              main.go (reads int, prints n*2), IO_test_1
  go/unit/            main.go (Add, Multiply), unit_test.go (stdlib testing)
  rust/io/            src/main.rs (reads int, prints n*2), IO_test_1
  rust/unit/          src/lib.rs (add, multiply), tests/unit_test.rs
```

All fixtures follow the same contract: for IO tests, input `5` → output `10`.

## CI

GitHub Actions runs `pytest -m "not integration"` (Layer 1) on every push — no Docker or compilers needed.

To add Layer 2 to CI, use a job with the `rpl-runner:local` image as the test runner, which has all required toolchains pre-installed.
