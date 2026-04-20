from enum import Enum

class Language(str, Enum):
    C = "c"
    PYTHON = "python"
    GO = "go"
    RUST = "rust"

    def with_version(self):
        if self == Language.C:
            return LanguageWithVersion.C
        elif self == Language.PYTHON:
            return LanguageWithVersion.PYTHON
        elif self == Language.GO:
            return LanguageWithVersion.GO
        elif self == Language.RUST:
            return LanguageWithVersion.RUST
        else:
            raise ValueError(f"Unsupported language: {self}")

class LanguageWithVersion(str, Enum):
    C = "c_std11"
    OLD_PYTHON = "python_3.7"
    PYTHON = "python_3.10"
    GO = "go_1.19"
    RUST = "rust_1.88.0"

    def without_version(self):
        if self == LanguageWithVersion.C:
            return Language.C
        elif self == LanguageWithVersion.PYTHON or self == LanguageWithVersion.OLD_PYTHON:
            return Language.PYTHON
        elif self == LanguageWithVersion.GO:
            return Language.GO
        elif self == LanguageWithVersion.RUST:
            return Language.RUST
        else:
            raise ValueError(f"Unsupported language: {self}")

class SubmissionStatus(str, Enum):
    NO_SUBMISSIONS = ""
    PENDING = "PENDING"
    ENQUEUED = "ENQUEUED"
    PROCESSING = "PROCESSING"
    BUILD_ERROR = "BUILD_ERROR"
    RUNTIME_ERROR = "RUNTIME_ERROR"
    FAILURE = "FAILURE"
    SUCCESS = "SUCCESS"
    TIME_OUT = "TIME_OUT"

    @classmethod
    def from_tests_execution_errored_stage(cls, tests_execution_stage: str) -> "SubmissionStatus":
        if tests_execution_stage == "BUILD":
            return cls.BUILD_ERROR
        else:
            return cls.RUNTIME_ERROR

class TestsExecutionResultStatus(str, Enum):
    ERROR = "ERROR"
    SUCCESS = "OK"
    TIME_OUT = "TIME_OUT"

class RPLFileType(str, Enum):
    GZIP = "application/gzip"
    TEXT = "text"
