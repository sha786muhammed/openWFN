import json
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
UHF = ROOT / "tests" / "fixtures" / "scientific" / "uhf_beta_homo.fchk"


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


def test_single_frontier_cli_accepts_all_spin_channels() -> None:
    result = run_cli(
        "--format",
        "json",
        str(UHF),
        "orbitals",
        "frontier",
        "--spin",
        "all",
    )

    assert result.returncode == 0, result.stderr
    payload = json.loads(result.stdout)
    assert payload["analysis_name"] == "frontier-all"
    assert payload["data"]["overall_homo_spin"] == "beta"


def test_batch_frontier_spin_all_maps_to_spin_complete_analysis(tmp_path: Path) -> None:
    output_dir = tmp_path / "results"
    result = run_cli(
        "--format",
        "json",
        "batch",
        str(UHF),
        "--analyses",
        "frontier",
        "--spin",
        "all",
        "--output-dir",
        str(output_dir),
    )

    assert result.returncode == 0, result.stderr
    payload = json.loads(result.stdout)
    assert payload["data"]["analyses"] == ["frontier-all"]
    manifest = json.loads((output_dir / "batch-manifest.json").read_text(encoding="utf-8"))
    assert manifest["analyses"] == ["frontier-all"]
    assert manifest["records"][0]["results"][0]["data"]["overall_homo_spin"] == "beta"
