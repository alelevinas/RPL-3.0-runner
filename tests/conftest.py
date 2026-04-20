import sys
import os

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

RUNNER_SERVER = os.path.join(REPO_ROOT, "runner_server")
if RUNNER_SERVER not in sys.path:
    sys.path.insert(0, RUNNER_SERVER)

# Flat imports inside runner files (e.g. `from runner import Runner`) need
# runner_server/runners/ on the path, just as they land flat at / in Docker.
RUNNERS = os.path.join(RUNNER_SERVER, "runners")
if RUNNERS not in sys.path:
    sys.path.insert(0, RUNNERS)

PARSERS = os.path.join(RUNNER_SERVER, "parsers")
if PARSERS not in sys.path:
    sys.path.insert(0, PARSERS)
