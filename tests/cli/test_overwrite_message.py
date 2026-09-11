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


def test_existing_structure_output_suggests_cli_overwrite_flag(tmp_path: Path) -> None:
    output = tmp_path / "water.xyz"
    output.write_text("existing\n", encoding="utf-8")

    result = run_cli(str(WATER), "convert", "--to", "xyz", "--output", str(output))

    assert result.returncode != 0
    combined = result.stdout + result.stderr
    assert "--overwrite" in combined
    assert "overwrite=True" not in combined
