import json
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
WATER = ROOT / "examples" / "water" / "water.fchk"
INTEROP = ROOT / "tests" / "fixtures" / "interop"


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


def test_capabilities_json_for_native_fchk() -> None:
    result = run_cli("--format", "json", str(WATER), "capabilities")

    assert result.returncode == 0, result.stderr
    payload = json.loads(result.stdout)
    assert payload["kind"] == "capabilities"
    assert payload["data"]["source_format"] == "fchk"
    assert payload["data"]["backend"] == "native"
    assert payload["data"]["capabilities"]["alpha_orbitals"]["state"] == "available"
    assert payload["data"]["analyses"]["frontier"]["available"] is True


def test_capabilities_json_for_structure_only_input(tmp_path: Path) -> None:
    source = tmp_path / "water.xyz"
    source.write_text("3\nwater\nO 0 0 0\nH 0.7586 0 0.5043\nH -0.7586 0 0.5043\n", encoding="utf-8")

    result = run_cli("--format", "json", str(source), "capabilities")

    assert result.returncode == 0, result.stderr
    payload = json.loads(result.stdout)
    assert payload["data"]["source_format"] == "xyz"
    assert payload["data"]["capabilities"]["structure"]["state"] == "available"
    assert payload["data"]["capabilities"]["alpha_orbitals"]["state"] == "missing"
    assert payload["data"]["analyses"]["frontier"]["available"] is False
    assert "alpha orbitals" in payload["data"]["analyses"]["frontier"]["missing_requirements"]


def test_cli_hint_and_doctor_use_canonical_loader() -> None:
    hinted = run_cli(
        "--format", "json", "--input-format", "gamess",
        str(INTEROP / "gamess" / "water.dat"), "capabilities",
    )
    assert hinted.returncode == 0, hinted.stderr
    assert json.loads(hinted.stdout)["data"]["source_format"] == "gamess"

    for relative in ("molden/water.molden", "wfx/water.wfx"):
        result = run_cli("--format", "json", str(INTEROP / relative), "doctor")
        assert result.returncode == 0, result.stderr
        data = json.loads(result.stdout)["data"]
        assert data["input_kind"] == "molecular-calculation"
        assert data["capabilities"]["orbitals"] is True
        assert data["normalized"]["source_format"] == relative.split("/")[0]

    invalid = run_cli(
        "--format", "json", "--input-format", "nonexistent", str(WATER), "capabilities"
    )
    assert invalid.returncode != 0
    assert "Unknown input format hint" in invalid.stderr + invalid.stdout


def test_cli_orbital_analysis_uses_canonical_loader() -> None:
    result = run_cli("--format", "json", str(INTEROP / "molden" / "water.molden"), "orbitals", "frontier")
    assert result.returncode == 0, result.stderr
    assert json.loads(result.stdout)["status"] == "success"


def test_cli_structure_summary_is_partial() -> None:
    result = run_cli(
        "--format", "json", str(INTEROP / "poscar" / "POSCAR-water"), "summary"
    )
    assert result.returncode == 0, result.stderr
    payload = json.loads(result.stdout)
    assert payload["status"] == "partial"
    assert payload["data"]["scope"] == "periodic"
