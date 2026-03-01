import io
import json
import subprocess
import sys
import tarfile
import tempfile
import os

import requests

from config import URL_RPL_BACKEND, API_KEY

# Add root to sys.path to import shared
sys.path.append(os.path.join(os.path.dirname(__file__), ".."))
from shared.logger import setup_logger

log_path = os.path.join(os.path.dirname(__file__), "../logs/runner.log")
logger = setup_logger("rpl_runner", log_file=log_path)

URL_RUNNER = os.environ.get("URL_RUNNER", "http://runner:8000")

# ... rest of the file ...

def get_unit_test_extension(lang):
    if "python" in lang:
        return "py"
    if "java" in lang:
        return "java"
    if "go" in lang:
        return "go"
    if "rust" in lang:
        return "rs"
    return "c"


def ejecutar(submission_id, lang="c_std11", runner_url=None):
    """
    Función principal del script.
    """
    if not runner_url:
        runner_url = URL_RUNNER

    with tempfile.TemporaryDirectory(prefix="corrector.") as tmpdir:
        submission_metadata = __get_submission_metadata(submission_id)
        if not submission_metadata:
            logger.error(f"Submission {submission_id} not found")
            return

        submission_rplfile_id = submission_metadata["submission_rplfile_id"]
        activity_unit_tests_content = submission_metadata["activity_unit_tests_content"]
        activity_io_tests_input = submission_metadata["activity_io_tests_input"]
        activity_compilation_flags = submission_metadata.get("compilation_flags", "")
        test_mode = "IO" if submission_metadata["is_io_tested"] else "unit_test"

        submission_rplfile_path = os.path.join(tmpdir, "submission.tar.gz")
        __get_rplfile(submission_rplfile_id, submission_rplfile_path)

        __update_submission_status(submission_id, "PROCESSING")

        submission_tar_path = os.path.join(tmpdir, "submission_for_runner.tar")
        __create_submission_tar_for_runner(
            submission_tar_path,
            submission_rplfile_path,
            activity_unit_tests_content,
            activity_io_tests_input,
            lang
        )

        execution_results = __post_to_runner(
            submission_tar_path,
            activity_compilation_flags,
            lang,
            test_mode,
            runner_url
        )

        logger.info(f"Execution result for submission {submission_id}")

        __post_exec_log(submission_id, execution_results)


def __get_submission_metadata(submission_id):
    logger.info(f"Obtaining submission data {submission_id}")
    response = requests.get(
        f"{URL_RPL_BACKEND}/api/v3/submissions/{submission_id}",
        headers={"Authorization": f"Bearer {API_KEY}"}
    )
    if response.status_code == 404:
        return None
    if response.status_code != 200:
        logger.error(f"Error obtaining submission data: {response.text}")
        raise Exception("Error al obtener la Submission")
    return response.json()


def __get_rplfile(rplfile_id, dest_path):
    logger.info(f"Obtaining submission files {rplfile_id}")
    response = requests.get(
        f"{URL_RPL_BACKEND}/api/v3/RPLFile/{rplfile_id}",
        headers={"Authorization": f"Bearer {API_KEY}"}
    )
    if response.status_code != 200:
        logger.error(f"Error obtaining RPL file {rplfile_id}: {response.text}")
        raise Exception("Error al obtener el comprimido de submission")
    with open(dest_path, "wb") as f:
        f.write(response.content)


def __update_submission_status(submission_id, status):
    logger.info(f"Updating submission {submission_id} status to: {status}")
    response = requests.put(
        f"{URL_RPL_BACKEND}/api/v3/submissions/{submission_id}/status",
        json={"status": status},
        headers={"Authorization": f"Bearer {API_KEY}"}
    )
    if response.status_code != 200:
        logger.error(f"Error updating submission status: {response.json()}")
        raise Exception(
            f"Error al actualizar el estado de la submission: {response.json()}"
        )


def __create_submission_tar_for_runner(
    submission_tar_path, 
    submission_rplfile_path, 
    activity_unit_tests_file_content, 
    activity_io_tests, 
    activity_language
):
    with tarfile.open(submission_tar_path, "w") as tar:
        logger.info("Adding submission files to tar")
        with tarfile.open(submission_rplfile_path) as submission_tar:
            for member_tarinfo in submission_tar.getmembers():
                member_fileobj = submission_tar.extractfile(member_tarinfo)
                if "rust" in activity_language:
                    member_tarinfo.name = f"src/{member_tarinfo.name}"
                tar.addfile(tarinfo=member_tarinfo, fileobj=member_fileobj)
        if activity_unit_tests_file_content:
            logger.info("Adding unit test files to tar")
            if "rust" in activity_language:
                unit_test_info = tarfile.TarInfo(name="tests/unit_test.rs")
            else:
                unit_test_info = tarfile.TarInfo(
                    name="unit_test." + get_unit_test_extension(activity_language)
                )
            unit_test_info.size = len(activity_unit_tests_file_content)
            tar.addfile(
                tarinfo=unit_test_info,
                fileobj=io.BytesIO(activity_unit_tests_file_content.encode("utf-8")),
            )
        if activity_io_tests:
            logger.info("Adding IO test files to tar")
            for i, io_test in enumerate(activity_io_tests):
                IO_test_info = tarfile.TarInfo(name=f"IO_test_{i}.txt")
                IO_test_info.size = len(io_test)
                tar.addfile(
                    tarinfo=IO_test_info,
                    fileobj=io.BytesIO(io_test.encode("utf-8")),
                )


def __post_to_runner(submission_tar_path, activity_compilation_flags, lang, test_mode, runner_url):
    with open(submission_tar_path, "rb") as sub_tar:
        logger.info(f"POSTing submission to runner server at {runner_url}")
        response = requests.post(
            f"{runner_url}/",
            files={
                "file": ("submissionRECEIVED.tar", sub_tar),
                "cflags": (None, activity_compilation_flags),
                "lang": (None, lang),
                "test_mode": (None, test_mode),
            },
        )
        return response.json()
    

def __post_exec_log(submission_id, execution_results):
    logger.info(f"Posting execution log for submission {submission_id}")
    response = requests.post(
        f"{URL_RPL_BACKEND}/api/v3/submissions/{submission_id}/execLog",
        json=execution_results,
        headers={"Authorization": f"Bearer {API_KEY}"}
    )
    if response.status_code != 201:
        logger.error(f"Error posting execution log: {response.json()}")
        raise Exception(
            f"Error al postear el resultado de la submission: {response.json()}"
        )


if __name__ == "__main__":
    main()
