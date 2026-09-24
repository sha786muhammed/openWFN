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


def test_multiwfn_references_are_active_complete_and_match_manifest() -> None:
    payload = json.loads(MANIFEST.read_text(encoding="utf-8"))
    cases = {case["id"]: case for case in payload["cases"]}

    for case_id in ("water-multiwfn", "lih-multiwfn", "acetylene"):
        case = cases[case_id]
        assert case["status"] == "active"
        assert case["reference"]["program"] == "Multiwfn"
        evidence_path = ROOT / case["reference"]["evidence_file"]
        evidence = json.loads(evidence_path.read_text(encoding="utf-8"))
        assert evidence["program"] == "Multiwfn"
        assert evidence["program_version"] == case["reference"]["version"]
        assert evidence["input_sha256"] == case["sha256"]
        assert re.fullmatch(r"[0-9a-f]{40}", evidence["openwfn_commit"])
        for name in (
            "binary_sha256",
            "settings_sha256",
            "procedure_sha256",
            "transcript_sha256",
        ):
            assert re.fullmatch(r"[0-9a-f]{64}", evidence[name])
        assert evidence["platform"]["host"] == "NASAKY"
        assert evidence["platform"]["threads"] == 4
        expected_metrics = {metric["name"]: metric["expected"] for metric in case["metrics"]}
        evidence_metrics = {metric["name"]: metric["value"] for metric in evidence["metrics"]}
        assert evidence_metrics == expected_metrics
        manifest_tolerances = {
            metric["name"]: metric.get(
                "absolute_tolerance", metric.get("max_absolute_tolerance")
            )
            for metric in case["metrics"]
        }
        evidence_tolerances = {
            metric["name"]: metric["absolute_tolerance"]
            for metric in evidence["metrics"]
        }
        assert evidence_tolerances == manifest_tolerances
