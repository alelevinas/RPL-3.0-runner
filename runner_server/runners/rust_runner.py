import shutil
import subprocess
import sys
from os import listdir

from runner import Runner, RunnerError

class RustRunner(Runner):
    def __init__(self, path, test_type, stdout=sys.stdout, stderr=sys.stderr):
        print("RustRunner")
        super().__init__(path, test_type, stdout, stderr)

    def generate_files(self):
        print("Generating files for RustRunner")
        shutil.copy("/rust_Makefile", self.path + "/Makefile")
        shutil.copy("/rust_parser.py", self.path)
        shutil.copy("/nextest.toml", self.path)
        shutil.copy("/home/runner/.aux_config_cargo/Cargo.toml", self.path)
        shutil.copy("/home/runner/.aux_config_cargo/Cargo.lock", self.path)


    def build_cmd(self):
        if self.test_type == "IO":
            build_target = "build_io"
            return (
                "Building",
                subprocess.Popen(
                    ["make", "-k", build_target],
                    cwd=self.path,
                    stdin=subprocess.DEVNULL,
                    stdout=subprocess.PIPE,
                    stderr=self.stderr,
                    start_new_session=True,
                ),
            )
        else:
            # first we check that the student code compiles without tests
            print("BUILDING PRE UNIT TEST")
            pre_build = subprocess.Popen(
                ["make", "-k", "build_pre_unit_test"],
                cwd=self.path,
                stdin=subprocess.DEVNULL,
                stdout=self.stdout,
                stderr=self.stderr,
            )
            pre_build_output, _ = pre_build.communicate()
            if pre_build.returncode != 0:
                self.my_print(
                    f"BUILD ERROR: error_code --> {pre_build.returncode}"
                )
                raise RunnerError(
                    self.stage,
                    f"Error de compilación. Codigo de Error: {pre_build.returncode}",
                )
            # now we can build with tests
            return (
                "Building",
                subprocess.Popen(
                    ["make", "-k", "build_unit_test"],
                    cwd=self.path,
                    stdin=subprocess.DEVNULL,
                    stdout=subprocess.PIPE,
                    stderr=self.stderr,
                    start_new_session=True,
                ),
            )

