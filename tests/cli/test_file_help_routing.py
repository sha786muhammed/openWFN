import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
WATER = ROOT / "examples" / "water" / "water.fchk"


def run_cli(*args: str) -> subprocess.CompletedProcess[str]:
    environment = os.environ.copy()
    environment["PYTHONPATH"] = str(ROOT / "src")
    return subprocess.run(
        [sys.executable, "-m", "openwfn.cli", *args],
        capture_output=True,
        text=True,
        env=environment,
    )


def test_help_after_input_file_shows_cli_help() -> None:
    result = run_cli(str(WATER), "--help")

    assert result.returncode == 0, result.stderr
    assert "usage: openwfn" in result.stdout
    assert "COMMAND" in result.stdout
    assert "invalid choice" not in result.stderr
