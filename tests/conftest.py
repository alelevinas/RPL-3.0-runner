import sys
import os

# Add the repo root to sys.path so tests can import receiver, config, etc.
REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

# Add rpl_runner/ to sys.path so tests can import init, runner, parsers, etc.
RUNNER_ROOT = os.path.join(REPO_ROOT, "rpl_runner")
if RUNNER_ROOT not in sys.path:
    sys.path.insert(0, RUNNER_ROOT)
