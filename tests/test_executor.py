"""Tests for runner_server/ executor code — parsers, executor.py helpers, and Flask server."""

import io
import json
import os
import tempfile
import textwrap

import pytest

# These imports work because conftest.py adds runner_server/ and its subdirs to sys.path
from executor import (
    parse_student_only_outputs_from_runs,
    get_custom_unit_test_results_json,
    sanitize_rust_stderr,
)
import go_parser
import rust_parser
import server as init_server


# ---------------------------------------------------------------------------
# parse_student_only_outputs_from_runs
# ---------------------------------------------------------------------------

class TestParseStudentOutputs:
    def test_single_run(self):
        log = "start_RUN\nHello, World!\nend_RUN\n"
        result = parse_student_only_outputs_from_runs(log)
        assert result == ["Hello, World!"]

    def test_multiple_runs(self):
        log = (
            "start_RUN\noutput1\nend_RUN\n"
            "start_RUN\noutput2\nend_RUN\n"
        )
        result = parse_student_only_outputs_from_runs(log)
        assert result == ["output1", "output2"]

    def test_no_runs(self):
        log = "some random log output\n"
        result = parse_student_only_outputs_from_runs(log)
        assert result == []

    def test_multiline_output(self):
        log = "start_RUN\nline1\nline2\nline3\nend_RUN\n"
        result = parse_student_only_outputs_from_runs(log)
        assert result == ["line1\nline2\nline3"]

    def test_skips_makefile_noise(self):
        log = "start_RUN\n./main\nHello\nend_RUN\n"
        result = parse_student_only_outputs_from_runs(log)
        assert result == ["Hello"]

    def test_empty_output_between_delimiters(self):
        log = "start_RUN\nend_RUN\n"
        result = parse_student_only_outputs_from_runs(log)
        assert result == [""]


# ---------------------------------------------------------------------------
# get_custom_unit_test_results_json (Criterion C test output)
# ---------------------------------------------------------------------------

class TestCriterionParser:
    def test_parses_passing_tests(self):
        criterion_output = json.dumps({
            "passed": 2,
            "failed": 0,
            "errored": 0,
            "test_suites": [{
                "tests": [
                    {"name": "test_add", "status": "PASSED", "messages": []},
                    {"name": "test_sub", "status": "PASSED", "messages": []},
                ]
            }]
        })
        result = get_custom_unit_test_results_json(criterion_output)
        assert result["amount_passed"] == 2
        assert result["amount_failed"] == 0
        assert len(result["single_test_reports"]) == 2

    def test_parses_failed_tests_with_messages(self):
        criterion_output = json.dumps({
            "passed": 0,
            "failed": 1,
            "errored": 0,
            "test_suites": [{
                "tests": [
                    {"name": "test_fail", "status": "FAILED", "messages": ["expected 1", "got 2"]},
                ]
            }]
        })
        result = get_custom_unit_test_results_json(criterion_output)
        assert result["amount_failed"] == 1
        assert result["single_test_reports"][0]["messages"] == "expected 1;    got 2"

    def test_handles_errored_tests(self):
        criterion_output = json.dumps({
            "passed": 0,
            "failed": 0,
            "errored": 1,
            "test_suites": [{
                "tests": [
                    {"name": "test_crash", "status": "ERRORED", "messages": ["segfault"]},
                ]
            }]
        })
        result = get_custom_unit_test_results_json(criterion_output)
        assert result["amount_errored"] == 1


# ---------------------------------------------------------------------------
# sanitize_rust_stderr
# ---------------------------------------------------------------------------

class TestSanitizeRustStderr:
    def test_removes_cargo_exit_noise(self):
        result = {
            "tests_execution_stderr": "real error\nmake: [Makefile:24: run_unit_test] Error 100 (ignored)\nmore output"
        }
        sanitize_rust_stderr("rust_1.88.0", result)
        assert "Error 100 (ignored)" not in result["tests_execution_stderr"]
        assert "real error" in result["tests_execution_stderr"]

    def test_no_op_for_non_rust(self):
        result = {
            "tests_execution_stderr": "make: [Makefile:24: run_unit_test] Error 100 (ignored)"
        }
        sanitize_rust_stderr("c_std11", result)
        assert "Error 100 (ignored)" in result["tests_execution_stderr"]

    def test_no_op_when_pattern_absent(self):
        result = {"tests_execution_stderr": "clean output"}
        sanitize_rust_stderr("rust_1.88.0", result)
        assert result["tests_execution_stderr"] == "clean output"


# ---------------------------------------------------------------------------
# go_parser.parse
# ---------------------------------------------------------------------------

class TestGoParser:
    def test_parses_passing_tests(self):
        lines = [
            "=== RUN   TestAdd",
            "--- PASS: TestAdd (0.00s)",
            "=== RUN   TestSub",
            "--- PASS: TestSub (0.00s)",
            "PASS",
        ]
        result = go_parser.parse(lines)
        assert result["amount_passed"] == 2
        assert result["amount_failed"] == 0
        assert len(result["single_test_reports"]) == 2
        assert result["single_test_reports"][0]["status"] == "PASSED"

    def test_parses_failing_tests(self):
        lines = [
            "=== RUN   TestAdd",
            "    expected 3 got 4",
            "--- FAIL: TestAdd (0.00s)",
            "FAIL",
        ]
        result = go_parser.parse(lines)
        assert result["amount_failed"] == 1
        assert result["single_test_reports"][0]["status"] == "FAILED"
        assert "expected 3 got 4" in result["single_test_reports"][0]["messages"]

    def test_mixed_results(self):
        lines = [
            "=== RUN   TestPass",
            "--- PASS: TestPass (0.00s)",
            "=== RUN   TestFail",
            "    wrong answer",
            "--- FAIL: TestFail (0.00s)",
        ]
        result = go_parser.parse(lines)
        assert result["amount_passed"] == 1
        assert result["amount_failed"] == 1

    def test_empty_input(self):
        result = go_parser.parse([])
        assert result["amount_passed"] == 0
        assert result["single_test_reports"] == []


# ---------------------------------------------------------------------------
# rust_parser.parse_junit
# ---------------------------------------------------------------------------

class TestRustParser:
    def _write_junit_xml(self, tmpdir, content: str) -> str:
        path = os.path.join(tmpdir, "junit.xml")
        with open(path, "w") as f:
            f.write(content)
        return path

    def test_parses_passing_tests(self):
        xml = textwrap.dedent("""\
            <?xml version="1.0" encoding="UTF-8"?>
            <testsuites>
                <testsuite name="tests" tests="2">
                    <testcase name="test_add" time="0.001"/>
                    <testcase name="test_sub" time="0.001"/>
                </testsuite>
            </testsuites>
        """)
        with tempfile.TemporaryDirectory() as tmpdir:
            path = self._write_junit_xml(tmpdir, xml)
            result = rust_parser.parse_junit(path)
            assert result["amount_passed"] == 2
            assert result["amount_failed"] == 0

    def test_parses_failing_tests(self):
        xml = textwrap.dedent("""\
            <?xml version="1.0" encoding="UTF-8"?>
            <testsuites>
                <testsuite name="tests" tests="1">
                    <testcase name="test_fail" time="0.001">
                        <failure message="assertion failed">expected 1, got 2</failure>
                    </testcase>
                </testsuite>
            </testsuites>
        """)
        with tempfile.TemporaryDirectory() as tmpdir:
            path = self._write_junit_xml(tmpdir, xml)
            result = rust_parser.parse_junit(path)
            assert result["amount_failed"] == 1
            assert result["single_test_reports"][0]["status"] == "FAILED"

    def test_strips_backtrace_noise(self):
        xml = textwrap.dedent("""\
            <?xml version="1.0" encoding="UTF-8"?>
            <testsuites>
                <testsuite name="tests" tests="1">
                    <testcase name="test_fail" time="0.001">
                        <failure message="fail">real error note: run with `RUST_BACKTRACE=1` environment variable to display a backtrace</failure>
                    </testcase>
                </testsuite>
            </testsuites>
        """)
        with tempfile.TemporaryDirectory() as tmpdir:
            path = self._write_junit_xml(tmpdir, xml)
            result = rust_parser.parse_junit(path)
            assert "RUST_BACKTRACE" not in result["single_test_reports"][0]["messages"]
            assert "real error" in result["single_test_reports"][0]["messages"]

    def test_mixed_results(self):
        xml = textwrap.dedent("""\
            <?xml version="1.0" encoding="UTF-8"?>
            <testsuites>
                <testsuite name="tests" tests="3">
                    <testcase name="test_pass" time="0.001"/>
                    <testcase name="test_fail" time="0.001">
                        <failure message="fail">wrong</failure>
                    </testcase>
                    <testcase name="test_error" time="0.001">
                        <error message="err">panic</error>
                    </testcase>
                </testsuite>
            </testsuites>
        """)
        with tempfile.TemporaryDirectory() as tmpdir:
            path = self._write_junit_xml(tmpdir, xml)
            result = rust_parser.parse_junit(path)
            assert result["amount_passed"] == 1
            assert result["amount_failed"] == 1
            assert result["amount_errored"] == 1


# ---------------------------------------------------------------------------
# init_server Flask app
# ---------------------------------------------------------------------------

class TestFlaskServer:
    @pytest.fixture
    def client(self):
        init_server.app.config["TESTING"] = True
        init_server.app.config["SECRET_KEY"] = "test-secret"
        with init_server.app.test_client() as client:
            yield client

    def test_health_endpoint(self, client):
        response = client.get("/health")
        assert response.status_code == 200
        assert response.data == b"pong"

    def test_post_rejects_missing_file(self, client):
        response = client.post("/", data={})
        # Flash + redirect pattern
        assert response.status_code == 302

    def test_post_rejects_empty_filename(self, client):
        data = {"file": (io.BytesIO(b""), "")}
        response = client.post("/", data=data, content_type="multipart/form-data")
        assert response.status_code == 302


# ---------------------------------------------------------------------------
# get_custom_unit_test_results_json — additional edge cases
# ---------------------------------------------------------------------------

class TestCriterionParserEdgeCases:
    def test_empty_test_suites_returns_empty_dict(self):
        criterion_output = json.dumps({
            "passed": 0, "failed": 0, "errored": 0,
            "test_suites": []
        })
        result = get_custom_unit_test_results_json(criterion_output)
        assert result == {}

    def test_missing_test_suites_key_returns_empty_dict(self):
        criterion_output = json.dumps({"passed": 0, "failed": 0, "errored": 0})
        result = get_custom_unit_test_results_json(criterion_output)
        assert result == {}

    def test_errored_test_messages_joined(self):
        criterion_output = json.dumps({
            "passed": 0, "failed": 0, "errored": 1,
            "test_suites": [{
                "tests": [
                    {"name": "test_crash", "status": "ERRORED", "messages": ["line1", "line2"]},
                ]
            }]
        })
        result = get_custom_unit_test_results_json(criterion_output)
        assert result["single_test_reports"][0]["messages"] == "line1;    line2"

    def test_passed_test_messages_not_joined(self):
        criterion_output = json.dumps({
            "passed": 1, "failed": 0, "errored": 0,
            "test_suites": [{
                "tests": [
                    {"name": "test_ok", "status": "PASSED", "messages": []},
                ]
            }]
        })
        result = get_custom_unit_test_results_json(criterion_output)
        assert result["single_test_reports"][0]["messages"] == []


# ---------------------------------------------------------------------------
# parse_student_only_outputs_from_runs — additional edge cases
# ---------------------------------------------------------------------------

class TestParseStudentOutputsEdgeCases:
    def test_skips_assignment_main_py_noise(self):
        log = "start_RUN\nassignment_main.py\nHello\nend_RUN\n"
        result = parse_student_only_outputs_from_runs(log)
        assert result == ["Hello"]

    def test_skips_custom_io_main_pyc_noise(self):
        log = "start_RUN\ncustom_IO_main.pyc\nHello\nend_RUN\n"
        result = parse_student_only_outputs_from_runs(log)
        assert result == ["Hello"]

    def test_skips_target_release_noise(self):
        log = "start_RUN\n./target/release/student_package\nHello\nend_RUN\n"
        result = parse_student_only_outputs_from_runs(log)
        assert result == ["Hello"]

    def test_trailing_newline_stripped(self):
        log = "start_RUN\nHello\n\nend_RUN\n"
        result = parse_student_only_outputs_from_runs(log)
        assert result[0].endswith("Hello\n")

    def test_nested_delimiter_names_in_output_ignored(self):
        log = "start_RUN\nstart_BUILD\nend_RUN\n"
        result = parse_student_only_outputs_from_runs(log)
        assert result == ["start_BUILD"]


# ---------------------------------------------------------------------------
# get_unit_test_results — reads real JSON file from tmpdir
# ---------------------------------------------------------------------------

class TestGetUnitTestResults:
    def test_returns_none_when_file_missing(self):
        from executor import get_unit_test_results
        with tempfile.TemporaryDirectory() as tmpdir:
            result = get_unit_test_results(tmpdir, "python_3.10")
            assert result is None

    def test_returns_none_on_invalid_json(self):
        from executor import get_unit_test_results
        with tempfile.TemporaryDirectory() as tmpdir:
            with open(os.path.join(tmpdir, "unit_test_results_output.json"), "w") as f:
                f.write("not valid json {{{")
            result = get_unit_test_results(tmpdir, "python_3.10")
            assert result is None

    def test_parses_python_unit_test_json(self):
        from executor import get_unit_test_results
        payload = json.dumps({
            "amount_passed": 1,
            "amount_failed": 0,
            "amount_errored": 0,
            "single_test_reports": [{"name": "test_foo", "status": "PASSED", "messages": None}]
        })
        with tempfile.TemporaryDirectory() as tmpdir:
            with open(os.path.join(tmpdir, "unit_test_results_output.json"), "w") as f:
                f.write(payload)
            result = get_unit_test_results(tmpdir, "python_3.10")
            assert result["amount_passed"] == 1
            assert result["single_test_reports"][0]["name"] == "test_foo"

    def test_parses_c_criterion_json_via_custom_parser(self):
        from executor import get_unit_test_results
        criterion_json = json.dumps({
            "passed": 2, "failed": 0, "errored": 0,
            "test_suites": [{
                "tests": [
                    {"name": "test_a", "status": "PASSED", "messages": []},
                    {"name": "test_b", "status": "PASSED", "messages": []},
                ]
            }]
        })
        with tempfile.TemporaryDirectory() as tmpdir:
            with open(os.path.join(tmpdir, "unit_test_results_output.json"), "w") as f:
                f.write(criterion_json)
            result = get_unit_test_results(tmpdir, "c_std11")
            assert result["amount_passed"] == 2
            assert len(result["single_test_reports"]) == 2
