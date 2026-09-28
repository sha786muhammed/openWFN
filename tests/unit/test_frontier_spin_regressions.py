from pathlib import Path

import pytest

import openwfn
from openwfn import scientific
from openwfn.analysis.orbitals import frontier_orbitals
from openwfn.analysis.registry import available_analyses
from openwfn.model import MolecularOrbitals
from openwfn.parsers.gaussian.fchk import parse_fchk
from openwfn.services import orbital_frontier

ROOT = Path(__file__).resolve().parents[2]
FIXTURES = ROOT / "tests" / "fixtures" / "scientific"
WATER = ROOT / "examples" / "water" / "water.fchk"


def test_frontier_selection_uses_occupations_not_array_adjacency() -> None:
    orbitals = MolecularOrbitals(
        energies=(-0.8, 0.1, -0.2, 0.3),
        coefficients=(
            (1.0, 0.0, 0.0, 0.0),
            (0.0, 1.0, 0.0, 0.0),
            (0.0, 0.0, 1.0, 0.0),
            (0.0, 0.0, 0.0, 1.0),
        ),
        occupations=(2.0, 0.0, 1.0, 0.0),
        spin="restricted",
    )

    frontier = frontier_orbitals(orbitals)

    assert frontier.homo_index == 2
    assert frontier.homo_hartree == pytest.approx(-0.2)
    assert frontier.lumo_index == 1
    assert frontier.lumo_hartree == pytest.approx(0.1)


def test_frontier_all_reports_true_beta_homo_for_unrestricted_fixture() -> None:
    data = parse_fchk(FIXTURES / "uhf_beta_homo.fchk")

    result = orbital_frontier(data, "all")

    assert result.data["reference_kind"] == "unrestricted"
    assert result.data["alpha"]["homo_hartree"] == pytest.approx(-0.7)
    assert result.data["beta"]["homo_hartree"] == pytest.approx(-0.5)
    assert result.data["overall_homo_hartree"] == pytest.approx(-0.5)
    assert result.data["overall_homo_spin"] == "beta"
    assert result.data["overall_homo_number"] == 1


def test_alpha_frontier_warns_when_beta_channel_exists() -> None:
    data = parse_fchk(FIXTURES / "uhf_beta_homo.fchk")

    result = orbital_frontier(data, "alpha")

    assert result.data["reference_kind"] == "unrestricted"
    assert any("beta" in warning.lower() and "complete" in warning.lower() for warning in result.warnings)


def test_rohf_and_closed_shell_reference_kinds_are_distinguished() -> None:
    classify = getattr(scientific, "orbital_reference_kind")

    rohf = parse_fchk(FIXTURES / "rohf_open_shell.fchk")
    water = parse_fchk(WATER)

    assert classify(rohf) == "restricted_open_shell"
    assert classify(water) == "restricted_closed_shell"


def test_fchk_orbitals_expose_synthesized_occupation_source() -> None:
    data = parse_fchk(FIXTURES / "rohf_open_shell.fchk")

    assert data.alpha_orbitals is not None
    assert data.alpha_orbitals.occupation_source == "electron-count filling"


def test_python_api_accepts_all_spin_frontier() -> None:
    calculation = openwfn.load(FIXTURES / "uhf_beta_homo.fchk")

    result = calculation.orbitals("all")

    assert result.data["overall_homo_spin"] == "beta"


def test_registry_exposes_spin_complete_frontier_analysis() -> None:
    assert "frontier-all" in available_analyses()


def test_all_occupied_frontier_has_clear_no_lumo_error() -> None:
    orbitals = MolecularOrbitals(
        energies=(-0.5, -0.2),
        coefficients=((1.0, 0.0), (0.0, 1.0)),
        occupations=(2.0, 2.0),
    )

    with pytest.raises(ValueError, match="LUMO"):
        frontier_orbitals(orbitals)
