import csv
import json
import shutil
from pathlib import Path

import pytest

from openwfn.batch import BATCH_SCHEMA_VERSION, discover_inputs, run_batch

ROOT = Path(__file__).resolve().parents[2]


def test_batch_manifest_is_deterministic_and_records_bad_input(tmp_path: Path) -> None:
    good = ROOT / "examples" / "water" / "water.fchk"
    bad = tmp_path / "bad.xyz"
    bad.write_text("not an xyz", encoding="utf-8")

    manifest = run_batch(
        inputs=[good, bad],
        operation="summary",
        workers=1,
        output_dir=tmp_path / "results",
    )

    assert [record.status for record in manifest.records] == ["success", "error"]
    saved = json.loads((tmp_path / "results" / "batch-manifest.json").read_text(encoding="utf-8"))
    assert [Path(item["input_path"]).name for item in saved["records"]] == ["water.fchk", "bad.xyz"]
    assert "generated_at" not in saved


def test_batch_fail_fast_stops_after_first_error(tmp_path: Path) -> None:
    bad = tmp_path / "bad.xyz"
    bad.write_text("broken", encoding="utf-8")
    good = ROOT / "examples" / "water" / "water.fchk"

    manifest = run_batch(
        inputs=[bad, good],
        operation="summary",
        workers=1,
        output_dir=tmp_path / "results",
        fail_fast=True,
    )

    assert len(manifest.records) == 1
    assert manifest.records[0].status == "error"


def test_batch_manifest_records_multiple_versioned_analysis_results(tmp_path: Path) -> None:
    water = ROOT / "examples" / "water" / "water.fchk"
    output_dir = tmp_path / "results"

    manifest = run_batch(
        inputs=[water],
        operation=None,
        analyses=("summary", "frontier"),
        workers=1,
        output_dir=output_dir,
    )

    assert BATCH_SCHEMA_VERSION == "1.0"
    assert manifest.schema_version == "1.0"
    assert manifest.analyses == ("summary", "frontier")
    assert manifest.records[0].status == "success"
    assert len(manifest.records[0].input_sha256) == 64
    assert [result.analysis_name for result in manifest.records[0].results] == [
        "summary",
        "frontier",
    ]

    saved = json.loads((output_dir / "batch-manifest.json").read_text(encoding="utf-8"))
    assert saved["schema_version"] == "1.0"
    assert saved["analyses"] == ["summary", "frontier"]
    assert [result["analysis_name"] for result in saved["records"][0]["results"]] == [
        "summary",
        "frontier",
    ]
    assert saved["records"][0]["input_sha256"] == manifest.records[0].input_sha256


def test_batch_marks_input_partial_when_one_analysis_is_unavailable(tmp_path: Path) -> None:
    xyz = tmp_path / "water.xyz"
    xyz.write_text("3\nwater\nO 0 0 0\nH 0 0 1\nH 1 0 0\n", encoding="utf-8")

    manifest = run_batch(
        inputs=[xyz],
        operation=None,
        analyses=("summary", "frontier"),
        workers=1,
        output_dir=tmp_path / "results",
    )

    record = manifest.records[0]
    assert record.status == "partial"
    assert [result.status for result in record.results] == ["success", "failed"]
    assert record.results[1].error is not None
    assert record.results[1].error.category == "DataUnavailableError"


def test_batch_rejects_unknown_analysis_before_creating_output(tmp_path: Path) -> None:
    output_dir = tmp_path / "results"

    with pytest.raises(ValueError, match="Unknown batch analyses: missing.*summary"):
        run_batch(
            inputs=[ROOT / "examples" / "water" / "water.fchk"],
            operation=None,
            analyses=("summary", "missing"),
            workers=1,
            output_dir=output_dir,
        )

    assert not output_dir.exists()


def test_batch_resume_reuses_matching_per_input_result(tmp_path: Path) -> None:
    source = ROOT / "examples" / "water" / "water.fchk"
    water = tmp_path / "water.fchk"
    shutil.copyfile(source, water)
    output_dir = tmp_path / "results"

    first = run_batch(
        inputs=[water],
        operation=None,
        analyses=("summary", "frontier"),
        workers=1,
        output_dir=output_dir,
    )
    record_path = next((output_dir / "records").glob("*.json"))
    saved_record = record_path.read_text(encoding="utf-8")

    resumed = run_batch(
        inputs=[water],
        operation=None,
        analyses=("summary", "frontier"),
        workers=1,
        output_dir=output_dir,
        resume=True,
    )

    assert first.records[0].skipped is False
    assert resumed.records[0].skipped is True
    assert resumed.records[0].results == first.records[0].results
    assert record_path.read_text(encoding="utf-8") == saved_record
    assert len(resumed.configuration_fingerprint) == 64
    manifest = json.loads((output_dir / "batch-manifest.json").read_text(encoding="utf-8"))
    assert manifest["configuration_fingerprint"] == resumed.configuration_fingerprint
    assert manifest["records"][0]["skipped"] is True


def test_batch_resume_recomputes_when_input_checksum_changes(tmp_path: Path) -> None:
    source = ROOT / "examples" / "water" / "water.fchk"
    water = tmp_path / "water.fchk"
    shutil.copyfile(source, water)
    output_dir = tmp_path / "results"
    first = run_batch([water], "summary", 1, output_dir)

    water.write_text(water.read_text(encoding="utf-8") + "\n", encoding="utf-8")
    resumed = run_batch([water], "summary", 1, output_dir, resume=True)

    assert resumed.records[0].skipped is False
    assert resumed.records[0].input_sha256 != first.records[0].input_sha256


def test_batch_writes_manifest_and_records_atomically(tmp_path: Path) -> None:
    output_dir = tmp_path / "results"

    run_batch(
        [ROOT / "examples" / "water" / "water.fchk"],
        "summary",
        1,
        output_dir,
    )

    assert (output_dir / "batch-manifest.json").exists()
    assert len(list((output_dir / "records").glob("*.json"))) == 1
    assert not list(output_dir.rglob("*.tmp"))


def test_discovery_is_recursive_deduplicated_and_ignores_output_directory(
    tmp_path: Path,
) -> None:
    root = tmp_path / "calculations"
    nested = root / "nested"
    output_dir = root / "results"
    nested.mkdir(parents=True)
    output_dir.mkdir()
    first = root / "first.xyz"
    second = nested / "second.xyz"
    first.write_text("1\nfirst\nH 0 0 0\n", encoding="utf-8")
    second.write_text("1\nsecond\nH 0 0 0\n", encoding="utf-8")
    (root / "notes.txt").write_text("ignore", encoding="utf-8")
    (output_dir / "cached.xyz").write_text("1\ncached\nH 0 0 0\n", encoding="utf-8")

    shallow = discover_inputs([root, first], recursive=False, output_dir=output_dir)
    recursive = discover_inputs([root, first], recursive=True, output_dir=output_dir)

    assert shallow.inputs == (first,)
    assert shallow.unsupported == (root / "notes.txt",)
    assert recursive.inputs == (first, second)
    assert recursive.unsupported == (root / "notes.txt",)


def test_directory_batch_writes_compact_csv_index(tmp_path: Path) -> None:
    root = tmp_path / "calculations"
    root.mkdir()
    (root / "hydrogen.xyz").write_text("1\nhydrogen\nH 0 0 0\n", encoding="utf-8")
    (root / "helium.xyz").write_text("1\nhelium\nHe 0 0 0\n", encoding="utf-8")
    output_dir = tmp_path / "results"

    manifest = run_batch(
        [root],
        "summary",
        1,
        output_dir,
        recursive=True,
    )

    assert len(manifest.records) == 2
    assert manifest.unsupported_inputs == ()
    with (output_dir / "batch-summary.csv").open(newline="", encoding="utf-8") as stream:
        rows = list(csv.DictReader(stream))
    assert [Path(row["input_path"]).name for row in rows] == ["helium.xyz", "hydrogen.xyz"]
    assert [row["status"] for row in rows] == ["success", "success"]
    assert [row["analysis_successes"] for row in rows] == ["1", "1"]
    assert [row["analysis_failures"] for row in rows] == ["0", "0"]
