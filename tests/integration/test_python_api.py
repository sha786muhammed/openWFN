from pathlib import Path

import pytest

import openwfn
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
