from dataclasses import replace

import numpy as np
import pytest

from openwfn.analysis.geometry import inertia_tensor, kabsch_rmsd, radius_of_gyration
from openwfn.model import Atom, CalculationMetadata, Molecule


def _water() -> Molecule:
    return Molecule(
        atoms=(
            Atom(8, (0.0, 0.0, 0.1)),
            Atom(1, (0.0, 0.8, -0.4)),
            Atom(1, (0.0, -0.8, -0.4)),
        ),
        charge=0,
        multiplicity=1,
        metadata=CalculationMetadata("fixture"),
    )


def test_inertia_tensor_is_translation_invariant() -> None:
    molecule = _water()
    translated = replace(
        molecule,
        atoms=tuple(
            Atom(
                atom.atomic_number,
                tuple(value + shift for value, shift in zip(atom.coordinates, (4.0, -2.0, 7.0))),
            )
            for atom in molecule.atoms
        ),
    )

    assert inertia_tensor(translated) == pytest.approx(inertia_tensor(molecule), abs=1e-12)


def test_radius_of_gyration_is_translation_invariant() -> None:
    molecule = _water()
    translated = replace(
        molecule,
        atoms=tuple(
            Atom(
                atom.atomic_number,
                (atom.coordinates[0] + 10.0, atom.coordinates[1], atom.coordinates[2]),
            )
            for atom in molecule.atoms
        ),
    )

    assert radius_of_gyration(translated) == pytest.approx(radius_of_gyration(molecule), abs=1e-12)


def test_kabsch_rmsd_removes_rotation_and_translation() -> None:
    reference = _water()
    rotation = np.array(((0.0, -1.0, 0.0), (1.0, 0.0, 0.0), (0.0, 0.0, 1.0)))
    transformed = replace(
        reference,
        atoms=tuple(
            Atom(
                atom.atomic_number,
                tuple(rotation @ np.asarray(atom.coordinates) + np.array((2.0, 3.0, -1.0))),
            )
            for atom in reference.atoms
        ),
    )

    assert kabsch_rmsd(reference, transformed) == pytest.approx(0.0, abs=1e-12)


def test_kabsch_rmsd_rejects_different_elements() -> None:
    reference = _water()
    changed = replace(
        reference, atoms=(Atom(7, reference.atoms[0].coordinates), *reference.atoms[1:])
    )

    with pytest.raises(ValueError, match="element ordering"):
        kabsch_rmsd(reference, changed)
