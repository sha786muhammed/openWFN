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
