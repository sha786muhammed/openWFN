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
        check=False,
    )


def test_density_integrate_accepts_explicit_grid_point_limit() -> None:
    result = run_cli(
        "--format",
        "json",
        str(WATER),
        "density",
        "integrate",
        "--spacing",
        "1.0",
        "--padding",
        "1.0",
        "--max-grid-points",
        "10",
    )

    assert result.returncode != 0
    payload = json.loads(result.stdout)
    assert payload["status"] == "failed"
    assert "10" in payload["error"]["message"]
    assert "grid" in payload["error"]["message"].lower()
