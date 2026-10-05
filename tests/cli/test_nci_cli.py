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


def test_cli_exports_signed_density_nci_cube(tmp_path: Path) -> None:
    output = tmp_path / "signed-density.cube"
    result = run_cli(
        "--format",
        "json",
        str(WATER),
        "nci",
        "cube",
        str(output),
        "--field",
        "signed-density",
        "--spacing",
        "1.0",
        "--padding",
        "2.0",
    )

    assert result.returncode == 0, result.stderr
    payload = json.loads(result.stdout)
    assert payload["kind"] == "nci_cube"
    assert payload["validation_status"] == "Experimental"
    assert payload["data"]["field"] == "signed_density"
    assert output.is_file()


def test_cli_rdg_requires_explicit_cap(tmp_path: Path) -> None:
    output = tmp_path / "rdg.cube"
    result = run_cli(
        "--format",
        "json",
        str(WATER),
        "nci",
        "cube",
        str(output),
        "--field",
        "rdg",
        "--spacing",
        "1.0",
        "--padding",
        "2.0",
    )

    assert result.returncode != 0
    payload = json.loads(result.stdout)
    assert payload["status"] == "failed"
    assert "rdg_cap" in payload["error"]["message"]
    assert not output.exists()


def test_cli_rejects_rdg_cap_for_non_rdg_field(tmp_path: Path) -> None:
    output = tmp_path / "rho.cube"
    result = run_cli(
        "--format",
        "json",
        str(WATER),
        "nci",
        "cube",
        str(output),
        "--field",
        "rho",
        "--rdg-cap",
        "2.0",
        "--spacing",
        "1.0",
        "--padding",
        "2.0",
    )

    assert result.returncode != 0
    payload = json.loads(result.stdout)
    assert payload["status"] == "failed"
    assert "rdg_cap" in payload["error"]["message"]
    assert not output.exists()


def test_cli_nci_cube_honors_global_overwrite(tmp_path: Path) -> None:
    output = tmp_path / "lambda2.cube"
    common = (
        str(WATER),
        "nci",
        "cube",
        str(output),
        "--field",
        "lambda2",
        "--spacing",
        "1.0",
        "--padding",
        "2.0",
    )

    first = run_cli(*common)
    assert first.returncode == 0, first.stderr

    second = run_cli(*common)
    assert second.returncode != 0
    diagnostic = second.stderr + second.stdout
    assert "Output exists:" in diagnostic
    assert "--overwrite" in diagnostic

    third = run_cli("--overwrite", *common)
    assert third.returncode == 0, third.stderr
