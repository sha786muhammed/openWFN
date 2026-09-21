from pathlib import Path

import pytest

import openwfn
from openwfn.errors import DataUnavailableError
from openwfn.services import geometry_distance

ROOT = Path(__file__).resolve().parents[2]


def test_python_api_and_service_return_same_distance() -> None:
    calculation = openwfn.load(ROOT / "examples" / "water" / "water.fchk")

    api_result = calculation.geometry_distance(1, 2)
    service_result = geometry_distance(calculation.molecule, 1, 2)

    assert api_result == service_result
    assert api_result.data["value"] == pytest.approx(0.966598)


def test_python_api_exposes_molecular_summary() -> None:
    calculation = openwfn.load(ROOT / "examples" / "water" / "water.fchk")

    summary = calculation.analyze_geometry()

    assert summary["atom_count"] == 3
    assert summary["charge"] == 0
    assert summary["multiplicity"] == 1


def test_python_api_runs_registered_analysis_with_provenance() -> None:
    calculation = openwfn.load(ROOT / "examples" / "water" / "water.fchk")

    result = calculation.analyze("summary")

    assert result.analysis_name == "summary"
    assert result.data["formula"] == "H2O"
    assert result.provenance["source_format"] == "fchk"
    assert result.provenance["input_sha256"] == calculation.molecule.provenance.sha256


def test_python_api_exposes_frontier_orbitals() -> None:
    calculation = openwfn.load(ROOT / "examples" / "water" / "water.fchk")

    result = calculation.orbitals()

    assert result.kind == "frontier_orbitals"
    assert result.data["homo_number"] == 5
    assert result.data["lumo_number"] == 6


def test_python_api_exposes_population_analysis() -> None:
    calculation = openwfn.load(ROOT / "examples" / "water" / "water.fchk")

    result = calculation.population("mulliken")

    assert result.kind == "mulliken_population"
    assert result.data["electron_count"] == pytest.approx(10.0, abs=1e-6)


def test_python_api_exposes_density_integration() -> None:
    calculation = openwfn.load(ROOT / "examples" / "water" / "water.fchk")

    result = calculation.density(spacing_bohr=0.35, padding_bohr=4.0)

    assert result.kind == "density_integration"
    assert result.data["density_kind"] == "total"
    assert result.data["expected_electrons"] == 10.0


def test_v08_model_foundation_is_available_from_top_level_package() -> None:
    assert openwfn.MODEL_SCHEMA_VERSION == "2.0"
    assert openwfn.BoundaryConditions().kind == "isolated"
    assert openwfn.CalculationData is not None
    assert openwfn.Provenance is not None
    assert {
        "MODEL_SCHEMA_VERSION",
        "BoundaryConditions",
        "CalculationData",
        "Provenance",
    }.issubset(openwfn.__all__)


def test_result_contract_and_registry_are_available_from_top_level_package() -> None:
    assert openwfn.RESULT_SCHEMA_VERSION == "1.0"
    assert "summary" in openwfn.available_analyses()
    assert {
        "RESULT_SCHEMA_VERSION",
        "ResultRecord",
        "available_analyses",
        "run_analysis",
    }.issubset(openwfn.__all__)


def test_batch_contract_is_available_from_top_level_package() -> None:
    assert openwfn.BATCH_SCHEMA_VERSION == "1.0"
    assert "run_batch" in openwfn.__all__
    assert callable(openwfn.discover_inputs)
    assert "discover_inputs" in openwfn.__all__


def test_load_rejects_metadata_only_input_with_accurate_message(tmp_path: Path) -> None:
    source = tmp_path / "job.log"
    source.write_text(
        "# RHF/3-21G\nSCF Done: E(RHF) = -7.5\nNormal termination of Gaussian\n",
        encoding="utf-8",
    )

    with pytest.raises(DataUnavailableError, match="calculation metadata"):
        openwfn.load(source)
