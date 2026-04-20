import shutil
import subprocess
import sys
from pathlib import Path

from runner import Runner, RunnerError

class PythonRunner(Runner):
    def __init__(self, path, test_type, stdout=sys.stdout, stderr=sys.stderr):
        super().__init__(path, test_type, stdout, stderr)

    def generate_files(self):
        shutil.copy("/python_Makefile", self.path + "/Makefile")
        if self.test_type != "IO":
            shutil.copy(
                "/usr/unit_test_wrapper.py", self.path + "/unit_test_wrapper.py"
            )
        else:
            shutil.copy(
                "/usr/custom_IO_main.py", self.path + "/custom_IO_main.py"
            )

    def lint(self):
        self.stage = "LINT"
        self.logger.info("Static Analysis Started (pylint)")
        # Find all .py files in path
        py_files = [str(p) for p in Path(self.path).glob("*.py")]
        if not py_files:
            return
            
        cmd = ["pylint", "--disable=all", "--enable=E,W,R", "--exit-zero"] + py_files
        self.exec_cmd(("pylint", subprocess.Popen(
            cmd,
            cwd=self.path,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            start_new_session=True,
        )), timeout=10)
        self.logger.info("Static Analysis Ended")

    def build_cmd(self):
        """
        We are using (pyinstaller)[https://pyinstaller.readthedocs.io/en/stable/usage.html] 
        to generate a binary file and then executing it in the 
        """
        if self.test_type == "IO":
            build_command = "build_io"
        else:
            build_command = "build_unit_test"

        return (
            "Building",
            subprocess.Popen(
                ["make", "-k", build_command],
                cwd=self.path,
                stdin=subprocess.DEVNULL,
                stdout=subprocess.PIPE,
                stderr=self.stderr,
                start_new_session=True,
            ),
        )

