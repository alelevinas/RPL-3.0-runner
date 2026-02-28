"""Tests for receiver.py — the component that fetches submissions,
builds a tar for the runner, and posts results back."""

import io
import json
import os
import tarfile
import tempfile
from unittest.mock import patch, MagicMock

import pytest

import receiver


# Module-level double-underscore functions aren't name-mangled in Python,
# so we access them via getattr to avoid SyntaxError with the __ prefix.
_create_tar = getattr(receiver, "__create_submission_tar_for_runner")
_get_metadata = getattr(receiver, "__get_submission_metadata")
_get_rplfile = getattr(receiver, "__get_rplfile")
_update_status = getattr(receiver, "__update_submission_status")
_post_to_runner = getattr(receiver, "__post_to_runner")
_post_exec_log = getattr(receiver, "__post_exec_log")


# ---------------------------------------------------------------------------
# get_unit_test_extension
# ---------------------------------------------------------------------------

class TestGetUnitTestExtension:
    def test_c_language(self):
        assert receiver.get_unit_test_extension("c_std11") == "c"

    def test_python_language(self):
        assert receiver.get_unit_test_extension("python_3.10") == "py"

    def test_java_language(self):
        assert receiver.get_unit_test_extension("java_17") == "java"

    def test_go_language(self):
        assert receiver.get_unit_test_extension("go_1.19") == "go"

    def test_rust_language(self):
        assert receiver.get_unit_test_extension("rust_1.88.0") == "rs"

    def test_unknown_defaults_to_c(self):
        assert receiver.get_unit_test_extension("unknown_lang") == "c"


# ---------------------------------------------------------------------------
# __create_submission_tar_for_runner
# ---------------------------------------------------------------------------

class TestCreateSubmissionTar:
    def _make_source_tar(self, tmpdir, files: dict[str, str]) -> str:
        path = os.path.join(tmpdir, "source.tar.gz")
        with tarfile.open(path, "w:gz") as tar:
            for name, content in files.items():
                data = content.encode("utf-8")
                info = tarfile.TarInfo(name=name)
                info.size = len(data)
                tar.addfile(info, io.BytesIO(data))
        return path

    def test_tar_contains_submission_and_unit_test(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            source_tar = self._make_source_tar(tmpdir, {"main.c": "int main(){}"})
            output_tar = os.path.join(tmpdir, "output.tar")

            _create_tar(output_tar, source_tar, "#include <criterion/criterion.h>", None, "c_std11")

            with tarfile.open(output_tar) as tar:
                names = tar.getnames()
                assert "main.c" in names
                assert "unit_test.c" in names

    def test_rust_files_get_src_prefix(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            source_tar = self._make_source_tar(tmpdir, {"lib.rs": "fn main(){}"})
            output_tar = os.path.join(tmpdir, "output.tar")

            _create_tar(output_tar, source_tar, "#[test] fn it_works() {}", None, "rust_1.88.0")

            with tarfile.open(output_tar) as tar:
                names = tar.getnames()
                assert "src/lib.rs" in names
                assert "tests/unit_test.rs" in names

    def test_io_tests_added_to_tar(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            source_tar = self._make_source_tar(tmpdir, {"main.c": "int main(){}"})
            output_tar = os.path.join(tmpdir, "output.tar")

            _create_tar(output_tar, source_tar, None, ["input1\n", "input2\n"], "c_std11")

            with tarfile.open(output_tar) as tar:
                names = tar.getnames()
                assert "IO_test_0.txt" in names
                assert "IO_test_1.txt" in names

    def test_no_unit_test_when_content_is_none(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            source_tar = self._make_source_tar(tmpdir, {"main.c": "int main(){}"})
            output_tar = os.path.join(tmpdir, "output.tar")

            _create_tar(output_tar, source_tar, None, None, "c_std11")

            with tarfile.open(output_tar) as tar:
                names = tar.getnames()
                assert "main.c" in names
                assert not any("unit_test" in n for n in names)


# ---------------------------------------------------------------------------
# __get_submission_metadata (mocked HTTP)
# ---------------------------------------------------------------------------

class TestGetSubmissionMetadata:
    @patch("receiver.requests.get")
    def test_returns_metadata_on_200(self, mock_get):
        expected = {"submission_rplfile_id": 1, "activity_language": "c_std11"}
        mock_get.return_value = MagicMock(status_code=200, json=lambda: expected)

        result = _get_metadata(42)
        assert result == expected

    @patch("receiver.requests.get")
    def test_returns_none_on_404(self, mock_get):
        mock_get.return_value = MagicMock(status_code=404, json=lambda: {})
        result = _get_metadata(999)
        assert result is None

    @patch("receiver.requests.get")
    def test_raises_on_server_error(self, mock_get):
        mock_get.return_value = MagicMock(status_code=500, json=lambda: {"error": "fail"})
        with pytest.raises(Exception, match="Error al obtener la Submission"):
            _get_metadata(42)


# ---------------------------------------------------------------------------
# __update_submission_status (mocked HTTP)
# ---------------------------------------------------------------------------

class TestUpdateSubmissionStatus:
    @patch("receiver.requests.put")
    def test_success(self, mock_put):
        mock_put.return_value = MagicMock(status_code=200)
        _update_status(1, "PROCESSING")
        mock_put.assert_called_once()

    @patch("receiver.requests.put")
    def test_raises_on_failure(self, mock_put):
        mock_put.return_value = MagicMock(status_code=500, json=lambda: {"error": "fail"})
        with pytest.raises(Exception, match="Error al actualizar"):
            _update_status(1, "PROCESSING")


# ---------------------------------------------------------------------------
# __post_exec_log (mocked HTTP)
# ---------------------------------------------------------------------------

class TestPostExecLog:
    @patch("receiver.requests.post")
    def test_success(self, mock_post):
        mock_post.return_value = MagicMock(status_code=201)
        _post_exec_log(1, {"result": "OK"})
        mock_post.assert_called_once()

    @patch("receiver.requests.post")
    def test_raises_on_failure(self, mock_post):
        mock_post.return_value = MagicMock(status_code=500, json=lambda: {"error": "fail"})
        with pytest.raises(Exception, match="Error al postear"):
            _post_exec_log(1, {"result": "OK"})


# ---------------------------------------------------------------------------
# __post_to_runner (mocked HTTP)
# ---------------------------------------------------------------------------

class TestPostToRunner:
    @patch("receiver.requests.post")
    def test_posts_tar_and_returns_json(self, mock_post):
        expected = {"tests_execution_result_status": "OK"}
        mock_post.return_value = MagicMock(status_code=200, json=lambda: expected)

        with tempfile.NamedTemporaryFile(suffix=".tar", delete=False) as f:
            f.write(b"fake tar content")
            tar_path = f.name

        try:
            result = _post_to_runner(tar_path, "-Wall", "c_std11", "unit_test")
            assert result == expected
        finally:
            os.unlink(tar_path)


# ---------------------------------------------------------------------------
# ejecutar (full flow, all HTTP mocked)
# ---------------------------------------------------------------------------

class TestEjecutar:
    @patch("receiver.requests.post")
    @patch("receiver.requests.put")
    @patch("receiver.requests.get")
    def test_full_flow(self, mock_get, mock_put, mock_post):
        metadata = {
            "submission_rplfile_id": 10,
            "activity_starting_rplfile_id": None,
            "activity_unit_tests_content": "#include <criterion/criterion.h>",
            "activity_io_tests_input": None,
            "activity_language": "c_std11",
            "compilation_flags": "-Wall",
            "is_io_tested": False,
        }
        # Build a valid tar.gz for __get_rplfile to write
        tar_buf = io.BytesIO()
        with tarfile.open(fileobj=tar_buf, mode="w:gz") as tar:
            data = b"int main(){}"
            info = tarfile.TarInfo(name="main.c")
            info.size = len(data)
            tar.addfile(info, io.BytesIO(data))
        tar_bytes = tar_buf.getvalue()

        runner_result = {
            "tests_execution_result_status": "OK",
            "tests_execution_stdout": "all passed",
            "tests_execution_stderr": "",
        }

        def get_side_effect(url, **kwargs):
            resp = MagicMock()
            if "RPLFile" in url:
                resp.status_code = 200
                resp.content = tar_bytes
            else:
                resp.status_code = 200
                resp.json.return_value = metadata
            return resp

        mock_get.side_effect = get_side_effect
        mock_put.return_value = MagicMock(status_code=200)

        def post_side_effect(url, **kwargs):
            resp = MagicMock()
            if "execLog" in url:
                resp.status_code = 201
            else:
                resp.status_code = 200
                resp.json.return_value = runner_result
            return resp

        mock_post.side_effect = post_side_effect

        receiver.ejecutar(1, "c_std11")

        assert mock_get.call_count >= 1
        assert mock_put.call_count == 1
        assert mock_post.call_count == 2

    @patch("receiver.requests.get")
    def test_returns_early_on_missing_submission(self, mock_get):
        mock_get.return_value = MagicMock(status_code=404, json=lambda: {})
        receiver.ejecutar(999, "c_std11")
