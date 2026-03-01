import pytest
import subprocess
from unittest.mock import MagicMock, patch
from rpl_runner.c_runner import CRunner
from rpl_runner.python_runner import PythonRunner

class TestLinting:
    @patch("subprocess.Popen")
    def test_c_runner_lint_calls_cppcheck(self, mock_popen):
        # Setup mock
        mock_process = MagicMock()
        mock_process.communicate.return_value = (b"cppcheck output", b"")
        mock_process.returncode = 0
        mock_popen.return_value = mock_process
        
        runner = CRunner("/tmp/test", "unit_test")
        runner.lint()
        
        # Verify cppcheck was called
        args, kwargs = mock_popen.call_args
        assert "cppcheck" in args[0]
        assert "--enable=all" in args[0]

    @patch("subprocess.Popen")
    @patch("pathlib.Path.glob")
    def test_python_runner_lint_calls_pylint(self, mock_glob, mock_popen):
        # Setup mocks
        mock_glob.return_value = ["file1.py"]
        mock_process = MagicMock()
        mock_process.communicate.return_value = (b"pylint output", b"")
        mock_process.returncode = 0
        mock_popen.return_value = mock_process
        
        runner = PythonRunner("/tmp/test", "unit_test")
        runner.lint()
        
        # Verify pylint was called
        args, kwargs = mock_popen.call_args
        assert "pylint" in args[0]
        assert "--enable=E,W,R" in args[0]
