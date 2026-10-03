import json
from pathlib import Path

import pytest

from openwfn.analysis.atom_quadrature import AtomQuadratureSettings
from openwfn.analysis.hirshfeld import HirshfeldSettings
from openwfn.analysis.registry import available_analyses, run_analysis
from openwfn.api import load
from openwfn.parsers.gaussian.fchk import parse_fchk
from openwfn.services import hirshfeld_population_analysis

ROOT = Path(__file__).resolve().parents[1]
WATER = ROOT / "examples" / "water" / "water.fchk"


def _assert_hirshfeld_record(record) -> None:
    assert record.kind == "hirshfeld_population"
    assert record.status == "success"
    assert record.validation_status == "Experimental"
    assert record.data["method"] == "Hirshfeld"
    assert len(record.data["atoms"]) == 3
    assert record.data["atoms"][0]["atom_index"] == 1
    assert record.data["atoms"][0]["element"] == "O"
    assert record.data["atoms"][0]["effective_nuclear_charge"] == pytest.approx(8.0)
    assert record.data["diagnostics"]["expected_electrons"] == pytest.approx(10.0)
    assert record.data["diagnostics"]["electron_count_residual"] <= 5.0e-3
    assert record.data["diagnostics"]["population_partition_residual"] <= 1.0e-8
    assert record.data["diagnostics"]["charge_closure_residual"] <= 5.0e-3
    assert record.data["diagnostics"]["unresolved_promolecule_points"] == 0
    assert record.data["reference_library"]["id"] == "openwfn-hirshfeld-proatoms-v1"
    assert len(record.data["reference_library"]["sha256"]) == 64
    assert record.data["density_source"] is not None
    assert record.data["quadrature"] == {
        "radial_points": 96,
        "theta_points": 18,
        "phi_points": 36,
        "radial_extent_bohr": 20.0,
        "chunk_size": 65536,
    }


def test_hirshfeld_service_registry_and_python_api_have_numeric_parity() -> None:
    data = parse_fchk(WATER)

    service = hirshfeld_population_analysis(data)
    registered = run_analysis(data, "hirshfeld")
    calculation = load(WATER)
    dedicated = calculation.hirshfeld()
    discoverable = calculation.population("hirshfeld")

    for record in (service, registered, dedicated, discoverable):
        _assert_hirshfeld_record(record)

    assert registered.analysis_name == "hirshfeld"
    assert registered.analysis_version == "1"
    assert registered.data == dedicated.data == discoverable.data
    assert registered.status == dedicated.status == discoverable.status
    assert registered.validation_status == dedicated.validation_status == discoverable.validation_status
    assert "hirshfeld" in available_analyses()


def test_registry_forwards_expert_hirshfeld_settings_without_hidden_defaults() -> None:
    data = parse_fchk(WATER)
    settings = HirshfeldSettings(
        quadrature=AtomQuadratureSettings(
            radial_points=8,
            theta_points=4,
            phi_points=8,
            radial_extent_bohr=0.5,
            chunk_size=512,
        )
    )

    record = run_analysis(data, "hirshfeld", settings=settings)

    assert record.status == "partial"
    assert record.validation_status == "Experimental"
    assert record.data["quadrature"]["radial_points"] == 8
    assert record.data["quadrature"]["radial_extent_bohr"] == pytest.approx(0.5)
    assert record.data["diagnostics"]["charge_closure_residual"] > 0.1
    assert any("not renormalized" in warning.lower() for warning in record.warnings)


def test_python_hirshfeld_settings_match_registry() -> None:
    calculation = load(WATER)
    settings = HirshfeldSettings(
        quadrature=AtomQuadratureSettings(radial_points=48, theta_points=12, phi_points=24)
    )

    direct = calculation.hirshfeld(settings=settings)
    registered = calculation.analyze("hirshfeld", settings=settings)

    assert direct.data == registered.data
    assert direct.status == registered.status
    assert direct.validation_status == registered.validation_status


def test_hirshfeld_result_is_json_serializable_without_custom_objects() -> None:
    record = hirshfeld_population_analysis(parse_fchk(WATER))

    payload = json.loads(json.dumps(record.data))

    assert payload["method"] == "Hirshfeld"
    assert isinstance(payload["atoms"], list)
    assert isinstance(payload["quadrature"], dict)
    assert isinstance(payload["diagnostics"], dict)
