# RPL-3.0-runner Improvements

Proposed improvements for the RPL-3.0-runner.
**Scoring:** 1 (Low) to 5 (High). C: Complexity, R: Risk.

## 1. Architecture & Performance
*   **Task Queue Framework:** Use Celery with RabbitMQ. This provides built-in retries, visibility, and worker management. This is much more robust for high-load student submissions than current manual scripts.
    *   **C: 4 | R: 3**
*   **Worker Concurrency:** Use Python's `multiprocessing` or Celery's `-c` flag to process multiple submissions in parallel based on CPU cores. This allows the cheap VPS to handle more concurrent runs.
    *   **C: 2 | R: 2**
*   **Pre-warmed Containers:** Maintain a small pool of pre-started, paused Docker containers for popular languages like C and Python. This eliminates the 1-2s container startup latency for students.
    *   **C: 5 | R: 4**
*   **Result JSON Schema:** Define a strict Pydantic/JSON schema for submission results. Shared as a Git submodule or private package between the Runner and the Backend.
    *   **C: 3 | R: 2**

## 2. Features: "Common Mistakes" & Analysis
*   **Static Analysis Phase:** Add a step to run `cppcheck` (for C) or `pylint` (for Python) on the submission. Report found issues (e.g., "Potential Buffer Overflow") back to the student.
    *   **C: 3 | R: 2**
*   **Regex-based Error Extraction:** Use a set of regex patterns to extract line numbers and error types from `stdout/stderr`. This allows the UI to point exactly to the broken line in the code editor.
    *   **C: 3 | R: 2**
*   **Rust/Go/Java Finalization:** Complete the Docker image setup for these languages. Ensure they follow the same "Mistake Engine" patterns for consistent feedback.
    *   **C: 3 | R: 1**

## 3. Documentation
*   **README Revamp:** Systematic "search and replace" for "RPL-3.0" and outdated setup steps. Verify every command in the README works in a fresh clone.
    *   **C: 1 | R: 1**
*   **Language Addition Guide:** Step-by-step documentation on how to add support for a new language (e.g., adding Docker layers, creating the parser/runner).
    *   **C: 2 | R: 1**
*   **Security Model Docs:** Document the Docker-in-Docker isolation, CPU/Memory limits per run, and network isolation to ensure maintainers understand how security is handled.
    *   **C: 2 | R: 1**

## 4. Testing
*   **Runner Unit Tests:** Use `pytest` to test the individual language runners (e.g., `c_runner.py`) using mocked execution results to verify that result parsing is correct.
    *   **C: 3 | R: 1**
*   **Known Failures Integration:** Create a library of code samples that "Fail" in specific ways (e.g., Timeout, Segfault, Leak). Verify that the runner correctly identifies each case.
    *   **C: 3 | R: 2**
*   **Security Audit (Trivy):** Run `trivy` on the runner Docker images in CI to scan for vulnerabilities in the base OS and language compilers/runtimes.
    *   **C: 2 | R: 1**

## 5. DX & CD
*   **Base Image Optimization:** Use multi-stage builds and `alpine` or `debian-slim` to reduce the runner's Docker image size. This speeds up deployment and saves disk space on the cheap VPS.
    *   **C: 3 | R: 2**
*   **Health Checks & Heartbeat:** Implement a simple API or RabbitMQ message that the Runner sends every minute to signify it's healthy. This allows the Activities API to show "Runner Offline" if needed.
    *   **C: 2 | R: 2**
