import json
from pathlib import Path

from openwfn.batch import run_batch

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
