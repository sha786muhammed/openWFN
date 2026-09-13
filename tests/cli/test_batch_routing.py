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


def test_batch_cli_accepts_multiple_registered_analyses(tmp_path: Path) -> None:
    output_dir = tmp_path / "results"

    result = run_cli(
        "--format",
        "json",
        "batch",
        str(WATER),
        "--analyses",
        "summary,frontier",
        "--output-dir",
        str(output_dir),
    )

    assert result.returncode == 0, result.stderr
    payload = json.loads(result.stdout)
    assert payload["data"]["analyses"] == ["summary", "frontier"]
    manifest = json.loads((output_dir / "batch-manifest.json").read_text(encoding="utf-8"))
    assert manifest["schema_version"] == "1.0"
    assert manifest["analyses"] == ["summary", "frontier"]


def test_batch_cli_reports_partial_inputs_separately_from_errors(tmp_path: Path) -> None:
    xyz = tmp_path / "water.xyz"
    xyz.write_text("3\nwater\nO 0 0 0\nH 0 0 1\nH 1 0 0\n", encoding="utf-8")

    result = run_cli(
        "--format",
        "json",
        "batch",
        str(xyz),
        "--analyses",
        "summary,frontier",
        "--output-dir",
        str(tmp_path / "results"),
    )

    assert result.returncode == 0, result.stderr
    payload = json.loads(result.stdout)["data"]
    assert payload["successes"] == 0
    assert payload["partial"] == 1
    assert payload["errors"] == 0


def test_batch_cli_resume_reports_skipped_inputs(tmp_path: Path) -> None:
    output_dir = tmp_path / "results"
    arguments = (
        "--format",
        "json",
        "batch",
        str(WATER),
        "--analyses",
        "summary,frontier",
        "--output-dir",
        str(output_dir),
    )
    first = run_cli(*arguments)

    resumed = run_cli(*arguments, "--resume")

    assert first.returncode == 0, first.stderr
    assert resumed.returncode == 0, resumed.stderr
    assert json.loads(resumed.stdout)["data"]["skipped"] == 1
    manifest = json.loads((output_dir / "batch-manifest.json").read_text(encoding="utf-8"))
    assert manifest["records"][0]["skipped"] is True
