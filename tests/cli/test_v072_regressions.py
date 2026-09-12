import json
import os
import subprocess
import sys
from pathlib import Path

from openwfn import __version__

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


def test_summary_honors_json_format() -> None:
    result = run_cli("--format", "json", str(WATER), "summary")

    assert result.returncode == 0, result.stderr
    payload = json.loads(result.stdout)
    assert payload["kind"] == "summary"
    assert payload["data"]["formula"] == "H2O"
    assert payload["data"]["atoms"] == 3
    assert payload["data"]["charge"] == 0
    assert payload["data"]["multiplicity"] == 1


def test_summary_table_keeps_atoms_label() -> None:
    result = run_cli(str(WATER), "summary")

    assert result.returncode == 0, result.stderr
    assert "Atoms: 3" in result.stdout


def test_mol_header_uses_installed_package_version(tmp_path: Path) -> None:
    output = tmp_path / "water.mol"
    result = run_cli(str(WATER), "convert", "--to", "mol", "--output", str(output))

    assert result.returncode == 0, result.stderr
    lines = output.read_text(encoding="utf-8").splitlines()
    assert lines[1].strip() == f"openWFN {__version__}"


def test_sdf_header_uses_installed_package_version(tmp_path: Path) -> None:
    output = tmp_path / "water.sdf"
    result = run_cli(str(WATER), "convert", "--to", "sdf", "--output", str(output))

    assert result.returncode == 0, result.stderr
    lines = output.read_text(encoding="utf-8").splitlines()
    assert lines[1].strip() == f"openWFN {__version__}"


def test_validate_accepts_explicit_grid_controls() -> None:
    result = run_cli(
        "--format",
        "json",
        str(WATER),
        "validate",
        "--spacing",
        "1.0",
        "--padding",
        "2.0",
    )

    assert result.returncode == 0, result.stderr
    payload = json.loads(result.stdout)
    assert payload["kind"] == "density_integration"
    assert payload["data"]["spacing"] == 1.0
    assert payload["data"]["padding"] == 2.0
