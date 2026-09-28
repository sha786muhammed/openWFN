"""Molecular-orbital inspection and spatial evaluation."""

from dataclasses import dataclass

import numpy as np

from ..model import BasisSet, MolecularOrbitals, Molecule
from .basis import evaluate_ao

HARTREE_TO_EV = 27.211386245981
OCCUPATION_THRESHOLD = 1e-8


@dataclass(frozen=True, slots=True)
class FrontierOrbitals:
    homo_index: int
    lumo_index: int
    homo_hartree: float
    lumo_hartree: float
    gap_hartree: float
    gap_ev: float
    spin: str


def frontier_orbitals(orbitals: MolecularOrbitals) -> FrontierOrbitals:
    occupied = [
        index
        for index, occupation in enumerate(orbitals.occupations)
        if occupation > OCCUPATION_THRESHOLD
    ]
    if not occupied:
        raise ValueError("HOMO is undefined because no occupied orbitals are present")
    homo = max(occupied, key=lambda index: orbitals.energies[index])
    homo_energy = orbitals.energies[homo]
    virtual = [
        index
        for index, occupation in enumerate(orbitals.occupations)
        if occupation <= OCCUPATION_THRESHOLD and orbitals.energies[index] > homo_energy
    ]
    if not virtual:
        raise ValueError("LUMO is unavailable because no unoccupied orbital lies above the HOMO")
    lumo = min(virtual, key=lambda index: orbitals.energies[index])
    gap = orbitals.energies[lumo] - homo_energy
    return FrontierOrbitals(
        homo_index=homo,
        lumo_index=lumo,
        homo_hartree=homo_energy,
        lumo_hartree=orbitals.energies[lumo],
        gap_hartree=gap,
        gap_ev=gap * HARTREE_TO_EV,
        spin=orbitals.spin,
    )


def evaluate_orbital(
    molecule: Molecule,
    basis: BasisSet,
    orbitals: MolecularOrbitals,
    orbital_index: int,
    points_bohr: np.ndarray,
) -> np.ndarray:
    if orbital_index < 0 or orbital_index >= len(orbitals.energies):
        raise IndexError(
            f"orbital index {orbital_index} is outside 0..{len(orbitals.energies) - 1}"
        )
    ao_values = evaluate_ao(basis, molecule, points_bohr)
    coefficients = np.asarray(orbitals.coefficients, dtype=float)
    if coefficients.shape[0] != ao_values.shape[1]:
        raise ValueError("orbital coefficient rows do not match evaluated basis functions")
    return ao_values @ coefficients[:, orbital_index]
