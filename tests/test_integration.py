"""
Layer 2 integration tests: call executor.process() end-to-end with real source files.

Each test builds a tar archive from fixture source files, patches the runner's
generate_files() to use local makefiles (instead of Docker's /), and asserts on
the returned TestsExecutionLogDTO dict.

Run with:
    pytest tests/test_integration.py -v -m integration

All tests are marked @pytest.mark.integration and skipped when the required
language toolchain is not on PATH. For full coverage, run these tests inside
the Docker container built from runner_server/Dockerfile.
"""

import os
import shutil
import sys
import tarfile
import tempfile

import pytest

# conftest.py adds runner_server/ and its subdirs to sys.path
from executor import process
from python_runner import PythonRunner
from c_runner import CRunner
from go_runner import GoRunner
from rust_runner import RustRunner

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FIXTURES = os.path.join(REPO_ROOT, "tests", "fixtures")
MAKEFILES = os.path.join(REPO_ROOT, "runner_server", "makefiles")
LIBS_PYTHON = os.path.join(REPO_ROOT, "runner_server", "libs", "python")

# TestsExecutionResultStatus.SUCCESS has string value "OK"
STATUS_OK = "OK"
STATUS_ERROR = "ERROR"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _has_cmd(*cmds):
    return all(shutil.which(c) is not None for c in cmds)


def _build_tar(fixture_dir: str, dest_path: str):
    """Pack all files under fixture_dir (flat) into a .tar archive."""
    with tarfile.open(dest_path, "w") as tar:
        for name in os.listdir(fixture_dir):
            full = os.path.join(fixture_dir, name)
            if os.path.isfile(full):
                tar.add(full, arcname=name)


def _build_tar_recursive(fixture_dir: str, dest_path: str):
    """Pack all files (including subdirs) under fixture_dir into a .tar archive."""
    with tarfile.open(dest_path, "w") as tar:
        for root, dirs, files in os.walk(fixture_dir):
            for fname in files:
                full = os.path.join(root, fname)
                arcname = os.path.relpath(full, fixture_dir)
                tar.add(full, arcname=arcname)


def _patch_python_generate(monkeypatch, test_type):
    """
    Override PythonRunner.generate_files to write a test-compatible Makefile
    and copy the required Python lib files, using the local Python interpreter
    instead of Docker's hardcoded /usr/bin/python3.10.
    """
    interp = sys.executable

    def fake_generate(self):
        if test_type == "IO":
            makefile = (
                f"ARCHIVOS = $(wildcard *.py)\n\n"
                f"build_io: $(ARCHIVOS)\n"
                f"\t@true\n\n"
                f"run:\n"
                f"\t{interp} custom_IO_main.py\n"
            )
            shutil.copy(os.path.join(LIBS_PYTHON, "custom_IO_main.py"), self.path)
        else:
            makefile = (
                f"ARCHIVOS = $(wildcard *.py)\n\n"
                f"build_unit_test: $(ARCHIVOS)\n"
                f"\t@true\n\n"
                f"run_unit_test:\n"
                f"\t{interp} unit_test_wrapper.py\n"
            )
            shutil.copy(os.path.join(LIBS_PYTHON, "unit_test_wrapper.py"), self.path)

        with open(os.path.join(self.path, "Makefile"), "w") as f:
            f.write(makefile)

    monkeypatch.setattr(PythonRunner, "generate_files", fake_generate)


def _patch_c_generate(monkeypatch):
    def fake_generate(self):
        shutil.copy(os.path.join(MAKEFILES, "c_Makefile"), os.path.join(self.path, "Makefile"))
    monkeypatch.setattr(CRunner, "generate_files", fake_generate)


def _patch_go_generate(monkeypatch):
    def fake_generate(self):
        shutil.copy(os.path.join(MAKEFILES, "go_Makefile"), os.path.join(self.path, "Makefile"))
        shutil.copy(os.path.join(REPO_ROOT, "runner_server", "go.mod"), self.path)
        shutil.copy(os.path.join(REPO_ROOT, "runner_server", "go.sum"), self.path)
        shutil.copy(os.path.join(REPO_ROOT, "runner_server", "parsers", "go_parser.py"), self.path)
    monkeypatch.setattr(GoRunner, "generate_files", fake_generate)


def _patch_rust_generate(monkeypatch):
    def fake_generate(self):
        shutil.copy(os.path.join(MAKEFILES, "rust_Makefile"), os.path.join(self.path, "Makefile"))
        shutil.copy(os.path.join(REPO_ROOT, "runner_server", "parsers", "rust_parser.py"), self.path)
        shutil.copy(os.path.join(REPO_ROOT, "runner_server", "nextest.toml"), self.path)
        shutil.copy(os.path.join(REPO_ROOT, "runner_server", "Cargo.toml"), self.path)
        shutil.copy(os.path.join(REPO_ROOT, "runner_server", "Cargo.lock"), self.path)
    monkeypatch.setattr(RustRunner, "generate_files", fake_generate)


# ---------------------------------------------------------------------------
# Executor error-handling paths (no compiler needed)
# ---------------------------------------------------------------------------

class TestExecutorErrorPaths:
    """Test executor.process() error-handling without running real student code."""

    def test_unknown_lang_returns_error_status(self):
        with tempfile.NamedTemporaryFile(suffix=".tar", delete=False) as f:
            tar_path = f.name
        try:
            with tarfile.open(tar_path, "w"):
                pass
            result = process("unsupported_lang", "IO", tar_path)
            assert result["tests_execution_result_status"] == STATUS_ERROR
            assert "unsupported_lang" in result["tests_execution_exit_message"]
        finally:
            os.unlink(tar_path)

    def test_empty_tar_does_not_raise(self):
        """An empty submission tar should not crash the executor — it returns a result dict."""
        with tempfile.NamedTemporaryFile(suffix=".tar", delete=False) as f:
            tar_path = f.name
        try:
            with tarfile.open(tar_path, "w"):
                pass
            result = process("python_3.10", "IO", tar_path)
            assert "tests_execution_result_status" in result
        finally:
            os.unlink(tar_path)


# ---------------------------------------------------------------------------
# Python — IO tests
# ---------------------------------------------------------------------------

@pytest.mark.integration
@pytest.mark.skipif(not _has_cmd("python3", "make"), reason="python3 or make not found")
class TestPythonIO:
    def test_successful_run_produces_output(self, monkeypatch):
        _patch_python_generate(monkeypatch, "IO")
        with tempfile.NamedTemporaryFile(suffix=".tar", delete=False) as f:
            tar_path = f.name
        try:
            _build_tar(os.path.join(FIXTURES, "python", "io"), tar_path)
            result = process("python_3.10", "IO", tar_path)
            assert result["tests_execution_result_status"] == STATUS_OK
            assert len(result["all_student_only_outputs_from_iotests_runs"]) == 1
            assert "10" in result["all_student_only_outputs_from_iotests_runs"][0]
        finally:
            os.unlink(tar_path)

    def test_syntax_error_returns_error_status(self, monkeypatch):
        _patch_python_generate(monkeypatch, "IO")
        with tempfile.TemporaryDirectory() as fixture:
            with open(os.path.join(fixture, "assignment_main.py"), "w") as f:
                f.write("def broken(:\n    pass\n")
            shutil.copy(
                os.path.join(FIXTURES, "python", "io", "IO_test_1"),
                os.path.join(fixture, "IO_test_1"),
            )
            with tempfile.NamedTemporaryFile(suffix=".tar", delete=False) as tf:
                tar_path = tf.name
            try:
                _build_tar(fixture, tar_path)
                result = process("python_3.10", "IO", tar_path)
                assert result["tests_execution_result_status"] in (STATUS_ERROR, "TIME_OUT")
            finally:
                os.unlink(tar_path)


# ---------------------------------------------------------------------------
# Python — unit tests
# ---------------------------------------------------------------------------

@pytest.mark.integration
@pytest.mark.skipif(not _has_cmd("python3", "make"), reason="python3 or make not found")
class TestPythonUnit:
    def _run_unit(self, monkeypatch, fixture_dir):
        _patch_python_generate(monkeypatch, "unit_test")
        with tempfile.NamedTemporaryFile(suffix=".tar", delete=False) as f:
            tar_path = f.name
        try:
            _build_tar(fixture_dir, tar_path)
            return process("python_3.10", "unit_test", tar_path)
        finally:
            os.unlink(tar_path)

    def test_passing_unit_tests(self, monkeypatch):
        with tempfile.TemporaryDirectory() as tmp:
            shutil.copy(os.path.join(FIXTURES, "python", "unit", "assignment_main.py"), tmp)
            shutil.copy(
                os.path.join(FIXTURES, "python", "unit", "unit_test.py"),
                os.path.join(tmp, "unit_test.py"),
            )
            result = self._run_unit(monkeypatch, tmp)
        assert result["tests_execution_result_status"] == STATUS_OK
        summary = result.get("unit_test_suite_result_summary")
        if summary:
            assert summary["amount_passed"] == 2
            assert summary["amount_failed"] == 0

    def test_failing_unit_tests_still_success_execution(self, monkeypatch):
        """Runner itself succeeds; test failures are reported inside the summary."""
        with tempfile.TemporaryDirectory() as tmp:
            shutil.copy(os.path.join(FIXTURES, "python", "unit", "assignment_main.py"), tmp)
            shutil.copy(
                os.path.join(FIXTURES, "python", "unit", "unit_test_failing.py"),
                os.path.join(tmp, "unit_test.py"),
            )
            result = self._run_unit(monkeypatch, tmp)
        assert result["tests_execution_result_status"] == STATUS_OK
        summary = result.get("unit_test_suite_result_summary")
        if summary:
            assert summary["amount_failed"] >= 1


# ---------------------------------------------------------------------------
# C — IO tests
# ---------------------------------------------------------------------------

@pytest.mark.integration
@pytest.mark.skipif(not _has_cmd("gcc", "make"), reason="gcc or make not found")
class TestCIO:
    def test_successful_run(self, monkeypatch):
        _patch_c_generate(monkeypatch)
        with tempfile.NamedTemporaryFile(suffix=".tar", delete=False) as f:
            tar_path = f.name
        try:
            _build_tar(os.path.join(FIXTURES, "c", "io"), tar_path)
            result = process("c_std11", "IO", tar_path)
            assert result["tests_execution_result_status"] == STATUS_OK
            assert len(result["all_student_only_outputs_from_iotests_runs"]) == 1
            assert "10" in result["all_student_only_outputs_from_iotests_runs"][0]
        finally:
            os.unlink(tar_path)

    def test_compile_error_returns_error_status(self, monkeypatch):
        _patch_c_generate(monkeypatch)
        with tempfile.TemporaryDirectory() as fixture:
            with open(os.path.join(fixture, "main.c"), "w") as f:
                f.write("int main(void { return 0; }\n")  # syntax error
            shutil.copy(
                os.path.join(FIXTURES, "c", "io", "IO_test_1"),
                os.path.join(fixture, "IO_test_1"),
            )
            with tempfile.NamedTemporaryFile(suffix=".tar", delete=False) as tf:
                tar_path = tf.name
            try:
                _build_tar(fixture, tar_path)
                result = process("c_std11", "IO", tar_path)
                assert result["tests_execution_result_status"] == STATUS_ERROR
                assert result["tests_execution_stage"] == "BUILD"
            finally:
                os.unlink(tar_path)


# ---------------------------------------------------------------------------
# C — unit tests (requires Criterion from runner-libs/)
# ---------------------------------------------------------------------------

def _has_criterion():
    return os.path.exists("/usr/include/criterion/criterion.h") and _has_cmd("gcc", "make")


@pytest.mark.integration
@pytest.mark.skipif(not _has_criterion(), reason="Criterion not installed — run inside Docker")
class TestCUnit:
    def test_passing_unit_tests(self, monkeypatch):
        _patch_c_generate(monkeypatch)
        with tempfile.NamedTemporaryFile(suffix=".tar", delete=False) as f:
            tar_path = f.name
        try:
            _build_tar(os.path.join(FIXTURES, "c", "unit"), tar_path)
            result = process("c_std11", "unit_test", tar_path)
            assert result["tests_execution_result_status"] == STATUS_OK
            summary = result.get("unit_test_suite_result_summary")
            if summary:
                assert summary["amount_passed"] == 2
        finally:
            os.unlink(tar_path)

    def test_failing_unit_tests_still_success_execution(self, monkeypatch):
        _patch_c_generate(monkeypatch)
        with tempfile.TemporaryDirectory() as fixture:
            shutil.copy(os.path.join(FIXTURES, "c", "unit", "main.c"), fixture)
            with open(os.path.join(fixture, "unit_test.c"), "w") as f:
                f.write(
                    '#include <criterion/criterion.h>\n'
                    '#include "main.c"\n'
                    'Test(fail, test_wrong) { cr_assert_eq(add(2,3), 999); }\n'
                )
            with tempfile.NamedTemporaryFile(suffix=".tar", delete=False) as tf:
                tar_path = tf.name
            try:
                _build_tar(fixture, tar_path)
                result = process("c_std11", "unit_test", tar_path)
                assert result["tests_execution_result_status"] == STATUS_OK
                summary = result.get("unit_test_suite_result_summary")
                if summary:
                    assert summary["amount_failed"] >= 1
            finally:
                os.unlink(tar_path)


# ---------------------------------------------------------------------------
# Go — IO tests
# ---------------------------------------------------------------------------

@pytest.mark.integration
@pytest.mark.skipif(not _has_cmd("go", "make"), reason="go or make not found")
class TestGoIO:
    def test_successful_run(self, monkeypatch):
        _patch_go_generate(monkeypatch)
        with tempfile.NamedTemporaryFile(suffix=".tar", delete=False) as f:
            tar_path = f.name
        try:
            _build_tar(os.path.join(FIXTURES, "go", "io"), tar_path)
            result = process("go_1.19", "IO", tar_path)
            assert result["tests_execution_result_status"] == STATUS_OK
            assert len(result["all_student_only_outputs_from_iotests_runs"]) == 1
            assert "10" in result["all_student_only_outputs_from_iotests_runs"][0]
        finally:
            os.unlink(tar_path)


# ---------------------------------------------------------------------------
# Go — unit tests
# ---------------------------------------------------------------------------

@pytest.mark.integration
@pytest.mark.skipif(not _has_cmd("go", "make"), reason="go or make not found")
class TestGoUnit:
    def test_passing_unit_tests(self, monkeypatch):
        _patch_go_generate(monkeypatch)
        with tempfile.NamedTemporaryFile(suffix=".tar", delete=False) as f:
            tar_path = f.name
        try:
            _build_tar(os.path.join(FIXTURES, "go", "unit"), tar_path)
            result = process("go_1.19", "unit_test", tar_path)
            assert result["tests_execution_result_status"] == STATUS_OK
            summary = result.get("unit_test_suite_result_summary")
            if summary:
                assert summary["amount_passed"] == 2
        finally:
            os.unlink(tar_path)


# ---------------------------------------------------------------------------
# Rust — IO tests (requires cargo + cargo-nextest)
# ---------------------------------------------------------------------------

def _has_rust():
    return _has_cmd("cargo", "make") and shutil.which("cargo-nextest") is not None


@pytest.mark.integration
@pytest.mark.skipif(not _has_rust(), reason="cargo/nextest not found — run inside Docker")
class TestRustIO:
    def test_successful_run(self, monkeypatch):
        _patch_rust_generate(monkeypatch)
        with tempfile.NamedTemporaryFile(suffix=".tar", delete=False) as f:
            tar_path = f.name
        try:
            _build_tar_recursive(os.path.join(FIXTURES, "rust", "io"), tar_path)
            result = process("rust_1.88.0", "IO", tar_path)
            assert result["tests_execution_result_status"] == STATUS_OK
        finally:
            os.unlink(tar_path)


# ---------------------------------------------------------------------------
# Rust — unit tests
# ---------------------------------------------------------------------------

@pytest.mark.integration
@pytest.mark.skipif(not _has_rust(), reason="cargo/nextest not found — run inside Docker")
class TestRustUnit:
    def test_passing_unit_tests(self, monkeypatch):
        _patch_rust_generate(monkeypatch)
        with tempfile.NamedTemporaryFile(suffix=".tar", delete=False) as f:
            tar_path = f.name
        try:
            _build_tar_recursive(os.path.join(FIXTURES, "rust", "unit"), tar_path)
            result = process("rust_1.88.0", "unit_test", tar_path)
            assert result["tests_execution_result_status"] == STATUS_OK
            summary = result.get("unit_test_suite_result_summary")
            if summary:
                assert summary["amount_passed"] == 2
        finally:
            os.unlink(tar_path)
