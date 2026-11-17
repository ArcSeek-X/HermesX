"""Execute the Dockerfile's APT shell step with a controlled package transport."""

import json
import os
import subprocess
import sys

import pytest

from tests.support.paths import get_repo_root


@pytest.mark.parametrize(
    "failures,update_fails,success,attempts",
    [(0, False, True, 1), (1, False, True, 2), (4, False, False, 4), (0, True, False, 0)],
)
def test_system_dependency_install_retries_are_bounded_and_fail_closed(
    tmp_path, failures, update_fails, success, attempts
):
    dockerfile = (get_repo_root() / "docker/Dockerfile").read_text()
    lines = dockerfile.splitlines()
    start = next(i for i, line in enumerate(lines) if line.startswith("RUN apt-get update"))
    command = lines[start][4:]
    for line in lines[start + 1:]:
        if not command.rstrip().endswith("\\"):
            break
        command = command.rstrip()[:-1] + line

    state_file = tmp_path / "state.json"
    transport = f"#!{sys.executable}\n" + '''import json, os, sys
from pathlib import Path
path = Path(os.environ["APT_TEST_STATE"])
state = json.loads(path.read_text()) if path.exists() else {"install": 0, "cleanup": 0}
program = Path(sys.argv[0]).name
result = 0
if program == "apt-get":
    if sys.argv[1] == "update":
        result = 100 if os.environ["APT_TEST_UPDATE_FAILS"] == "1" else 0
    else:
        state["install"] += 1
        result = 100 if state["install"] <= int(os.environ["APT_TEST_FAILURES"]) else 0
elif program == "rm":
    state["cleanup"] += 1
path.write_text(json.dumps(state))
sys.exit(result)
'''
    for name in ("apt-get", "sleep", "rm"):
        executable = tmp_path / name
        executable.write_text(transport)
        executable.chmod(0o755)
    # A closed PATH ensures no real apt-get, sleep or rm can execute on the host.
    environment = dict(
        os.environ,
        PATH=str(tmp_path),
        APT_TEST_STATE=str(state_file),
        APT_TEST_FAILURES=str(failures),
        APT_TEST_UPDATE_FAILS="1" if update_fails else "0",
    )
    result = subprocess.run(
        ["/bin/sh", "-c", command], env=environment, capture_output=True, text=True, timeout=10
    )
    state = json.loads(state_file.read_text())
    assert (result.returncode == 0) is success, result.stderr
    assert state["install"] == attempts
    assert state["cleanup"] == (1 if success else 0)
