import subprocess
from pathlib import Path

# utility for running terminal commands


def run(cmd: list[str], cwd: Path | str) -> subprocess.CompletedProcess:
    result = subprocess.run(cmd, cwd=cwd, check=True)
    return result
