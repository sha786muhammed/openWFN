import json
import subprocess
import sys
from hashlib import sha256
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
MANIFEST = ROOT / "validation" / "manifest.json"
REQUIRED = {
    "water", "carbon-dioxide", "methane", "ammonia", "oxygen", "ethanol",
    "water-dimer", "benzene", "polarization", "transition-metal",
}


def test_manifest_has_required_cases_provenance_and_tolerances() -> None:
    payload = json.loads(MANIFEST.read_text(encoding="utf-8"))

    assert payload["schema_version"] == "1.0"
    assert {case["id"] for case in payload["cases"]} == REQUIRED
    for case in payload["cases"]:
        assert case["origin"]
        assert case["generation_procedure"]
        assert case["redistribution_status"]
        if case["status"] == "active":
            assert case["software"]
            assert case["method"] and case["basis"]
            assert case["targets"]
            assert all("absolute_tolerance" in target for target in case["targets"])
        else:
            assert case["status"] == "pending"
            assert case["reason"]


def test_active_reference_checksums_match_files() -> None:
    payload = json.loads(MANIFEST.read_text(encoding="utf-8"))
    for case in payload["cases"]:
        if case["status"] != "active":
            continue
        source = ROOT / case["path"]
        assert sha256(source.read_bytes()).hexdigest() == case["sha256"]


def test_validation_runner_writes_machine_and_human_reports(tmp_path: Path) -> None:
    result = subprocess.run(
        [sys.executable, str(ROOT / "scripts" / "run_validation.py"), "--output-dir", str(tmp_path)],
        cwd=ROOT,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0, result.stderr
    payload = json.loads((tmp_path / "results.json").read_text(encoding="utf-8"))
    assert payload["status"] == "passed"
    assert all(item["status"] in {"passed", "pending"} for item in payload["results"])
    report = (tmp_path / "report.md").read_text(encoding="utf-8")
    assert "# openWFN Scientific Validation Report" in report
    assert "Observed" in report and "Tolerance" in report
