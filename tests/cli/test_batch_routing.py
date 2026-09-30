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


def test_batch_dry_run_discovers_directory_without_output_directory(tmp_path: Path) -> None:
    calculations = tmp_path / "calculations"
    nested = calculations / "nested"
    nested.mkdir(parents=True)
    (calculations / "water.xyz").write_text(
        "3\nwater\nO 0 0 0\nH 0 0 1\nH 1 0 0\n", encoding="utf-8"
    )
    (nested / "hydrogen.xyz").write_text("1\nhydrogen\nH 0 0 0\n", encoding="utf-8")
    (calculations / "README.txt").write_text("not an input", encoding="utf-8")

    result = run_cli(
        "--format",
        "json",
        "batch",
        str(calculations),
        "--recursive",
        "--dry-run",
        "--analyses",
        "summary",
    )

    assert result.returncode == 0, result.stderr
    payload = json.loads(result.stdout)
    assert payload["kind"] == "batch_dry_run"
    assert payload["data"]["discovered"] == 2
    assert payload["data"]["unsupported"] == 1
    assert [Path(path).name for path in payload["data"]["inputs"]] == [
        "water.xyz",
        "hydrogen.xyz",
    ]


def test_batch_progress_uses_stderr_and_quiet_suppresses_it(tmp_path: Path) -> None:
    visible = run_cli(
        "--format",
        "json",
        "batch",
        str(WATER),
        "--output-dir",
        str(tmp_path / "visible"),
    )
    quiet = run_cli(
        "--quiet",
        "batch",
        str(WATER),
        "--output-dir",
        str(tmp_path / "quiet"),
    )

    assert visible.returncode == quiet.returncode == 0
    assert "Batch 1/1: success" in visible.stderr
    assert "Batch 1/1:" not in quiet.stderr
    assert json.loads(visible.stdout)["kind"] == "batch"


def test_cli_batch_format_map_paths_are_relative_to_map(tmp_path: Path) -> None:
    fixture = ROOT / "tests" / "fixtures" / "interop" / "gamess" / "water.dat"
    source = tmp_path / "water.dat"
    source.write_bytes(fixture.read_bytes())
    mapping = tmp_path / "formats.json"
    mapping.write_text(json.dumps({"water.dat": "gamess"}), encoding="utf-8")

    result = run_cli(
        "--format", "json", "batch", str(source),
        "--format-map", str(mapping), "--output-dir", str(tmp_path / "results"),
    )

    assert result.returncode == 0, result.stderr
    assert json.loads(result.stdout)["data"]["inputs"] == 1
    manifest = json.loads((tmp_path / "results" / "batch-manifest.json").read_text())
    assert manifest["records"][0]["source_format"] == "gamess"


def test_batch_exit_reflects_records(tmp_path: Path) -> None:
    bad = tmp_path / "bad.xyz"
    bad.write_text("not xyz\n", encoding="utf-8")
    failed = run_cli(
        "--format", "json", "batch", str(WATER), str(bad),
        "--output-dir", str(tmp_path / "failed"),
    )
    assert failed.returncode != 0
    failed_payload = json.loads(failed.stdout)
    assert failed_payload["status"] == "failed"
    assert failed_payload["data"]["successes"] == 1
    assert failed_payload["data"]["errors"] == 1

    partial_xyz = tmp_path / "structure.xyz"
    partial_xyz.write_text("1\nH\nH 0 0 0\n", encoding="utf-8")
    partial = run_cli(
        "--format", "json", "batch", str(partial_xyz),
        "--output-dir", str(tmp_path / "partial"),
    )
    assert partial.returncode == 0, partial.stderr
    assert json.loads(partial.stdout)["status"] == "partial"


def test_all_unsupported_writes_manifest(tmp_path: Path) -> None:
    directory = tmp_path / "inputs"
    directory.mkdir()
    source = directory / "ambiguous.dat"
    source.write_text("not recognized\n", encoding="utf-8")
    output = tmp_path / "results"

    result = run_cli("--format", "json", "batch", str(directory), "--output-dir", str(output))

    assert result.returncode != 0
    assert json.loads(result.stdout)["status"] == "failed"
    manifest = json.loads((output / "batch-manifest.json").read_text())
    assert manifest["records"] == []
    assert manifest["unsupported_details"][0]["path"] == str(source)
    assert manifest["unsupported_details"][0]["reason"]
    assert len(manifest["unsupported_details"][0]["sha256"]) == 64


def test_fail_fast_reports_attempted_subset(tmp_path: Path) -> None:
    first = tmp_path / "bad.xyz"
    first.write_text("broken\n", encoding="utf-8")
    output = tmp_path / "results"
    result = run_cli(
        "--format", "json", "batch", str(first), str(WATER),
        "--fail-fast", "--output-dir", str(output),
    )
    assert result.returncode != 0
    payload = json.loads(result.stdout)
    assert payload["data"]["attempted"] == 1
    assert payload["data"]["stopped_early"] is True
    manifest = json.loads((output / "batch-manifest.json").read_text())
    assert manifest["attempted_count"] == 1
    assert manifest["stopped_early"] is True


def test_invalid_format_map_is_one_json_failure(tmp_path: Path) -> None:
    mapping = tmp_path / "invalid.json"
    mapping.write_text("[not a map]", encoding="utf-8")
    result = run_cli(
        "--format", "json", "batch", str(WATER), "--format-map", str(mapping),
        "--output-dir", str(tmp_path / "results"),
    )
    assert result.returncode != 0
    payload = json.loads(result.stdout)
    assert payload["status"] == "failed"
    assert "Invalid format map" in payload["error"]["message"]
