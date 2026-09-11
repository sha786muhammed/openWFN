import math

import numpy as np
import pytest

from openwfn.analysis.orbitals import evaluate_orbital, frontier_orbitals
from openwfn.model import (
    Atom,
    BasisSet,
    BasisShell,
    CalculationMetadata,
    MolecularOrbitals,
    Molecule,
)


def _hydrogen() -> tuple[Molecule, BasisSet]:
    molecule = Molecule(
        (Atom(1, (0.0, 0.0, 0.0)),), 0, 2, CalculationMetadata("fixture")
    )
    basis = BasisSet((BasisShell(0, 0, (1.0,), (1.0,)),))
    return molecule, basis


def test_frontier_orbitals_reports_hartree_and_ev() -> None:
    orbitals = MolecularOrbitals(
        energies=(-0.5, 0.2),
        coefficients=((1.0, 0.0), (0.0, 1.0)),
        occupations=(2.0, 0.0),
        spin="restricted",
    )

    frontier = frontier_orbitals(orbitals)

    assert frontier.homo_index == 0
    assert frontier.lumo_index == 1
    assert frontier.gap_hartree == pytest.approx(0.7)
    assert frontier.gap_ev == pytest.approx(19.0479703722)


def test_evaluate_orbital_contracts_ao_values_with_selected_coefficients() -> None:
    molecule, basis = _hydrogen()
    orbitals = MolecularOrbitals(
        energies=(-0.5,),
        coefficients=((0.5,),),
        occupations=(1.0,),
        spin="alpha",
    )

    values = evaluate_orbital(
        molecule,
        basis,
        orbitals,
        orbital_index=0,
        points_bohr=np.array(((0.0, 0.0, 0.0),)),
    )

    assert values[0] == pytest.approx(0.5 * (2.0 / math.pi) ** 0.75, abs=1e-12)


def test_evaluate_orbital_rejects_index_out_of_range() -> None:
    molecule, basis = _hydrogen()
    orbitals = MolecularOrbitals((-0.5,), ((1.0,),), (1.0,), spin="alpha")

    with pytest.raises(IndexError, match="orbital index"):
        evaluate_orbital(molecule, basis, orbitals, 1, np.zeros((1, 3)))
