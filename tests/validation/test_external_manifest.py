import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
MANIFEST = ROOT / "validation" / "external" / "manifest.json"
REQUIRED_CASES = {
    "water",
    "benzene",
    "lih",
    "oxygen-pure",
    "oxygen-cartesian",
    "acetylene",
    "helium-high-l",
    "water-multiwfn",
    "lih-multiwfn",
}


def test_external_manifest_has_required_cases_and_states() -> None:
    payload = json.loads(MANIFEST.read_text(encoding="utf-8"))

    assert payload["schema_version"] == "1.0"
    case_ids = [case["id"] for case in payload["cases"]]
    assert REQUIRED_CASES <= set(case_ids)
    assert len(case_ids) == len(set(case_ids))
    assert {case["status"] for case in payload["cases"]} <= {"active", "pending"}


def test_external_manifest_requires_complete_evidence_before_activation() -> None:
    payload = json.loads(MANIFEST.read_text(encoding="utf-8"))

    for case in payload["cases"]:
        assert case["provenance"]["origin"]
        assert case["provenance"]["redistribution_status"]
        if case["status"] == "pending":
            assert case["reason"]
            assert "passed" not in case
            continue

        assert case["input"]
        assert re.fullmatch(r"[0-9a-f]{64}", case["sha256"])
        assert case["provenance"]["generation_procedure"]
        assert case["provenance"]["upstream_commit"]
        assert case["reference"]["program"]
        assert case["reference"]["version"]
        assert case["reference"]["procedure"]
        assert case["metrics"]
        for metric in case["metrics"]:
            assert metric["name"]
            assert metric["unit"]
            assert "expected" in metric
            assert (
                "absolute_tolerance" in metric
                or "max_absolute_tolerance" in metric
            )
