"""Mulliken and symmetric Löwdin atomic population analysis."""

from dataclasses import dataclass

import numpy as np

from ..model import DensityMatrix, Molecule


@dataclass(frozen=True, slots=True)
class PopulationResult:
    """Atomic electron populations and derived partial charges."""

    method: str
    electron_populations: tuple[float, ...]
    atomic_charges: tuple[float, ...]
    electron_count: float
    total_charge: float
    conservation_error: float


def _validated_inputs(
    molecule: Molecule,
    density_matrix: DensityMatrix,
    overlap_matrix: np.ndarray,
    ao_atom_indices: tuple[int, ...],
) -> tuple[np.ndarray, np.ndarray]:
    density = np.asarray(density_matrix.values, dtype=float)
    overlap = np.asarray(overlap_matrix, dtype=float)
    if overlap.ndim != 2 or density.shape != overlap.shape:
        raise ValueError("density and overlap matrices must have the same square shape")
    if not np.allclose(overlap, overlap.T, atol=1e-10, rtol=1e-10):
        raise ValueError("overlap matrix must be symmetric")
    if len(ao_atom_indices) != density.shape[0] or any(
        index < 0 or index >= len(molecule.atoms) for index in ao_atom_indices
    ):
        raise ValueError("AO-to-atom mapping must contain one valid atom index per basis function")
    return density, overlap


def _result(
    method: str,
    molecule: Molecule,
    ao_populations: np.ndarray,
    ao_atom_indices: tuple[int, ...],
) -> PopulationResult:
    populations = np.zeros(len(molecule.atoms), dtype=float)
    for population, atom_index in zip(ao_populations, ao_atom_indices, strict=True):
        populations[atom_index] += population
    nuclear_charges = np.asarray([atom.atomic_number for atom in molecule.atoms], dtype=float)
    atomic_charges = nuclear_charges - populations
    electron_count = float(np.sum(populations))
    total_charge = float(np.sum(atomic_charges))
    return PopulationResult(
        method=method,
        electron_populations=tuple(float(value) for value in populations),
        atomic_charges=tuple(float(value) for value in atomic_charges),
        electron_count=electron_count,
        total_charge=total_charge,
        conservation_error=abs(total_charge - molecule.charge),
    )


def mulliken_population(
    molecule: Molecule,
    density_matrix: DensityMatrix,
    overlap_matrix: np.ndarray,
    ao_atom_indices: tuple[int, ...],
) -> PopulationResult:
    """Partition ``diag(P S)`` over basis-function centers."""

    density, overlap = _validated_inputs(molecule, density_matrix, overlap_matrix, ao_atom_indices)
    ao_populations = np.diag(density @ overlap)
    return _result("Mulliken", molecule, ao_populations, ao_atom_indices)


def lowdin_population(
    molecule: Molecule,
    density_matrix: DensityMatrix,
    overlap_matrix: np.ndarray,
    ao_atom_indices: tuple[int, ...],
) -> PopulationResult:
    """Partition the symmetrically orthogonalized density ``S^1/2 P S^1/2``."""

    density, overlap = _validated_inputs(molecule, density_matrix, overlap_matrix, ao_atom_indices)
    eigenvalues, eigenvectors = np.linalg.eigh(overlap)
    if float(np.min(eigenvalues)) < -1e-10:
        raise ValueError("overlap matrix must be positive semidefinite")
    square_root = (eigenvectors * np.sqrt(np.clip(eigenvalues, 0.0, None))) @ eigenvectors.T
    ao_populations = np.diag(square_root @ density @ square_root)
    return _result("Lowdin", molecule, ao_populations, ao_atom_indices)
