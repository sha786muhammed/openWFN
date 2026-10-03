"""Permanent contract for native Hirshfeld independent validation evidence."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
VALIDATION = ROOT / "validation" / "hirshfeld"
REFERENCE = VALIDATION / "reference-report.json"
CONVERGENCE = VALIDATION / "convergence-report.json"

REQUIRED_CASES = {
    "water",
    "methane",
    "ammonia",
    "carbon_dioxide",
    "benzene",
    "ethanol",
    "ammonium_cation",
    "oxygen_triplet",
    "oh_diffuse_uhf",
    "water_dimer",
}


def _load(path: Path) -> dict[str, object]:
    return json.loads(path.read_text(encoding="utf-8"))


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_hirshfeld_reference_capture_is_complete_and_auditable() -> None:
    reference = _load(REFERENCE)

    assert reference["schema_version"] == "1.0"
    assert reference["method"] == "Hirshfeld"
    assert reference["external_reference"]["tool"] == "HORTON-PART"
    assert reference["external_reference"]["runtime_dependency"] is False
    assert reference["reference_library"]["id"] == "openwfn-hirshfeld-proatoms-v1"
    assert len(reference["reference_library"]["sha256"]) == 64
    assert reference["acceptance"]["max_per_atom_external_difference_e"] == pytest.approx(1.0e-3)

    cases = {case["id"]: case for case in reference["cases"]}
    assert set(cases) == REQUIRED_CASES
    for case_id, case in cases.items():
        source = ROOT / case["input_path"]
        assert source.is_file()
        assert case["input_sha256"] == _sha256(source)
        assert case["external_tool_version"]
        assert case["openwfn_standard_status"] in {"success", "partial"}
        assert case["external_charges_e"]
        assert len(case["openwfn_standard_charges_e"]) == len(case["external_charges_e"])
        observed = max(
            abs(float(left) - float(right))
            for left, right in zip(
                case["openwfn_standard_charges_e"], case["external_charges_e"], strict=True
            )
        )
        assert case["max_abs_external_difference_e"] == pytest.approx(observed, abs=1.0e-12)
        expected_pass = observed <= float(
            reference["acceptance"]["max_per_atom_external_difference_e"]
        )
        assert case["external_gate_passed"] is expected_pass
        assert case["ordinary_hirshfeld_uses_total_density"] is True
        if case_id in {"oxygen_triplet", "oh_diffuse_uhf"}:
            assert case["open_shell"] is True
        if case_id == "ammonium_cation":
            assert case["molecular_charge"] == 1


def test_hirshfeld_convergence_capture_enforces_promotion_gate() -> None:
    convergence = _load(CONVERGENCE)

    assert convergence["schema_version"] == "1.0"
    assert convergence["method"] == "Hirshfeld"
    assert convergence["acceptance"]["max_per_atom_grid_shift_e"] == pytest.approx(5.0e-4)
    assert convergence["standard_settings"] == {
        "radial_points": 96,
        "theta_points": 18,
        "phi_points": 36,
        "radial_extent_bohr": 20.0,
        "chunk_size": 65536,
    }
    assert convergence["fine_settings"] == {
        "radial_points": 144,
        "theta_points": 24,
        "phi_points": 48,
        "radial_extent_bohr": 24.0,
        "chunk_size": 65536,
    }

    cases = {case["id"]: case for case in convergence["cases"]}
    assert set(cases) == REQUIRED_CASES
    for case in cases.values():
        observed = max(
            abs(float(left) - float(right))
            for left, right in zip(
                case["standard_charges_e"], case["fine_charges_e"], strict=True
            )
        )
        assert case["max_abs_charge_shift_e"] == pytest.approx(observed, abs=1.0e-12)
        expected_pass = (
            case["standard_status"] == "success"
            and case["fine_status"] == "success"
            and observed <= float(convergence["acceptance"]["max_per_atom_grid_shift_e"])
        )
        assert case["convergence_gate_passed"] is expected_pass


def test_hirshfeld_promotion_scope_is_derived_from_both_evidence_gates() -> None:
    reference = _load(REFERENCE)
    convergence = _load(CONVERGENCE)
    convergence_cases = {case["id"]: case for case in convergence["cases"]}

    passing = sorted(
        case["id"]
        for case in reference["cases"]
        if case["external_gate_passed"]
        and convergence_cases[case["id"]]["convergence_gate_passed"]
    )
    assert reference["validated_case_ids"] == passing
    assert convergence["validated_case_ids"] == passing

    promotion = reference["promotion_status"]
    assert promotion in {"Validated", "Experimental"}
    if promotion == "Validated":
        assert set(passing) == REQUIRED_CASES
    else:
        assert set(passing) != REQUIRED_CASES
