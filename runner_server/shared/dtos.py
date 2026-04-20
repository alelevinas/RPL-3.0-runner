from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel
from shared.enums import TestsExecutionResultStatus

class SingleUnitTestRunReportDTO(BaseModel):
    name: str
    status: str
    messages: Optional[str] = None

class UnitTestSuiteRunsSummaryDTO(BaseModel):
    amount_passed: int
    amount_failed: int
    amount_errored: int
    single_test_reports: List[SingleUnitTestRunReportDTO]

class TestsExecutionLogDTO(BaseModel):
    tests_execution_result_status: TestsExecutionResultStatus
    tests_execution_stage: str
    tests_execution_exit_message: str
    tests_execution_stderr: str
    tests_execution_stdout: str
    all_student_only_outputs_from_iotests_runs: Optional[list[str]] = []
    unit_test_suite_result_summary: Optional[UnitTestSuiteRunsSummaryDTO] = None

class ErrorResponseDTO(BaseModel):
    detail: str
    error_code: Optional[str] = None
    timestamp: datetime = datetime.now()
