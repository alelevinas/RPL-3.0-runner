import io
import json
import subprocess
import sys
import tarfile
import tempfile

import requests

from config import URL_RPL_BACKEND, API_KEY

import os
URL_RUNNER = os.environ.get("URL_RUNNER", "http://runner:8000")


def main():
    ejecutar(
        int(sys.argv[1]) if len(sys.argv) > 1 else 1,
        sys.argv[2] if len(sys.argv) > 2 else "c_std11",
    )


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


def ejecutar(submission_id, lang="c_std11"):
    """
    Función principal del script.
    """
    with tempfile.TemporaryDirectory(prefix="corrector.") as tmpdir:
        solution_tar = "tar_assignment_solved_c.tar.gz"
        submission_metadata = __get_submission_metadata(submission_id)
        if not submission_metadata:
            return

        submission_rplfile_id = submission_metadata["submission_rplfile_id"]
        activity_starting_rplfile_id = submission_metadata["activity_starting_rplfile_id"]
        activity_unit_tests_file_content = submission_metadata["activity_unit_tests_content"]
        activity_io_tests = submission_metadata["activity_io_tests_input"]
        activity_language = submission_metadata["activity_language"]
        activity_compilation_flags = submission_metadata["compilation_flags"]
        is_io_tested = submission_metadata["is_io_tested"]
        test_mode = "IO" if is_io_tested else "unit_test"

        print(f"======TEST MODE: {test_mode} ===========")

        submission_rplfile_path = tmpdir + "/submission_rplfile.tar.gz"
        __get_rplfile(submission_rplfile_id, submission_rplfile_path)

        if activity_starting_rplfile_id:
            activity_files_path = tmpdir + "/activity_files.tar.gz"
            __get_rplfile(activity_starting_rplfile_id, activity_files_path)
        else:
            print("NO HAY ACTIVITY FILES")

        print(f"Submission obtenida. Lenguaje: {activity_language}; Flags: [{activity_compilation_flags}]; Test mode: {test_mode}; Submission RPLFile ID: {submission_rplfile_id}")

        __update_submission_status(submission_id, "PROCESSING")

        submission_tar_path = "submission.tar"
        __create_submission_tar_for_runner(
            submission_tar_path,
            submission_rplfile_path,
            activity_unit_tests_file_content,
            activity_io_tests,
            activity_language
        )

        execution_results = __post_to_runner(
            submission_tar_path,
            activity_compilation_flags,
            lang,
            test_mode
        )

        print("Result:\n\n")
        print(json.dumps(execution_results, indent=4))
        print("################## STDOUT ######################")
        print(execution_results["tests_execution_stdout"])
        print("################## STDOUT ######################")
        print("################## STDERR ######################")
        print(execution_results["tests_execution_stderr"])
        print("################## STDERR ######################")

        __post_exec_log(submission_id, execution_results)


def __get_submission_metadata(submission_id):
    print(f"Obteniendo submission data {submission_id}....")
    response = requests.get(
        f"{URL_RPL_BACKEND}/api/v3/submissions/{submission_id}",
        headers={"Authorization": f"Bearer {API_KEY}"}
    )
    print(json.dumps(response.json(), indent=4))
    if response.status_code == 404:
        return None
    if response.status_code != 200:
        raise Exception("Error al obtener la Submission")
    return response.json()


def __get_rplfile(rplfile_id, dest_path):
    print(f"Obteniendo submission files {rplfile_id}....")
    response = requests.get(
        f"{URL_RPL_BACKEND}/api/v3/RPLFile/{rplfile_id}",
        headers={"Authorization": f"Bearer {API_KEY}"}
    )
    if response.status_code != 200:
        raise Exception("Error al obtener el comprimido de submission")
    with open(dest_path, "wb") as f:
        f.write(response.content)


def __update_submission_status(submission_id, status):
    print(f"Actualizando submission: {status}")
    response = requests.put(
        f"{URL_RPL_BACKEND}/api/v3/submissions/{submission_id}/status",
        json={"status": status},
        headers={"Authorization": f"Bearer {API_KEY}"}
    )
    if response.status_code != 200:
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
        print("Agrego archivos de la submission")
        with tarfile.open(submission_rplfile_path) as submission_tar:
            for member_tarinfo in submission_tar.getmembers():
                member_fileobj = submission_tar.extractfile(member_tarinfo)
                if "rust" in activity_language:
                    member_tarinfo.name = f"src/{member_tarinfo.name}"
                tar.addfile(tarinfo=member_tarinfo, fileobj=member_fileobj)
        if activity_unit_tests_file_content:
            print("Agrego archivos de Unit test")
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
            print("Agrego archivos de IO test")
            for i, io_test in enumerate(activity_io_tests):
                IO_test_info = tarfile.TarInfo(name=f"IO_test_{i}.txt")
                IO_test_info.size = len(io_test)
                tar.addfile(
                    tarinfo=IO_test_info,
                    fileobj=io.BytesIO(io_test.encode("utf-8")),
                )


def __post_to_runner(submission_tar_path, activity_compilation_flags, lang, test_mode):
    with open(submission_tar_path, "rb") as sub_tar:
        print("POSTing submission to runner server")
        response = requests.post(
            f"{URL_RUNNER}/",
            files={
                "file": ("submissionRECEIVED.tar", sub_tar),
                "cflags": (None, activity_compilation_flags),
                "lang": (None, lang),
                "test_mode": (None, test_mode),
            },
        )
        return response.json()
    

def __post_exec_log(submission_id, execution_results):
    response = requests.post(
        f"{URL_RPL_BACKEND}/api/v3/submissions/{submission_id}/execLog",
        json=execution_results,
        headers={"Authorization": f"Bearer {API_KEY}"}
    )
    if response.status_code != 201:
        raise Exception(
            f"Error al postear el resultado de la submission: {response.json()}"
        )


if __name__ == "__main__":
    main()
