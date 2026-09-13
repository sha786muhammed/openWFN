import json
from pathlib import Path

import pytest

from openwfn.batch import BATCH_SCHEMA_VERSION, run_batch

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
