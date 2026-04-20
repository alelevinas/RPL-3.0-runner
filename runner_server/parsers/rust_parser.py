import json
import xml.etree.ElementTree as ET

BACKTRACE_MSG = "note: run with `RUST_BACKTRACE=1` environment variable to display a backtrace"

def parse_junit(xml_file):
    tree = ET.parse(xml_file)
    root = tree.getroot()
    tests = []
    passed = failed = errored = 0

    for testcase in root.iter('testcase'):
        name = testcase.attrib.get('name', 'unknown')
        status = "PASSED"
        messages = None

        failure = testcase.find('failure')
        error = testcase.find('error')
        skipped = testcase.find('skipped')

        if failure is not None:
            status = "FAILED"
            messages = failure.text.replace(BACKTRACE_MSG, "").replace("thread ", "").replace("panicked at", "failed at")
            failed += 1
        elif error is not None:
            status = "ERROR"
            messages = error.text.replace(BACKTRACE_MSG, "")
            errored += 1
        elif skipped is not None:
            status = "SKIPPED"
            messages = skipped.text.replace(BACKTRACE_MSG, "")
        else:
            passed += 1

        tests.append({
            "name": name,
            "status": status,
            "messages": messages
        })

    return {
        "single_test_reports": tests,
        "amount_passed": passed,
        "amount_failed": failed,
        "amount_errored": errored
    }

if __name__ == "__main__":
    result = parse_junit("rust_junit.xml")
    with open("unit_test_results_output.json", "w") as of:
        of.write(json.dumps(result, indent=4))
        