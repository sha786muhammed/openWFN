"""Independent numerical references for equivalent and program-output fixtures."""

import json
from pathlib import Path

from scripts.run_interop_validation import run

ROOT = Path(__file__).resolve().parents[2]
MANIFEST = ROOT / "validation/interop/cross_format_manifest.json"


def test_cross_format_manifest_has_explicit_reference_and_tolerances() -> None:
    payload = json.loads(MANIFEST.read_text(encoding="utf-8"))
    assert payload["schema_version"] == "1.0"
    assert {case["format_id"] for case in payload["equivalent_water"]} == {
        "fchk", "molden", "wfn", "wfx", "mwfn"
    }
    assert {case["format_id"] for case in payload["program_references"]} == {
        "orcalog", "qchemlog", "gamess", "cp2klog"
    }
    for case in (*payload["equivalent_water"], *payload["program_references"]):
        assert len(case["sha256"]) == 64
        assert case["metrics"]
        assert all("expected" in metric and "absolute_tolerance" in metric
                   for metric in case["metrics"])
        assert all(metric["absolute_tolerance"] >= 0 for metric in case["metrics"])


def test_cross_format_report_passes_and_is_a_separate_release_gate(tmp_path: Path) -> None:
    report = run(ROOT / "validation/interop/manifest.json", output_dir=tmp_path)
    cross = report["cross_format"]
    assert cross["status"] == "PASSED"
    assert cross["failed"] == 0
    assert cross["results"]
    assert all({"expected", "observed", "absolute_error", "tolerance", "status"} <= set(item)
               for item in cross["results"])
    assert "Cross-format scientific equivalence" in (tmp_path / "report.md").read_text()


def test_cross_format_gate_detects_bad_reference(tmp_path: Path) -> None:
    payload = json.loads(MANIFEST.read_text(encoding="utf-8"))
    payload["equivalent_water"][0]["metrics"][0]["expected"] = 999
    altered = tmp_path / "bad-reference.json"
    altered.write_text(json.dumps(payload), encoding="utf-8")
    report = run(ROOT / "validation/interop/manifest.json", output_dir=tmp_path,
                 cross_manifest_path=altered)
    assert report["overall"] == "FAILED"
    assert report["cross_format"]["failed"] >= 1
