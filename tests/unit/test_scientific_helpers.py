import importlib
import importlib.util
from pathlib import Path

import pytest

from openwfn.errors import DataUnavailableError
from openwfn.model import Atom, CalculationData, CalculationMetadata, MolecularOrbitals, Molecule
from openwfn.parsers.gaussian.fchk import parse_fchk

ROOT = Path(__file__).resolve().parents[2]
FIXTURES = ROOT / "tests" / "fixtures" / "scientific"


def _scientific_module():
    spec = importlib.util.find_spec("openwfn.scientific")
    assert spec is not None, "openwfn.scientific must define source-faithful scientific helpers"
    return importlib.import_module("openwfn.scientific")


def test_expected_electron_count_prefers_fchk_records() -> None:
    scientific = _scientific_module()
    data = parse_fchk(FIXTURES / "ecp_minimal.fchk")

    total = scientific.expected_electron_count(data, "total")
    alpha = scientific.expected_electron_count(data, "alpha")
    beta = scientific.expected_electron_count(data, "beta")
    spin = scientific.expected_electron_count(data, "spin")

    assert (total.value, total.source, total.warnings) == (4.0, "Number of electrons", ())
    assert (alpha.value, alpha.source) == (2.0, "Number of alpha electrons")
    assert (beta.value, beta.source) == (2.0, "Number of beta electrons")
    assert (spin.value, spin.source) == (0.0, "alpha-beta electron counts")


def test_expected_spin_counts_fall_back_to_unrestricted_orbital_occupations() -> None:
    scientific = _scientific_module()
    molecule = Molecule(
        atoms=(Atom(1, (0.0, 0.0, 0.0)),),
        charge=0,
        multiplicity=2,
        metadata=CalculationMetadata("fixture"),
    )
    alpha = MolecularOrbitals((-0.5,), ((1.0,),), (1.0,), spin="alpha")
    beta = MolecularOrbitals((-0.2,), ((1.0,),), (0.0,), spin="beta")
    data = CalculationData(molecule, alpha_orbitals=alpha, beta_orbitals=beta)

    assert scientific.expected_electron_count(data, "alpha") == scientific.ElectronExpectation(
        1.0, "alpha orbital occupations"
    )
    assert scientific.expected_electron_count(data, "beta") == scientific.ElectronExpectation(
        0.0, "beta orbital occupations"
    )
    assert scientific.expected_electron_count(data, "spin") == scientific.ElectronExpectation(
        1.0, "alpha-beta orbital occupations"
    )


def test_expected_spin_count_is_unavailable_without_both_orbital_channels() -> None:
    scientific = _scientific_module()
    molecule = Molecule(
        atoms=(Atom(1, (0.0, 0.0, 0.0)),),
        charge=0,
        multiplicity=2,
        metadata=CalculationMetadata("fixture"),
    )
    alpha = MolecularOrbitals((-0.5,), ((1.0,),), (1.0,), spin="alpha")

    with pytest.raises(DataUnavailableError, match="Expected electron count"):
        scientific.expected_electron_count(CalculationData(molecule, alpha_orbitals=alpha), "spin")


def test_expected_electron_count_uses_effective_nuclear_charge_before_atomic_number() -> None:
    scientific = _scientific_module()
    molecule = Molecule(
        atoms=(Atom(14, (0.0, 0.0, 0.0), nuclear_charge=4.0),),
        charge=0,
        multiplicity=1,
        metadata=CalculationMetadata("fixture"),
    )

    expectation = scientific.expected_electron_count(CalculationData(molecule), "total")

    assert expectation.value == 4.0
    assert expectation.source == "effective nuclear charges"
    assert expectation.warnings == ()


def test_atomic_number_electron_fallback_is_explicitly_warned() -> None:
    scientific = _scientific_module()
    molecule = Molecule(
        atoms=(Atom(1, (0.0, 0.0, 0.0)),),
        charge=0,
        multiplicity=2,
        metadata=CalculationMetadata("fixture"),
    )

    expectation = scientific.expected_electron_count(CalculationData(molecule), "total")

    assert expectation.value == 1.0
    assert expectation.source == "atomic-number fallback"
    assert any("atomic numbers" in warning for warning in expectation.warnings)


def test_effective_charge_and_ghost_helpers_use_nuclear_charge() -> None:
    scientific = _scientific_module()
    ecp = Atom(14, (0.0, 0.0, 0.0), nuclear_charge=4.0)
    ghost = Atom(8, (0.0, 0.0, 0.0), nuclear_charge=0.0)

    assert scientific.effective_nuclear_charge(ecp) == 4.0
    assert scientific.is_ghost_atom(ecp) is False
    assert scientific.is_ghost_atom(ghost) is True
