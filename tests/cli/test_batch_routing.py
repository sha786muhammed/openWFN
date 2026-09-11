import json
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


def test_batch_accepts_command_first_without_primary_input(tmp_path: Path) -> None:
    output_dir = tmp_path / "results"

    result = run_cli(
        "--format",
        "json",
        "batch",
        str(WATER),
        "--operation",
        "summary",
        "--output-dir",
        str(output_dir),
    )

    assert result.returncode == 0, result.stderr
    payload = json.loads(result.stdout)
    assert payload["kind"] == "batch"
    assert payload["data"]["inputs"] == 1
    assert payload["data"]["successes"] == 1
    assert (output_dir / "batch-manifest.json").exists()
